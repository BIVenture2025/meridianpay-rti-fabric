"""Seed, version and RNG-factory constants. See GENERATOR_SPEC.md section 1.

Hard rule enforced by convention across this whole package: no function that
contributes to an output row may call datetime.now(), time.time() or the stdlib
`random` module. The simulation clock (SIM_NOW) is a fixed constant. Wall-clock
provenance belongs only in the _run_meta.json sidecar, written outside the
reproducibility-diffed output tree.
"""

from __future__ import annotations

import hashlib
import datetime as _dt

import numpy as np

GENERATOR_VERSION = "1.0.0"
MASTER_SEED = 250817  # date this spec was frozen (YYMMDD), documented not arbitrary

# Entirely synthetic simulation "now". The 90-day auth backfill window and the
# 30-day telemetry backfill window are both defined relative to this constant.
# All timestamps in this package are UTC by convention and stored tz-naive
# (documented once, here, rather than carrying a tz object through every
# vectorized numpy/pandas operation).
SIM_NOW = _dt.datetime(2026, 8, 17, 0, 0, 0)

AUTH_BACKFILL_DAYS = 90
TELEMETRY_BACKFILL_DAYS = 30


def stream_seed(stream_name: str, master_seed: int = MASTER_SEED) -> int:
    """Stable, deterministic per-stream seed derived from (master_seed, stream_name).

    Using a hash rather than e.g. `master_seed + len(stream_name)` means every
    stream is independently reproducible regardless of what order callers ask
    for RNGs in -- important once backfill.py and live_replay.py run as separate
    processes that may not touch streams in the same sequence.
    """
    digest = hashlib.sha256(f"{master_seed}:{stream_name}".encode("ascii")).digest()
    # numpy Generator seeds want a non-negative int < 2**32 for readability in logs;
    # take the low 32 bits of the digest.
    return int.from_bytes(digest[:4], "big")


def rng_for(stream_name: str, master_seed: int = MASTER_SEED) -> np.random.Generator:
    """One independent PCG64 Generator per logical stream. Never share a global RNG."""
    return np.random.default_rng(stream_seed(stream_name, master_seed))


def terminal_seed(terminal_id: str, master_seed: int = MASTER_SEED) -> int:
    """Per-terminal deterministic seed, used for e.g. the fixed clock-skew offset
    (DQ rule 4) so the same terminal gets the same offset in every run and in
    both the backfill and live-replay routes."""
    return stream_seed(f"terminal:{terminal_id}", master_seed)
