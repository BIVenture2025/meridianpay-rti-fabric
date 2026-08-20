# Generator Spec — Project 25 (Meridian Pay)

**Written Session 2, 2026-08-17.** Governs `01_Source/generator/` — the single module that both the
Fabric notebook backfill route and the local Python live-replay route import. There is no supplied
source system for this project (contract §5): the generator **is** the specification. Everything it
produces must be seeded, versioned and byte-reproducible.

---

## 1. Fixed seed and version

| | Value |
|---|---|
| `GENERATOR_VERSION` | `1.0.0` |
| `MASTER_SEED` | `250817` (date this spec was frozen, YYMMDD — documented so the choice is traceable, not arbitrary) |
| RNG | `numpy.random.Generator` (PCG64), one instance per logical stream, each seeded by
  `spawn_child(MASTER_SEED, stream_name)` — a stable hash of `(MASTER_SEED, stream_name)` — **never**
  a shared global RNG. This is what makes the streams independently reproducible regardless of call
  order, which matters once backfill and live-replay run as separate processes |
| Simulation clock | Entirely synthetic. `SIM_NOW` is a fixed constant (`2026-08-17T00:00:00Z`), never
  `datetime.now()`. No function in the generator may call `datetime.now()`, `time.time()` or
  `random` (stdlib) for anything that ends up in an output row — wall-clock calls are confined to a
  `_run_meta.json` sidecar that sits **outside** the reproducibility diff |

Both entry points (`backfill.py`, `live_replay.py`) print `GENERATOR_VERSION` and `MASTER_SEED` into
`Landing_Manifest.csv` so every downstream table can cite what produced it.

---

## 2. `dim_estate` hierarchy

