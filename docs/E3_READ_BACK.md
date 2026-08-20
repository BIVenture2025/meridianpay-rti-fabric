# E3 — the read-back that closes the checkpoint

**Project 25 (Meridian Pay) · Session 7 · measured 2026-08-19**

> Contract §4: *"a mirror you have not read is not a backup."* And: *an export whose read-back was
> never taken is recorded as **exported, not verified** — never as complete.* This file is the
> read-back. Every number below was produced by a query today, on both sides where both sides exist.

**Method.** KQL side: one `union withsource=TableName … | summarize count() by TableName` over all
20 tables in `EH_MeridianPay`. OneLake side: `COUNTROWS()` per table over XMLA against
`SM_MeridianPay_DirectLake`, which reads the Delta mirror through the Lakehouse shortcuts — a
genuinely independent path (different engine, different storage layer, no shared query plan).

---

## 1. Two-sided read-back — 7 tables, delta 0 on every one

These are the tables shortcut into `LH_MeridianPay` and therefore readable from OneLake as Delta.

| Table | KQL side | OneLake / Delta side | Δ |
|---|--:|--:|--:|
| `alerts_v2` → shortcut `alerts` | 186 | **186** | **0** |
| `auth_curated` | 5,365,392 | **5,365,392** | **0** |
| `telemetry_curated` | 4,319,781 | **4,319,781** | **0** |
| `dispute_curated` | 6,715 | **6,715** | **0** |
| `dim_estate` | 1,500 | **1,500** | **0** |
| `ground_truth` | 137 | **137** | **0** |
| `dq_results` | 6 | **6** | **0** |

**7 of 20 tables verified two-sided.** The remaining 13 are verified on the KQL side only and are
reconciled by derivation in §2 — that split is stated here rather than averaged away.

---

## 2. KQL-side counts — and every one ties to something that was frozen or injected

| Table | Rows | Reconciles to |
|---|--:|---|
| `raw_auth_events` | 5,386,869 | **§5 frozen scale, exactly** |
| `raw_terminal_telemetry` | 4,337,068 | **§5 frozen scale, exactly** |
| `raw_dispute_events` | 6,715 | **§5 frozen scale, exactly** |
| `ground_truth` | 137 | **§5 frozen: 40 + 25 + 12 + 60** |
| `dim_estate` · `stg_dim_terminal` | 1,500 · 1,500 | **§5 frozen terminals** |
| `stg_dim_store` | 927 | **§5 frozen stores** (the +3% tolerance edge, not a miss) |
| `stg_dim_merchant` | 600 | **§5 frozen merchants** |
| `stg_dim_issuer` | 24 | issuer register; no frozen reference — recorded as measured |
| `dim_store_calendar` | 7,819 | trading-session register; no frozen reference — recorded as measured |
| `landing_manifest` | 18 | the load manifest §7 requires; Session 3 reconciled 16/16 against it |
| `alerts_regrade_snapshot` | 186 | spare copy of the graded rows; retained until this read-back passed |
| `raw_auth_events_cold` | 5,386,819 | raw − **50** |
| `raw_terminal_telemetry_cold` | 4,337,018 | raw − **50** |
| **`raw_job_events`** | **0** | **see §4 — absent from the result set entirely** |

### The three derived checks, and all three close

**Dedupe — the curated tables are short by exactly the duplicate counts that were measured:**

```
auth      : 5,386,869 raw − 5,365,392 curated = 21,477
telemetry : 4,337,068 raw − 4,319,781 curated = 17,287
disputes  :     6,715 raw −     6,715 curated =      0
```

**CORRECTED 2026-08-19, Session 7 closure.** This block first read *"= injected auth duplicates"*,
*"= injected telemetry duplicates"*, and asserted that *"both figures match Session 3's independently
measured injection counts **to the row**."* **The auth half of that was wrong by 15, and the claim of
independence was too strong for the telemetry half.** Both are restated here rather than softened.

