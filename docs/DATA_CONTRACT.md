# Outcome Contract — Project 25

**Fabric E2E Real-Time Payments Risk — Meridian Pay**
Type D (platform build) · opened 2026-08-17 · Skill 8 Step 0

> **Rev 3 — 2026-08-17.** Gate **C1 FAILED**: Digital Twin Builder is not available in this region.
> The kill criterion is executed here, in the same session the failure was reported — the twin is
> removed, the estate hierarchy degrades to a KQL table plus a Power BI decomposition tree, and Git
> integration is promoted into the vacated component slot. Full change table in
> `00_Plan/Gate_Check_Results.md`.
>
> *Rev 2 corrected nine defects found by an adversarial audit against Skill 8, CLAUDE.md's Standing
> Rules, Skill 10 and P24's own contract; §9 records the two audit findings that were false. Rev 1's
> decision record survives as `00_Plan/P25_Brainstorm.md` and `00_Plan/P25_Concept_v2.md`.*

Re-read this file at the **start of every session** and report plan-versus-built in one line before
doing anything else. P23 lacked that habit and drifted 5-of-7 pages; P24 kept it and did not.

---

## 0. Decisions already taken (do not re-litigate)

| Decision | Answer |
|---|---|
| Domain | Payments — **acquirer-side**, not issuer-side |
| Estate hierarchy | Merchant → Store → Terminal → Issuer, as a **KQL table + decomposition tree** *(Rev 3: was a Digital Twin)* |
| Differentiation stance | **Maximum-new**: KQL is the transformation layer, Spark is not |
| ~~Digital Twin Builder~~ | **KILLED 2026-08-17 — not available in region.** Gate C1 |
| Event producer | **Both** — Fabric notebook for backfill, local Python for the live window |
| Dispute-grading cold path | **Protected.** Report pages and the Map are dropped before it |
| Narrative entity | **Meridian Pay**, SE-Asia regional acquirer |
| Capacity | Current Fabric trial, **expires ~2026-09-09** *(hypothesis — gate C0)* |
| Theme | `Themes/MyLifeInLegoBricks_Theme.json` (Standing Rule default) — no new theme JSON |

**Folder deliberately named short** — `25) Fabric E2E Real-Time Payments Risk (MeridianPay)`,
**52 chars** against P24's **56**. P24's tree hit MAX_PATH and `git add` staged *nothing*, silently.
Publishing still robocopies to `C:\p25pub` first, and never uses `2>$null` on a native command
(`feedback_windows_publishing_traps`).

## 1. What does *done* look like?

> A regional card acquirer runs 1,500 payment terminals across 600 merchants. Today fraud is caught
> by a nightly batch and a dead terminal is caught by the merchant phoning in. Fabric Real-Time
> Intelligence puts both on the same event stream: authorisations and device telemetry land in an
> Eventhouse within seconds, every event is resolved to its merchant, store and terminal, and four
> reflexes fire on patterns instead of on schedules. Then — and this is the part nobody demos — when
> the chargebacks arrive 30 to 60 days later, the same platform grades every alert it raised, and
> publishes its own precision.

**The pitch is the last sentence: a real-time system that measures its own precision.** P24's pitch
was *zero source-system change*; this one is *the hot path decides in seconds, the cold path marks
its homework two months later.*

## 2. What is this for?

**Portfolio piece #3 for Microsoft Fabric.** Public-facing: GitHub repo, Pages walkthrough, pitch
deck, portfolio card. Consequences, same as P24:

- Data is synthetic and every extension is declared in §5 and in the repo README.
- The **component list is part of the point** — a reviewer counts Fabric items, so §3's ranking is
  binding, not advisory.
- Screenshots and the written walkthrough matter as much as the artefacts. **More acute than in P24:
  KQL tables are not files.** Rev 3 partly mitigates this — see component 11.

## 3. Components

**Non-negotiable — the build fails without these:**

