# C2 — Plan vs actual

**Project 25 · Meridian Pay** · classified against `OUTCOME_CONTRACT.md` Rev 3 + the 2026-08-18 addendum
Compiled Session 7, 2026-08-19 · every classification carries the evidence that produced it

> This section is only possible because the outcome contract committed numbers. Where a criterion could
> only be confirmed to *exist* and not to *match its spec*, it is classified **exists; spec-match
> unverified** rather than promoted to delivered.

**Legend** — ✅ delivered as specified · ◐ delivered differently · ❌ not delivered · ➕ added unplanned

---

## 1. The eleven non-negotiable components

| # | Component | | Evidence | The deviation, where there is one |
|---|---|:--:|---|---|
| 1 | **Eventstream ×2** | ❌ | Workspace item list, unfiltered, *"Showing 9 items"* — **zero Eventstream items**, read three times on two days | **Never built. Recorded DEGRADED, option 2, decision taken by the user 2026-08-19.** Not on §3's drop list; only the *third*, job-events stream was droppable |
| 2 | Eventhouse / KQL Database | ✅ | `EH_MeridianPay` in the item list; 29.2M rows loaded | — |
| 3 | Update policies + MVs | ✅ | 3 policies `IsEnabled: true`; 3 MVs `IsHealthy` | The dedupe **behaviour** was defective and was repaired out-of-band — §4 |
| 4 | KQL Queryset + functions | ✅ | `KustoQueryWorkbench_1`; 24 functions on disk, 12 counted | The membership of "the 12" was **redefined three times** — §3.3 |
| 5 | Real-Time Dashboard ×3 | ✅ | JSON parses to 3 pages; imported and rendering | Tile content revised four times, 20 → 17 → 14 → **11** |
| 6 | Activator ×4 reflexes | ✅ | 4 rules Running; **a live Teams notification** | Frequency 5-minutely → daily since Session 4 |
| 7 | OneLake availability → Direct Lake | ◐ | Gate C2 PASSED; `EVALUATE dim_estate` → 1,500 rows | **The route is not direct.** It needs a Lakehouse plus a OneLake shortcut — *"a planning miss"*, and the dependency was invisible to Phase 0 |
| 8 | Lakehouse (cold path) | ◐ | `LH_MeridianPay` exists; shortcut surface built | **Dispute batch landing and the cold tables live inside the Eventhouse, not the Lakehouse.** Recorded at the time as *"a Session 3 shortcut, not a substitute — component 8 is still owed"*, and it stayed owed |
| 9 | Power BI report ×2 pages | ✅➕ | 5 pages, 53 visuals, `validate_pbip.py` **0 errors / 1 warning** at close (the warning is the deliberately-declined `ALTTEXT_COVERAGE`) | Over-delivered: 4 contract pages + the mandatory guide page. The drop list was **not** needed |
| 10 | Stream DQ ×6 rules | ✅ | 6 rules persisted, every floor satisfied, `dq_results` verified two-sided | **Rule 2's −2 (8,231 vs 8,233) is unexplained and was carried from Session 3 to Session 7 untouched** |
| 11 | Git integration (RTI ALM) | ✅ | Branch `P25_MeridianPay`, all items Synced | The branch read `(deleted)` between Sessions 2 and 3; **cause never diagnosed**, kept in the record because *"this broke once"* is the useful signal |

**10 of 11.** §8's target row — *11/11, or each degradation documented* — is **missed on the first clause
and met on the second.**

---

## 2. Committed numbers

| Committed | Mandatory / target | Actual | | Basis |
|---|---|---|:--:|---|
| Eventstreams | 2 / 3 | **0** | ❌ | item list ×3 |
| KQL tables | 12 / 12 | **20** (12 counted + 8 working) | ◐ | `E3R:§3`, itemised |
| Materialized views | 3 / 3 | **3** | ✅ | named in DDL; the addendum explicitly refused a 4th and 5th |
| KQL functions | 12 / 12 | 12 counted, **24 on disk** | ◐ | see §3.3 |
| Stream DQ rules | 6 / 6 | **6** | ✅ | `dq_results` = 6, two-sided |
| RTD pages | 3 / 3 | **3** | ✅ | JSON parse |
| Activator reflexes | 4 / 4, ≥1 fired | **4, one fired to Teams** | ✅ | E2 evidence |
| Report pages | 2 / 4 | **5** | ✅➕ | `pages.json` |
| DAX measures | 12 / 20 | **24 written, 24 loaded, read back** | ◐ | 24 loaded over XMLA in one transaction, 0.7 s, format strings carried by TOM; `Precision (Reportable)` reads BLANK unfiltered and 100.0% sliced, which is the guard passing |
| **Spark notebooks** | — / **≤ 2** | **1** | ✅ | *The anti-drift number held.* Against an engine whose every instinct pushes toward Bronze/Silver/Gold notebooks, this project used one |
| Sessions | 8 / 8 | **7 run, Phase 7 outstanding** | ◐ | §5 |

