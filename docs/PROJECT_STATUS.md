# PROJECT_STATUS.md — plan vs built, honestly

**Project 25 · Meridian Pay · Fabric End-to-End Real-Time Payments Risk**
Status as at **2026-08-20, published** · required by `OUTCOME_CONTRACT.md` §7

> This file exists because Project 23 was labelled `PLANNING` for months after it had been built and
> published, and had itself flagged the label as an outstanding fix. **A status file that is not
> current is worse than none**, so this one carries its date in the first line and names what is
> unfinished before it names what is done.

## Status: **PUBLISHED — 2026-08-20.**

Live, and each of these was read back rather than assumed:

| | |
|---|---|
| Repository | <https://github.com/BIVenture2025/meridianpay-rti-fabric> — public, 89 files, 6 folders |
| Guide | `…/meridianpay-rti-fabric/docs/guide.html` — 9 steps, 9 figures, a **Get the code** section with a working ZIP link |
| Architecture · Closure | `…/docs/ARCHITECTURE.html` · `…/docs/CLOSURE.html` — the closure page carries all **9** tabs |
| Portfolio card | `biventure2025.github.io` — card **05**, with the site-local guide copy and its eight figures |

**One thing is NOT independently verified:** that the portfolio card *renders* on the live site. The
card is JavaScript-rendered from `data.js`, the fetch tool cannot execute it, and this container
cannot reach the host to drive a browser. The same `data.js` and `index.html` bytes were rendered
locally and the card was correct; the live render was left to the author's own eyes, and is recorded
here as that rather than as a check that was run.

| Phases 0–5 | **complete** |
| Phase 6 (Closure, Skill 10) | **complete** — C1, C2, C3, C5, C6, C7, C8 written; `Project25_Closure.html` built |
| Phase 7 (Publishing, Skill 9) | **complete.** Portfolio card, 89-file repository, rebuild guide and pitch deck built, gated and pushed 2026-08-19/20 |
| Export checkpoints | E1 ◐ · E2 ◐ · **E3 ✅ CLOSED 2026-08-19, 7 of 7** — see below |
| Live estate | **up.** Trial capacity `FTL64`; the Eventhouse, dashboard, model, report and four Activator reflexes are all running |

---

## What is built and working

**Ten of the eleven non-negotiable components.** An Eventhouse holding 29,158,765 rows across 20 KQL
tables; three update policies and three materialized views doing the work Silver and Gold notebooks
would normally do; twelve counted KQL functions; six stream data-quality rules with independent
checks and floors; a three-page Real-Time Dashboard; four Activator reflexes, one of which has fired
end-to-end into Teams; a Direct Lake semantic model with **no Gold notebook underneath it**, carrying
24 measures and validated relationships; a five-page Power BI report that passes both validators at
**0 errors**, with one deliberately-declined warning, including this engine's **first working `decompositionTreeVisual`**; and Git
integration with every item definition on disk.

**One Spark notebook.** The contract's anti-drift number was ≤ 2. Against an engine whose every
instinct pushes toward Bronze/Silver/Gold notebooks, this project used one.

---

## What is NOT built, stated before anything else

| | |
|---|---|
| **Component 1 — Eventstream ×2, mandatory** | **NOT BUILT.** Zero Eventstream items exist in the workspace and none ever did — read unfiltered three times across two days. Recorded **DEGRADED**, decision taken by the user 2026-08-19. It is **not** on §3's drop list; only the third, job-events stream was droppable, and that one was dropped and recorded |
| §7 — *"2 mandatory Eventstreams live… evidenced by query"* | **NOT MET.** Recorded unmet, not reinterpreted |
| §7 — *"both producer routes proven"* | **PARTIALLY MET.** The Spark backfill route is proven end to end; the live-replay route has code (`01_Source/generator/live_replay.py`) and no Eventstream to replay into |
| §8 — components complete | **10 of 11**, against a target of 11 of 11 or each degradation documented. First clause missed, second met |
| §8 — browser share of tool calls | **19% against a ≤10% target.** Measured, over, recorded |
| §8 — validator errors, first pass | **26**, against a target of 0. All 26 real; 24 were one block of invented `matrix` property names |
| §7 — cost snapshots, 8 of 8 | **6 of 8 sessions captured.** Sessions 4 and 5 are lost and unrecoverable — the tool that would have captured them was recorded as absent by two consecutive sessions while sitting on the device. Session 8 was captured, and its snapshot carries `partial: true`: this session's transcript also begins at a compaction boundary |
| §4 — the explicit `.export` to OneLake | **Not run.** Only the Delta-mirror half was performed. Two reasons stated and the residual risk named in `00_Plan/E3_Read_Back_Results.md` §6 |

---

## Export checkpoints