| # | Component | New to the engine? | Why non-negotiable |
|---|---|:--:|---|
| 1 | **Eventstream** ×2 mandatory | ✅ NEW | auth · terminal telemetry. (A third, Fabric job events, is nice-to-have) |
| 2 | **Eventhouse / KQL Database** | ✅ NEW | The system of record for events. The spine |
| 3 | **KQL update policies + materialized views** | ✅ NEW | **The transformation layer.** This replaces Silver/Gold notebooks — the biggest structural difference from P23/P24 |
| 4 | **KQL Queryset + functions** | ✅ NEW | The hot path's "measures". Also holds `dim_estate`, the hierarchy that resolves every alert to its merchant and store |
| 5 | **Real-Time Dashboard** ×3 pages | ✅ NEW | Co-hero deliverable. The operator's surface |
| 6 | **Activator** ×4 reflexes | ⚠️ reused, new tier | P24 fired it on a monthly close calendar. Here it fires on a live stream |
| 7 | **Eventhouse OneLake availability → Direct Lake model** | ✅ NEW route | A semantic model with **no Gold notebook underneath it**. Behind gate **C2** |
| 8 | **Lakehouse** (cold path only) | ⚠️ thin reuse | Replay/backfill store, dispute batch landing, hot-vs-cold reconciliation |
| 9 | **Power BI report** ×2 mandatory pages | ⚠️ reused, demoted | **Home + Alert Precision** mandatory; the decomposition tree over `dim_estate` lives here |
| 10 | **Stream DQ framework** ×6 rules | ✅ NEW class | §5 |
| 11 | **Git integration (RTI ALM)** | ✅ NEW | *Promoted in Rev 3 into the slot the twin vacated.* P24 deselected it at intake. **It is also a continuous export mechanism** — every item definition lands on disk as it is built, which is exactly the risk §2 names |

**Nice-to-have — drop in this order:**

| Component | Drop rationale |
|---|---|
| **Map** item | First to go. Real but not load-bearing. **Not part of any export checkpoint's minimum content** |
| Power BI pages **4 → 2** | Merchant & Terminal Risk, then Estate Health |
| Fabric **job-events** Eventstream | The ops-page bonus, not the story |
| **Fabric Data Agent** over Eventhouse | Capacity-gated in P23. Gate **C4**, do not plan around it |
| Deployment pipeline (needs a second workspace) | Git integration alone carries the ALM story |

**Never dropped, at any cost:** the three export checkpoints, and the **dispute-grading cold path**.

**Committed numbers:**

| | Mandatory | Target | Composition |
|---|---:|---:|---|
| Eventstreams | **2** | 3 | auth · telemetry · *(job events)* |
| Eventhouse KQL tables | **12** | 12 | 4 raw (auth, telemetry, disputes, job events) · 5 curated (incl. **`dim_estate`**) · `dq_results` · `alerts` · `ground_truth` |
| Materialized views | 3 | 3 | the Gold equivalent |
| KQL functions | 12 | 12 | |
| Stream DQ rules | 6 | 6 | §5 |
| Real-Time Dashboard pages | 3 | 3 | Estate Health · Fraud Watch · Issuer Performance |
| Activator reflexes | 4 | 4 | ≥1 demonstrably fired, evidenced |
| Power BI report pages | **2** | 4 | Home · **Alert Precision** · *(Merchant & Terminal Risk)* · *(Estate Health)* |
| DAX measures | 12 | 20 | down from P24's 45, deliberately |
| **Spark notebooks** | — | **≤ 2** | generator/backfill · dispute batch + `dim_estate` load |
| Sessions | 8 | 8 | §6 — **six capacity-bound, two not** |

**`Spark notebooks ≤ 2` is the anti-drift number.** Every instinct in this engine pushes toward
Bronze/Silver/Gold notebooks. A third notebook is a contract change and gets written down as one.

## 4. Hard constraints

