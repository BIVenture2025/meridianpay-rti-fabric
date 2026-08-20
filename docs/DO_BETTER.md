# C5 — What to do better next project

**Project 25 (Meridian Pay) · Skill 10 · written Session 7, 2026-08-19**

> **Diagnose before prescribing.** For each item below the cause is established from the record
> first — a `§`, a file, a dated line in `Gate_Check_Results.md` — and only then is a fix proposed.
> P24's notebook churn looked like a planning failure and wasn't; the same trap applies here.

---

## 0. The one pattern that explains most of this document

**Six separate incidents in this project are the same failure: a negative reported from an inability
to look.** Guide §118a already names the shape. `OUTCOME_CONTRACT.md` §9 audit finding #1 is an
instance of it — an auditor with no device access declaring two engine files absent that were on
disk. The contract recorded that finding as *rejected*, in writing, at Session 1.

**And then the project did it six more times from the inside.**

| # | Session | The negative asserted | What was actually true | Cost |
|---|---|---|---|---|
| 1 | 1–5 | *"the official PBIR validator cannot run here"* — never stated, just never run | `npm install -g @microsoft/powerbi-report-authoring-cli`, ~2 seconds; the install line is in the engine's own `powerbi-report-authoring/SKILL.md` line 148 | 5 sessions of a mandated check not running |
| 2 | 1–5 | same, sharper | **P24 had already run this exact CLI** and recorded it in `B2_Plan_vs_Actual.md` | the knowledge existed one project away |
| 3 | 4 | *"no `capture_session_cost.py`-compatible tooling in this environment"* | tool on the device (13,206 b), transcript in the container | session 4 cost data lost permanently |
| 4 | 5 | same claim, repeated | same | session 5 cost data lost permanently |
| 5 | 5 | *"the mirror is catching up"* | it had moved **zero bytes in five hours** | ~1 session of blocked work |
| 6 | 5 | *"decompositionTreeVisual exists nowhere in this engine"* — **true**, but read as "so it must be designed from scratch" | `catalog describe` answered every role, property and enum in **2 minutes** against a **1-hour** budget | 58 minutes, recovered |

**Incidents 3 and 4 are unrecoverable.** Sessions 4 and 5 are the two most portal-heavy sessions in
the project and the ones that would most sharply test C6's browser hypothesis. Their data is gone
because a tool that was present was recorded as absent, twice, without either session recording what
it ran to find out.

### The rule, and it is one line

> **Before recording a tool, file or capability as unavailable, record the command you ran to find
> out. If you cannot name the command, you have not established absence — you have established that
> you did not look.**

**Cost to adopt: zero.** It is a sentence in `CORE_RULES.md` §1 and one line in the session-close
checklist. **Expected value: highest in this document**, because it is the only item here with six
measured instances in one project and a prior recorded instance in the contract that everyone read.

---

## 1. What I did wrong

Ranked by cost, each with the record that proves it.

### 1.1 I closed a checkpoint on an assertion I had not counted — and flagged the check myself, then skipped it

**Evidence.** Session 4 closed **E2** with *"All four mandatory pieces … satisfied: Activator rule
configs + evidence of firing, **Eventstream definitions (Git-synced)**, alerts/ground_truth/
dim_estate."* The workspace contains **zero Eventstream items**, read unfiltered on 2026-08-19 and
re-read independently in Session 7 (*"Showing 9 items"*, nine rows, no Eventstream).

**And the same session wrote the check that would have caught it, then did not run it.**
`Gate_Check_Results.md`, Session 4, ends: *"the `KustoQueryWorkbench_1` queryset was saved via Ctrl+S
mid-session but its post-edit sync status is unconfirmed — **worth a 30-second check in Source
control before calling E2 closed**."* E2 was called closed.

**Diagnosis.** Not carelessness about Eventstreams specifically. The cause is that **nothing in the
session-close checklist required enumerating workspace items against contract §3.** The spec
reconciliation gate mandates re-reading an artefact before writing a spec section about it; it does
not mandate counting the *component inventory* unless a checkpoint happens to ask for an item list.
E3 does ask, which is why the gap surfaced at Session 6 rather than Session 9 — one phase late, but
before publication, which is exactly why E3 sits where it does.

**Fix — the spec reconciliation gate gets a fifth clause.** *Every session, count the workspace
items against contract §3 and record the count. A component's existence is a `.show`/item-list row,
never a memory of having planned it.* **Cost: 30 seconds a session.** Expected value: high — it is
the only item in this project that reached backwards and invalidated a *closed* checkpoint.

### 1.2 I invented 24 property names against a rule that already forbade it

