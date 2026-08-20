"""PyArrow schemas -- single source of truth for column order/types across the
generator, the notebook backfill route and the Parquet files a KQL .ingest or a
Lakehouse shortcut will read. See GENERATOR_SPEC.md section 4.
"""

from __future__ import annotations

import pyarrow as pa

AUTH_EVENTS_SCHEMA = pa.schema(
    [
        ("auth_id", pa.string()),
        ("event_type", pa.string()),
        ("related_auth_id", pa.string()),
        ("event_time", pa.timestamp("us")),
        ("ingest_time", pa.timestamp("us")),
        ("terminal_id", pa.string()),
        ("store_id", pa.string()),
        ("merchant_id", pa.string()),
        ("issuer_bin", pa.string()),
        ("card_token", pa.string()),
        ("amount", pa.float64()),
        ("currency", pa.string()),
        ("mcc", pa.string()),
        ("auth_result", pa.string()),
        ("decline_reason", pa.string()),
        ("pos_entry_mode", pa.string()),
        ("is_card_present", pa.bool_()),
        ("sca_flag", pa.bool_()),
        ("schema_version", pa.int32()),
    ]
)

TERMINAL_TELEMETRY_SCHEMA = pa.schema(
    [
        ("telemetry_id", pa.string()),
        ("event_time", pa.timestamp("us")),
        ("ingest_time", pa.timestamp("us")),
        ("terminal_id", pa.string()),
        ("store_id", pa.string()),
        ("merchant_id", pa.string()),
        ("heartbeat_ok", pa.bool_()),
        ("tamper_flag", pa.bool_()),
        ("battery_pct", pa.float64()),
        ("signal_strength", pa.float64()),
        ("schema_version", pa.int32()),
    ]
)

DISPUTE_EVENTS_SCHEMA = pa.schema(
    [
        ("dispute_id", pa.string()),
        ("auth_id", pa.string()),
        ("dispute_time", pa.timestamp("us")),
        ("dispute_reason", pa.string()),
        ("dispute_outcome", pa.string()),
        ("amount", pa.float64()),
    ]
)

GROUND_TRUTH_SCHEMA = pa.schema(
    [
        ("episode_id", pa.string()),
        ("episode_type", pa.string()),
        ("affected_entity_type", pa.string()),
        ("affected_entity_id", pa.string()),
        ("window_start", pa.timestamp("us")),
        ("window_end", pa.timestamp("us")),
        ("intensity_param_1", pa.float64()),
        ("intensity_param_2", pa.float64()),
        ("row_count_hint", pa.int64()),
    ]
)

DIM_MERCHANT_SCHEMA = pa.schema(
    [
        ("merchant_id", pa.string()),
        ("merchant_tier", pa.string()),
        ("mcc", pa.string()),
        ("mcc_description", pa.string()),
    ]
)

DIM_STORE_SCHEMA = pa.schema(
    [
        ("store_id", pa.string()),
        ("merchant_id", pa.string()),
    ]
)

DIM_TERMINAL_SCHEMA = pa.schema(
    [
        ("terminal_id", pa.string()),
        ("store_id", pa.string()),
        ("merchant_id", pa.string()),
    ]
)

DIM_ISSUER_SCHEMA = pa.schema(
    [
        ("issuer_id", pa.string()),
        ("issuer_bin", pa.string()),
        ("issuer_name", pa.string()),
    ]
)

DIM_STORE_CALENDAR_SCHEMA = pa.schema(
    [
        ("store_id", pa.string()),
        ("day_of_week", pa.int32()),
        ("day_name", pa.string()),
        ("session_no", pa.int32()),
        ("is_closed", pa.bool_()),
        ("open_time", pa.string()),
        ("close_time", pa.string()),
    ]
)

SCHEMAS = {
    "auth_events": AUTH_EVENTS_SCHEMA,
    "terminal_telemetry": TERMINAL_TELEMETRY_SCHEMA,
    "dispute_events": DISPUTE_EVENTS_SCHEMA,
    "ground_truth": GROUND_TRUTH_SCHEMA,
    "dim_merchant": DIM_MERCHANT_SCHEMA,
    "dim_store": DIM_STORE_SCHEMA,
    "dim_terminal": DIM_TERMINAL_SCHEMA,
    "dim_issuer": DIM_ISSUER_SCHEMA,
    "dim_store_calendar": DIM_STORE_CALENDAR_SCHEMA,
}