| Constraint | Value | Consequence |
|---|---|---|
| **Fabric trial capacity** | **23 days at 2026-08-17 → expires ~2026-09-09** — measured directly, gate C0 CLOSED | Sessions 1–6 capacity-bound; 7–8 are not (§6). Dates unchanged in value, but the basis moved from "inherited from P24" to "read from this project's own capacity" |
| Capacity SKU | **64 capacity units, Fabric Trial, Malaysia West** — basis: Admin Portal → Capacity settings → Trial, measured 2026-08-17, this project's **own** trial capacity (`Trial-20250909T024501Z-…`, admin: user), **not** the FabricDemo capacity P24 used | A second, previously-unrecorded FTL64-shaped trial (`Trial-20260222T155835Z-…`, admin FabricDemo, 24 days left) also exists on this tenant — not in use by this project, noted for completeness in `00_Plan/Gate_Check_Results.md` Session 2 |
| Region | **Malaysia West** | Digital Twin Builder is not offered here. Assume nothing else in preview is, either |
| Source systems | Synthetic generator, seeded | No real acquirer feed exists; realism is engineered, §5 |
| Execution route | Offline files + written click-steps | Browser automation needs explicit per-task approval (CLAUDE.md hard rule) |
| Sessions | One per phase | §6 |

### Phase-0 gate checks — results in `00_Plan/Gate_Check_Results.md`

| # | Gate | State | If it fails |
|---|---|---|---|
| **C0** | Same FTL64 trial still live; remaining days **re-read from the banner** | **RESOLVED 2026-08-17 — not the same trial** | A **second**, previously-unrecorded FTL64 trial exists on this tenant, under the user's own account; this project uses that one. 23 days left, read 2026-08-17 → expires ~2026-09-09. Details: `00_Plan/Gate_Check_Results.md` |
| **C1** | Digital Twin Builder in-region, ontology survives a reopen | **FAIL 2026-08-17** | **Executed.** Twin removed; `dim_estate` + decomposition tree; Git integration promoted |
| **C2** | Direct Lake binds to an Eventhouse via OneLake availability | **COULD NOT RUN 2026-08-17 — finding** | OneLake availability needs ≥1 KQL table first; `EH_MeridianPay` has zero. Re-run Session 3 once the KQL layer exists |
| **C3** | Eventhouse idle CU burn, generator stopped | **MEASURED 2026-08-17 — caveated** | No CU recorded for `EH_MeridianPay` in the Capacity Metrics item table as of the last refresh; not distinguishable from "refresh predates creation." Capacity is **shared** with another workspace's live workload (`Order Management`, ~2.35% avg util / ~1.76M CU-s over 14 days) — read as shared headroom, not dedicated. Re-check Session 3 |
| **C4** | Activator triggers from a KQL query / Eventstream; Data Agent availability | **RESOLVED 2026-08-17 — mixed** | Eventstream/KQL-query trigger path confirmed reachable (Activator's source picker offers it; KQL Queryset's "Add alert" button exists but is disabled pending data). Data Agent confirmed **unavailable** — SKU-gated, matching P23 exactly, request ID logged; user also lacks a Copilot license |
| **C5** | Cost instrumentation live-fires | **PASS 2026-08-17** | — |

**C3 and C4 needed an Eventhouse and an Activator to exist first** — both were created in Session 2
before any generator output was loaded, per this row's own instruction. Full evidence for C0–C4:
`00_Plan/Gate_Check_Results.md`. **C2 and C3 both carry residual ambiguity — a gate that "could not be
run cleanly" is a finding, never a pass** (guide §104) — both get one more read early in Session 3
once the KQL layer exists and has had time to accrue metrics.

### Export checkpoints — three, and harder than P24's

KQL tables are not files. Every checkpoint needs **both** OneLake availability (the Delta mirror)
**and** an explicit `.export` to OneLake — *and the export read back*. A mirror you have not read is
not a backup; P24's §118a defect was exactly a check that never read its input.

**Git integration (component 11) covers item definitions continuously**, so the checkpoints below
carry the *data* and the screenshots. Definitions arriving on disk as a by-product of ALM is the main
practical dividend of the Rev 3 swap.

| Checkpoint | When | Minimum content (all mandatory) |
|---|---|---|
| **E1** | End of Phase 2 | Curated tables + MVs exported to Parquet **and re-read**; all KQL DDL, update policies, MV and function definitions as `.kql` files; generator source; `dq_results` |
| **E2** | End of Phase 3 | Activator rule configs + evidence of a firing; Eventstream definitions; `alerts`, `ground_truth`, `dim_estate` |
| **E3** | **End of Phase 5 (Session 6)** — deliberately not the last session | RTD JSON + page screenshots, `.pbix`, model TMDL, workspace item list, notebook sources, remaining KQL tables |

