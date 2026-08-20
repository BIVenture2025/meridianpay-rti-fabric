# C8 — Cost analysis and the ledger row

**Project 25 · Meridian Pay** · `capture_session_cost.py --merge` over `_cost/`, 2026-08-19
Ledger row appended to `_ENGINE/reference/PROJECT_COST_LEDGER.md`

> **Read the caveats before the totals.** Every one of them is printed by the tool, on the run, above
> the numbers — not discovered here.

```
  [!] MISSING SESSIONS: 4, 5 — totals below are a FLOOR, not a total.
  [!] PARTIAL SESSIONS: 7 — context compaction truncated the transcript;
      those sessions' turns, hours and tokens are FLOORS for themselves.
  [?] COMPACTION UNKNOWN: 1, 2, 3, 6 — captured before this tool could detect it.
  [+] SUBAGENTS: 3 transcript(s) in session 7 — 21,910,540 cache-read,
      real spend on the same task, NOT included in the totals below.
```

---

## 1. The floor

| | Figure | What it is |
|---|--:|---|
| Sessions captured | **5 of 7** | 01, 02, 03, 06, 07. Sessions 4 and 5 are **lost and unrecoverable** |
| Active working time | **7.5 h** over 9 sittings | Excludes gaps > the tool's idle cap — this is time *working*, not elapsed |
| Assistant turns | **1,415** | |
| Tool calls | **838** | |
| Browser share | **17%** | Against a **≤10%** target. **Over, and recorded over** |
| Output tokens | **1,892,245** | |
| Cache-write tokens | **10,187,232** | ~12.5× the unit price of a read |
| Cache-read tokens | **348,635,249** | |
| **Cache-read per turn** | **246,385** | The scale-free number. Project 23's single session: **478,216** |
| Subagent cache-read | **21,910,540** | Session 7 only, and **invisible to every snapshot this engine has ever taken** until today |

**Three independent reasons the totals are a floor, and it matters which:**

1. **Two whole sessions are missing.** ~29% of the project by session count. Sessions 4 and 5 were the
   Activator and RTD/model sessions — Session 5 in particular carried the mirror blocker and was long.
   The true project total is materially higher than 348M cache-read.
2. **Session 7 is a compaction fragment.** Its transcript *begins* with a compaction boundary at 08:17
   on a session that started at 04:36. Its 247 turns and 0.9 h describe the tail only.
3. **Four sessions are compaction-*unknown*.** They were captured before the tool could detect it, so
   they are reported as unknown rather than as clean. *We did not look* is not *we looked and it was
   fine* — guide §118a, applied to this project's own instrument.

---

## 2. Per session — and what the shape says

| S | Phase | Turns | Active h | Cache read | **cr/turn** | Browser % |
|---|---|--:|--:|--:|--:|--:|
| 1 | 0 Architecture + gates | 176 | 0.9 | 36,059,146 | **204,882** | 0% |
| 2 | 1 Gates · Git · generator | 380 | 1.9 | 78,022,700 | **205,323** | 19% |
| 3 | 2 KQL transformation + DQ | 404 | 3.3 | 129,600,921 | **320,794** | 30% |
| 4 | 3 Activator reflexes | — | — | — | — | — |
| 5 | 4 RTD + Direct Lake model | — | — | — | — | — |
| 6 | 5 Power BI report → E3 | 208 | 0.5 | 48,476,312 | **233,059** | 32% |
| 7 | 6 Closure + E3 close | 247 | 0.9 | 56,476,170 | **228,648** | 0% |

### The split-session hypothesis, tested on this project's own data

The engine's standing claim is that splitting a build across phase-boundary sessions keeps context cost
flat instead of letting it compound. The quantity that tests it is **cache-read per turn**, because it
is scale-free — a longer session has more turns, but if context is being managed, each turn should not
be dragging a larger tail.

**The column does not rise.** 204,882 → 205,323 → **320,794** → 233,059 → 228,648. Four of the five sit
in a narrow 205k–233k band; the outlier is **Session 3**, the longest session in the project (3.3 active
hours, 404 turns, and the session that hit three platform limits in sequence).

