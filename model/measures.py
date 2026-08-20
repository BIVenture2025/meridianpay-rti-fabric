#!/usr/bin/env python3
"""
Project 25 (Meridian Pay) -- Session 5, Phase 4
measures.py -- the 24 DAX measures for SM_MeridianPay_DirectLake, as DATA.

Emits FOUR artefacts from one definition, so they cannot drift apart:
  * P25_measures.tmdl        -- CRLF, for the service's TMDL view / Tabular Editor
  * P25_measures_batch.json  -- payload for the Power BI MCP's BatchCreate over XMLA
  * P25_measure_readback.dax -- one EVALUATE per measure, for the contract's
                                "every measure definition read back against its
                                rendered value" exit criterion
  * P25_measures_define.dax  -- the DAX-query-view load script

The fourth was added 2026-08-19 (Session 7). It already carried the header "Generated
by 04_Model/measures.py" and was in fact hand-maintained, so when the DQ measures were
rescoped it was the one artefact that silently kept the old definition. A file that
claims a provenance the code does not implement is the same defect class as a snapshot
that records a selection rule its own sort does not follow.

STATUS 2026-08-19: all 24 are LOADED in SM_MeridianPay_DirectLake, applied over XMLA via
the Power BI MCP's BatchCreate (24/24, one transaction, 0.7s -- and it carries
formatString, which DEFINE MEASURE does not, so the seven 0.0% formats came free). Every
one was read back against its rendered value; see Gate_Check_Results.md, Session 7.

WHERE THE MEASURES LIVE. Direct Lake models do not support calculated tables or
calculated columns -- adding either drops the model out of Direct Lake mode. So
there is no dedicated `_Measures` table; every measure is attached to `alerts`
and organised with displayFolder instead. This is a Direct Lake constraint, not
a style preference.

THE ONE MEASURE THAT MATTERS. `Precision (Reportable)` returns BLANK() unless a
single graded cohort is in filter context. The contract's whole pitch is a system
that publishes its own precision honestly; the failure mode it exists to avoid is
a blended or ungraded number rendered as if it were real. A guard measure makes
that structurally impossible rather than a reviewer's responsibility -- and BLANK
renders as an empty cell the visual can label "pending", where 0 would render as
a confident, wrong bar.

DEPENDENCIES -- these are NOT all in the model yet. See MODEL_NOTES.md:
  * ground_truth and dispute_curated are not currently shortcut into
    LH_MeridianPay; two of the five shortcuts are missing for the pitch page.
  * alerts[gt_episode_id] and alerts[dispute_confirmed] do not exist yet; they
    are added by 02_KQL/12_alert_grading.kql, prepared this session, run in
    Session 6.
Measures that depend on them are marked `pending_dependency` and will error
until those two steps are done. They are shipped anyway, deliberately: the
alternative is Session 6 writing them from scratch under time pressure.
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
HOME_TABLE = "alerts"

# (name, dax, formatString, displayFolder, description, pending_dependency)
MEASURES = [
    # ---- 01 Volume ---------------------------------------------------------
    ("Total Auths",
     'CALCULATE ( COUNTROWS ( auth_curated ), auth_curated[event_type] = "auth" )',
     "#,0", "01 Volume",
     "Authorisation attempts only. event_type filters out reversals and partial "
     "captures, which are separate events against the same auth and would double-count.",
     False),

    ("Approved Auths",
     'CALCULATE ( COUNTROWS ( auth_curated ), auth_curated[event_type] = "auth", '
     'auth_curated[auth_result] = "approved" )',
     "#,0", "01 Volume", "Approved authorisations.", False),

    ("Declined Auths",
     'CALCULATE ( COUNTROWS ( auth_curated ), auth_curated[event_type] = "auth", '
     'auth_curated[auth_result] = "declined" )',
     "#,0", "01 Volume", "Declined authorisations.", False),

    ("Approval Rate %",
     "DIVIDE ( [Approved Auths], [Total Auths] )",
     "0.0%", "01 Volume",
     "DIVIDE, not '/', so an empty filter context returns BLANK rather than an error.",
     False),

    ("Decline Rate %",
     "DIVIDE ( [Declined Auths], [Total Auths] )",
     "0.0%", "01 Volume", "Complement of approval rate over the same denominator.", False),

    # ---- 02 Estate ---------------------------------------------------------
    ("Merchants", "DISTINCTCOUNT ( dim_estate[merchant_id] )", "#,0", "02 Estate",
     "600 at the frozen scale. Read from dim_estate, never hand-typed on a card.", False),

    ("Stores", "DISTINCTCOUNT ( dim_estate[store_id] )", "#,0", "02 Estate",
     "927 at the frozen scale -- the +3% tolerance edge of the 900 proposed, not a miss.",
     False),

    ("Terminals", "DISTINCTCOUNT ( dim_estate[terminal_id] )", "#,0", "02 Estate",
     "1,500 at the frozen scale. dim_estate is one row per terminal, so this also "
     "equals COUNTROWS -- a divergence between the two means duplicates.", False),

    ("Terminals with Alerts",
     'CALCULATE ( DISTINCTCOUNT ( alerts[entity_id] ), alerts[entity_type] = "terminal" )',
     "#,0", "02 Estate",
     "entity_type guard is load-bearing: reflex 4 rows carry an issuer BIN in "
     "entity_id, and counting those as terminals would inflate this silently.", False),

    ("Estate Coverage %",
     "DIVIDE ( [Terminals with Alerts], [Terminals] )", "0.0%", "02 Estate",
     "Share of the estate that has ever raised an alert. Low is good news, not a gap.",
     False),

    # ---- 03 Alerts ---------------------------------------------------------
    ("Alerts Raised", "COUNTROWS ( alerts )", "#,0", "03 Alerts",
     "The denominator of every precision measure.", False),

    ("Reflex Types Fired", "DISTINCTCOUNT ( alerts[reflex_type] )", "0", "03 Alerts",
     "The contract's '4 reflexes, >=1 fired with evidence' exit criterion, as a "
     "number the report actually renders. Expect 4.", False),

    ("Disputes Matured", "COUNTROWS ( dispute_curated )", "#,0", "03 Alerts",
     "Disputes raised as of SIM_NOW -- 6,715 against an eventual ~13.5k. This is a "
     "maturity effect, not a shortfall; the Home card's subtitle must say so.", True),

    # ---- 04 Precision ------------------------------------------------------
    ("Alerts Matched (Ground Truth)",
     'CALCULATE ( COUNTROWS ( alerts ), NOT ISBLANK ( alerts[gt_episode_id] ), '
     'alerts[gt_episode_id] <> "" )',
     "#,0", "04 Precision",
     "True positives against the injected episode register. Both guards are needed: "
     "the KQL grading writes an empty string, not a null, for an unmatched alert.",
     True),

    ("Alerts Confirmed (Disputes)",
     "CALCULATE ( COUNTROWS ( alerts ), alerts[dispute_confirmed] = TRUE () )",
     "#,0", "04 Precision",
     "True positives against real chargebacks -- the independent second opinion the "
     "contract requires alongside ground truth.", True),

    ("Precision (Ground Truth)",
     "DIVIDE ( [Alerts Matched (Ground Truth)], [Alerts Raised] )",
     "0.0%", "04 Precision",
     "Unguarded. Do NOT bind this to a visual directly -- use Precision (Reportable).",
     True),

    ("Precision (Disputes)",
     "DIVIDE ( [Alerts Confirmed (Disputes)], [Alerts Raised] )",
     "0.0%", "04 Precision", "Unguarded, same warning as above.", True),

    ("Episodes In Scope",
     "VAR RefTypes = VALUES ( alerts[reflex_type] )\n"
     "VAR EpTypes =\n"
     "    SELECTCOLUMNS (\n"
     "        RefTypes,\n"
     '        "@episode_type",\n'
     "        SWITCH (\n"
     "            alerts[reflex_type],\n"
     '            "terminal_dark", "terminal_dark_outage",\n'
     "            alerts[reflex_type]\n"
     "        )\n"
     "    )\n"
     "RETURN\n"
     "    CALCULATE (\n"
     "        COUNTROWS ( ground_truth ),\n"
     "        TREATAS ( EpTypes, ground_truth[episode_type] )\n"
     "    )",
     "#,0", "04 Precision",
     "Recall's denominator. The SWITCH exists because exactly one name differs "
     "between the two vocabularies: reflex_type 'terminal_dark' is episode_type "
     "'terminal_dark_outage'. Mapping it in one place stops that mismatch becoming "
     "a silent zero. Unfiltered this returns 137.", True),

    ("Episodes Detected",
     'CALCULATE ( DISTINCTCOUNT ( alerts[gt_episode_id] ), alerts[gt_episode_id] <> "" )',
     "#,0", "04 Precision",
     "Distinct real episodes the reflexes caught. Distinct, not a row count: one "
     "episode legitimately produces many 5-minute alert buckets.", True),

    ("Recall (Ground Truth)",
     "DIVIDE ( [Episodes Detected], [Episodes In Scope] )", "0.0%", "04 Precision",
     "Report by reflex_type, NOT by maturity cohort. Cohort is a property of an "
     "alert's age; a ground-truth episode has no cohort, so a per-cohort recall has "
     "no honest denominator. Stated here so the page does not invent one.", True),

    ("Cohort Status",
     "VAR C = SELECTEDVALUE ( alerts[maturity_cohort] )\n"
     "RETURN\n"
     "    SWITCH (\n"
     "        C,\n"
     '        "graded_T90_T60", "Graded",\n'
     '        "partially_matured_T60_T30", "Partially matured / not reportable",\n'
     '        "awaiting_grading_T30_T", "Awaiting grading",\n'
     '        BLANK (), "Mixed cohorts / select one",\n'
     "        C\n"
     "    )",
     None, "04 Precision",
     "The label the Alert Precision table shows instead of a number for any cohort "
     "that is not fully graded. SELECTEDVALUE returns BLANK on a mixed selection, "
     "which is exactly the case that must never render a percentage.", False),

    ("Precision (Reportable)",
     "VAR C = SELECTEDVALUE ( alerts[maturity_cohort] )\n"
     "RETURN\n"
     '    IF ( C = "graded_T90_T60", [Precision (Ground Truth)], BLANK () )',
     "0.0%", "04 Precision",
     "THE GUARD. Blank -- not zero -- for every cohort that is not fully graded, and "
     "blank for a mixed selection. Bind visuals to this, never to the unguarded "
     "measures. Zero would render as a confident wrong bar; blank renders as the "
     "'pending' state the contract's exit criteria require.", True),

    # ---- 05 Data quality ---------------------------------------------------
    # ---------------------------------------------------------------------
    # BOTH DQ measures were rescoped 2026-08-19 (Session 7) after the STEP 4
    # read-back returned BLANK for `DQ Rules Passed` and 100 for
    # `DQ Faults Found`. Cause, measured not guessed:
    #
    #   distinct run_id   = 1        ("session3-run1")
    #   distinct run_time = 6        -- EACH RULE WRITES ITS OWN run_time
    #   rows at MAX(run_time) = 1    -- so "latest run" selected ONE RULE
    #
    # `run_time` is a per-rule execution stamp, not a run key. The run key is
    # `run_id`. The old filter therefore reported rule 6 alone and called it
    # the run. Scope by run_id, choosing the run_id that owns the most recent
    # run_time so it still means "latest".
    #
    # Second defect in the same measure: it demanded
    # independent_check_passed = TRUE() for all six. Contract SS7 requires an
    # independent downstream structural check for RULES 1-3 ONLY; rules 4, 5
    # and 6 legitimately write BLANK. Measured: 3 TRUE, 3 BLANK, 6 with
    # floor_satisfied = TRUE. A BLANK independent check is a pass provided the
    # floor holds -- which is the contract's actual rule.
    # ---------------------------------------------------------------------
    ("DQ Rules Passed",
     "VAR LatestTime =\n"
     "    CALCULATE ( MAX ( dq_results[run_time] ), ALL ( dq_results ) )\n"
     "VAR LatestRunId =\n"
     "    CALCULATE (\n"
     "        MAX ( dq_results[run_id] ),\n"
     "        ALL ( dq_results ),\n"
     "        dq_results[run_time] = LatestTime\n"
     "    )\n"
     "RETURN\n"
     "    CALCULATE (\n"
     "        COUNTROWS (\n"
     "            FILTER (\n"
     "                dq_results,\n"
     "                dq_results[run_id] = LatestRunId\n"
     "                    && dq_results[floor_satisfied] = TRUE ()\n"
     "                    && ( ISBLANK ( dq_results[independent_check_passed] )\n"
     "                        || dq_results[independent_check_passed] = TRUE () )\n"
     "            )\n"
     "        ),\n"
     "        ALL ( dq_results )\n"
     "    )",
     "0", "05 Data quality",
     "Rules passing in the latest RUN, scoped by run_id. dq_results keeps every run "
     "and never overwrites, so an unfiltered count would sum history and always look "
     "healthy -- but run_time is a per-rule stamp, so scoping by it counts one rule "
     "(P25 S7 read-back defect). The floor is required for every rule; the independent "
     "downstream check is required for rules 1-3 and is BLANK by design for 4-6 "
     "(contract SS7), so BLANK counts as passing. A rule that found nothing but proved "
     "it read nothing still has not passed -- that is what floor_satisfied encodes.",
     False),

    ("DQ Rows Flagged",
     "VAR LatestTime =\n"
     "    CALCULATE ( MAX ( dq_results[run_time] ), ALL ( dq_results ) )\n"
     "VAR LatestRunId =\n"
     "    CALCULATE (\n"
     "        MAX ( dq_results[run_id] ),\n"
     "        ALL ( dq_results ),\n"
     "        dq_results[run_time] = LatestTime\n"
     "    )\n"
     "RETURN\n"
     "    CALCULATE (\n"
     "        SUM ( dq_results[faults_found] ),\n"
     "        ALL ( dq_results ),\n"
     "        dq_results[run_id] = LatestRunId\n"
     "    )",
     "#,0", "05 Data quality",
     "Rows flagged across every rule in the latest RUN, scoped by run_id. RENAMED from "
     "'DQ Faults Found' 2026-08-19 (Session 7) because that noun was wrong: rule 5 "
     "(payload_schema_evolution) contributes 2,151,584 of the 2,185,579, and its own "
     "detail JSON calls those rows carrying the v2 sca_flag -- a population, not a fault. "
     "Rule 4 likewise reports all 1,500 terminals as having nonzero clock skew, which is "
     "the expected state. The sum is kept whole rather than narrowed to a hard-coded list "
     "of 'real fault' rules, because that list would rot the moment a rule is added; the "
     "DqTbl beneath the card shows the per-rule split. Guide SS94.",
     False),
]


def emit_tmdl(path):
    """CRLF, per the contract's exit criteria."""
    lines = [
        "/// Project 25 (Meridian Pay) -- measure layer for SM_MeridianPay_DirectLake",
        "/// Generated by 04_Model/measures.py -- edit that file, never this one.",
        "/// Paste these into the `alerts` table in the service's TMDL view, or apply",
        "/// P25_measures_batch.json over XMLA.",
        "",
        f"table {HOME_TABLE}",
        "",
    ]
    for name, dax, fmt, folder, desc, pending in MEASURES:
        for dl in _wrap(desc, 74):
            lines.append(f"\t/// {dl}")
        if pending:
            lines.append("\t/// PENDING DEPENDENCY: needs the grading columns and/or the "
                         "missing Lakehouse shortcuts. See MODEL_NOTES.md.")
        lines.append(f"\tmeasure '{name}' = ```")
        for dl in dax.split("\n"):
            lines.append(f"\t\t\t{dl}")
        lines.append("\t\t\t```")
        if fmt:
            lines.append(f"\t\tformatString: {fmt}")
        lines.append(f"\t\tdisplayFolder: {folder}")
        lines.append("")
    with open(path, "w", encoding="utf-8", newline="\r\n") as fh:
        fh.write("\n".join(lines))
    return len(lines)


