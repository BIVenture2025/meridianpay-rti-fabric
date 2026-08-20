"""Per-store trading-hours calendar. See GENERATOR_SPEC.md section 3.

Produces dim_store_calendar (flat table, for KQL/Power BI joins) plus a compact
archetype map used internally by auth_events/telemetry/episodes for fast
vectorized "is this timestamp inside trading hours" checks.
"""

from __future__ import annotations

import pandas as pd
import numpy as np

from .core import rng_for

ARCHETYPES = {
    # name: (weight, [(open_hour, close_hour), ...] per normal day, closed_days)
    "standard_retail": (0.55, [(8, 22)], set()),
    "convenience_24h": (0.15, [(0, 24)], set()),
    "restricted_fnb": (0.20, [(11, 15), (18, 23)], set()),
    "weekday_only": (0.10, [(8, 20)], {6}),  # closed Sunday (day_of_week=6)
}

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def assign_archetypes(store_ids: list[str], master_seed: int | None = None) -> pd.Series:
    rng = rng_for("calendar_archetype", master_seed) if master_seed is not None else rng_for(
        "calendar_archetype"
    )
    names = list(ARCHETYPES.keys())
    weights = [ARCHETYPES[n][0] for n in names]
    choice = rng.choice(names, size=len(store_ids), p=weights)
    return pd.Series(choice, index=store_ids, name="archetype")


def build_trading_hours(dim_store: pd.DataFrame, master_seed: int | None = None):
    """Returns (dim_store_calendar, archetype_map).

    dim_store_calendar: one row per (store_id, day_of_week, session_no) with
    open_time/close_time as HH:MM strings, or is_closed=True.
    archetype_map: store_id -> archetype name, for fast internal lookups.
    """
    store_ids = dim_store["store_id"].tolist()
    archetype_map = assign_archetypes(store_ids, master_seed)

    rows = []
    for store_id in store_ids:
        archetype = archetype_map[store_id]
        _, sessions, closed_days = ARCHETYPES[archetype]
        for dow in range(7):
            if dow in closed_days:
                rows.append(
                    {
                        "store_id": store_id,
                        "day_of_week": dow,
                        "day_name": DAY_NAMES[dow],
                        "session_no": 1,
                        "is_closed": True,
                        "open_time": None,
                        "close_time": None,
                    }
                )
                continue
            for session_no, (open_h, close_h) in enumerate(sessions, start=1):
                rows.append(
                    {
                        "store_id": store_id,
                        "day_of_week": dow,
                        "day_name": DAY_NAMES[dow],
                        "session_no": session_no,
                        "is_closed": False,
                        "open_time": f"{open_h:02d}:00",
                        "close_time": f"{close_h:02d}:00" if close_h < 24 else "24:00",
                    }
                )
    dim_store_calendar = pd.DataFrame(rows)
    return dim_store_calendar, archetype_map


def is_trading_hours(store_id: str, timestamp: "pd.Timestamp", archetype_map: pd.Series) -> bool:
    """Scalar helper -- used by episode injection when it needs to bias a single
    window (e.g. reflex-2 terminal_compromise preferring out-of-hours). Bulk
    generation uses is_trading_hours_vec instead for speed."""
    archetype = archetype_map[store_id]
    _, sessions, closed_days = ARCHETYPES[archetype]
    dow = timestamp.weekday()
    if dow in closed_days:
        return False
    hour = timestamp.hour + timestamp.minute / 60.0
    return any(open_h <= hour < close_h for open_h, close_h in sessions)


def is_trading_hours_vec(store_ids: np.ndarray, timestamps: pd.DatetimeIndex, archetype_map: pd.Series) -> np.ndarray:
    """Vectorized version for whole-frame generation."""
    archetypes = archetype_map.reindex(store_ids).to_numpy()
    dows = timestamps.weekday.to_numpy()
    hours = timestamps.hour.to_numpy() + timestamps.minute.to_numpy() / 60.0

    result = np.zeros(len(store_ids), dtype=bool)
    for name, (_, sessions, closed_days) in ARCHETYPES.items():
        mask = archetypes == name
        if not mask.any():
            continue
        not_closed = ~np.isin(dows, list(closed_days)) if closed_days else np.ones(len(store_ids), dtype=bool)
        in_session = np.zeros(len(store_ids), dtype=bool)
        for open_h, close_h in sessions:
            in_session |= (hours >= open_h) & (hours < close_h)
        result |= mask & not_closed & in_session
    return result