---

## 3. Where the drift actually is

### 3.1 The theme — a deviation with no record until now

§0 and §7 both commit to *"theme `Themes/MyLifeInLegoBricks_Theme.json` … **no new theme JSON**"*.

The delivered report's `report.json` names **`My_Life,_In_LEGO_Bricks___Japa9164530027503082.json`** under
`RegisteredResources`, and carries a second, **`Fluent2-CY26SU07`**, under `SharedResources/BaseThemes/`.
Neither string appears in any `.md` in this project.

**What actually happened, measured rather than assumed:** the registered file is the same theme —
its `name` field reads *"My Life, In LEGO Bricks — Japanese Indigo (Bright)"* — re-registered by Power BI
Desktop under a mangled filename when the user re-applied it through View → Themes → Browse. Desktop added
the Fluent2 base theme at the same time. **No new theme was authored, so §7's clause is satisfied in
substance and violated in the letter.** Recorded here rather than quietly reconciled.

The re-apply is also why the report renders. The embedded theme's `visualStyles["*"]["*"]` still forces
`title` and `visualHeader` onto every visual — and it now carries the
`cardVisual: {"title":[{"show":false}],"visualHeader":[{"show":false}]}` override that Session 7 added to
all 37 engine themes. **The delivered report is therefore a live false-positive control for the new
`THEME_BLANKS_CARDVISUAL` rule: the forced wildcard is present, the override neutralises it, the linter is
silent, and the cards are on screen.**

### 3.2 The report is no longer reproducible from its own generator — measured

`C7_Folder_Disposition.md` claimed `build_report.py` *"regenerates all 65 files byte-for-byte — verified
this session."* That is now false, and the correction is in C7. Measured at close by regenerating into a
scratch directory and comparing the delivered folder against it:

| | Files |
|---|--:|
| Byte-identical | **0** |
| Identical once parsed as JSON (Desktop reserialisation only) | **47** |
| **Semantically changed** | **14** |
| Non-JSON differing (`.platform`, `definition.pbir`) | 2 |
| Only in the delivered report | 3 — `.pbi/localSettings.json`, the renamed theme, the Fluent2 base theme |

The 14 are the user's Desktop layer, and they are not cosmetic noise:

- **`Merchant/Tree`** gained **`expansionStates`** — the decomposition tree's pinned and collapsed levels,
  `store_id` → `merchant_id` → `terminal_id`, all `isPinned: true`. **The generator cannot produce these.**
  A regeneration silently returns the engine's first decomposition tree to an unconfigured state.
- **`Precision/MxCohort`** gained an explicit sort on `Precision (Reportable)` descending, replacing
  `isDefaultSort`.
- **`Estate/CovTier`** had its secondary value axis switched off.
- Ten visuals carry sub-pixel position changes from being dragged (`620` → `706.947…`).

**Consequence, stated plainly:** `build_report.py` remains the source of truth for report *content* — the
Session-7 fixes are all in the delivered file (`ByTier`'s `entity_type` guard is present, `DqKpi` binds
`DQ Rows Flagged`) — but **it is no longer the source of truth for the delivered artefact.** Re-running it
over `06_Report/` would destroy the tree configuration and the sort. That is now written into the handover
as a standing constraint rather than left as folklore.

### 3.3 "The 12 counted functions" was redefined three times

1. `04_functions.kql` defines the 12: reflex ×4 + DQ ×6 + `fn_maturity_cohort` + `fn_issuers_for_estate_selection`.
2. Session 3 restates it as a decision: transform and `dim_estate` build functions are *"infrastructure, not counted."*
3. `01b_dispute_curated_FIX.kql` **demotes `fn_maturity_cohort` to a helper** so that adding `fn_dispute_graded`
   keeps the total at 12 — *"To stay at 12 rather than quietly becoming 13."*
4. The reflex-3 time-travel work adds two more *"uncounted helpers."*

Twenty-four functions exist. Twelve are counted. **The demotion is documented, which is what makes it a
decision rather than a fudge** — but a committed number that is preserved by redefining its membership is
worth naming as such, and this is the naming.