def _wrap(text, width):
    out, cur = [], ""
    for w in text.split():
        if len(cur) + len(w) + 1 > width:
            out.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        out.append(cur)
    return out


def emit_define(path):
    """P25_measures_define.dax -- the DAX-query-view load script.

    ADDED 2026-08-19, Session 7. This file already carried the header
    "Generated by 04_Model/measures.py. Do not hand-edit; edit that file and
    regenerate." -- and measures.py did not emit it. It was a hand-maintained twin
    whose header asserted a provenance the code did not implement, which is how it
    kept the pre-Session-7 `DQ Rules Passed` definition after the model, the TMDL,
    the batch payload and the read-back had all moved on. Same failure shape as
    capture_session_cost.py's "largest of N candidates" note. The header is now true.
    """
    pct = [n for n, _, f, _, _, _ in MEASURES if f == "0.0%"]
    lines = [
        "// Project 25 (Meridian Pay) -- load all "
        f"{len(MEASURES)} measures into SM_MeridianPay_DirectLake",
        "// Generated by 04_Model/measures.py. Do not hand-edit; edit that file and regenerate.",
        "//",
        "// HOW TO USE -- DAX query view, NOT TMDL view.",
        "//   1. Open SM_MeridianPay_DirectLake -> DAX query view.",
        "//   2. Paste this whole file into a new query tab.",
        "//   3. Run. The EVALUATE at the bottom is a smoke test -- it returns one row.",
        f"//   4. Click 'Update model with changes'. It should report {len(MEASURES)}.",
        "//",
        "// WHY NOT TMDL VIEW. P25_measures.tmdl opens with `table alerts`, and applying a",
        "// partial table block in TMDL view REPLACES that table's definition -- it would drop",
        "// the column and partition metadata the Direct Lake binding depends on. DEFINE MEASURE",
        "// is purely additive and cannot remove anything. Use the .tmdl file for review and for",
        "// the E3 export; use this file to actually load them.",
        "//",
        "// THERE IS A CHEAPER ROUTE, PROVEN 2026-08-19. The Power BI MCP server's",
        "// batch_measure_operations BatchCreate applies P25_measures_batch.json over XMLA in",
        "// one transactional call (24/24 in 0.7s) AND carries formatString, which DEFINE",
        "// MEASURE does not. Use this file when XMLA is unavailable or an interactive sign-in",
        "// cannot be completed.",
        "//",
        "// FORMAT STRINGS ARE NOT CARRIED BY DEFINE MEASURE. After applying, set these",
        f"// {len(pct)} in Model view -> select measure -> Format. Everything else defaults acceptably:",
    ]
    for n in pct:
        lines.append(f"//     {n:<32} -> 0.0%")
    lines += ["", "DEFINE"]
    for name, dax, _fmt, _folder, desc, pending in MEASURES:
        lines.append("")
        for dl in _wrap(desc, 92):
            lines.append(f"    // {dl}")
        if pending:
            lines.append("    // PENDING DEPENDENCY: see MODEL_NOTES.md.")
        lines.append(f"    MEASURE {HOME_TABLE}[{name}] =")
        for dl in dax.split("\n"):
            lines.append(f"        {dl}" if dl.strip() else "")
    lines += [
        "",
        "// Smoke test. A non-BLANK Alerts Raised proves the measures bound to a real table",
        "// rather than merely parsing.",
        "EVALUATE",
        "    ROW (",
        '        "Alerts Raised", [Alerts Raised],',
        '        "Terminals", [Terminals],',
        '        "Reflex Types Fired", [Reflex Types Fired]',
        "    )",
    ]
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    return len(lines)