- **E1** — substantively satisfied by E3's read-back; **never formally closed.** No closure entry exists in the record.
- **E2** — **closed**, with one of its four pieces later withdrawn as false. The withdrawal is left visible in the gate file rather than edited away.
- **E3** — **CLOSED, 7 of 7, 2026-08-19.** Six screenshots: three pages × two reference windows. E3 slipped one session past its contracted end-of-Session-6 deadline, which is what made Phase 6 run capacity-bound against a plan that said it would not.

---

## What Session 8 produced, and what is left

| Deliverable | State |
|---|---|
| Portfolio card (`data.js`) | **Written to the Website folder.** 15 projects, P25 at no. 05, `services` untouched, validated by parsing rather than by eye |
| Architecture diagram (`meridianDiagram`) | **Written.** 5 lanes, 10 links, 16 rects, 15 connectors, and no connector routes through a box |
| GitHub repository | **Assembled and gated at 89 files.** `check_rebuild_materials.py` returns *ALL REBUILD MATERIALS PRESENT, NON-EMPTY AND SCRUBBED*, 0 BLOCK instances |
| Rebuild guide | **Built.** 9 steps, 17 traps, 9 figures, 13 anchors. Written to both the repository (`docs/guide.html`) and the Website folder (`fabric-meridianpay-guide.html`), with its eight figures |
| Pitch deck | **Built.** 9 core slides plus appendices A1–A8; three rounds of adversarial visual QA on the rendered slides |
| **Publication** | **DONE, 2026-08-20**, in three pushes: the repository, a correction to it, and the portfolio card. Pages serves branch `main`, folder `/ (root)`. `RUN_THIS_TO_PUBLISH.md` now carries the *update* path as well as the first-publish one |

### Fabric source control

`KustoQueryWorkbench_1` and `RTD_MeridianPay` read **Uncommitted** through Session 7 and were flagged
twice. The user reports both committed on 2026-08-19. **Recorded as reported, not as read** — this
file has not itself opened the source-control panel since, and the distinction is the whole point of
the file.

---

### A defect caught at the publishing gate, and the gate that now catches it

Five README links, the portfolio card and the publish instructions all pointed at
`biventure2025.github.io/meridianpay-rti-fabric/guide.html` while the file sits at
`docs/guide.html`. **Eight dead links, and the publish gate passed them**, because *"we do not fetch
external URLs"* had been allowed to mean *"we do not look at them at all"* — a Pages link into the
repository being published is the one external link that is checkable entirely offline.

`check_rebuild_materials.py` now resolves every such link against the repository tree and fails when
no single Pages serving folder resolves them all, with three new self-test controls (13 in total).
`RUN_THIS_TO_PUBLISH.md` now names the Pages source folder explicitly, because the ambiguity that
made the old links *arguably* valid is itself the thing to close.

---

## Open items a reader should know about

1. **The Issuer Performance anomaly band cannot span the backfill.** Measured: `make-series` at 1h ×
   24 issuers over ~89 days returns **152,640** points against a **50,000** recommended maximum
   (3 series × 50,880). **Not fixed** — re-binning by window width would silently change a contracted
   analysis. It is a short-window instrument; Window A is its evidence window.
2. **DQ rule 2's shortfall of 2** (8,231 against 8,233) — raised in Session 3, carried untouched to Session 7. An open question, never a pass.
3. **`10_streaming_dedupe_maintenance.kql` is on HOLD and has never been run.** It stage-replaces two curated tables that carry live mirrors — the exact operation that cost this project two sessions.
4. **`14_alerts_v2_rebuild.kql` STEP 5 is unexecutable** — `.rename tables` is refused while a mirroring policy is enabled.
5. **`build_report.py` no longer reproduces the delivered report.** It is still the source of truth for content; the delivered folder additionally carries the user's Desktop layer, including the decomposition tree's pinned expansion states, which the generator cannot emit. Regenerate to a scratch path and diff — never in place.
6. **`RTD_MeridianPay_with_footers.json`** — the `markdownCard` tile type has never been proven to import. One import settles it.
7. **`_to_delete/` holds two report snapshots that must NOT be deleted** — they are the only copy of the pre-decoration state. They belong in `_Archive/06_Report/`.

---

## Where the record lives

| | |
|---|---|
| The contract | `OUTCOME_CONTRACT.md` — Rev 3 plus the 2026-08-18 addendum |
| Every gate, reading and correction | `00_Plan/Gate_Check_Results.md` |
| E3's evidence | `00_Plan/E3_Export_Checklist.md` · `00_Plan/E3_Read_Back_Results.md` |
| Closure analysis | `09_Closure/` — C1, C2, C3, C5, C6, C7 |
| Frozen controls | `09_Closure/_controls/` |
| Cost | `_cost/session-NN.json` — and read the `partial` flag before quoting any figure |
| Portfolio deliverables | `06_Portfolio/` — deck and its generator · `07_Published_GitHub/` — the exact mirror of what will be public |
| Architecture | `00_Plan/Project25_Architecture.html` |