**Evidence.** 24 of 26 first-pass PBIR errors were one block: `fontSize`, `bold`, `stepped`,
`rowSubtotals`, `columnSubtotals` and a bare `fontColor` under `values` on a matrix. Verified against
the CLI in Session 7: `matrix.values` carries **`fontColorPrimary`/`fontColorSecondary`**, and no
matrix object carries any of the other five.

**Diagnosis.** CORE_RULES_ESSENTIAL §3 already ends *"Anything else — ask the CLI. Do not assume."*
The rule was not missing, not ambiguous, and not disagreed with. **It was simply not mechanical**,
and a prose rule that costs a tool call is skipped under time pressure every time.

**Fix — done this session.** `VISUAL_FORMAT_PROP_UNKNOWN` in `validate_pbip.py`, driven by
`_ENGINE/reference/visual_formatting_props.json`, itself **harvested from the CLI** by
`_ENGINE/tools/harvest_formatting_props.py` across 33 visual types. Positive control: all 7 invented
names fire. False-positive control: **0 findings over 1,019 real formatting properties** across P24's
and P25's delivered reports. **Cost to adopt: already paid.**

**A near-miss worth recording.** My first draft also flagged unknown *objects* and produced **94
false positives** on those same two delivered reports, because `general` legitimately exists in both
the `/visual.objects` and `visualContainerObjects` namespaces. It was caught by running the
false-positive control before shipping, which is the only reason this section is not describing a
new defect instead of a new rule.

### 1.3 I shipped a lint rule with one control, and it cried wolf on the reference implementation

**Evidence.** `PAGENAV_ORPHAN_SELECTOR` fired **9× on P24's delivered, published report** and 5× on
P25's — on the engine's own proven page-navigator pattern, every time. Reproduced exactly in Session
7 against a reconstruction of P24's 115 delivered visuals.

**Diagnosis.** `feedback_lint_rules_need_both_controls` already exists as a memory. The rule was
written from the failure it was meant to catch and never run against a known-good report.

**Fix — done this session**, plus `_ENGINE/tools/test_lint_rules_p25.py`, which carries **both**
controls for all three rules and asserts a **floor** on each false-positive control (5 and 9 real
navigators walked; 267 and 752 real properties walked) so that "0 findings" cannot be satisfied by a
scan that never ran.

### 1.4 I gave the user a portal path that was wrong, for a gate the path could not have tested anyway

**Evidence.** `Gate_Check_Results.md` Session 3 close: *"The user was told to look for 'Eventhouse'
under Power BI → Get data. What the Power Query New source → Microsoft Fabric tab actually offers is
Dataflows · Datamarts (Preview) · KQL Database (Preview). The user correctly reported 'there's no
Eventhouse'."*

**And the deeper miss in the same paragraph:** Power Query builds an **Import** model. C2 is about
**Direct Lake**, which reads Delta files and does not go through Power Query at all. The route needs
a **Lakehouse** — component 8 — *"which the contract already commits to but which has NOT been
built. C2 was therefore never testable this session regardless of mirroring."*

**Diagnosis.** The instruction was written from how the product is *described* rather than from its
dependency graph. A one-line dependency check — *what does this gate need to exist first?* — was not
in the gate table.

**Fix.** Every Phase-0 gate row gains a **`Depends on`** column naming the components that must
exist before the gate is runnable. **Cost: one column, filled at intake.** This is cheap and it is
the second time in this project that a gate was attempted before its precondition existed (C2, twice).

### 1.5 I read a progress indicator once and drew a conclusion from it

**Evidence.** Session 5 read `21/21 · 99% · 171.6 KB pending` immediately after ingesting
`alerts_v2` and concluded the mirror was catching up. Session 6 read **the same 171.6 KB, the same
99%, the same 11-minute latency** roughly five hours later.

**Diagnosis.** Reasonable on the evidence available at the time. The defect is not the inference; it
is that **one reading cannot distinguish "slow" from "stuck"** and nothing required a second.

**Fix — the extension to `feedback_stop_hypothesising_read_a_layer_out`.** *A progress indicator read
once is a snapshot; the same indicator read twice, spaced, is a derivative — and only the derivative
distinguishes slow from stuck. Never conclude "catching up" from a single reading.* **Cost: one extra
reading, deferred.** Expected value: high — this single missing reading is the direct cause of the
blocker that has now cost two sessions and E3's schedule.

### 1.6 I wrote a hypothesis into a tool's docstring before testing it — this session

**Evidence.** Session 7. `session-06.json` derives 92.15M cache-read/hour against 39.6–41.3M for
sessions 1–3, and 9.1 s/turn against 17.9–29.2. I wrote *"Project 25's session-06.json is the live
instance"* of a partial-transcript defect into `capture_session_cost.py`'s docstring **as fact**, then
ran the control: session 7, against a verified sole-candidate transcript, produced **7.5 s/turn and
81.9M cache-read/hour** — session 6's profile. The hypothesis was refuted by the next command I ran.