def emit_batch(path):
    items = []
    for name, dax, fmt, folder, desc, pending in MEASURES:
        item = {
            "name": name,
            "tableName": HOME_TABLE,
            "expression": dax,
            "displayFolder": folder,
            "description": desc,
        }
        if fmt:
            item["formatString"] = fmt
        items.append(item)
    payload = {
        "operation": "BatchCreate",
        "batchCreateRequest": {
            "items": items,
            "options": {"continueOnError": False, "useTransaction": True},
        },
    }
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return len(items)


def emit_readback(path):
    """One EVALUATE per measure -- the contract's read-back obligation, as a script.

    ROW() rather than a bare measure reference so each returns a one-row table
    whose value can be eyeballed against the visual that renders it.
    """
    out = [
        "// Project 25 -- measure read-back script.",
        "// Contract exit criterion: 'Every measure definition read back against its",
        "// rendered value.' Run each statement against SM_MeridianPay_DirectLake and",
        "// record the value next to the visual that shows it. A measure that has never",
        "// been evaluated is not built, it is typed.",
        "",
    ]
    for name, _dax, _fmt, _folder, _desc, pending in MEASURES:
        if pending:
            out.append(f"// PENDING DEPENDENCY -- expect an error until 12_alert_grading.kql has run")
        out.append(f'EVALUATE ROW ( "{name}", [{name}] )')
        out.append("")
    with open(path, "w", encoding="utf-8", newline="\r\n") as fh:
        fh.write("\n".join(out))
    return len(MEASURES)