**The honest reading is that the hypothesis is not falsified and is not confirmed either.** With two
sessions missing and one a compaction fragment, five points is not a test — it is a shape. What can be
said with the data present:

- **Every session is well under Project 23's single-session 478,216**, which is the comparison the
  engine set for itself. On that specific comparison the split looks good.
- **Session 3's excursion correlates with session length, not with session number**, which is the
  opposite of what "context compounds across sessions" predicts. If the driver were accumulation, S6 and
  S7 would be the expensive ones. They are not.
- **A confound that cannot be removed from this data:** Sessions 1 and 3 ran on Opus and the rest on
  Sonnet, and `_cost/session-NN.json` **records no model field**, so the routing cannot even be verified
  from disk, let alone controlled for. Recorded as a defect in the instrument, not as a result.

---

## 3. Browser share — 17%, against ≤10%

| Session | Browser % | What was happening |
|---|--:|---|
| 1 | 0% | offline architecture |
| 2 | 19% | portal gates C0–C4 |
| 3 | 30% | Capacity Metrics, and a viewport that could not be pixel-fought |
| 6 | 32% | the OneLake pane, read twice five hours apart |
| 7 | **0%** | everything through files, XMLA and written click-steps |

**The target was missed, by 7 points, and the miss is concentrated in exactly the sessions that had to
read a portal panel no API exposes.** Session 7 — the heaviest closure session, 154 tool calls — ran at
**zero** browser share, because every piece of portal work was handed to the user as written steps and
every read came back as a query result or a screenshot.

That is the lever, and it is not "click less". It is **"is there a surface that answers this without a
click"**: XMLA answered the measure load and the model read-back; a KQL union answered the table
inventory; the item list answered the component count. The three sessions that went over are the three
where the answer genuinely sat behind a cross-origin iframe.

---

## 4. The two blind spots this analysis found in its own instrument

Both were found by *running* the tool at close, not by reading it. Both are fixed, with six controls
frozen at `_controls/cost_tool_compaction_subagents.txt`. Full write-up in guide **§125**.

**Context compaction truncates the transcript.** A compacted session's `.jsonl` is rewritten from the
boundary; everything before it leaves disk. Every long session's snapshot has silently been a tail.
**This is the same family as the *"largest of N candidates"* basis line corrected earlier today: a
number that looks like a total and is not one.** Snapshots now carry `partial: true` and the merge says
so.

**Subagent tokens appear in no snapshot ever taken.** Session 7's three research agents carry **21.9M
cache-read** — 39% of the session's own visible 56.5M, on top of it. Every cost figure this engine has
recorded for any project that used subagents is understated by an unknown amount.

They are reported **separately, never folded in**, because folding them in would silently change what
every historical snapshot's numbers mean. And the subagent **output** figure is refused rather than
printed: 572 / 287 / 796 tokens across 43 / 31 / 96 assistant records, against the Agent tool's own
returned 203,865 / 126,839 / 301,047. **A figure that cannot be reconciled is not published as a
figure; the discrepancy is published instead.**

---

## 5. What the cost bought

Comparison is against what the project produced, not against a budget it never had.

| | |
|---|---|
| **7.5 measured active hours** (a floor over 5 of 7 sessions) | An Eventhouse holding 29,158,765 rows; 3 update policies; 3 materialized views; 24 KQL functions; 6 DQ rules; a 3-page Real-Time Dashboard; 4 Activator reflexes, one fired to Teams; a Direct Lake model with 24 measures and **no Gold notebook underneath it**; a 5-page report with the engine's first `decompositionTreeVisual` |
| **One Spark notebook** | against a ≤2 anti-drift budget, in an engine whose every instinct pushes toward three |
| **Engine changes paid for out of the same hours** | 5 new/fixed `validate_pbip.py` rules with both controls · a scan floor that closed a silent-pass defect · a retired-object rule for offline checkers · two cost-tool blind spots · a `scrub_check.py` classifier fix · 37 theme files swept · `arch_page.py` promoted to carry closure pages · **and a correction to Project 24's delivered closure record** |