**E3 sits at Session 6.** Closure and publishing need no capacity, so nothing capacity-bound may be
scheduled after it. P23 lost its entire estate to a plan that put the export last.

## 5. What must be true about the data?

**Everything is synthetic and declared.** There is no supplied source file; unlike P23 and P24 this
project generates from zero. That voids two of P24's safeguards legitimately — no "not extended"
negative-scope list, no frozen-control-totals obligation, because nothing was supplied to preserve.
It replaces them with a harder one: **the generator is the specification, and it must be seeded,
versioned and byte-reproducible.**

**Scale — FROZEN, Session 2, 2026-08-17, from measured generator output** (basis:
`01_Source/GENERATOR_SPEC.md` §9 "Measured, Session 2, 2026-08-17"; full run, `MASTER_SEED=250817`,
`GENERATOR_VERSION=1.0.0`, `diff -rq` clean across two independent runs):

| | Proposed (Rev 3) | **Measured / frozen** |
|---|---|---|
| Merchants · Stores · Terminals | 600 · ~900 · 1,500 | 600 · **927** · **1,500** (927 sits at this spec's own declared +3% tolerance edge, not a miss) |
| `auth_events` (hot path) | ~60k/day, 90-day ≈ 5.4m rows | **5,386,869 rows** |
| `terminal_telemetry` (hot path) | 15-min heartbeat × 1,500, 30-day ≈ 4.3m rows | **4,337,068 rows** |
| `dispute_events` | ~0.3% of auths ≈ 16k, lagged 30–60 days | **6,715 rows raised as of `SIM_NOW`** — see note below |
| `ground_truth` episodes | not itemised | **137**: 40 card_testing_burst · 25 terminal_compromise · 12 issuer_degradation · 60 terminal_dark_outage |
| Total backfill | ≈ 10m events | **9,730,652 events** (auth + telemetry + disputes) |
| Live replay | 60× real time | unchanged — `live_replay.py --speed 60` |

**Dispute count note, not a correction.** The proposed ~16k assumed the full disputable population;
the measured 6,715 is only what has *matured* (30–60 day lag) as of `SIM_NOW` against a 90-day backfill
— exactly the maturity-cohort effect this section already describes below. The eventual total (0.3% of
~4.5m approved-eligible auths, ≈13.5k) is unchanged; **read "~16k" as the eventual total, not the count
this backfill exposes today.** No contract number was wrong; the distinction between "eventual" and
"raised so far" was implicit and is now explicit.

**Capacity cross-check against gate C3 — done, with an open question of its own.** C3 ran 2026-08-17
via direct browser automation against the tenant's `Microsoft Fabric Capacity Metrics` app (details:
`00_Plan/Gate_Check_Results.md`). `EH_MeridianPay` shows **zero recorded CU consumption** — read as
consistent with negligible idle burn (expected, nothing has ever loaded into it), though not
distinguishable from the metrics refresh simply predating the item's creation. **The more consequential
finding is that this capacity is not dedicated to this project**: a different workspace,
`Order Management`, is already running a live workload on the same FTL64 capacity — ~2.35% avg
utilization, ~1.76M CU-seconds over the trailing 14 days, dominated by its own Eventhouse and
Eventstream items. This project's own headroom therefore has to be read as **shared** headroom, not a
clean 64-CU budget. Whether 9.7m events' worth of ingest fits comfortably alongside that other
workload's baseline is not yet answerable — it depends on how steady `Order Management`'s load is,
which this single snapshot cannot show. **Re-check C3 in Session 3** once `EH_MeridianPay` has real
load and a few Capacity Metrics refreshes have run, and read the trend rather than one point.

**The generator writes a `Landing_Manifest.csv`** — per-stream row counts, min/max event time, seed,
generator version, and the injected-episode register. Every downstream count reconciles to it.

### The maturity-cohort insight — why the 23-day squeeze does **not** threaten the pitch

Grading appears to need 30–60 day-old disputes against a 23-day trial. **That tension is false.** The
generator's clock is synthetic, so a 90-day backfill already contains matured disputes for its own
earlier auths:

- **T-90 → T-60**: fully graded — precision and recall measurable on day one;
- **T-60 → T-30**: partially matured;
- **T-30 → T** and everything live: awaiting grading.

