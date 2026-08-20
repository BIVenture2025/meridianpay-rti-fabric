"""The six stream DQ faults. See GENERATOR_SPEC.md section 6.

Applied to already-generated raw frames (auth_events, terminal_telemetry). Each
function returns the mutated frame plus a small dict of counts for the
Landing_Manifest.csv fault register -- a rule reporting zero faults injected
would be a bug in this file, not a clean run (CORE_RULES Appendix C 12: every
rule needs a floor that "nothing" cannot satisfy).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .core import rng_for, terminal_seed, SIM_NOW, AUTH_BACKFILL_DAYS

# Rule 5's cutover point -- re-exported here so any downstream consumer (a KQL
# function, a validation script) has one place to read it from, even though the
# cutover itself is applied inline during auth_events.py generation (the field
# has to not exist before the cutover, which is a generation-time decision, not
# a post-hoc mutation).
AUTH_WINDOW_START = SIM_NOW - pd.Timedelta(days=AUTH_BACKFILL_DAYS)
SCHEMA_CUTOVER = AUTH_WINDOW_START + 0.6 * (SIM_NOW - AUTH_WINDOW_START)


def duplicate_rows(df: pd.DataFrame, rng: np.random.Generator, frac: float = 0.004) -> tuple[pd.DataFrame, int]:
    """DQ rule 1: idempotent dedupe target. Exact duplicates of a random sample,
    identical natural key (e.g. auth_id / telemetry_id) and every other field."""
    n = max(1, int(round(len(df) * frac)))
    dup_idx = rng.choice(len(df), size=n, replace=False)
    dupes = df.iloc[dup_idx].copy()
    out = pd.concat([df, dupes], ignore_index=True)
    return out, n


def reorder_reversals(auth_df: pd.DataFrame, rng: np.random.Generator, frac: float = 0.02) -> tuple[pd.DataFrame, int]:
    """DQ rule 2: out-of-order resolution. For a sample of reversal/partial_capture
    rows, set ingest_time earlier than the original auth_id row's own ingest_time
    -- the resolution genuinely arrives first."""
    df = auth_df.copy()
    resolutions = df.index[df["event_type"].isin(["reversal", "partial_capture"])].to_numpy()
    if len(resolutions) == 0:
        return df, 0
    n = max(1, int(round(len(resolutions) * frac)))
    n = min(n, len(resolutions))
    chosen = rng.choice(resolutions, size=n, replace=False)

    # dedupe on auth_id before indexing -- rule 1 (duplicate_rows) runs first in
    # apply_all_dq_faults, so auth_id is not guaranteed unique here; duplicates
    # created by rule 1 are exact copies at this point, so any one of them
    # carries the correct ingest_time to look up.
    original_ingest = df.drop_duplicates(subset="auth_id").set_index("auth_id")["ingest_time"]
    applied = 0
    related_ids = df.loc[chosen, "related_auth_id"].to_numpy()
    lookup = original_ingest.reindex(related_ids)
    valid = ~lookup.isna().to_numpy()
    chosen_valid = chosen[valid]
    lookup_valid = lookup.to_numpy()[valid]
    if len(chosen_valid):
        lead_minutes = rng.uniform(1, 10, size=len(chosen_valid))
        new_ingest = (pd.to_datetime(lookup_valid) - pd.to_timedelta(lead_minutes, unit="m")).astype(
            df["ingest_time"].dtype
        )
        df.loc[chosen_valid, "ingest_time"] = new_ingest
        applied = len(chosen_valid)
    return df, applied


def late_burst(df: pd.DataFrame, rng: np.random.Generator, window_days: int, bursts_per_day: int = 15) -> tuple[pd.DataFrame, int]:
    """DQ rule 3: late arrival past the watermark. `bursts_per_day` (terminal, day)
    pairs get a 40-minute cluster of rows whose ingest_time is pushed 35-50
    minutes after event_time -- one buffered offline dump.

    Groups row positions by terminal_id ONCE so each of the (bursts_per_day *
    window_days) iterations only scans that terminal's own rows (~thousands),
    not the full multi-million-row frame -- the naive full-array mask per
    iteration is what made this the slowest step in the pipeline."""
    df = df.copy()
    event_time_np = pd.to_datetime(df["event_time"]).to_numpy()
    terminal_groups = df.groupby("terminal_id", sort=False, observed=True).indices
    terminals = np.array(list(terminal_groups.keys()))
    if len(terminals) == 0:
        return df, 0
    n_bursts = bursts_per_day * window_days
    applied = 0
    window_start = event_time_np.min()
    ingest_col = df.columns.get_loc("ingest_time")
    for _ in range(n_bursts):
        term = rng.choice(terminals)
        term_idx = terminal_groups[term]
        day_offset = rng.integers(0, window_days)
        hour_offset = rng.uniform(0, 24)
        burst_start = window_start + np.timedelta64(int(day_offset), "D") + np.timedelta64(
            int(hour_offset * 3600), "s"
        )
        burst_end = burst_start + np.timedelta64(40, "m")
        term_times = event_time_np[term_idx]
        mask = (term_times >= burst_start) & (term_times <= burst_end)
        idx = term_idx[mask]
        if len(idx) == 0:
            continue
        delay_min = rng.uniform(35, 50, size=len(idx))
        new_ingest = (pd.to_datetime(event_time_np[idx]) + pd.to_timedelta(delay_min, unit="m")).astype(
            df["ingest_time"].dtype
        )
        df.iloc[idx, ingest_col] = new_ingest
        applied += len(idx)
    return df, applied


def clock_skew(df: pd.DataFrame, master_seed: int | None = None) -> tuple[pd.DataFrame, int]:
    """DQ rule 4: device clock skew. Each terminal draws one fixed offset in
    [-5, +5] minutes, seeded per terminal (stable across its whole history and
    identical whichever route -- backfill or live-replay -- generates it), and
    that offset is applied to event_time. ingest_time is left as the
    (unskewed) true arrival time, so the two columns now genuinely diverge."""
    df = df.copy()
    terminals = df["terminal_id"].unique()
    offsets = {}
    for t in terminals:
        seed = terminal_seed(str(t), master_seed) if master_seed is not None else terminal_seed(str(t))
        local_rng = np.random.default_rng(seed)
        offsets[t] = float(local_rng.uniform(-5, 5))
    offset_minutes = df["terminal_id"].map(offsets).to_numpy()
    new_event_time = (pd.to_datetime(df["event_time"]) + pd.to_timedelta(offset_minutes, unit="m")).astype(
        df["event_time"].dtype
    )
    df["event_time"] = new_event_time
    applied = int((offset_minutes != 0).sum())
    return df, applied


def cold_path_gap(df: pd.DataFrame, rng: np.random.Generator, key_col: str, n: int = 50):
    """DQ rule 6: hot-vs-cold reconciliation. The cold-path (Lakehouse) copy
    deliberately excludes `n` rows that the hot-path (Eventhouse) export
    includes, so the reconciliation check (row count and summed amount, per
    stream) has a genuine, known, non-zero discrepancy to find. Returns
    (hot_df, cold_df, excluded_keys_df)."""
    n = min(n, len(df))
    excl_idx = rng.choice(len(df), size=n, replace=False)
    excluded_keys = df.iloc[excl_idx][[key_col]].copy()
    cold_df = df.drop(df.index[excl_idx]).reset_index(drop=True)
    return df, cold_df, excluded_keys


def apply_all_dq_faults(auth_events: pd.DataFrame, telemetry: pd.DataFrame, master_seed: int | None = None):
    """Orchestrates rules 1-4 and 6 against both raw streams (rule 5 is applied
    at generation time in auth_events.py -- see SCHEMA_CUTOVER above). Returns
    (auth_hot, auth_cold, telemetry_hot, telemetry_cold, fault_log,
    cold_exclusions) where fault_log is the per-rule count register that lands
    in Landing_Manifest.csv."""
    rng = rng_for("dq_faults", master_seed) if master_seed is not None else rng_for("dq_faults")

    auth_events, n_dup_auth = duplicate_rows(auth_events, rng, frac=0.004)
    auth_events, n_reorder = reorder_reversals(auth_events, rng, frac=0.02)
    auth_events, n_late_auth = late_burst(auth_events, rng, window_days=AUTH_BACKFILL_DAYS, bursts_per_day=15)
    auth_events, n_skew_auth = clock_skew(auth_events, master_seed)

    telemetry, n_dup_tel = duplicate_rows(telemetry, rng, frac=0.004)
    telemetry, n_late_tel = late_burst(telemetry, rng, window_days=30, bursts_per_day=15)
    telemetry, n_skew_tel = clock_skew(telemetry, master_seed)

    auth_hot, auth_cold, auth_excl = cold_path_gap(auth_events, rng, "auth_id", n=50)
    tel_hot, tel_cold, tel_excl = cold_path_gap(telemetry, rng, "telemetry_id", n=50)

    fault_log = {
        "rule1_duplicate_auth": n_dup_auth,
        "rule1_duplicate_telemetry": n_dup_tel,
        "rule2_reorder_reversals": n_reorder,
        "rule3_late_burst_auth": n_late_auth,
        "rule3_late_burst_telemetry": n_late_tel,
        "rule4_clock_skew_auth_terminals_affected": n_skew_auth,
        "rule4_clock_skew_telemetry_terminals_affected": n_skew_tel,
        "rule5_schema_cutover_applied_at": str(SCHEMA_CUTOVER),
        "rule6_cold_path_gap_auth": len(auth_excl),
        "rule6_cold_path_gap_telemetry": len(tel_excl),
    }
    cold_exclusions = {"auth_events": auth_excl, "terminal_telemetry": tel_excl}
    return auth_hot, auth_cold, tel_hot, tel_cold, fault_log, cold_exclusions