**Diagnosis.** §1.5's failure with the roles reversed: I had a plausible mechanism and started
writing the record before taking the reading that could falsify it. The docstring is corrected and
now carries the refutation in full, including the wrong turn.

**Fix.** Nothing new is needed — §1.5's rule covers it. It is listed because *the same session that
diagnosed the pattern committed it*, which is the most useful evidence there is that a prose rule
does not change behaviour on its own.

### 1.7 Two planning documents disagreed, and only luck picked the right one

**Evidence.** `KICKOFF_SESSION_06.md` Route A step 2 said *"toggle OneLake availability off, then
back on"*. `HANDOVER.md` said, in bold, *"**Wait and re-read** — do NOT toggle OneLake availability."*
Session 6 resolved it by taking the free reading first — which both documents happened to agree on —
and that reading changed the answer.

**Diagnosis.** Guide §114g already forbids embedding the kickoff inside the handover, on the grounds
that a duplicate goes stale. This is the *same class* one level up: two documents, written at
different moments, both giving instructions for the same job, with no rule about which wins.

**Fix.** The conflict-resolution order in `CLAUDE.md` gains a line: **the kickoff states the plan;
the handover states the state; where they disagree about an action, the handover wins, because it
was written later and against the artefact.** **Cost: one line.**

---

## 2. What the user did that cost time

Skill 10 says this is the section people soften and the one worth most. **I searched for it
deliberately** — `grep -n -i "the user\|you chose\|user decided\|user asked"` over all 2,045 lines of
`Gate_Check_Results.md`, plus the six session handovers — and I am reporting what that search
returned rather than what would make the section look balanced.

**It returned two items, and one of them is not really the user's.**

### 2.1 A portal setting was changed outside the record, and later cost a session's worth of suspicion

**Evidence.** The Activator rules were changed from 5-minutely to daily at the close of Session 4.
When `alerts` went unreadable on 2026-08-19, that change was the obvious suspect, and Session 5 had
to refute it on three independent grounds — wrong mechanism (Activator issues read queries and has no
path to a Delta mirror), wrong direction (5-minutely → daily *reduces* load), and wrong time (the
rules changed on 2026-08-18; the fault appears only after `12_alert_grading.kql` ran on 2026-08-19).

**The verdict is not what it looks like.** The change itself was **correct** — it is exactly the
right instinct on a trial capacity. And **asking whether it caused the breakage was correct too**;
the gate file says so explicitly: *"'we changed something yesterday and something broke today' is
exactly the shape of a false lead that costs a session."*

**What cost time is that the change was not written down when it was made.** The refutation took
three arguments and a timeline reconstruction that a single dated line — *"2026-08-18, Activator
rules 5-min → daily, reason: trial CU"* — would have made unnecessary.

**Fix, and it is mine to build, not yours to remember.** `SESSION_NN_PORTAL_STEPS.md` gains a
standing final section: **"Portal changes made this session"** — one line each, dated, with the
reason. **Cost: seconds.** The asymmetry is the point: you make the change in ten seconds and I spend
a session reconstructing when it happened.

### 2.2 The screenshot channel — a real cost, correctly attributed to my rule and not to you

**Evidence.** Several of this project's gate closures rest on an image: C0's capacity reading
(*"measured from the user's screenshot of Admin Portal → Capacity settings → Trial"*), C2's
`.show tables` → "No Tables" (*"screenshotted by the user"*), and Git item/commit state at two
separate closes.

**This is not a user error.** `CLAUDE.md`'s own Standing Rules say *"Screenshots the user supplies
are free to me and are the preferred verification channel."* You followed the engine's instruction
exactly.

**The rule has a blind spot.** A screenshot cannot be re-read by a later session, diffed, or checked
by a linter — only my description of it survives, and the description is what enters the record. For
portal state with no API that is the right trade. For **`.show tables`**, which is a KQL query
returning text, it is not: the query result could have been pasted, stored, and re-run.

**Fix — sharpen the rule rather than drop it.** *Screenshots are the preferred channel for portal
**configuration state**. Anything a query returns is pasted as text, never as an image —
including `.show` commands, row counts, and item lists.* **Cost: none; it is usually easier for you
too.**

**And to be explicit about what the search did not find:** no instance where a decision you were
asked for was left open and the build then guessed at it, and no instance where you overrode a
correct recommendation. Sessions 4 and 6 each put a set of decisions to you at session open and
every one came back before building started.

---

## 3. What the user did that was right and I did not

### 3.1 You reported the absence I had wrongly predicted, precisely, and it was the more useful half

