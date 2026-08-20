"""terminal_telemetry raw stream generator. See GENERATOR_SPEC.md sections 2 and 4.2.

15-minute heartbeat x 1,500 terminals x 30 days = 4,320,000 candidate rows, minus
the rows removed inside terminal_dark_outage episode windows (the ABSENCE of a
heartbeat is the signal reflex 3 detects -- no row is emitted, not a flag).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .core import rng_for, SIM_NOW, TELEMETRY_BACKFILL_DAYS

TELEMETRY_WINDOW_START = SIM_NOW - pd.Timedelta(days=TELEMETRY_BACKFILL_DAYS)
HEARTBEAT_INTERVAL_MIN = 15
INTERVALS_PER_DAY = (24 * 60) // HEARTBEAT_INTERVAL_MIN  # 96


def generate_telemetry(dim_terminal, ground_truth, master_seed=None, window_start=None, window_end=None):
    """window_start/window_end default to the full 30-day backfill window --
    backfill.py's call is unchanged. live_replay.py passes a short trailing
    window directly (not a slice of a full 30-day generation), so the heartbeat
    grid built here is sized to that window, not the full backfill."""
    rng = rng_for("telemetry", master_seed) if master_seed is not None else rng_for("telemetry")

    if window_start is None:
        window_start = TELEMETRY_WINDOW_START
    if window_end is None:
        window_end = SIM_NOW

    n_terminals = len(dim_terminal)
    window_minutes = max(int((window_end - window_start).total_seconds() // 60), 0)
    n_intervals = max(window_minutes // HEARTBEAT_INTERVAL_MIN, 1)

    terminal_ids = dim_terminal["terminal_id"].to_numpy()
    store_ids = dim_terminal["store_id"].to_numpy()
    merchant_ids = dim_terminal["merchant_id"].to_numpy()

    offsets_min = np.arange(n_intervals) * HEARTBEAT_INTERVAL_MIN
    base_times = np.datetime64(window_start) + offsets_min.astype("timedelta64[m]")

    # full terminal x interval grid, built once via repeat/tile (vectorized, no python loop)
    event_time = np.tile(base_times, n_terminals)
    terminal_id_col = np.repeat(terminal_ids, n_intervals)
    store_id_col = np.repeat(store_ids, n_intervals)
    merchant_id_col = np.repeat(merchant_ids, n_intervals)

    n_rows = len(event_time)
    df = pd.DataFrame(
        {
            "event_time": event_time,
            "terminal_id": terminal_id_col,
            "store_id": store_id_col,
            "merchant_id": merchant_id_col,
        }
    )

    # remove rows inside terminal_dark_outage windows -- the absence IS the signal
    if ground_truth is not None and len(ground_truth):
        outages = ground_truth[ground_truth["episode_type"] == "terminal_dark_outage"]
        drop_mask = np.zeros(n_rows, dtype=bool)
        for _, ep in outages.iterrows():
            term_mask = df["terminal_id"].to_numpy() == ep["affected_entity_id"]
            time_mask = (df["event_time"] >= ep["window_start"]) & (df["event_time"] <= ep["window_end"])
            drop_mask |= term_mask & time_mask.to_numpy()
        df = df[~drop_mask].reset_index(drop=True)
        n_rows = len(df)

        # tamper_flag=True for rows inside terminal_compromise windows
        tamper_mask = np.zeros(n_rows, dtype=bool)
        compromises = ground_truth[ground_truth["episode_type"] == "terminal_compromise"]
        for _, ep in compromises.iterrows():
            term_mask = df["terminal_id"].to_numpy() == ep["affected_entity_id"]
            time_mask = (df["event_time"] >= ep["window_start"]) & (df["event_time"] <= ep["window_end"])
            tamper_mask |= term_mask & time_mask.to_numpy()
    else:
        tamper_mask = np.zeros(n_rows, dtype=bool)

    df["tamper_flag"] = tamper_mask
    df["ingest_time"] = df["event_time"]  # perturbed later by dq_faults.py
    df["heartbeat_ok"] = rng.random(n_rows) > 0.01  # ~1% cosmetic hiccup, independent of tamper
    df["battery_pct"] = np.clip(rng.normal(70, 15, size=n_rows), 5, 100).round(1)
    df["signal_strength"] = np.clip(rng.normal(75, 12, size=n_rows), 10, 100).round(1)

    df["telemetry_id"] = [f"TEL-{x:010x}" for x in rng.integers(0, 2**40, size=n_rows)]
    df["schema_version"] = np.int32(1)  # telemetry has no schema-evolution field; kept for consistency
    df["event_time"] = pd.to_datetime(df["event_time"])
    df["ingest_time"] = pd.to_datetime(df["ingest_time"])

    column_order = [
        "telemetry_id", "event_time", "ingest_time", "terminal_id", "store_id",
        "merchant_id", "heartbeat_ok", "tamper_flag", "battery_pct",
        "signal_strength", "schema_version",
    ]
    df = df[column_order].sort_values(["event_time", "terminal_id"]).reset_index(drop=True)
    return df