Merchant → Store → Terminal, generated in that order so child counts are drawn from the parent's
distribution rather than independently (a merchant with 1 store cannot have 6 terminals split across
stores that don't exist).

| Level | Count | Generation rule |
|---|---:|---|
| `dim_merchant` | 600 | `merchant_id` = `MER-000001`…`MER-000600`; `mcc` drawn from a 12-code retail/F&B/fuel mix; `merchant_tier` (small/medium/large) drawn 60/30/10, which sets its store-count distribution |
| `dim_store` | ~900 | store count per merchant: small→1, medium→Poisson(λ=2)+1, large→Poisson(λ=4)+2, clipped so the **total lands at 900 ±3%** (the ±3% is declared, not silently rounded) |
| `dim_terminal` | 1,500 | terminal count per store: Poisson(λ=1.2)+1, clipped so the total lands at **1,500 exactly** by trimming/padding the last stores deterministically (seeded, not arbitrary) |
| `dim_issuer` | 24 | synthetic issuer BINs, not a child of terminal — see note below |

**Hierarchy note, stated rather than silently assumed:** contract §0 writes the chain as
"Merchant → Store → Terminal → Issuer." Issuer is not structurally nested under Terminal — an issuer
is resolved **per transaction** (whichever card's BIN authorised at that terminal), not owned by it.
`dim_estate` therefore ships as `dim_merchant` + `dim_store` + `dim_terminal` (the true tree, one
surrogate key per level, single-column keys throughout per Skill 8 §4) plus a separate `dim_issuer`.
The Power BI decomposition tree walks Merchant → Store → Terminal → **Issuer of the selected
transactions**, which reproduces the reviewer-facing hierarchy from §0 without inventing a structural
relationship that doesn't exist. Flagged here so Session 5/6 doesn't rediscover it while building the
decomposition tree.

Every terminal carries its resolved `merchant_id` and `store_id` directly (denormalised at generation
time) so `dim_estate` resolving every alert to a merchant and store — an exit criterion — is a single
join, not a three-hop traversal.

---

## 3. Per-store trading-hours calendar

`build_trading_hours(stores, rng)` assigns each store one of four calendar archetypes, weighted:

| Archetype | Weight | Hours |
|---|---:|---|
| Standard retail | 55% | 08:00–22:00 daily |
| Convenience (24h) | 15% | 00:00–24:00 daily |
| Restricted (F&B lunch/dinner) | 20% | 11:00–15:00, 18:00–23:00 |
| Weekday-only | 10% | 08:00–20:00 Mon–Sat, closed Sun |

Stored as `dim_store_calendar` (store_id, day_of_week, open_time, close_time) — a flat table, not code,
so both routes and any downstream KQL function can join against it directly. This is what makes
reflex 2 ("out-of-trading-hours activity") and reflex 3 ("no heartbeat during trading hours") queries
rather than judgment calls.

---

## 4. Event schemas

### 4.1 `auth_events` (raw)

| Column | Type | Notes |
|---|---|---|
| `auth_id` | string | `AUTH-{10 hex}`, the natural/idempotency key — **DQ rule 1** duplicates this exactly |
| `event_type` | string | `auth` \| `reversal` \| `partial_capture` — reversals/partial captures reference the original via `related_auth_id` |
| `related_auth_id` | string, nullable | set for `reversal`/`partial_capture` rows |
| `event_time` | datetime(UTC) | when the transaction actually happened |
| `ingest_time` | datetime(UTC) | when the row lands in the stream — **diverges from `event_time`** under DQ rules 2/3/4 |
| `terminal_id`, `store_id`, `merchant_id` | string | denormalised from `dim_estate` at generation time |
| `issuer_bin` | string | FK to `dim_issuer` |
| `card_token` | string | synthetic tokenised PAN surrogate, never a real PAN shape |
| `amount` | double | 2dp, IEEE-754-safe per Skill 8 §4 |
| `currency` | string | `MYR` (single-currency, declared) |
| `mcc` | string | inherited from the merchant |
| `auth_result` | string | `approved` \| `declined` |
| `decline_reason` | string, nullable | set when `auth_result = declined` |
| `pos_entry_mode` | string | `chip` \| `contactless` \| `magstripe` |
| `is_card_present` | bool | |
| `sca_flag` | bool, nullable | **absent before the schema-evolution cutover — DQ rule 5** |
| `schema_version` | int | `1` before cutover, `2` after |

### 4.2 `terminal_telemetry` (raw)

| Column | Type | Notes |
|---|---|---|
| `telemetry_id` | string | `TEL-{10 hex}` |
| `event_time`, `ingest_time` | datetime(UTC) | per-terminal fixed skew applied to `event_time` — **DQ rule 4** |
| `terminal_id`, `store_id`, `merchant_id` | string | |
| `heartbeat_ok` | bool | `false` marks a degraded-but-present heartbeat; a **missing** interval (no row) is what reflex 3 detects, not a flag |
| `tamper_flag` | bool | true only inside injected `terminal_compromise` episodes |
| `battery_pct`, `signal_strength` | double | cosmetic realism, bounded 0–100 |
| `schema_version` | int | mirrors `auth_events` cutover for consistency, though telemetry has no new field added |

### 4.3 `dispute_events` (raw)

| Column | Type | Notes |
|---|---|---|
| `dispute_id` | string | `DSP-{10 hex}` |
| `auth_id` | string | FK to the original `auth` row (never a reversal/partial_capture) |
| `dispute_time` | datetime(UTC) | `auth.event_time + Uniform(30, 60)` days — this is the maturity-cohort lag contract §5 describes |
| `dispute_reason` | string | `fraud` \| `not_as_described` \| `duplicate_processing` \| `other`, weighted so `fraud` dominates disputes raised against `card_testing_burst`/`terminal_compromise` episode auths |
| `dispute_outcome` | string | `merchant_won` \| `cardholder_won` \| `pending` — `pending` for anything whose maturity window hasn't closed as of `SIM_NOW` |
| `amount` | double | equals the original auth amount |

---

## 5. Injected fraud/operational episodes → `ground_truth`

`inject_episodes(estate, calendar, rng)` runs **before** the raw streams are generated and returns an
episode register; the raw generators then bias their output inside each episode's window so the
episode is actually detectable, not just labelled.

| `episode_type` | Count (backfill) | What it does to the raw stream |
|---|---:|---|
| `card_testing_burst` | 40 | picks one terminal + a 5–15 min window; injects 15–40 low-value (<MYR 5) auths on distinct `card_token`s with an elevated decline rate (>60%) |
| `terminal_compromise` | 25 | picks one terminal + a 2–6 hour window, weighted toward out-of-trading-hours; sets `tamper_flag=true` on that terminal's telemetry for the window and raises its decline rate step-change for auths in-window |
| `issuer_degradation` | 12 | picks one issuer BIN + a 3–8 hour window; drops that issuer's approval rate by 15–35 percentage points against its own 30-day rolling baseline (the generator writes the baseline explicitly so reflex 4's `series_decompose_anomalies` check has a real distribution to work against, not a step function dressed up as one) |
| `terminal_dark_outage` | 60 | picks one terminal + a window **inside its store's trading hours**, length 20–90 min; **no telemetry rows are emitted** for that terminal in that window (the absence is the signal — reflex 3 exit criterion) |

Each episode row in `ground_truth` carries: `episode_id`, `episode_type`, `affected_entity_type`
(`terminal`/`issuer`), `affected_entity_id`, `window_start`, `window_end`, and the generator's own
intensity parameters (decline-rate target, row count, etc.) so reflex precision/recall can be scored
against a documented expectation, not just "did an alert fire in this window."

This is declared synthetic extension #2 from contract §5.

---

## 6. The six DQ faults — fault and injection point

| # | Rule | Injected in | Mechanism |
|---|---|---|---|
| 1 | Idempotent dedupe | `dq_faults.duplicate_rows()` | ~0.4% of `auth_events` rows are exactly duplicated (identical `auth_id`, identical everything) at emission time, in **both** routes |
| 2 | Out-of-order resolution | `dq_faults.reorder_reversals()` | For ~2% of `reversal`/`partial_capture` rows, `ingest_time` is set **earlier** than the `related_auth_id` row's own `ingest_time` — the resolution genuinely arrives first |
| 3 | Late arrival past watermark | `dq_faults.late_burst()` | ~15 terminals per backfill day are chosen to "go offline"; their events in a 40-minute window get `ingest_time = event_time + Uniform(35, 50) min`, arriving as one buffered dump |
| 4 | Device clock skew | `dq_faults.clock_skew()` | Each terminal draws one fixed offset ∈ [-5, +5] minutes at generation time (seeded per terminal, stable across its whole history); applied to `event_time` relative to `ingest_time` on **both** `auth_events` and `terminal_telemetry` for that terminal |
| 5 | Payload schema evolution | `dq_faults.schema_cutover()` | `sca_flag`/`schema_version=2` begins at a fixed cutover point 60% of the way through the 90-day backfill window; nothing before it carries the field — schema-on-read must treat its absence as "not yet collected," not null-as-error |
| 6 | Hot-vs-cold reconciliation | `dq_faults.cold_path_gap()` | The cold-path (Lakehouse) copy of the backfill **deliberately excludes ~50 rows per raw stream** that the hot-path (Eventhouse) export includes — a small, counted, seeded gap so the reconciliation check (row count **and** summed amount, per stream) has a genuine non-zero discrepancy to find. The excluded row IDs are written to `_cold_path_exclusions.csv` (sidecar, outside the manifest) precisely so the check's own correctness can be verified against a known answer, not just "did it complain" |

Rules 1–3 each need an independent downstream structural check per contract §5 — that check lives in
the KQL layer (Session 3), not here; the generator's job is only to make sure the fault is real and
counted. Every rule also needs a floor that "nothing" cannot satisfy (CORE_RULES Appendix C 12): the
injection counts above are all non-zero and logged to `Landing_Manifest.csv`'s episode/fault register,
so a rule reporting zero faults found is verifiably wrong, not verifiably clean.

---

## 7. `Landing_Manifest.csv` contract

One row per output stream, columns:

`stream_name, row_count, min_event_time, max_event_time, generator_version, master_seed, run_id,
fault_rules_applied, episode_count_by_type`

`run_id` is a deterministic label (`backfill-v1`, not a wall-clock stamp) so the manifest itself stays
byte-identical across reproducibility runs. Real wall-clock provenance (when this specific run actually
executed) goes to `_run_meta.json`, generated **outside** `01_Source/output/` so it never enters the
`diff -rq` comparison.

Streams manifested: `auth_events`, `terminal_telemetry`, `dispute_events`, `ground_truth`,
`dim_merchant`, `dim_store`, `dim_terminal`, `dim_issuer`, `dim_store_calendar`. Every downstream KQL
table count (Session 3) reconciles to this file — that reconciliation is the spec-reconciliation gate
applied to the generator's own output, one session early.

---

## 8. Shared module: one generator, two entry points

```
01_Source/generator/
  __init__.py
  core.py        # MASTER_SEED, GENERATOR_VERSION, SIM_NOW, per-stream RNG factory
  estate.py       # build_dim_estate() -> merchants, stores, terminals, issuers
  calendar.py     # build_trading_hours(stores)
  episodes.py     # inject_episodes(estate, calendar) -> ground_truth + episode windows
  schemas.py      # pyarrow schemas for every table above; single source of truth for column order/types
  auth_events.py  # generate_auth_events(estate, calendar, episodes, window) -> DataFrame
  telemetry.py    # generate_telemetry(estate, calendar, episodes, window) -> DataFrame
  disputes.py     # generate_disputes(auth_events, episodes) -> DataFrame
  dq_faults.py    # the six injectors in §6, applied to already-generated raw frames
  manifest.py     # build_landing_manifest(streams_dict) -> writes Landing_Manifest.csv
  backfill.py     # ENTRY POINT 1 — notebook route: full 90/30-day window, writes Parquet + manifest to disk
  live_replay.py  # ENTRY POINT 2 — local Python route: same estate/calendar/episodes/schemas/dq_faults,
                  #   iterated event-by-event at 60x real time, sink is pluggable (--sink file|eventstream)
```

**What is shared:** `estate.py`, `calendar.py`, `episodes.py`, `schemas.py`, `dq_faults.py` — the
entire "what is true about this world" layer. Both routes call the identical functions with the
identical `MASTER_SEED`, so a terminal that is `terminal_dark` in the backfill is the same terminal,
same window, if replayed live for that period.

**What differs:** only the *iteration and sink*. `backfill.py` materialises the full window as
DataFrames and writes Parquet once. `live_replay.py` walks the same generated timeline but emits rows
one at a time, sleeping to a real (accelerated) clock, and posts each to a sink — a local JSONL file in
dry-run mode (used until an Eventstream custom endpoint exists), or the Eventstream endpoint once
Session 2's Job A/B creates one. The **fault injectors in `dq_faults.py` run identically in both** —
duplication, reordering and skew are properties of the underlying event set, not of how it's delivered.

---

## 9. Reproducibility proof

`backfill.py` run twice, from empty, into two separate output directories, with no argument changes:

```
python backfill.py --out output_run1
python backfill.py --out output_run2
diff -rq output_run1 output_run2
```

Expected result: **no output** (clean diff) for everything under `output_run*/` — `_run_meta.json`
lives outside that tree specifically so a real wall-clock difference between the two invocations can
never appear inside the compared directories. A checksum of the data alone was ruled out per contract
§5 (P24's `openpyxl` determinism trap): `diff -rq` catches file-count and structural drift that a
content-only hash would miss.

### Measured, Session 2, 2026-08-17

Run at the **full contract scale** (600 merchants, `MASTER_SEED=250817`, `GENERATOR_VERSION=1.0.0`),
two fully independent invocations, `diff -rq output_run1 output_run2`:

```
=== CLEAN DIFF: reproducible ===
```

Every file under both trees compared identical, including `Landing_Manifest.csv` (`md5sum` matched:
`cf1c270b8440bde4c779dd127550e168` on both runs) — the 14-file structure (9 dimension/fact Parquet
files, 2 hot/cold pairs, `_cold_path_exclusions/`, the manifest) was identical in both shape and byte
content. Wall time: ~5 minutes per run (dominated by the per-terminal auth-event rejection sampling and
the DQ-fault injectors; profiled and the late-arrival injector was rewritten from an O(bursts ×
full-table) scan to an O(bursts × per-terminal-subset) scan mid-session after the first full run took 9
minutes — see the code history in `dq_faults.py`'s `late_burst()` docstring).

**Measured row counts, this run** (basis for the Job C scale freeze):

| Stream | Measured | Contract §5 proposal |
|---|---:|---|
| `dim_merchant` | 600 | 600 |
| `dim_store` | 927 | ~900 (±3% tolerance in this spec §2 — 927 is exactly the +3% edge) |
| `dim_terminal` | 1,500 | 1,500 (exact, by design) |
| `dim_issuer` | 24 | not specified in the contract; fixed here at 24 synthetic BINs |
| `auth_events` (hot) | 5,386,869 | ~5.4m |
| `terminal_telemetry` (hot) | 4,337,068 | ~4.3m |
| `dispute_events` | 6,715 **raised as of `SIM_NOW`** | ~16k |
| `ground_truth` episodes | 137 (40 card_testing_burst, 25 terminal_compromise, 12 issuer_degradation, 60 terminal_dark_outage) | not itemised in the contract |
| **Total backfill events** | **9,730,652** | ~10m |

**The dispute count needs a footnote, not a correction.** Contract §5's maturity-cohort insight (its own
words: *"reporting precision across an ungraded cohort is the defect this design exists to avoid"*)
predicts this exactly: of the ~13,500 auths that will *eventually* be disputed (0.3% × ~4.5m
approved-and-eligible auths), only auths older than 30 days can have matured into a raised dispute by
`SIM_NOW`, and even those mature probabilistically across the 30–60 day lag window. The measured 6,715
is the raised-and-observed count; the remainder are the T-30→T "awaiting grading" cohort the contract
itself describes. **Contract §5's "~16k disputes" should be read as the eventual total, not the count
this backfill exposes as of `SIM_NOW`** — carried into the Job C freeze below.