### 3.4 Two drop-list items were dropped in silence — §8's own prohibition

§3's rule is quoted throughout the project: ***"the drop list is expected to be used, and using it is not
a failure. Silently not using it is."***

| Drop-list item | What the record says |
|---|---|
| **Map** — *"first to go"* | **Nothing.** No Map artefact, no Map item, no drop decision anywhere in `00_Plan/` or `09_Closure/`. It simply stopped being mentioned after Phase 0 |
| Report pages 4 → 2 | Not used — 5 delivered. Recorded |
| Job-events Eventstream | Dropped, **recorded loudly** — `raw_job_events` carries 0 rows and `E3R:§4` says so before a reader can discover it by querying |
| Fabric Data Agent | Dropped, **evidenced** — the create dialog's error text and its request ID |
| **Deployment pipeline** | **Nothing.** No mention in any planning or closure document |

**Two of five went unrecorded.** Both are hereby recorded as dropped: the **Map** was never built and is
not part of any export checkpoint's minimum content, which is why nothing missed it; the **deployment
pipeline** needs a second workspace this trial capacity does not have, and §3's own rationale — *"Git
integration alone carries the ALM story"* — is satisfied by component 11. Neither is a loss. **The failure
was procedural, not architectural, and it is exactly the failure §8 names.**

### 3.5 Export checkpoints

| | | Evidence |
|---|:--:|---|
| **E1** (end Phase 2) | ◐ | **No closure entry exists anywhere.** The last dated status is *"E1 ❌ not started — depends on C2's toggle"*; later, only *"E1's Parquet-export half is unblocked."* `C3_Comparison_P24.md` asserts *"E1, E2 done"* — **asserted, not evidenced.** Recorded here as **substantively satisfied by E3's read-back and never formally closed** |
| **E2** (end Phase 3) | ◐ | Closed, then one of its four pieces **withdrawn as false**. Remains closed on the other three; the withdrawal is left visible *"rather than edited away"* |
| **E3** (end Phase 5) | ◐ | **Slipped by one session** and took Phase 6 with it. 6 of 7 items complete at the time of writing; item 2 (RTD screenshots) outstanding |
| §4's *"explicit `.export`… and the export read back"* | ◐ | **Only the mirror half was performed.** Two reasons stated, and the residual risk named: *"If the Eventhouse is deleted, the mirror goes with it"* |

---

## 4. Added unplanned — twenty items, and most of them were repairs

Nothing in the contract asks for any of the following. Grouped by why they exist, because *"unplanned"*
covers two very different things.

**Repairs to something already built (11).** `08_dedupe_fix.kql` and its two helpers ·
`01b_dispute_curated_FIX.kql` · `04b_missing_functions.kql` (six functions silently never created — a
**packaging** fault, found by alphabetical gap analysis rather than by an error) · `09_dq_rules_run_v2.kql`
· `10_streaming_dedupe_maintenance.kql` **plus a formal contract addendum**, still on HOLD, never run ·
`13_alerts_remirror_fix.kql` · `14_alerts_v2_rebuild.kql` and the tables `alerts_v2`,
`alerts_regrade_snapshot`, `alerts_probe` · `15_reflex3_timetravel_grading.kql` · the RTD's
`alerts` → `alerts_v2` repoint.

**New instruments — checks that did not exist before (7).** `check_rtd_queries.py`, with a positive and a
false-positive control and three floors · its `retired_objects.json` rule, added the day a portal drop
broke three tiles the checker had just passed · `12_alert_grading.kql`'s 180-day shifted-window control ·
`guarded_measures.json` + `UNGUARDED_MEASURE_BOUND` · `VISUAL_FORMAT_PROP_UNKNOWN` +
`harvest_formatting_props.py` + a 33-type property reference · the `PAGENAV_ORPHAN_SELECTOR` fix +
`test_lint_rules_p25.py` + P24's 115-visual control corpus · `THEME_BLANKS_CARDVISUAL`.

**Deliverables (2).** Report page 5, *Guide & Data Dictionary* — the mandatory "+1" page. And the
`_with_footers` RTD variant, built to test whether `markdownCard` imports; **still unproven**.

**Corrections to the engine's own record (2).** Two defects fixed in `capture_session_cost.py` — including
a basis line every historical snapshot carried and the code did not implement. And **a correction to
Project 24's delivered closure record**, the first this engine has produced from a later project.

---

## 5. Sessions: three honest readings, because the sources disagree