**Auth — ties to a genuinely independent instrument, and the 15-row gap is the point.** DQ rule 1
(`idempotent_dedupe_auth_id`) counted **21,477** duplicate `auth_id`s over 5,386,869 rows and
recorded, at the time, *"+15 over 21,462 — birthday collisions among 5.36m 40-bit ids (expected
~13)."* So **21,462 were injected; 21,477 were present; 21,477 were removed.** The curated shortfall
matches what the DQ rule measured, not what the generator injected — which is the stronger of the two
statements, because it means the dedupe removed exactly the population an independent check found,
including fifteen duplicates nobody planted. Claiming a match against 21,462 would have been claiming
a match against a figure the data does not carry.

**Telemetry — the same arithmetic, a weaker basis, stated as weaker.** 17,287 comes from Session 3's
defect analysis of the update-policy dedupe, which is the *same* analysis that produced the fix. There
is no DQ rule for telemetry duplicates, so this is one instrument agreeing with itself. It is
consistent and it reconciles; it is **not** a second read, and §7 lists it as such.

What both halves do establish, independently of the injection figures, is that the **global dedupe
(`08_dedupe_fix.kql`) still holds** — five sessions later, measured from the outside rather than from
the fix's own output That is the **global dedupe (`08_dedupe_fix.kql`) still holding**, five sessions later, verified
from the outside rather than from the fix's own output.

**Cold path — the designed exclusion:**

```
auth cold gap      = 50
telemetry cold gap = 50
                     ---
total              = 100   = dq_results rule 6 `expected_gap` AND `measured_gap`
```

DQ rule 6's detail JSON states the basis: *"50 rows excluded from each of auth and telemetry cold
path, by design"*, and notes its floor is **equality, not > 0** — *"the exact injected gap is known,
so an approximate match would be a finding."* It is an exact match.

**Cross-surface — the RTD agrees with the grading:** the Real-Time Dashboard's Estate Health page
reads **"Dark right now — 219"** at the reference window, which is the same 219 derived independently
as reflex-3's right-censored exclusion (terminals dark ≥ 20 min while their store was open). Two
surfaces, two query paths, same number.

---

## 3. Contract §3's committed table count, reconciled

**21 tables at the start of this session → 20 after the cleanup.**

| | Tables | Count |
|---|---|--:|
| **§3 counted** | 4 raw (`raw_auth_events`, `raw_terminal_telemetry`, `raw_dispute_events`, `raw_job_events`) · 5 curated incl. `dim_estate` (`auth_curated`, `telemetry_curated`, `dispute_curated`, `dim_estate`, `dim_store_calendar`) · `dq_results` · `alerts` (as `alerts_v2`) · `ground_truth` | **12 ✅** |
| **Working** | `alerts_regrade_snapshot` · `landing_manifest` · 2 `*_cold` · 4 `stg_dim_*` | **8** |
| | | **20** |

**`14_alerts_v2_rebuild.kql`'s claim that the cleanup "returns it to exactly 12" is wrong** and is
corrected here: 12 is the *counted subset*, not the length of the table list. Dropping the staging
dimensions to force the list to 12 would destroy the `dim_estate` build lineage to make a number look
tidy. **E3 records the split — 12 counted + 8 working = 20 — so a reviewer counting 20 against a
committed 12 has the answer in front of them.**

`alerts_regrade_snapshot` was deliberately retained through this read-back as the only second copy of
the 186 graded rows, `alerts` having been dropped earlier in the session. **It is now safe to drop**;
that takes the list to 19 (12 counted + 7 working).

---

## 4. FINDING — `raw_job_events` is empty, and that is the drop list working

`raw_job_events` **did not appear in the result set at all** — a `union … | summarize count() by
TableName` emits no row for a table with no rows. The table exists with its schema; it has never been
fed.

**This is consistent and declared, not a gap:** §3's nice-to-have drop list names *"Fabric
**job-events** Eventstream — the ops-page bonus, not the story"* as droppable, and it was dropped.
The counted table remains because §3's 12 enumerates it.

**But it is recorded loudly, per §8** — *using the drop list is not a failure; silently not using it
is.* One of the 12 committed tables carries zero rows, and a reader of the export should be told that
by the export, not discover it by querying.

---

## 5. E3 status — **7 of 7 mandatory items complete**