That is how a real fraud-ops team reports precision. **No synthetic lag-compression is needed**, so it
is not a declared extension. The Alert Precision page must show cohort maturity, never a blended
number — reporting precision across an ungraded cohort is the defect this design exists to avoid.

### Declared synthetic extensions

| # | Extension | Why |
|---|---|---|
| 1 | Entire dataset generated from a fixed seed | No real acquirer data exists |
| 2 | Card-testing bursts, terminal-compromise episodes, an issuer-degradation window | So the four reflexes have something true to find. **Ground truth recorded to `ground_truth`**, so reflex precision is measurable against it *and* against disputes |
| 3 | Duplicate delivery, out-of-order reversals, buffered late dumps, per-terminal clock skew, a mid-stream schema addition | The six DQ rules need real faults, not decorative ones |
| 4 | Trading-hours calendar per store | Reflexes 2 and 3 are meaningless without it |

**Must survive a rebuild:** yes. Fixed seed, versioned generator, checkpoint E1. Verify with
`diff -rq` across two independent runs, not a checksum of the data alone — P24's openpyxl
determinism trap.

### The four reflexes

| # | Reflex | Signal |
|---|---|---|
| 1 | **Card-testing burst** | ≥ N low-value auths on distinct tokens at one terminal in M minutes, decline rate > X% |
| 2 | **Terminal compromise** | Tamper flag **and** out-of-trading-hours activity **and** a decline-rate step change |
| 3 | **Terminal dark** | No heartbeat for X min during that store's trading hours — revenue loss, not fraud |
| 4 | **Issuer degradation** | Approval rate for one issuer BIN drops > Nσ against its **own** baseline — `series_decompose_anomalies`, not a fixed threshold |

Reflex 3 is deliberately not fraud. A platform that only ever cries fraud is a demo; one that also
tells a merchant their terminal is dead is a product.

### The six stream DQ rules

| # | Rule | Fault modelled | P24's batch analogue |
|---|---|---|---|
| 1 | **Idempotent dedupe** on `auth_id` | At-least-once delivery replay | duplicate natural keys |
| 2 | **Out-of-order resolution** | A reversal/partial capture arrives *before* its original auth | the `_R2` restatement — harder |
| 3 | **Late arrival past the watermark** | A terminal buffers offline, then dumps 40 minutes at once | the late file |
| 4 | **Device clock skew** | `event_time` vs `ingest_time` per terminal; the dashboard declares which it trusts | — *(no analogue)* |
| 5 | **Payload schema evolution** | A 3DS/SCA field appears mid-stream; schema-on-read absorbs it, no redeploy | the schema drift |
| 6 | **Hot-vs-cold reconciliation** | Eventhouse vs Lakehouse replay — row counts **and** summed amounts | row-count reconciliation |

Rules 2 and 4 are the ones a reviewer will not have seen before. Results persist to `dq_results`.

**Two design rules carried from P24:** *"the cell didn't error" is not proof* — every silent-tagging
rule (1, 2, 3) needs an independent downstream structural check. And *every check needs a floor that
"nothing" cannot satisfy* — a rule that finds no rows must prove it read some (CORE_RULES Appendix C
12; `feedback_recognition_is_not_prevention`).

## 6. Sessions — 8, of which only six are capacity-bound

