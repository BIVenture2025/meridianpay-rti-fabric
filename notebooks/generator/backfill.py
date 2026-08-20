"""ENTRY POINT 1 -- notebook backfill route. See GENERATOR_SPEC.md section 8.

This is what would run inside a Fabric notebook against OneLake; here it writes
to local disk so it can be developed, tested and diff-proved for reproducibility
before anything touches a live workspace. Everything under --out is what the
diff -rq reproducibility proof compares -- wall-clock run provenance is written
to a sidecar OUTSIDE that tree (<out>_meta.json), never inside it.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generator.core import GENERATOR_VERSION, MASTER_SEED
from generator.estate import build_dim_estate
from generator.trading_calendar import build_trading_hours
from generator.episodes import inject_episodes
from generator.auth_events import generate_auth_events
from generator.telemetry import generate_telemetry
from generator.disputes import generate_disputes
from generator.dq_faults import apply_all_dq_faults
from generator.manifest import build_landing_manifest
from generator.schemas import SCHEMAS


def _write_parquet(df: pd.DataFrame, path: str, schema_name: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    schema = SCHEMAS[schema_name]
    df = df[[f.name for f in schema]].copy()
    # floor every timestamp column to microsecond resolution as a final safety
    # net -- some columns accumulate ns-precision noise from float-seconds
    # Timedelta arithmetic upstream, which pyarrow's safe cast to timestamp('us')
    # rejects rather than silently truncates.
    for field in schema:
        if pa.types.is_timestamp(field.type) and field.name in df.columns:
            df[field.name] = pd.to_datetime(df[field.name]).dt.floor("us")
    # cast explicitly against the named schema (single source of truth for
    # column order/types) rather than letting pyarrow infer types from pandas,
    # which is one of the things that makes the file non-reproducible.
    table = pa.Table.from_pandas(df, schema=schema, preserve_index=False)
    pq.write_table(table, path, compression="snappy", use_dictionary=True, write_statistics=True)


def run(out_dir: str, run_id: str, master_seed: int = MASTER_SEED) -> dict:
    os.makedirs(out_dir, exist_ok=True)

    dim_merchant, dim_store, dim_terminal, dim_issuer = build_dim_estate(master_seed)
    dim_store_calendar, archetype_map = build_trading_hours(dim_store, master_seed)
    ground_truth = inject_episodes(dim_terminal, dim_issuer, archetype_map, master_seed)

    auth_events = generate_auth_events(
        dim_merchant, dim_store, dim_terminal, dim_issuer, archetype_map, ground_truth, master_seed
    )
    telemetry = generate_telemetry(dim_terminal, ground_truth, master_seed)
    dispute_events = generate_disputes(auth_events, ground_truth, master_seed)

    auth_hot, auth_cold, tel_hot, tel_cold, fault_log, cold_exclusions = apply_all_dq_faults(
        auth_events, telemetry, master_seed
    )

    # hot path (Eventhouse-bound) and cold path (Lakehouse-bound, DQ rule 6 gap)
    _write_parquet(auth_hot, os.path.join(out_dir, "hot", "auth_events.parquet"), "auth_events")
    _write_parquet(auth_cold, os.path.join(out_dir, "cold", "auth_events.parquet"), "auth_events")
    _write_parquet(tel_hot, os.path.join(out_dir, "hot", "terminal_telemetry.parquet"), "terminal_telemetry")
    _write_parquet(tel_cold, os.path.join(out_dir, "cold", "terminal_telemetry.parquet"), "terminal_telemetry")

    _write_parquet(dispute_events, os.path.join(out_dir, "dispute_events.parquet"), "dispute_events")
    _write_parquet(ground_truth, os.path.join(out_dir, "ground_truth.parquet"), "ground_truth")
    _write_parquet(dim_merchant, os.path.join(out_dir, "dim_merchant.parquet"), "dim_merchant")
    _write_parquet(dim_store, os.path.join(out_dir, "dim_store.parquet"), "dim_store")
    _write_parquet(dim_terminal, os.path.join(out_dir, "dim_terminal.parquet"), "dim_terminal")
    _write_parquet(dim_issuer, os.path.join(out_dir, "dim_issuer.parquet"), "dim_issuer")
    _write_parquet(dim_store_calendar, os.path.join(out_dir, "dim_store_calendar.parquet"), "dim_store_calendar")

    excl_dir = os.path.join(out_dir, "_cold_path_exclusions")
    os.makedirs(excl_dir, exist_ok=True)
    for stream_name, excl_df in cold_exclusions.items():
        excl_df.to_csv(os.path.join(excl_dir, f"{stream_name}_excluded.csv"), index=False)

    streams_for_manifest = {
        "auth_events": auth_hot,
        "terminal_telemetry": tel_hot,
        "dispute_events": dispute_events,
        "ground_truth": ground_truth,
        "dim_merchant": dim_merchant,
        "dim_store": dim_store,
        "dim_terminal": dim_terminal,
        "dim_issuer": dim_issuer,
        "dim_store_calendar": dim_store_calendar,
    }
    manifest = build_landing_manifest(streams_for_manifest, run_id, fault_log, master_seed)
    manifest.to_csv(os.path.join(out_dir, "Landing_Manifest.csv"), index=False)

    counts = {name: len(df) for name, df in streams_for_manifest.items()}
    counts["auth_events_cold"] = len(auth_cold)
    counts["terminal_telemetry_cold"] = len(tel_cold)
    return {"counts": counts, "fault_log": fault_log}


def main():
    parser = argparse.ArgumentParser(description="Project 25 backfill generator (notebook route)")
    parser.add_argument("--out", required=True, help="output directory (this whole tree is what diff -rq compares)")
    parser.add_argument("--run-id", default="backfill-v1", help="deterministic run label, never a timestamp")
    parser.add_argument("--seed", type=int, default=MASTER_SEED)
    args = parser.parse_args()

    result = run(args.out, args.run_id, args.seed)

    # wall-clock provenance sidecar, written OUTSIDE --out on purpose
    meta_path = args.out.rstrip("/\\") + "_meta.json"

    with open(meta_path, "w") as f:
        json.dump(
            {
                "generator_version": GENERATOR_VERSION,
                "master_seed": args.seed,
                "run_id": args.run_id,
                "wall_clock_started_note": "written outside the diffed --out tree by design",
                "counts": result["counts"],
            },
            f,
            indent=2,
            default=str,
        )

    print(json.dumps(result["counts"], indent=2))
    print(f"Wrote manifest and {sum(result['counts'].values())} total rows to {args.out}")
    print(f"Run metadata (outside the diffed tree): {meta_path}")


if __name__ == "__main__":
    main()
