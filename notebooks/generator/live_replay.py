"""ENTRY POINT 2 -- local Python live-replay route. See GENERATOR_SPEC.md section 8.

Shares estate.py, calendar.py, episodes.py, schemas.py and dq_faults.py with
backfill.py -- the "what is true about this world" layer is identical between
the two routes, seeded from the same MASTER_SEED, so a terminal that is
terminal_dark in the backfill is the same terminal, same window, if replayed
live for that period. Only the iteration and the sink differ: this route walks
a short live window event-by-event at accelerated real time and posts each row
to a pluggable sink (a local JSONL file in dry-run mode, or an Eventstream
custom endpoint once Session 2's Job A/B creates one).

No Eventstream exists yet as of this session (contract Rev 3, gates C0/C2/C3/C4
still open at time of writing) -- --sink file is the only exercised path so
far. --sink eventstream is wired for when the endpoint exists, not tested here.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generator.core import GENERATOR_VERSION, MASTER_SEED, SIM_NOW
from generator.estate import build_dim_estate
from generator.trading_calendar import build_trading_hours
from generator.episodes import inject_episodes
from generator.auth_events import generate_auth_events, AUTH_WINDOW_START
from generator.telemetry import generate_telemetry
from generator.dq_faults import clock_skew


def _sink_file(path):
    f = open(path, "a")

    def _emit(stream: str, row: dict):
        f.write(json.dumps({"stream": stream, **row}, default=str) + "\n")
        f.flush()

    return _emit, f.close


def _sink_eventstream(endpoint_url: str):
    """Placeholder for the Eventstream custom endpoint sink. Not exercised until
    an Eventstream exists (Job A/B). Left as a clearly-marked stub rather than a
    silent no-op so it fails loudly if someone points --sink eventstream at a
    real run before this is implemented against a live connection string."""

    def _emit(stream: str, row: dict):
        raise NotImplementedError(
            "Eventstream sink not yet implemented -- no Eventstream exists as of "
            "Session 2 (gates C0/C2/C3/C4 still open). Use --sink file until Job A/B lands one."
        )

    return _emit, lambda: None


def run(minutes: int, speed: float, sink_kind: str, sink_path: str, master_seed: int = MASTER_SEED):
    dim_merchant, dim_store, dim_terminal, dim_issuer = build_dim_estate(master_seed)
    dim_store_calendar, archetype_map = build_trading_hours(dim_store, master_seed)
    ground_truth = inject_episodes(dim_terminal, dim_issuer, archetype_map, master_seed)

    # Generate ONLY the requested trailing window directly -- NOT the full
    # 90-day/30-day backfill sliced down afterward. estate/calendar/episodes
    # are still the exact same shared functions and seed as backfill.py (so a
    # terminal that is terminal_dark in the backfill is the same terminal, same
    # window, here too); only auth_events/telemetry are asked for a short
    # window so a live-replay run costs seconds, not the backfill's minutes.
    window_end = pd.Timestamp(SIM_NOW)
    window_start = window_end - pd.Timedelta(minutes=minutes)

    auth_events = generate_auth_events(
        dim_merchant,
        dim_store,
        dim_terminal,
        dim_issuer,
        archetype_map,
        ground_truth,
        master_seed,
        window_start=window_start,
        window_end=window_end,
    )
    telemetry = generate_telemetry(
        dim_terminal, ground_truth, master_seed, window_start=window_start, window_end=window_end
    )

    auth_events, _ = clock_skew(auth_events, master_seed)
    telemetry, _ = clock_skew(telemetry, master_seed)

    auth_slice = auth_events.sort_values("event_time")
    tel_slice = telemetry.sort_values("event_time")

    combined = pd.concat(
        [auth_slice.assign(_stream="auth_events"), tel_slice.assign(_stream="terminal_telemetry")]
    ).sort_values("event_time")

    if sink_kind == "file":
        emit, close = _sink_file(sink_path)
    elif sink_kind == "eventstream":
        emit, close = _sink_eventstream(sink_path)
    else:
        raise ValueError(f"unknown sink kind: {sink_kind}")

    prev_time = None
    emitted = 0
    for _, row in combined.iterrows():
        stream = row["_stream"]
        payload = row.drop(labels=["_stream"]).to_dict()
        if prev_time is not None:
            gap_seconds = (row["event_time"] - prev_time).total_seconds()
            # capped low: a handful of reversal/partial_capture rows can land up
            # to 24h after their original auth (see auth_events.py), which would
            # otherwise dominate wall-clock time in a dry run even at high speed
            sleep_for = min(max(gap_seconds / speed, 0), 0.25)
            time.sleep(sleep_for)
        emit(stream, payload)
        emitted += 1
        prev_time = row["event_time"]
    close()
    return emitted


def main():
    parser = argparse.ArgumentParser(description="Project 25 live-replay generator (local Python route)")
    parser.add_argument("--minutes", type=int, default=15, help="trailing window, in simulated minutes, to replay")
    parser.add_argument("--speed", type=float, default=60.0, help="replay speed multiplier, contract section 5 default 60x")
    parser.add_argument("--sink", choices=["file", "eventstream"], default="file")
    parser.add_argument("--sink-path", default="live_replay_output.jsonl")
    parser.add_argument("--seed", type=int, default=MASTER_SEED)
    args = parser.parse_args()

    emitted = run(args.minutes, args.speed, args.sink, args.sink_path, args.seed)
    print(f"Emitted {emitted} events to {args.sink} sink ({args.sink_path})")


if __name__ == "__main__":
    main()
