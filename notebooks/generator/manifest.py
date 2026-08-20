"""Landing_Manifest.csv. See GENERATOR_SPEC.md section 7.

run_id is a deterministic label, never a wall-clock stamp -- that is what keeps
this file byte-identical across reproducibility runs. Real wall-clock provenance
belongs in _run_meta.json, written by the caller outside this tree.
"""

from __future__ import annotations

import json

import pandas as pd

from .core import GENERATOR_VERSION, MASTER_SEED

TIME_COLUMN = {
    "auth_events": "event_time",
    "terminal_telemetry": "event_time",
    "dispute_events": "dispute_time",
    "ground_truth": "window_start",
    "dim_merchant": None,
    "dim_store": None,
    "dim_terminal": None,
    "dim_issuer": None,
    "dim_store_calendar": None,
}


def build_landing_manifest(
    streams: dict[str, pd.DataFrame],
    run_id: str,
    fault_log: dict | None = None,
    master_seed: int | None = None,
) -> pd.DataFrame:
    rows = []
    episode_counts = None
    if "ground_truth" in streams and len(streams["ground_truth"]):
        episode_counts = streams["ground_truth"]["episode_type"].value_counts().to_dict()

    for name, df in streams.items():
        time_col = TIME_COLUMN.get(name)
        if time_col and len(df):
            min_t = str(df[time_col].min())
            max_t = str(df[time_col].max())
        else:
            min_t = ""
            max_t = ""
        rows.append(
            {
                "stream_name": name,
                "row_count": len(df),
                "min_event_time": min_t,
                "max_event_time": max_t,
                "generator_version": GENERATOR_VERSION,
                "master_seed": master_seed if master_seed is not None else MASTER_SEED,
                "run_id": run_id,
                "fault_rules_applied": json.dumps(fault_log, sort_keys=True) if fault_log and name in (
                    "auth_events",
                    "terminal_telemetry",
                ) else "",
                "episode_count_by_type": json.dumps(episode_counts, sort_keys=True)
                if episode_counts and name == "ground_truth"
                else "",
            }
        )
    manifest = pd.DataFrame(rows).sort_values("stream_name").reset_index(drop=True)
    return manifest