Session 3 told you to find "Eventhouse" in the Power Query source picker. You reported *"there's no
Eventhouse"* — flatly, without trying to make my instruction work.

**That is the behaviour §0 of this document is entirely about, and you did it without being asked.**
You looked, you named what you saw, and you reported the negative *with its method attached*. I spent
five sessions failing to do that with an npm package. **The contrast is not a rhetorical flourish —
it is the same test, and you passed it while the engine's own audit-finding-#1 warning was sitting in
the contract.**

### 3.2 You insisted on the re-read before the toggle

`HANDOVER.md`'s *"wait and re-read"* is the instruction that turned a 1.8 GB blind re-mirror into a
five-hour-apart second reading that **diagnosed the fault**. The kickoff pointed the other way. Taking
the free reading first is the cheapest possible first action and it changed the answer.

### 3.3 You chose both RTD reference windows

Offered "the quiet default window" or "a busy trading hour", you took **both**. The default matches
every number in the gate file and keeps the reflex-3 feed populated; the busy hour makes auths/sec
and the decline sparkline mean something. **Two true readings of the same estate at different hours
is a better artefact than either alone**, and I had framed it as an either/or.

---

## 4. The changes, ranked by expected value

| # | Change | Evidence | Cost to adopt | Where it lands |
|--:|---|---|---|---|
| 1 | **Record what you ran to find out, before recording anything as absent** | 6 instances this project; 2 unrecoverable; 1 already rejected in the contract at Session 1 | one sentence | `CORE_RULES.md` §1 + session-close checklist |
| 2 | **Count workspace items against contract §3 every session** | E2 closed on an uncounted component; survived 6 sessions | 30 s / session | spec reconciliation gate, 5th clause |
| 3 | **Take the second reading before concluding from a progress indicator** | the single missing reading that cost E3 its schedule | one deferred reading | `CORE_RULES.md`; extends `feedback_stop_hypothesising_read_a_layer_out` |
| 4 | **Install the PBIR CLI at the start of any session that writes PBIR** | 5 sessions without a mandated check; ~2 s to install | one line | `CORE_RULES_ESSENTIAL.md` §4 opening |
| 5 | **`VISUAL_FORMAT_PROP_UNKNOWN`** | 24 of 26 first-pass errors, all one cause | **done** | `validate_pbip.py` + harvested reference |
| 6 | **`PAGENAV_ORPHAN_SELECTOR` fixed; both controls mandatory** | 9 false positives on a published report | **done** | `validate_pbip.py` + `test_lint_rules_p25.py` |
| 7 | **`UNGUARDED_MEASURE_BOUND`** | the guard held here by review, not by machine | **done** | `validate_pbip.py` + `guarded_measures.json` |
| 8 | **`Depends on` column on every Phase-0 gate** | C2 attempted twice before its precondition existed | one column | Skill 8 gate table |
| 9 | **"Portal changes made this session" section** | one undated change cost a three-argument refutation | seconds | `SESSION_NN_PORTAL_STEPS.md` template |
| 10 | **Query results as text, screenshots for configuration only** | `.show tables` recorded as an image | none | `CLAUDE.md` Standing Rules |
| 11 | **Handover beats kickoff on actions** | two documents, opposite instructions, same job | one line | `CLAUDE.md` conflict-resolution order |
| 12 | **Retire "UI-driving days cost 3.5× more per hour"; stop ranking the two cost levers** | C6 Results 1 and 2 | edit two documents | `project23-cost-analysis.md`, `CLAUDE.md` |
| 13 | **Snapshots record the transcripts they did not read** | the "largest of N candidates" note was false — it sorts by mtime | **done** | `capture_session_cost.py` |

**Items 5, 6, 7 and 13 are already implemented and committed to the device this session**, with
9/9 controls green in `09_Closure/_controls/lint_rule_controls.txt`. Items 1–4 and 8–12 are
one-line documentation changes and are applied as part of this closure's dual-write pass.

---

## 5. What this section could not establish

- **Sessions 4 and 5 have no cost data**, so no claim here about their tool mix, duration or burn is
  measured; where they appear above it is from `Gate_Check_Results.md` prose, not from a snapshot.
- **I can directly observe only Session 7.** Everything about sessions 1–6 is reconstructed from
  artefacts — the gate file, the handovers, the portal-step documents and the `_cost/` snapshots.
  Where those disagree with anyone's memory, they are what I used, and where they are silent I have
  said so rather than filled the gap.
- **No counterfactual was run for any item above.** Every "would have caught it" is an argument from
  the mechanism, not a measurement — with the two exceptions of the lint rules, where the controls in
  `09_Closure/_controls/` are an actual before-and-after on real delivered files.
