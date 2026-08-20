"""Injected fraud/operational episodes -> ground_truth. See GENERATOR_SPEC.md section 5.

Runs BEFORE the raw streams are generated. auth_events.py / telemetry.py read the
returned episode list and bias their output inside each window so the episode is
actually detectable, not just labelled.
"""

from __future__ import annotations

import uuid

import pandas as pd
import numpy as np

from .core import rng_for, SIM_NOW, AUTH_BACKFILL_DAYS, TELEMETRY_BACKFILL_DAYS
from .trading_calendar import is_trading_hours, ARCHETYPES

N_CARD_TESTING = 40
N_TERMINAL_COMPROMISE = 25
N_ISSUER_DEGRADATION = 12
N_TERMINAL_DARK = 60

AUTH_WINDOW_START = SIM_NOW - pd.Timedelta(days=AUTH_BACKFILL_DAYS)
TELEMETRY_WINDOW_START = SIM_NOW - pd.Timedelta(days=TELEMETRY_BACKFILL_DAYS)


def _episode_id(rng: np.random.Generator) -> str:
    # deterministic-looking id built from the seeded RNG, not uuid4 (which is
    # not seedable) -- draw 16 random hex nibbles from the seeded generator.
    return "EP-" + "".join(f"{rng.integers(0, 16):x}" for _ in range(12))


def _random_ts(rng: np.random.Generator, start: pd.Timestamp, end: pd.Timestamp) -> pd.Timestamp:
    span_seconds = (end - start).total_seconds()
    offset = rng.uniform(0, span_seconds)
    return start + pd.Timedelta(seconds=offset)


