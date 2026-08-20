"""dispute_events raw stream generator. See GENERATOR_SPEC.md sections 4.3 and 5's
maturity-cohort note.

A candidate auth becomes a dispute row only if its computed dispute_time
(event_time + Uniform(30, 60) days) falls at or before SIM_NOW. Auths inside the
T-30 -> T window mostly fail that test and simply produce no dispute row yet --
which is exactly the "awaiting grading" cohort the contract describes, modelled
structurally rather than flagged after the fact.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .core import rng_for, SIM_NOW

DISPUTE_RATE = 0.003  # ~0.3% of primary 'auth' rows, contract section 5
FRAUD_LINKED_SHARE = 0.70  # share of the dispute target preferentially drawn from episode-linked auths

DISPUTE_REASON_BASELINE = ["not_as_described", "duplicate_processing", "other", "fraud"]
DISPUTE_REASON_BASELINE_WEIGHTS = [0.35, 0.20, 0.25, 0.20]


def generate_disputes(auth_events: pd.DataFrame, ground_truth: pd.DataFrame, master_seed=None):
    rng = rng_for("disputes", master_seed) if master_seed is not None else rng_for("disputes")

    candidates = auth_events[
        (auth_events["event_type"] == "auth") & (auth_events["auth_result"] == "approved")
    ].reset_index(drop=True)
    n_candidates = len(candidates)
    target_n = int(round(DISPUTE_RATE * n_candidates))

    episode_linked_mask = np.zeros(n_candidates, dtype=bool)
    if ground_truth is not None and len(ground_truth):
        risky = ground_truth[ground_truth["episode_type"].isin(["card_testing_burst", "terminal_compromise"])]
        cand_term = candidates["terminal_id"].to_numpy()
        cand_time = candidates["event_time"].to_numpy()
        for _, ep in risky.iterrows():
            term_mask = cand_term == ep["affected_entity_id"]
            time_mask = (cand_time >= np.datetime64(ep["window_start"])) & (
                cand_time <= np.datetime64(ep["window_end"])
            )
            episode_linked_mask |= term_mask & time_mask

    linked_idx = np.flatnonzero(episode_linked_mask)
    unlinked_idx = np.flatnonzero(~episode_linked_mask)

    n_from_linked = min(int(target_n * FRAUD_LINKED_SHARE), len(linked_idx))
    n_from_unlinked = target_n - n_from_linked

    chosen_linked = rng.choice(linked_idx, size=n_from_linked, replace=False) if n_from_linked else np.empty(0, dtype=int)
    chosen_unlinked = (
        rng.choice(unlinked_idx, size=min(n_from_unlinked, len(unlinked_idx)), replace=False)
        if n_from_unlinked > 0
        else np.empty(0, dtype=int)
    )
    chosen_idx = np.concatenate([chosen_linked, chosen_unlinked]).astype(int)

    chosen = candidates.iloc[chosen_idx].reset_index(drop=True)
    n_chosen = len(chosen)

    lag_days = rng.uniform(30, 60, size=n_chosen)
    event_time_np = pd.to_datetime(chosen["event_time"]).to_numpy()
    dispute_time = event_time_np + (lag_days * 86400 * 1e6).astype("timedelta64[us]")

    matured_mask = dispute_time <= np.datetime64(SIM_NOW)
    chosen = chosen[matured_mask].reset_index(drop=True)
    dispute_time = dispute_time[matured_mask]
    is_linked = np.concatenate(
        [np.ones(n_from_linked, dtype=bool), np.zeros(len(chosen_unlinked), dtype=bool)]
    )[matured_mask] if n_chosen else np.array([], dtype=bool)
    n_final = len(chosen)

    reason = np.where(
        is_linked,
        "fraud",
        rng.choice(DISPUTE_REASON_BASELINE, size=n_final, p=DISPUTE_REASON_BASELINE_WEIGHTS),
    )
    outcome_roll = rng.random(n_final)
    cardholder_win_prob = np.where(reason == "fraud", 0.65, 0.40)
    outcome = np.where(outcome_roll < cardholder_win_prob, "cardholder_won", "merchant_won")

    df = pd.DataFrame(
        {
            "dispute_id": [f"DSP-{x:010x}" for x in rng.integers(0, 2**40, size=n_final)],
            "auth_id": chosen["auth_id"].to_numpy(),
            "dispute_time": pd.to_datetime(dispute_time),
            "dispute_reason": reason,
            "dispute_outcome": outcome,
            "amount": chosen["amount"].to_numpy(),
        }
    )
    return df.sort_values(["dispute_time", "dispute_id"]).reset_index(drop=True)