if __name__ == "__main__":
    n_tmdl = emit_tmdl(os.path.join(HERE, "P25_measures.tmdl"))
    n_batch = emit_batch(os.path.join(HERE, "P25_measures_batch.json"))
    n_read = emit_readback(os.path.join(HERE, "P25_measure_readback.dax"))
    n_def = emit_define(os.path.join(HERE, "P25_measures_define.dax"))

    # Read back what we just wrote -- an export that has not been re-read is not
    # an export (contract Sec4).
    with open(os.path.join(HERE, "P25_measures_batch.json"), "r", encoding="utf-8") as fh:
        rt = json.load(fh)
    with open(os.path.join(HERE, "P25_measures.tmdl"), "rb") as fh:
        raw = fh.read()

    pending = sum(1 for m in MEASURES if m[5])
    folders = sorted({m[3] for m in MEASURES})
    names = [m[0] for m in MEASURES]
    assert len(names) == len(set(names)), "duplicate measure name"
    assert b"\r\n" in raw and raw.count(b"\n") == raw.count(b"\r\n"), \
        "TMDL is not uniformly CRLF"

    print(f"measures defined      : {len(MEASURES)}  "
          f"(contract: 12 mandatory, 20 target)")
    print(f"  pending dependency  : {pending}")
    print(f"  display folders     : {', '.join(folders)}")
    print(f"P25_measures.tmdl     : {n_tmdl} lines, CRLF verified")
    print(f"P25_measures_batch.json: {len(rt['batchCreateRequest']['items'])} items, "
          f"json.load() OK")
    print(f"P25_measure_readback.dax: {n_read} EVALUATE statements")
    print(f"P25_measures_define.dax : {n_def} lines")