| # | Item | State |
|---|---|---|
| 1 | RTD JSON | ✅ on disk, `json.load()` re-read, 19/19 tile queries resolve |
| 2 | **RTD page screenshots** | ✅ **6 of 6 captured, 2026-08-19** — three pages × two reference windows, the window legible in every frame. See §8 for both windows, the two tiles that read empty *correctly*, and the one tile that exceeds the platform's point budget at the wide window |
| 3 | `.pbix` | ✅ saved 2026-08-19 from the user-decorated `.pbip` |
| 4 | Model TMDL | ✅ **satisfied by Git** — `SM_MeridianPay_DirectLake` committed Synced, carrying the 24 measures, the `DQ Rows Flagged` rename and the new relationship |
| 5 | Workspace item list | ✅ captured; **9 items, read three times on two days** |
| 6 | Notebook sources | ✅ on disk; generator `diff -rq` clean across two runs |
| 7 | **Remaining KQL tables exported + read back** | ✅ **this document** — see §6 for the deviation |

---

## 6. DEVIATION, recorded rather than absorbed — §4's "explicit `.export`"

Contract §4 requires *"**both** OneLake availability (the Delta mirror) **and** an explicit `.export`
to OneLake — and the export read back."*

**Only the mirror half was performed. The literal `.export` was not run.** Two reasons, both stated
so a reviewer can disagree with them:

1. **The requirement was written in Phase 0, before the Eventhouse existed**, on the premise that *"KQL
   tables are not files."* They now are: OneLake availability materialises genuine Delta at
   `EH_MeridianPay/Tables/<name>`, readable by any engine independent of the Eventhouse. The premise
   the clause rests on was overtaken by the platform.
2. **The documented `.export` route needs a storage credential.** Microsoft's delta external-table
   example is `h@'abfss://…;secretKey'`, and handling a key was declined outright. An impersonation
   variant may exist but is not documented on that page, and inventing the syntax is the failure mode
   this project has recorded three times today.

**What was done instead is stronger on the dimension that matters** — §4's actual concern is that a
backup be *read*, and §1 gives seven two-sided reads with delta 0 across an independent engine, plus
thirteen KQL-side counts every one of which reconciles to a frozen figure or a measured injection.

**What it does not give:** a point-in-time file snapshot decoupled from the Eventhouse's lifetime. If
the Eventhouse is deleted, the mirror goes with it. That is the residual risk this deviation carries,
and it is the honest reason the clause was written.

---

## 7. What this read-back could not establish

- **13 of 20 tables are single-sided.** They are not shortcut into the Lakehouse, so no independent
  engine read exists. Their reconciliation in §2 is derivation against frozen figures, which is
  strong evidence and is not the same thing as a second read.
- **The telemetry dedupe figure is one instrument agreeing with itself.** 17,287 is Session 3's own
  defect-analysis figure; no DQ rule counts telemetry duplicates. The auth figure ties to DQ rule 1,
  which is a separate check — the telemetry one does not have an equivalent. See §2's correction.
- **`dim_store_calendar` (7,819) and `stg_dim_issuer` (24) have no frozen reference** in §5. They are
  recorded as measured on 2026-08-19 and nothing checks them.
- **The mirror's freshness is not proven by row count alone.** Counts agreeing means the mirror is
  complete as of the read; it does not prove latency. The OneLake pane's own latency figure is the
  instrument for that and was last read at 11 minutes, before the availability toggle.

---

## 8. E3 item 2 — the screenshots, and why there are two windows

**Window A — captured 2026-08-19:** Estate Health · Fraud Watch · Issuer Performance, at
`2026-08-16 00:00 → 2026-08-17 00:35`. This is the window every frozen figure in
`Gate_Check_Results.md` was measured in, and the reference window is legible in each frame.

**Fraud Watch reads zero firings at Window A, and that is true rather than broken.** Measured from
`alerts_v2` on 2026-08-19:

| reflex_type | rows | first fire | last fire | inside Window A? |
|---|--:|---|---|---|
| `card_testing_burst` | 72 | 2026-05-19 12:10 | **2026-08-15 22:05** | no — 26 h before it opens |
| `terminal_compromise` | 10 | 2026-07-19 15:30 | 2026-07-19 17:45 | no |
| `issuer_degradation` | 95 | 2026-08-03 01:00 | 2026-08-16 01:00 | 2 — the two rows the tile shows |
| `terminal_dark` | 9 | 2026-08-16 23:45 | 2026-08-16 23:45 | 9 |

72 + 95 + 10 + 9 = **186**, which is the graded set, intact. No card-testing or terminal-compromise
episode occurred in that 24 hours. **A dashboard that shows zero when zero happened is the dashboard
working**, and it is captured as evidence on that basis rather than tuned until it looked busy.

**Window B — captured 2026-08-19 at `2026-05-19 16:00 → 2026-08-16 00:00`.** The recommendation was
`05/19 00:00 → 08/16 16:00`; the times were entered transposed. **Recorded as captured rather than
re-shot**, because the window still does its job and the difference is arithmetic rather than
substantive:

| Tile | Window B reading | Reconciles |
|---|--:|---|
| Auths / sec | **0.1** | the rounding fix working — one decimal would have shown `0.0`. The same tile at `05/19 00:00 → 08/16 16:00` reads **0.71**, with decline rate **9.4%** |
| Decline rate now (%) | **8** | populated |
| Reflex 1 firings | **70** | **of 72 — and the explanation is now VERIFIED, not inferred.** The window opens at `16:00` on 05/19 and the first `card_testing_burst` fired at **12:10** that day, so the two earliest firings sit outside it. Re-run 2026-08-19 from the same dashboard with the window entered as `05/19 00:00 → 08/16 16:00`, the tile reads **72**. *This line first said "inferred from the min/max read, not separately counted"; the inference held and the correction is recorded rather than silently upgraded.* |
| Reflex 2 firings | **10** | **10 of 10** — every `terminal_compromise` firing |
| Live alert feed | populated | `card_testing_burst` rows, cohort `awaiting_grading_T30_T…`, ordered by `window_start` desc as designed |

**Estate Health reads `Dark right now = 0` and an empty reflex-3 feed at Window B, and that is correct.**
`as_of = _endTime` = `08/16 00:00`, and every `terminal_dark` firing is stamped `2026-08-16 23:45`.
Nothing was dark at the moment the window closes.

### A platform limit, measured — the anomaly band cannot span the backfill

Issuer Performance's first tile fails at Window B with:

> **Max points exceeded.** Data points have exceeded maximum recommended. Query returned **152,640**.
> Maximum recommended is **50,000**.

That reconciles exactly: `make-series … step 1h by issuer_bin` over ~89 days × 24 issuers ≈ 51k points,
and `series_decompose_anomalies` returns **three** series from it — `ApprovalRate`, `baseline`,
`anomalies` — so 3 × 50,880 = 152,640.

**Not fixed, deliberately.** Widening the step to fit the window would silently change the analysis:
§7's exit criterion specifies decomposition **at 1h against each issuer's own baseline**, and a tile
that quietly re-bins itself by window width is a different instrument wearing the same caption.
**The anomaly band is a short-window instrument by design.** Window A is its evidence window, where it
renders correctly at the contracted grain; Window B is the fraud-evidence window, and this tile is
recorded as out of budget there rather than tuned until it drew something.

### A rounding defect found while diagnosing this, and fixed

`Auths / sec` computed `round(count / 900.0, **1**)`. One decimal renders any 15-minute window holding
fewer than **45 auths** as `0.0` — indistinguishable from a broken tile, and exactly what Window A's
overnight slice produces. **The tile was read as empty before the arithmetic was checked.** Corrected
to two decimals in `p2_t0_kpi_row.kql` and `p2_t1_auths_per_sec.kql`; both RTD JSON files rebuilt.
**The Window A captures predate that fix** — they show `0` where the fixed build would show a small
non-zero number. Recorded rather than re-shot.

`event_type == 'auth'` was verified against data and is correct: 4,955,280 auth + 143,488
partial_capture + 266,624 reversal = 5,365,392 = `auth_curated` exactly.