def inject_episodes(dim_terminal: pd.DataFrame, dim_issuer: pd.DataFrame, archetype_map: pd.Series, master_seed: int | None = None):
    """Returns a ground_truth DataFrame. Row order is deterministic for a given seed."""
    rng = rng_for("episodes", master_seed) if master_seed is not None else rng_for("episodes")

    terminal_to_store = dim_terminal.set_index("terminal_id")["store_id"]
    terminal_ids = dim_terminal["terminal_id"].to_numpy()
    issuer_bins = dim_issuer["issuer_bin"].to_numpy()

    rows = []

    # 1. card_testing_burst -- any time in the 90-day auth window
    for _ in range(N_CARD_TESTING):
        term_id = rng.choice(terminal_ids)
        start = _random_ts(rng, AUTH_WINDOW_START, SIM_NOW - pd.Timedelta(minutes=20))
        duration_min = int(rng.integers(5, 16))
        end = start + pd.Timedelta(minutes=duration_min)
        row_count = int(rng.integers(15, 41))
        decline_target = float(rng.uniform(0.6, 0.9))
        rows.append(
            {
                "episode_id": _episode_id(rng),
                "episode_type": "card_testing_burst",
                "affected_entity_type": "terminal",
                "affected_entity_id": term_id,
                "window_start": start,
                "window_end": end,
                "intensity_param_1": float(row_count),
                "intensity_param_2": decline_target,
                "row_count_hint": row_count,
            }
        )

    # 2. terminal_compromise -- restricted to the telemetry window (last 30 days)
    #    so both the tamper-flag telemetry signal and the auth decline-rate
    #    signal co-occur. Biased 70% toward starting outside trading hours.
    for _ in range(N_TERMINAL_COMPROMISE):
        term_id = rng.choice(terminal_ids)
        store_id = terminal_to_store[term_id]
        prefer_after_hours = rng.random() < 0.7
        # try a handful of candidate starts, keep the first that matches the bias
        start = None
        for _attempt in range(8):
            candidate = _random_ts(rng, TELEMETRY_WINDOW_START, SIM_NOW - pd.Timedelta(hours=6))
            in_hours = is_trading_hours(store_id, candidate, archetype_map)
            if prefer_after_hours and not in_hours:
                start = candidate
                break
            if not prefer_after_hours and in_hours:
                start = candidate
                break
        if start is None:
            start = _random_ts(rng, TELEMETRY_WINDOW_START, SIM_NOW - pd.Timedelta(hours=6))
        duration_hours = float(rng.uniform(2, 6))
        end = start + pd.Timedelta(hours=duration_hours)
        decline_step = float(rng.uniform(0.20, 0.40))
        rows.append(
            {
                "episode_id": _episode_id(rng),
                "episode_type": "terminal_compromise",
                "affected_entity_type": "terminal",
                "affected_entity_id": term_id,
                "window_start": start,
                "window_end": end,
                "intensity_param_1": decline_step,
                "intensity_param_2": duration_hours,
                "row_count_hint": 0,
            }
        )

    # 3. issuer_degradation -- any time in the 90-day auth window
    for _ in range(N_ISSUER_DEGRADATION):
        issuer_bin = rng.choice(issuer_bins)
        start = _random_ts(rng, AUTH_WINDOW_START, SIM_NOW - pd.Timedelta(hours=8))
        duration_hours = float(rng.uniform(3, 8))
        end = start + pd.Timedelta(hours=duration_hours)
        baseline_approval = float(rng.uniform(0.85, 0.95))
        drop_pct = float(rng.uniform(0.15, 0.35))
        rows.append(
            {
                "episode_id": _episode_id(rng),
                "episode_type": "issuer_degradation",
                "affected_entity_type": "issuer",
                "affected_entity_id": issuer_bin,
                "window_start": start,
                "window_end": end,
                "intensity_param_1": baseline_approval,
                "intensity_param_2": drop_pct,
                "row_count_hint": 0,
            }
        )

    # 4. terminal_dark_outage -- must fall entirely inside a trading-hours
    #    session for that store's archetype, within the telemetry window.
    for _ in range(N_TERMINAL_DARK):
        term_id = rng.choice(terminal_ids)
        store_id = terminal_to_store[term_id]
        duration_min = int(rng.integers(20, 91))
        start = None
        for _attempt in range(12):
            candidate = _random_ts(rng, TELEMETRY_WINDOW_START, SIM_NOW - pd.Timedelta(hours=2))
            candidate_end = candidate + pd.Timedelta(minutes=duration_min)
            if is_trading_hours(store_id, candidate, archetype_map) and is_trading_hours(
                store_id, candidate_end, archetype_map
            ):
                start = candidate
                break
        if start is None:
            # fall back to a standard-hours window (11:00 local-naive UTC) on a
            # deterministic day offset so the episode is never silently dropped
            day_offset = int(rng.integers(0, TELEMETRY_BACKFILL_DAYS - 1))
            start = TELEMETRY_WINDOW_START + pd.Timedelta(days=day_offset, hours=11)
        end = start + pd.Timedelta(minutes=duration_min)
        rows.append(
            {
                "episode_id": _episode_id(rng),
                "episode_type": "terminal_dark_outage",
                "affected_entity_type": "terminal",
                "affected_entity_id": term_id,
                "window_start": start,
                "window_end": end,
                "intensity_param_1": float(duration_min),
                "intensity_param_2": 0.0,
                "row_count_hint": 0,
            }
        )

    ground_truth = pd.DataFrame(rows)
    # floor to microsecond resolution here so ns-precision noise from
    # pd.Timedelta(seconds=<float>) never leaks into later arithmetic (e.g.
    # np.datetime64(window_start) + timedelta64[us] in auth_events.py's
    # card_testing_burst sub-generation, which would otherwise silently
    # upcast the result to datetime64[ns] and fail the schema cast at write time)
    ground_truth["window_start"] = pd.to_datetime(ground_truth["window_start"]).dt.floor("us")
    ground_truth["window_end"] = pd.to_datetime(ground_truth["window_end"]).dt.floor("us")
    return ground_truth