| Basis | Reading |
|---|---|
| **Sessions started** | **7 of 8.** `_cost/` + six kickoff files + gate-file headers |
| **`C3_Comparison_P24.md` as written** | *"8 → 7 in progress"*, verdict *"P25 well ahead"* — **written mid-Session-7, before E3's residue was known**, and it should be read with that date on it |
| **Work remaining** | **8 at best, with zero slack.** Session 7 must still close E3 item 2, write C4 and C8, run `scrub_check.py`, and close out; Session 8 is Publishing |

§6 said *"the remaining slack is deliberately kept as slack, not spent."* **It was spent** — by E3 slipping
one session, which is also what made Phase 6 capacity-bound against a contract that said it would not be.

Two sources disagree on the comparator: `OC:358` says P24 ran **16** sessions against 11 planned;
`C3_Comparison_P24.md:62` says **15**. **Unreconciled here**; P24's own closure record is the authority and
this project should not adjudicate it from the outside.

**Model routing** (Opus for Sessions 1 and 3 only) is **not verifiable from disk** — `_cost/session-NN.json`
records no model field. Recorded as unverifiable, and worth a field in the next version of the tool.

---

## 6. Which drift was avoidable, and which was discovery

The split matters more than the total, because conflating them produces a useless lesson. The weighting
basis below is **sessions or session-fractions attributable**, taken from the gate file's own session
boundaries — not from a subjective sense of how bad each felt.

### Discovery — the only way the information could have been obtained (≈ 2.2 sessions)

- **The per-batch update-policy defect (≈ 0.5).** Microsoft's documentation describes update policies at
  the level this project used them. That Kusto evaluates them per ingested batch, and that the generator's
  own unshuffled append guarantees the split, is a genuine platform contract that had to be discovered by
  running it. The three platform limits hit in getting the fix in — `ClientAdminCommandFromQueryBadRequest`,
  ingestion throttling, `LowMemoryCondition` — are the same class.
- **The mirror's failure mode (≈ 1.0).** That `.set-or-replace` on a table whose OneLake mirror is already
  live produces a permanently jammed mirror is not documented anywhere. Five hypotheses were formed and
  five refuted; **that is what discovery looks like from the inside.**
- **Reflex 3's right-censoring (≈ 0.4).** An `arg_max` materialized view cannot time-travel. Reasonable
  design; the consequence only appears when you try to grade it against a frozen backfill.
- **Gate C4, C1, and the Capacity Metrics instrument (≈ 0.3).** Region availability, SKU gating and a
  metrics app that does not see your own Eventhouse are all *findings*, and all three were closed with
  evidence at near-zero build cost.

### Avoidable — the information was available and nobody looked (≈ 1.6 sessions)

- **The two Eventstreams (≈ 0.6).** Six sessions. The workspace item list was one click away for all of
  them. Nothing was hard here; the *enumeration* was never done.
- **The PBIR validator, five sessions unrun (≈ 0.4).** One `npm install -g`, ~2 seconds, and **the install
  line was already in the engine's own SKILL.md at line 148**. It cost 26 first-pass errors, 24 of them a
  single block of invented `matrix` property names that `formatting describe-object` would have refused.
- **The cost tooling, recorded absent by two consecutive sessions (≈ 0.2).** The tool was on the device the
  whole time. **Two cost snapshots are permanently lost** and §7's *"8 of 8"* is now unreachable.
- **Kickoff defects (≈ 0.2).** A cited mockup path that did not exist; a scope that contradicted the
  contract; a wrong precondition figure. All three were caught by reading the artefact rather than the
  brief, and the rule that came out of it — *handover beats kickoff* — is now in `CLAUDE.md`.
- **The model's zero relationships (≈ 0.2).** Two visuals shipped reading a constant numerator over a
  varying denominator. `validate_pbip.py` passed it, the PBIR CLI passed it, and a 19/19 measure-projection
  check passed it, **because none of them asks whether the model can join.** Avoidable by one
  `EVALUATE SUMMARIZECOLUMNS` against the live model, which is now the recommendation.

**The split is roughly 58% discovery, 42% avoidable**, and the honest caveat is that the boundary is not
crisp: the mirror jam was discovery, but *taking the same reading twice five hours apart* — which is what
finally distinguished "slow" from "stuck" — was available on day one and cost a session to learn.

### The one thing that was neither

**Session 7 running capacity-bound.** The contract put Phase 6 in a session that needed no capacity. It ran
under capacity pressure because E3 slipped. That is not avoidable drift and it is not discovery — it is a
**dependency the plan created and then did not track**, and it is the same shape as Phase 0 writing a gate
that depended on a component nobody had built.
