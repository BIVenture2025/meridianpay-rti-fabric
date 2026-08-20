"""Project 25 (Meridian Pay) synthetic data generator.

Single module shared by the notebook backfill route (backfill.py) and the local
Python live-replay route (live_replay.py). See ../GENERATOR_SPEC.md for the full
design. Nothing in this package may call datetime.now(), time.time() or the stdlib
`random` module for anything that ends up in an output row -- see core.py.
"""

from .core import GENERATOR_VERSION, MASTER_SEED, SIM_NOW

__all__ = ["GENERATOR_VERSION", "MASTER_SEED", "SIM_NOW"]
