"""auth_events raw stream generator. See GENERATOR_SPEC.md sections 2 and 4.1.

Vectorized: per-terminal timestamp assignment uses rejection sampling against
trading hours (fast, ~1,500 terminal-level batches) rather than a per-event or
per-terminal-day Python loop.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .core import rng_for, SIM_NOW, AUTH_BACKFILL_DAYS
from .trading_calendar import is_trading_hours_vec, ARCHETYPES

AUTH_WINDOW_START = SIM_NOW - pd.Timedelta(days=AUTH_BACKFILL_DAYS)
TARGET_PRIMARY_AUTHS = 4_954_128  # sized so + ~9% reversal/partial_capture rows lands at ~5.4m
SCHEMA_CUTOVER = AUTH_WINDOW_START + 0.6 * (SIM_NOW - AUTH_WINDOW_START)


def _as_ns(frame: pd.DataFrame) -> pd.DataFrame:
    """Force every datetime column to datetime64[ns].

    WHY THIS EXISTS (2026-08-18, Fabric runtime pandas 2.1.4 / numpy 1.26.4):
    pandas 2.x preserves non-nanosecond datetime64 units instead of coercing
    everything to ns the way pandas 1.x did. That creates an asymmetry in this
    module:

      * the main `df` timestamps come out of _rejection_sample_timestamps(),
        which seeds an accumulator as np.empty(0, dtype="datetime64[ns]") --
        so np.concatenate promotes the whole column to ns;
      * the injected card_testing_burst frames and the reversal frame build
        their timestamps directly as np.datetime64(x) + timedelta64[us],
        which stays at MICROSECOND resolution.

    pd.concat of a datetime64[ns] frame with a datetime64[us] frame then dies
    inside DatetimeArray._concat_same_type with a misleading shape error
    ("along dimension 1, the array at index 0 has size 4954129 and the array at
    index 1 has size 38" -- the 38 is just one burst's row count). pandas 3.0,
    which this generator was originally developed against, reconciles the units
    silently, which is why this never surfaced until the notebook ran on
    Fabric.

    us -> ns is exact and lossless, and backfill.py's _write_parquet floors
    every timestamp back to us against the declared pyarrow schema before
    writing -- so this normalisation cannot change a single output byte. That
    claim is not taken on trust: the full-scale Landing_Manifest.csv md5 is
    re-verified against the frozen cf1c270b8440bde4c779dd127550e168 on BOTH
    pandas 3.0 and pandas 2.1.4 after this change.
    """
    for col in frame.columns:
        if pd.api.types.is_datetime64_any_dtype(frame[col]):
            if frame[col].dtype != np.dtype("datetime64[ns]"):
                frame[col] = frame[col].astype("datetime64[ns]")
    return frame

DUTY_FRACTION = {
    "standard_retail": 14 / 24,
    "convenience_24h": 1.0,
    "restricted_fnb": 9 / 24,
    "weekday_only": (12 * 6) / (24 * 7),
}

POS_ENTRY_MODES = ["chip", "contactless", "magstripe"]
POS_ENTRY_WEIGHTS = [0.45, 0.45, 0.10]
DECLINE_REASONS = ["insufficient_funds", "suspected_fraud", "invalid_card", "issuer_unavailable", "expired_card"]


def _rejection_sample_timestamps(store_id, archetype, count, rng, window_start, window_end):
    if count == 0:
        return np.empty(0, dtype="datetime64[ns]")
    duty = DUTY_FRACTION[archetype]
    span_seconds = (window_end - window_start).total_seconds()
    kept = np.empty(0, dtype="datetime64[ns]")
    attempts = 0
    while kept.size < count and attempts < 8:
        remaining = count - kept.size
        oversample = int(remaining / max(duty, 0.05) * 1.3) + 20
        offsets = rng.uniform(0, max(span_seconds, 0.001), size=oversample)
        candidates = np.datetime64(window_start) + (offsets * 1e6).astype("timedelta64[us]")
        mask = is_trading_hours_vec(
            np.full(oversample, store_id), pd.DatetimeIndex(candidates), _ARCHETYPE_MAP_REF[0]
        )
        kept = np.concatenate([kept, candidates[mask]])
        attempts += 1
    if kept.size < count:
        if kept.size == 0:
            kept = np.array([np.datetime64(window_start)])
        pad_idx = rng.integers(0, kept.size, size=count - kept.size)
        kept = np.concatenate([kept, kept[pad_idx]])
    rng.shuffle(kept)
    return kept[:count]


# module-level mutable ref so _rejection_sample_timestamps can see the archetype
# map without threading it through every call (set once per generate_auth_events call)
_ARCHETYPE_MAP_REF = [None]


def generate_auth_events(
    dim_merchant,
    dim_store,
    dim_terminal,
    dim_issuer,
    archetype_map,
    ground_truth,
    master_seed=None,
    window_start=None,
    window_end=None,
    target_primary_total=None,
):
    """window_start/window_end/target_primary_total default to the full 90-day
    backfill window and TARGET_PRIMARY_AUTHS -- backfill.py's call is unchanged.
    live_replay.py passes a short trailing window directly (NOT a slice of a
    full 90-day generation) so a live-replay run costs seconds, not minutes;
    target_primary_total then defaults to a proportional share of the full
    total scaled by window length, so the live window has a realistic density
    rather than the full backfill's raw count."""
    rng = rng_for("auth_events", master_seed) if master_seed is not None else rng_for("auth_events")
    _ARCHETYPE_MAP_REF[0] = archetype_map

    if window_start is None:
        window_start = AUTH_WINDOW_START
    if window_end is None:
        window_end = SIM_NOW
    if target_primary_total is None:
        if window_start == AUTH_WINDOW_START and window_end == SIM_NOW:
            target_primary_total = TARGET_PRIMARY_AUTHS
        else:
            full_span = (SIM_NOW - AUTH_WINDOW_START).total_seconds()
            this_span = (window_end - window_start).total_seconds()
            target_primary_total = max(1, int(round(TARGET_PRIMARY_AUTHS * (this_span / full_span))))

    n_terminals = len(dim_terminal)
    terminal_ids = dim_terminal["terminal_id"].to_numpy()
    store_ids = dim_terminal["store_id"].to_numpy()
    merchant_ids = dim_terminal["merchant_id"].to_numpy()

    # per-terminal weight -> count, sums to target_primary_total
    weights = rng.lognormal(mean=0.0, sigma=0.6, size=n_terminals)
    weights = weights / weights.sum()
    counts = np.round(weights * target_primary_total).astype(int)
    counts = np.clip(counts, 0, None)

    merchant_mcc = dim_merchant.set_index("merchant_id")["mcc"]
    issuer_bins = dim_issuer["issuer_bin"].to_numpy()

    frames = []
    for i in range(n_terminals):
        term_id = terminal_ids[i]
        store_id = store_ids[i]
        merch_id = merchant_ids[i]
        n = int(counts[i])
        archetype = archetype_map[store_id]
        ts = _rejection_sample_timestamps(store_id, archetype, n, rng, window_start, window_end)
        frames.append(
            pd.DataFrame(
                {
                    "event_time": ts,
                    "terminal_id": term_id,
                    "store_id": store_id,
                    "merchant_id": merch_id,
                }
            )
        )
    df = pd.concat(frames, ignore_index=True)
    n_rows = len(df)

    df["auth_id"] = [f"AUTH-{x:010x}" for x in rng.integers(0, 2**40, size=n_rows)]
    df["event_type"] = "auth"
    df["related_auth_id"] = None
    df["ingest_time"] = df["event_time"]  # perturbed later by dq_faults.py
    df["issuer_bin"] = rng.choice(issuer_bins, size=n_rows)
    df["card_token"] = [f"TOK-{x:012x}" for x in rng.integers(0, 2**48, size=n_rows)]
    df["mcc"] = df["merchant_id"].map(merchant_mcc)
    df["currency"] = "MYR"
    df["amount"] = np.round(rng.lognormal(mean=3.6, sigma=0.9, size=n_rows), 2)  # centred ~ MYR 40-60
    df["pos_entry_mode"] = rng.choice(POS_ENTRY_MODES, size=n_rows, p=POS_ENTRY_WEIGHTS)
    df["is_card_present"] = rng.random(n_rows) < 0.95

    base_decline_prob = 0.08
    decline_roll = rng.random(n_rows)
    df["auth_result"] = np.where(decline_roll < base_decline_prob, "declined", "approved")
    decline_reason_choice = rng.choice(DECLINE_REASONS, size=n_rows)
    df["decline_reason"] = np.where(df["auth_result"] == "declined", decline_reason_choice, None)

    event_time_dt = pd.to_datetime(df["event_time"])
    is_v2 = event_time_dt >= SCHEMA_CUTOVER
    df["schema_version"] = np.where(is_v2, 2, 1)
    sca_roll = rng.random(n_rows) < 0.70
    df["sca_flag"] = np.where(is_v2, sca_roll, None)

    # --- episode overrides: terminal_compromise and issuer_degradation bias
    # baseline decline probability upward for rows that fall inside an active
    # episode window for the matching entity. ---
    if ground_truth is not None and len(ground_truth):
        tc = ground_truth[ground_truth["episode_type"] == "terminal_compromise"]
        for _, ep in tc.iterrows():
            in_window = (
                (df["terminal_id"] == ep["affected_entity_id"])
                & (event_time_dt >= ep["window_start"])
                & (event_time_dt <= ep["window_end"])
            )
            if in_window.any():
                extra_decline = rng.random(int(in_window.sum())) < ep["intensity_param_1"]
                idx = df.index[in_window]
                current = df.loc[idx, "auth_result"].to_numpy()
                new_result = np.where(extra_decline, "declined", current)
                df.loc[idx, "auth_result"] = new_result
                still_declined_no_reason = (new_result == "declined") & pd.isna(df.loc[idx, "decline_reason"])
                if still_declined_no_reason.any():
                    fill_idx = idx[still_declined_no_reason]
                    df.loc[fill_idx, "decline_reason"] = rng.choice(DECLINE_REASONS, size=len(fill_idx))

        idg = ground_truth[ground_truth["episode_type"] == "issuer_degradation"]
        for _, ep in idg.iterrows():
            in_window = (
                (df["issuer_bin"] == ep["affected_entity_id"])
                & (event_time_dt >= ep["window_start"])
                & (event_time_dt <= ep["window_end"])
            )
            if in_window.any():
                extra_decline = rng.random(int(in_window.sum())) < ep["intensity_param_2"]
                idx = df.index[in_window]
                current = df.loc[idx, "auth_result"].to_numpy()
                new_result = np.where(extra_decline, "declined", current)
                df.loc[idx, "auth_result"] = new_result
                still_declined_no_reason = (new_result == "declined") & pd.isna(df.loc[idx, "decline_reason"])
                if still_declined_no_reason.any():
                    fill_idx = idx[still_declined_no_reason]
                    df.loc[fill_idx, "decline_reason"] = "issuer_unavailable"

        # card_testing_burst: extra low-value rows, distinct tokens, elevated decline
        ctb = ground_truth[ground_truth["episode_type"] == "card_testing_burst"]
        extra_rows = []
        for _, ep in ctb.iterrows():
            n = int(ep["row_count_hint"])
            term_id = ep["affected_entity_id"]
            term_row = dim_terminal[dim_terminal["terminal_id"] == term_id].iloc[0]
            span = (ep["window_end"] - ep["window_start"]).total_seconds()
            offsets = rng.uniform(0, max(span, 1), size=n)
            ts = np.datetime64(ep["window_start"]) + (offsets * 1e6).astype("timedelta64[us]")
            decline_roll_ctb = rng.random(n) < ep["intensity_param_2"]
            sub = pd.DataFrame(
                {
                    "event_time": ts,
                    "terminal_id": term_id,
                    "store_id": term_row["store_id"],
                    "merchant_id": term_row["merchant_id"],
                    "auth_id": [f"AUTH-{x:010x}" for x in rng.integers(0, 2**40, size=n)],
                    "event_type": "auth",
                    "related_auth_id": None,
                    "issuer_bin": rng.choice(issuer_bins, size=n),
                    "card_token": [f"TOK-{x:012x}" for x in rng.integers(0, 2**48, size=n)],
                    "mcc": merchant_mcc.get(term_row["merchant_id"]),
                    "currency": "MYR",
                    "amount": np.round(rng.uniform(0.5, 4.99, size=n), 2),
                    "pos_entry_mode": rng.choice(POS_ENTRY_MODES, size=n, p=POS_ENTRY_WEIGHTS),
                    "is_card_present": True,
                    "auth_result": np.where(decline_roll_ctb, "declined", "approved"),
                }
            )
            sub["decline_reason"] = np.where(sub["auth_result"] == "declined", "suspected_fraud", None)
            sub["ingest_time"] = sub["event_time"]
            sub_dt = pd.to_datetime(sub["event_time"])
            sub_is_v2 = sub_dt >= SCHEMA_CUTOVER
            sub["schema_version"] = np.where(sub_is_v2, 2, 1)
            sub["sca_flag"] = np.where(sub_is_v2, rng.random(n) < 0.70, None)
            extra_rows.append(_as_ns(sub))
        if extra_rows:
            df = pd.concat([_as_ns(df)] + extra_rows, ignore_index=True)

    # --- reversal / partial_capture rows referencing approved 'auth' rows ---
    approved = df[(df["event_type"] == "auth") & (df["auth_result"] == "approved")]
    n_reversal_candidates = int(len(approved) * 0.09)
    if n_reversal_candidates > 0:
        sample = approved.sample(n=n_reversal_candidates, random_state=int(rng.integers(0, 2**31 - 1)))
        delay_minutes = rng.uniform(2, 24 * 60, size=len(sample))
        rev_event_time = pd.to_datetime(sample["event_time"]).to_numpy() + (
            delay_minutes * 60 * 1e6
        ).astype("timedelta64[us]")
        rev_type = rng.choice(["reversal", "partial_capture"], size=len(sample), p=[0.65, 0.35])
        rev_amount = np.where(
            rev_type == "partial_capture",
            np.round(sample["amount"].to_numpy() * rng.uniform(0.3, 0.9, size=len(sample)), 2),
            sample["amount"].to_numpy(),
        )
        rev_dt = pd.to_datetime(rev_event_time)
        rev_is_v2 = rev_dt >= SCHEMA_CUTOVER
        rev = pd.DataFrame(
            {
                "auth_id": [f"AUTH-{x:010x}" for x in rng.integers(0, 2**40, size=len(sample))],
                "event_type": rev_type,
                "related_auth_id": sample["auth_id"].to_numpy(),
                "event_time": rev_event_time,
                "ingest_time": rev_event_time,
                "terminal_id": sample["terminal_id"].to_numpy(),
                "store_id": sample["store_id"].to_numpy(),
                "merchant_id": sample["merchant_id"].to_numpy(),
                "issuer_bin": sample["issuer_bin"].to_numpy(),
                "card_token": sample["card_token"].to_numpy(),
                "amount": rev_amount,
                "currency": "MYR",
                "mcc": sample["mcc"].to_numpy(),
                "auth_result": "approved",
                "decline_reason": None,
                "pos_entry_mode": sample["pos_entry_mode"].to_numpy(),
                "is_card_present": sample["is_card_present"].to_numpy(),
                "schema_version": np.where(rev_is_v2, 2, 1),
                "sca_flag": np.where(rev_is_v2, rng.random(len(sample)) < 0.70, None),
            }
        )
        df = pd.concat([_as_ns(df), _as_ns(rev)], ignore_index=True)

    df["event_time"] = pd.to_datetime(df["event_time"])
    df["ingest_time"] = pd.to_datetime(df["ingest_time"])
    df["is_card_present"] = df["is_card_present"].astype(bool)
    df["schema_version"] = df["schema_version"].astype("int32")

    column_order = [
        "auth_id", "event_type", "related_auth_id", "event_time", "ingest_time",
        "terminal_id", "store_id", "merchant_id", "issuer_bin", "card_token",
        "amount", "currency", "mcc", "auth_result", "decline_reason",
        "pos_entry_mode", "is_card_present", "sca_flag", "schema_version",
    ]
    df = df[column_order].sort_values(["event_time", "auth_id"]).reset_index(drop=True)
    return df