**The single most expensive thing in this project was not a build.** It was the mirror blocker: one
`.set-or-replace` on a table whose OneLake mirror was already live, which cost the measure load, cost
export checkpoint E3 its scheduled session, and made Phase 6 run capacity-bound against a contract that
said it would not. Sessions 4 and 5 — the two whose cost data is gone — are the two that carried it,
so **the project cannot price its own most expensive mistake.** That is the strongest argument in this
document for the snapshot discipline the tool exists to enforce.

---

## 6. The ledger row, as written

```
| 25 Meridian Pay | 5 | 7.5 | 1,415 | 838 | 17% | 348,635,249 | 1,892,245 | 246,385 |
   <-- INCOMPLETE, missing sessions [4, 5]
   <-- PARTIAL (compaction) in sessions [7]
   <-- compaction unknown in sessions [1, 2, 3, 6]
```

Three caveats on one row, all generated by the tool rather than added by hand. **A ledger row that
cannot be told apart from a complete one is how a 2.2-hour fragment came to sit next to a whole project
in this same file** — the correction note above Project 24's row records exactly that. This row cannot
be misread the same way.

---

## 7. Session 8 addendum — closed 2026-08-19, after publishing

The publishing session was captured. The row is restated over **6 of 8** sessions.

```
  [!] MISSING SESSIONS: 4, 5 - totals below are a FLOOR, not a total.
  [!] PARTIAL SESSIONS: 7, 8 - context compaction truncated the transcript.
  [?] COMPACTION UNKNOWN: 1, 2, 3, 6 - captured before this tool could detect it.
  [+] SUBAGENTS: 9 transcript(s) across sessions 7, 8 - 66,167,251 cache-read,
      real spend on the same task, NOT included in the totals below.

| 25 Meridian Pay | 6 | 8.6 | 1,623 | 986 | 15% | 379,013,063 | 2,054,625 | 233,526 |
```

| Session 8 | Figure |
|---|--:|
| Active working time | **1.1 h** over 2 sittings |
| Assistant turns | 208 |
| Tool calls | 145 · browser **0%** |
| Cache-read | 30,377,814 |
| **Cache-read per turn** | **146,047** |
| Subagent transcripts | 6, carrying **44,256,711** cache-read |

**Three things this addendum records rather than smooths over.**

**One — the lowest cost-per-turn of the project is its last session, which is the wrong direction for
the hypothesis this engine used to hold.** `cache_read_per_turn` across the six captured sessions now
reads 204,882 · 205,323 · **320,794** · 233,059 · 228,648 · **146,047**. It does not rise with session
number, and the excursion is still the *longest* session rather than the latest. C6 withdrew the cost
half of the split-session claim on five points; this is a sixth, pointing the same way.

**Two — the subagent spend on this session exceeds the session's own visible spend.** Six QA and
research agents carried 44.3M cache-read against the session's 30.4M. Three adversarial visual-QA
passes over seventeen rendered slides are most of it, and they found eleven, then eleven more, then
six defects that re-reading the generator had not produced. That is a real cost and a real return, and
it is counted **separately** — folding it in would silently change what every earlier snapshot means.

**Three — the first capture of this session was taken with a stale copy of the tool and was wrong.**
The snapshot it wrote carried no `partial` flag, no compaction record and no subagent count, and it
looked completely clean. The staged copy of `capture_session_cost.py` in the container was the
*pre-fix* version; the fixed one had been committed to the device earlier the same day. It was caught
by reading the JSON for the three fields Skill 11 says to read, not by anything the tool printed.

> **A tool that was fixed is not the same as a tool you are running.** The snapshot was rewritten with
> the correct binary and the discarded one is not in `_cost/`. This is the fourth instrument in this
> project to report a clean result it had not earned, and the first to do it by being the wrong copy
> rather than by being wrong.
