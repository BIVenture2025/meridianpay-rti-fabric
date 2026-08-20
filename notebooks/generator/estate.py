"""dim_estate hierarchy: Merchant -> Store -> Terminal, plus dim_issuer.

See GENERATOR_SPEC.md section 2, including the note that Issuer is resolved per
transaction rather than structurally nested under Terminal.
"""

from __future__ import annotations

import pandas as pd
import numpy as np

from .core import rng_for

N_MERCHANTS = 600
TARGET_STORES = 900
STORE_TOLERANCE = 0.03  # +/-3%, declared in the spec rather than silently rounded
TARGET_TERMINALS = 1500
N_ISSUERS = 24

MCC_POOL = [
    ("5411", "Grocery Stores"),
    ("5812", "Restaurants"),
    ("5541", "Fuel Stations"),
    ("5691", "Apparel"),
    ("5999", "Specialty Retail"),
    ("5912", "Pharmacies"),
    ("5814", "Fast Food"),
    ("5311", "Department Stores"),
    ("5732", "Electronics"),
    ("5261", "Garden Supply"),
    ("5651", "Family Clothing"),
    ("5942", "Book Stores"),
]

TIER_WEIGHTS = {"small": 0.60, "medium": 0.30, "large": 0.10}


def _merchant_tiers(rng: np.random.Generator) -> np.ndarray:
    tiers = list(TIER_WEIGHTS.keys())
    probs = list(TIER_WEIGHTS.values())
    return rng.choice(tiers, size=N_MERCHANTS, p=probs)


def _store_counts_per_merchant(tiers: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    counts = np.empty(N_MERCHANTS, dtype=int)
    for i, tier in enumerate(tiers):
        if tier == "small":
            counts[i] = 1
        elif tier == "medium":
            counts[i] = int(rng.poisson(2)) + 1
        else:  # large
            counts[i] = int(rng.poisson(4)) + 2
    return counts


def _fit_store_total(counts: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Deterministically nudge store counts so the total lands within
    TARGET_STORES +/- STORE_TOLERANCE. Adjustments always touch the merchants
    with the largest counts first, in a stable (index) order, so the result is
    reproducible for a given seed."""
    lo = int(TARGET_STORES * (1 - STORE_TOLERANCE))
    hi = int(TARGET_STORES * (1 + STORE_TOLERANCE))
    counts = counts.copy()
    order = np.argsort(-counts, kind="stable")  # largest first, stable order
    pos = 0
    while counts.sum() > hi:
        idx = order[pos % len(order)]
        if counts[idx] > 1:
            counts[idx] -= 1
        pos += 1
        if pos > 10 * len(order):
            break
    pos = 0
    while counts.sum() < lo:
        idx = order[pos % len(order)]
        counts[idx] += 1
        pos += 1
        if pos > 10 * len(order):
            break
    return counts


def _terminal_counts_per_store(n_stores: int, rng: np.random.Generator) -> np.ndarray:
    counts = rng.poisson(1.2, size=n_stores) + 1
    diff = TARGET_TERMINALS - int(counts.sum())
    if diff > 0:
        # pad the first `diff` stores (store_id ascending == array index order)
        for i in range(diff):
            counts[i % n_stores] += 1
    elif diff < 0:
        need = -diff
        # trim from largest stores first, never below 1 terminal
        order = np.argsort(-counts, kind="stable")
        i = 0
        while need > 0:
            idx = order[i % len(order)]
            if counts[idx] > 1:
                counts[idx] -= 1
                need -= 1
            i += 1
            if i > 20 * len(order):
                break
    return counts


def build_dim_estate(master_seed: int | None = None):
    """Returns (dim_merchant, dim_store, dim_terminal, dim_issuer) DataFrames,
    each terminal carrying its resolved merchant_id/store_id denormalised."""
    rng = rng_for("estate", master_seed) if master_seed is not None else rng_for("estate")

    tiers = _merchant_tiers(rng)
    mcc_idx = rng.integers(0, len(MCC_POOL), size=N_MERCHANTS)
    merchant_ids = [f"MER-{i+1:06d}" for i in range(N_MERCHANTS)]
    dim_merchant = pd.DataFrame(
        {
            "merchant_id": merchant_ids,
            "merchant_tier": tiers,
            "mcc": [MCC_POOL[j][0] for j in mcc_idx],
            "mcc_description": [MCC_POOL[j][1] for j in mcc_idx],
        }
    )

    store_counts = _store_counts_per_merchant(tiers, rng)
    store_counts = _fit_store_total(store_counts, rng)

    store_rows = []
    store_seq = 0
    for m_idx, m_id in enumerate(merchant_ids):
        for _ in range(int(store_counts[m_idx])):
            store_seq += 1
            store_rows.append(
                {
                    "store_id": f"STR-{store_seq:06d}",
                    "merchant_id": m_id,
                }
            )
    dim_store = pd.DataFrame(store_rows)
    n_stores = len(dim_store)

    terminal_counts = _terminal_counts_per_store(n_stores, rng)

    term_rows = []
    term_seq = 0
    for s_idx, store_row in dim_store.iterrows():
        for _ in range(int(terminal_counts[s_idx])):
            term_seq += 1
            term_rows.append(
                {
                    "terminal_id": f"TRM-{term_seq:06d}",
                    "store_id": store_row["store_id"],
                    "merchant_id": store_row["merchant_id"],
                }
            )
    dim_terminal = pd.DataFrame(term_rows)

    issuer_ids = [f"ISS-{i+1:03d}" for i in range(N_ISSUERS)]
    issuer_bins = [f"{400000 + i * 137}" for i in range(N_ISSUERS)]  # synthetic BIN-shaped strings
    dim_issuer = pd.DataFrame(
        {
            "issuer_id": issuer_ids,
            "issuer_bin": issuer_bins,
            "issuer_name": [f"Issuer Bank {i+1:02d}" for i in range(N_ISSUERS)],
        }
    )

    return dim_merchant, dim_store, dim_terminal, dim_issuer