| # | Phase | Model | Capacity? | Ends when |
|---|---|---|:--:|---|
| **1** | **0 · Architecture + gates** ← *done* | **Opus** | ✅ | Contract Rev 3 approved; C1 failed and executed, C5 passed, C0/C2/C3/C4 open |
| 2 | 1 · Gates C0–C4 · Git integration · generator · Eventstreams · Eventhouse landing | Sonnet | ✅ | Four gates recorded; workspace git-connected; generator reproducible (`diff -rq` clean); backfill loaded and reconciled to `Landing_Manifest.csv` |
| 3 | 2 · KQL transformation + stream DQ | **Opus** | ✅ | Update policies, MVs, 12 functions, `dim_estate`; 6 DQ rules green **by query**. **→ E1** |
| 4 | 3 · Activator reflexes (+ Map if kept) + **Skill 0 mockups** | Sonnet | ✅ | 4 reflexes, ≥1 fired with evidence; one approved `P25_Package.html` covering all 7 surfaces. **→ E2** |
| 5 | 4 · Real-Time Dashboard ×3 + Direct Lake model | Sonnet | ✅ | 3 RTD pages; model bound over Eventhouse OneLake availability (or C2's fallback) |
| 6 | 5 · Power BI report | Sonnet | ✅ | 20 measures; 4 pages at mockup fidelity first pass; Alert Precision shows cohort maturity; decomposition tree over `dim_estate`. **→ E3** |
| 7 | 6 · **Closure — Skill 10** | Sonnet | ❌ | C1–C8 in `09_Closure/`; `--merge` over `_cost/`; ledger row |
| 8 | 7 · **Publishing — Skill 9** | Sonnet | ❌ | Portfolio card → repo → Pages guide → deck |

**Rev 3 rebalanced sessions 2–6.** Killing the twin freed roughly a session of work; the four open
gates and Git integration were pulled into Session 2, and Skill 0 mockups into Session 4. **The
remaining slack is deliberately kept as slack, not spent** — P24 planned 11 sessions and ran 16.

**Model routing:** Opus for the two judgement points — Session 1, and the Phase 2 KQL transformation
design (update-policy vs materialized view vs function is architecture, not mechanics). Sonnet
otherwise.

**Mockups (Standing Rule).** Session 4 runs Skill 0 on **all seven** consumption surfaces — no mockup
exists for any of them. Build to mockup fidelity **on the first pass**: titles, takeaway subtitles, no
gridlines, nav pill bar, disclaimer footer. Before generating any PBIR, grep P24's report folder for
its `$schema` versions and one working example of each visual type; never hand-write schema versions
from memory.

**Every session closes with, in this order:**

1. **Spec reconciliation gate** — before writing or building against any section describing a built
   artefact, re-read the artefact, not this contract. Every KQL table named → one `count()`; every
   column named → one read of the DDL; every reflex named → one row of Activator's own output.
2. Cost snapshot → `_cost/session-NN.json`, **committed to the device**.
3. `HANDOVER.md` overwritten.
4. The next kickoff prompt written to **its own file**, never embedded in the handover (guide §114g).
5. **No measured number quoted without its measurement timestamp.**

## 7. Exit criteria

**Streams & ingest**
- [ ] Generator runs from a fixed seed and reproduces the full event set from empty; `diff -rq` clean across two runs
- [ ] `Landing_Manifest.csv` produced; every downstream count reconciles to it
- [ ] 2 mandatory Eventstreams live (3rd if retained); auth and telemetry landing within seconds, evidenced by query
- [ ] Backfill loaded: 90-day auth, 30-day telemetry, disputes, ground truth
- [ ] Both producer routes proven: notebook backfill **and** local Python live replay
- [ ] Workspace connected to Git; item definitions land on disk as built

**KQL layer (the structural claim)**
- [ ] Transformation is in update policies + materialized views. **Spark notebooks ≤ 2**, counted
- [ ] 12 KQL tables, 3 MVs, 12 functions; curated tables reconcile to raw
- [ ] `dim_estate` resolves every alert to a merchant and store; zero orphan terminals
- [ ] 6 DQ rules executed and persisted to `dq_results`; rules 1–3 each have an **independent downstream structural check**; every rule has a **floor that "nothing" cannot satisfy**
- [ ] Reflex 4 uses `series_decompose_anomalies` against each issuer's own baseline, not a fixed threshold

**Reflexes**
- [ ] 4 Activator reflexes configured; **≥1 demonstrably fired**, evidence saved
- [ ] Reflex precision measured against `ground_truth` as well as against disputes

**The pitch**
- [ ] Every reflex firing written to `alerts` with its maturity cohort
- [ ] Disputes joined back to alerts; **precision/recall published by cohort**, never blended
- [ ] The T-30 → T and live cohorts shown as *awaiting grading*, not as zero

**Semantic & report**
- [ ] Direct Lake bound over Eventhouse OneLake availability — **or** C2's fallback executed and the pitch corrected
- [ ] Skill 0 package approved for all 7 surfaces before any build
- [ ] 20 DAX measures; 3 RTD pages; 4 PBI pages — **or** the drop to 2 executed and recorded, not silent
- [ ] Decomposition tree over `dim_estate` built — the C1 degradation delivered, not just declared
- [ ] Theme is `MyLifeInLegoBricks_Theme.json`; no new theme JSON generated
- [ ] All `.tmdl` CRLF; all JSON via `json.dump()` and re-loaded; `validate_pbip.py` 0/0; **official PBIR CLI `validate` run**
- [ ] Visual roles and formatting from `catalog describe` / `formatting describe-object`, never memory
- [ ] Every measure definition read back against its rendered value

**Close-out — Skill 10, then Skill 9**
- [ ] `HANDOVER.md` overwritten every session; kickoff prompt in its own file
- [ ] `_cost/session-NN.json` committed **every session**, 8 of 8; `--merge` run at closure
- [ ] E1, E2, E3 complete; **E3 by end of Session 6**; every export **read back**, not assumed
- [ ] Skill 10 **C1–C8** all produced in `09_Closure/`: post-mortem · plan-vs-actual · **C3 comparison against P24** · **C4 self-contained HTML package** (`dataviz` skill, palette validated) · do-better · **C6 one inherited assumption tested** · **C7 folder disposition approved before any move, checks re-run after** · **C8 cost analysis + `PROJECT_COST_LEDGER.md` row**
- [ ] `scrub_check.py` run with `--allow`, **whole-file not line-scoped** (guide §118a), over `09_Closure/` and the publishable scope; findings classified INSTANCE vs TEMPLATE
- [ ] `check_rebuild_materials.py` gates the publish
- [ ] Guide imports `_ENGINE/templates/guide_theme.py`; **P25 gets its own architecture diagram**, not P24's
- [ ] `PROJECT_STATUS.md` — plan vs built, honestly, including what was not delivered
- [ ] Lessons dual-written to `PBIP_GENERATION_GUIDE.md` (new §) and `CORE_RULES.md`; mechanically-detectable ones become `validate_pbip.py` rules, each with a positive **and** a false-positive control
- [ ] `_ENGINE/ENGINE_PROFILE.md` changelog line for any engine-level change
- [ ] `BUSINESS_CONTEXT.md` appended, each fact `[confirmed]` or `[inferred]`
- [ ] Retrospective **offered**, with the metrics line: validator errors first pass, fix rounds, sessions used

## 8. What this must beat

**Basis:** P23 — `_ENGINE/reference/project23-cost-analysis.md` headline (the measured transcript).
P24 — `project_24_session16` memory + `09_Closure/B9_Retrospective.md`, measured at close 2026-08-16.

| Metric | P23 | P24 | P25 target |
|---|---:|---:|---:|
| Sessions | 1 | 16 *(11 planned)* | **8** *(6 capacity-bound)* |
| Components complete | 6.5 / 7 | 10 / 10 | **11 / 11, or each degradation documented** |
| Components new to the engine | — | 3 | **8** |
| Report pages, planned vs delivered | 5 / 7 | 8 / 8 | 4 / 4, **or the drop to 2 recorded** |
| Browser share of calls | 70% | ≤ 15% | **≤ 10%** |
| Validator errors, first pass | not measured | 7 → 43 → 0 | **0, first pass** |
| Cost snapshots captured | 0 | 2 of 16 | **8 of 8** |
| **Preview components lost** | 1, **mid-build** | 1, **de-scoped at intake** | 1, **in Phase 0, at zero build cost** |

**The sessions row is the one to watch.** P24 planned 11 and ran 16 — a 45% overrun on a project with
a better plan than this one and a longer runway. §3's drop list is expected to be used, and using it
is not a failure. **Silently not using it is.**

**The last row is the one that already paid.** Three consecutive Fabric platform projects have lost a
preview component. P23 lost Fabric Graph mid-build; P25 lost Digital Twin Builder in Phase 0 for zero
build hours. That difference is the entire argument for Skill 8 Step 1, now evidenced twice.

## 9. Audit record — two findings rejected (Rev 2)

Kept visible rather than dropped, because an audit finding that is wrong is itself a data point.

1. *"`check_rebuild_materials.py`, `guide_theme.py` and guide §118a appear nowhere in the engine."*
   **False.** Verified on disk 2026-08-17: both files exist (16,993 b and 11,778 b). The auditor had
   no device access and reported absence from an inability to look — the exact failure shape as guide
   §118a itself. See `feedback_verify_auditor_negative_claims`.
2. *"`FTL64` has no basis."* **Partly false.** FTL64 is recorded in P24's
   `00_Plan/Gate_Check_Results.md`, measured Session 2. The auditor read P24's *contract*, written
   before the gate ran. **The underlying finding was right, though**: Rev 2 had no SKU gate. That is
   now **C0** — and C1's failure vindicates it, since region is what killed the twin.

---

*Session 2 close, 2026-08-17: §5 scale frozen from measured generator output (done) · generator spec
written and generator built, `diff -rq` clean across two independent full-scale runs (done) · workspace
Git-connected, GitHub PAT, branch `P25_MeridianPay` (done) · `EH_MeridianPay` + `ACT_MeridianPay`
created (done) · all four remaining gates now have a dated entry — C0 resolved (second, previously
unknown trial capacity), C1 resolved Session 1, C2 could not run yet (finding, needs a KQL table), C3
measured with a shared-capacity caveat, C4 resolved mixed (trigger path reachable, Data Agent
unavailable), C5 passed Session 1. C2 and C3 both get one more read early in Session 3. Phase 1 is
functionally complete; what carries into Session 3 is the KQL transformation layer itself.*

---

## Addendum — 2026-08-18, Session 4: streaming dedupe, decided

**Decision: no 4th/5th materialized view. Curated-table dedupe stays a periodic maintenance
operation, run at checkpoints, not a schema addition.** §3's MV count stays **3**.

**Why not an MV.** Two independent reasons, not one:
1. §3 commits to exactly 3 materialized views as a contract number a reviewer counts. A dedup MV
   makes 5 (one per stream) and that number gets changed on purpose or not at all — this decides
   not at all.
2. Even setting the count aside, an MV doesn't fully solve it: Kusto cannot build a materialized
   view over another materialized view (confirmed in `08_dedupe_fix.kql`'s rev history). The three
   *existing* aggregate MVs (`mv_terminal_activity_5min`, `mv_terminal_last_seen`,
   `mv_issuer_baseline`) read directly from `auth_curated` / `telemetry_curated`. A new dedup MV
   sitting beside those tables would not be their source unless the aggregate MVs were redefined to
   read from it — and Kusto's stacking limit means the aggregate MVs still cannot read from an MV.
   So the fix has to land in the **curated table itself**, not in a new MV, regardless of the count.

**What actually happens instead.** The curated tables are the thing that needs to stay clean, and
the tool for that is the same staged `take_any(*)` dedupe already proven in `08_dedupe_fix.kql` —
run as a **periodic maintenance pass**, not a standing pipeline object:
- Run before **every export checkpoint** (E2 today; E3 at Session 6) so the exported/report-facing
  data is clean at the two points that matter for the deliverable.
- Between maintenance runs — i.e. during the live-replay demo window itself — residual streaming
  duplicates are **accepted, not hidden**: measured backfill inflation was ~0.4% against
  reflex 1's thresholds, which the contract already designed with deliberate margin (§5). A 0.4%
  inflation in a 5-minute bucket's `auth_count` does not move a `>= 10` low-value-count trigger.
- `take_any(*)` remains the correct idiom for this, not `arg_max(ingest_time, *)`: Session 3's
  finding that injected duplicates are byte-identical holds for live-replay duplicates too, since
  the same `dq_faults.duplicate_rows()` path generates them.

**Script:** `02_KQL/10_streaming_dedupe_maintenance.kql` — the same 13-step sequence as
`08_dedupe_fix.kql`, generalized to run against whatever `auth_curated` / `telemetry_curated` holds
at run time rather than the fixed backfill counts. Run it now (before E2) and again before E3.

**What this is not.** Not a claim that duplicates never reach a live dashboard — they can, between
maintenance runs, at the ~0.4% level. The Real-Time Dashboard pages built in Session 5 should not
imply zero-duplicate guarantees; the DQ page / rule 1 tile is where duplicate handling is the
honest story, and it already shows this as a rate, not a boolean.
