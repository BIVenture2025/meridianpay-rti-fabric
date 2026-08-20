#!/usr/bin/env python3
"""
Project 25 (Meridian Pay) -- Session 5, Phase 4
check_rtd_queries.py -- offline static check of every RTD tile query against the
                        estate's ACTUAL DDL, not against memory.

WHAT THIS CATCHES, and why it is worth writing.
The failure mode for a generated dashboard is not a syntax error -- the portal
reports those loudly. It is a tile that references a column which does not exist
(or existed in an earlier revision of the spec), renders an error in one corner
of a 20-tile board, and gets screenshotted anyway. This script resolves every
bare identifier in every tile query against a catalogue parsed from 02_KQL/*.kql
and fails on anything it cannot account for.

HOW IT WORKS
  1. Parse the DDL for: table names + their columns; materialized-view names +
     the columns their bodies produce; function names + arity.
  2. For each tile query, collect every identifier-like token.
  3. Subtract: KQL keywords and builtins; the query's own local names (let
     bindings, `alias =` outputs of extend/project/summarize/make-series,
     ['bracketed display names']); string literals; numbers.
  4. Whatever remains MUST be a known table, MV, function or column.

FLOORS -- a check that finds nothing must prove it read something
(CORE_RULES Appendix C 12). This script fails if the catalogue is empty, if any
query resolved zero estate identifiers, or if fewer than 15 queries were checked.
That is what stops "0 problems found" from meaning "0 files parsed".

WHAT IT DOES NOT CATCH, stated rather than left implied: it does not type-check,
does not verify that a column belongs to the SPECIFIC table it is used against
(only that it exists somewhere in the estate), and cannot know whether a
materialized view has actually been created in the live database. Those need the
portal read-back listed in 00_Plan/SESSION_05_PORTAL_STEPS.md.
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# The DDL lives beside this folder in the project tree. Resolve it RELATIVE to
# this file first: the absolute path below was a session-container upload path
# and broke the moment the tool was run from the user's own disk (2026-08-19,
# Session 7). A tool that only runs in the container it was written in is not a
# tool, it is a transcript.
_SIBLING_DDL = os.path.normpath(os.path.join(HERE, os.pardir, "02_KQL"))
_LEGACY_DDL = os.path.join(
    "/mnt/user-data/uploads/Power BI Automation Engine/Projects",
    "25) Fabric E2E Real-Time Payments Risk (MeridianPay)",
    "02_KQL",
)
DEFAULT_DDL = _SIBLING_DDL if os.path.isdir(_SIBLING_DDL) else _LEGACY_DDL

KQL_RESERVED = set(
    """
    let where summarize extend project join kind inner leftouter rightouter fullouter
    anti semi on by asc desc order sort top take limit count countif dcount distinct
    union render make-series make_series mv-expand mv_expand parse evaluate print
    materialize toscalar iff case iif isnull isnotnull isempty isnotempty coalesce
    todouble toint tolong tostring todatetime totimespan tobool real long int string
    datetime timespan bool dynamic double now ago startofday endofday startofweek
    bin floor round abs strcat substring split trim replace tolower toupper
    dayofweek dayofmonth dayofyear hourofday monthofyear getyear datetime_diff
    datetime_add format_datetime percentile percentiles avg sum min max minif maxif
    sumif avgif any anyif arg_max arg_min take_any make_list make_set
    series_decompose_anomalies series_decompose series_fir series_stats
    max_of min_of pack pack_all bag_pack new_guid hash range typeof between and or not
    in has contains startswith endswith matches regex has_any nulls first last
    step from to default true false null with asc nulls
    """.split()
)

# KQL operators containing a hyphen. The tokenizer splits on non-word characters,
# so `make-series` would otherwise arrive as the two bogus identifiers `make` and
# `series`. Normalised to their underscore forms before tokenising.
HYPHENATED = {
    "make-series": "make_series",
    "mv-expand": "mv_expand",
    "mv-apply": "mv_apply",
    "top-nested": "top_nested",
    "parse-where": "parse_where",
    "sort-by": "sort_by",
}
KQL_RESERVED |= set(HYPHENATED.values())


def _balanced(text, open_at, opener="(", closer=")"):
    """Index just past the closer that balances the opener at open_at.

    Needed because a function's parameter list can itself contain parentheses --
    `as_of: datetime = datetime(null)` is the case in this estate. A naive
    `\\([^)]*\\)` stops at the inner `)`, silently skipping every reflex function
    with a datetime default. That produced this script's first false FAIL, which
    is why it is a real parser and not a regex.
    """
    depth = 0
    i = open_at
    while i < len(text):
        if text[i] == opener:
            depth += 1
        elif text[i] == closer:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return -1


def parse_ddl(ddl_dir):
    """Return (tables{name:set(cols)}, mvs{name:set(cols)}, funcs{name:set(params)})."""
    tables, mvs, funcs = {}, {}, {}
    text = ""
    for fn in sorted(os.listdir(ddl_dir)):
        if fn.endswith(".kql"):
            with open(os.path.join(ddl_dir, fn), "r", encoding="utf-8") as fh:
                text += fh.read() + "\n"

    # strip // comments so commented-out DDL cannot enter the catalogue
    text = "\n".join(re.sub(r"//.*$", "", l) for l in text.splitlines())

    # .create-merge table NAME ( col: type, ... )   /  .alter table NAME ( ... )
    for m in re.finditer(
        r"\.(?:create-merge|create|alter)\s+table\s+([A-Za-z_]\w*)\s*\(([^)]*)\)", text
    ):
        name, body = m.group(1), m.group(2)
        cols = set(re.findall(r"([A-Za-z_]\w*)\s*:", body))
        tables.setdefault(name, set()).update(cols)

    # .alter-merge table NAME (col: type)
    for m in re.finditer(
        r"\.alter-merge\s+table\s+([A-Za-z_]\w*)\s*\(([^)]*)\)", text
    ):
        tables.setdefault(m.group(1), set()).update(
            re.findall(r"([A-Za-z_]\w*)\s*:", m.group(2))
        )

    # materialized views: name + the columns its summarize produces
    for m in re.finditer(
        r"\.create-or-alter\s+materialized-view\s+([A-Za-z_]\w*)\s+on\s+table\s+"
        r"([A-Za-z_]\w*)\s*\{(.*?)\n\}",
        text,
        re.S,
    ):
        name, src, body = m.group(1), m.group(2), m.group(3)
        cols = set(re.findall(r"([A-Za-z_]\w*)\s*=", body))          # aliased outputs
        by = re.search(r"\bby\s+([^\n|]+)", body)
        if by:
            for part in by.group(1).split(","):
                part = part.strip()
                cols.add(part.split("=")[0].strip() if "=" in part else part)
        # arg_max(k, a, b, ...) passes its arguments through as columns
        for am in re.finditer(r"arg_max\s*\(([^)]*)\)", body, re.S):
            for a in am.group(1).split(","):
                a = a.strip()
                if re.fullmatch(r"[A-Za-z_]\w*", a):
                    cols.add(a)
        cols.discard("")
        mvs[name] = cols

    # functions + parameter names -- balanced-paren scan, see _balanced()
    for m in re.finditer(r"\.create-or-alter\s+function\s+([A-Za-z_]\w*)\s*\(", text):
        open_at = m.end() - 1
        close_at = _balanced(text, open_at)
        if close_at < 0:
            continue
        params = text[open_at + 1: close_at - 1]
        funcs[m.group(1)] = set(re.findall(r"([A-Za-z_]\w*)\s*:", params))

    return tables, mvs, funcs


def function_output_columns(ddl_dir):
    """Columns each fn_* projects, so tiles that call a function resolve cleanly."""
    out = {}
    text = ""
    for fn in sorted(os.listdir(ddl_dir)):
        if fn.endswith(".kql"):
            with open(os.path.join(ddl_dir, fn), "r", encoding="utf-8") as fh:
                text += fh.read() + "\n"
    text = "\n".join(re.sub(r"//.*$", "", l) for l in text.splitlines())
    for m in re.finditer(r"\.create-or-alter\s+function\s+([A-Za-z_]\w*)\s*\(", text):
        open_at = m.end() - 1
        close_at = _balanced(text, open_at)
        if close_at < 0:
            continue
        brace_at = text.find("{", close_at)
        if brace_at < 0:
            continue
        brace_end = _balanced(text, brace_at, "{", "}")
        if brace_end < 0:
            continue
        name, body = m.group(1), text[brace_at + 1: brace_end - 1]
        cols = set()
        for pm in re.finditer(r"\|\s*project\s+([^|]+)", body):
            for part in pm.group(1).split(","):
                part = part.strip()
                cols.add(part.split("=")[0].strip() if "=" in part else part)
        out[name] = {c for c in cols if re.fullmatch(r"[A-Za-z_]\w*", c)}
    return out


LOCAL_ALIAS_RE = re.compile(r"([A-Za-z_]\w*)\s*=(?!=)")
LET_RE = re.compile(r"\blet\s+([A-Za-z_]\w*)\s*=")
BRACKET_RE = re.compile(r"\['[^']*'\]")
STRING_RE = re.compile(r"'[^']*'|\"[^\"]*\"")
TOKEN_RE = re.compile(r"\b([A-Za-z_]\w*)\b")


TUPLE_ALIAS_RE = re.compile(r"\(([^()]*?)\)\s*=(?!=)")
JOIN_QUALIFIER_RE = re.compile(r"\$(?:left|right)\.")


def check_query(text, known, verbose=False):
    body = "\n".join(l for l in text.splitlines() if not l.strip().startswith("//"))
    body = BRACKET_RE.sub(" ", body)
    body = STRING_RE.sub(" ", body)
    for hyph, under in HYPHENATED.items():
        body = body.replace(hyph, under)
    # `$left.col` / `$right.col` -- the qualifier is syntax, the column after the
    # dot is the real identifier and must still be resolved.
    body = JOIN_QUALIFIER_RE.sub("", body)

    locals_ = set(LET_RE.findall(body)) | set(LOCAL_ALIAS_RE.findall(body))
    # Tuple assignment: `extend (anomalies, score, baseline) = series_...(...)`
    # declares all three names, not just the one adjacent to the `=`.
    for tm in TUPLE_ALIAS_RE.findall(body):
        for part in tm.split(","):
            part = part.strip()
            if re.fullmatch(r"[A-Za-z_]\w*", part):
                locals_.add(part)
    locals_ |= {"_startTime", "_endTime"}

    unknown, resolved = set(), set()
    for tok in TOKEN_RE.findall(body):
        if tok in KQL_RESERVED or tok in locals_ or tok.startswith("_"):
            continue
        if re.fullmatch(r"\d+[dhms]?", tok):
            continue
        if tok in known:
            resolved.add(tok)
        else:
            unknown.add(tok)
    return unknown, resolved


# ---------------------------------------------------------------------------
# RETIRED OBJECTS -- the failure this catalogue is structurally blind to.
#
# The catalogue is parsed from 02_KQL/*.kql, which is the DDL we WROTE. A table
# dropped in the portal is still in that DDL, so `alerts` resolved cleanly here
# on 2026-08-19 while three RTD tiles were rendering
#   "Semantic error: 'where' operator: Failed to resolve table or column
#    expression named 'alerts'"
# in the live dashboard. The check said 19/19 and it was telling the truth about
# the wrong estate. Static analysis against source can only ever prove the source
# is self-consistent; the drift between source and live has to be DECLARED.
#
# retired_objects.json is that declaration. It is deliberately manual: nothing
# offline can discover a portal drop, so the honest design is a file a human
# updates when they drop something, and a checker that fails loudly if a query
# still names it.
# ---------------------------------------------------------------------------
RETIRED_FILE = os.path.join(HERE, "retired_objects.json")


def load_retired(known):
    """Return {retired_name: replacement}. Fails closed on a malformed file."""
    if not os.path.isfile(RETIRED_FILE):
        return {}, ["retired_objects.json not found -- no drift declaration read"]
    with open(RETIRED_FILE, "r", encoding="utf-8") as fh:
        doc = json.load(fh)
    out, notes = {}, []
    for e in doc.get("retired", []):
        name, repl = e.get("name"), e.get("replacement")
        if not name or not repl:
            notes.append(f"entry missing name/replacement: {e!r}")
            continue
        # A retired entry whose successor is not in the catalogue would let a
        # query pass by pointing at a second thing that does not exist.
        if repl not in known:
            notes.append(
                f"'{name}' declares replacement '{repl}', which is NOT in the DDL "
                "catalogue -- fix the DDL or the declaration"
            )
        out[name] = repl
    return out, notes


def check_retired(text, retired):
    """Retired names used in EXECUTABLE lines. Comments may name them freely --
    a header that explains why a table was replaced is documentation, not a bug."""
    body = "\n".join(l for l in text.splitlines() if not l.strip().startswith("//"))
    body = re.sub(r"//.*$", "", body, flags=re.M)
    body = STRING_RE.sub(" ", body)
    return sorted({tok for tok in TOKEN_RE.findall(body) if tok in retired})


def selftest_retired():
    """Positive AND false-positive control for the retired-object rule."""
    retired = {"alerts": "alerts_v2"}
    positive = "alerts\n| where reflex_type == 'card_testing_burst'\n| summarize Value = count()"
    negative = ("// the reflex that writes to `alerts` -- renamed, see retired_objects.json\n"
                "alerts_v2\n| where reflex_type == 'card_testing_burst'\n"
                "| where note == 'alerts'\n| summarize Value = count()")
    if check_retired(positive, retired) != ["alerts"]:
        print("SELFTEST FAILED: retired rule did not catch a live `alerts` reference",
              file=sys.stderr)
        return False
    if check_retired(negative, retired) != []:
        print("SELFTEST FAILED: retired rule fired on a comment or a string literal",
              file=sys.stderr)
        return False
    return True


def selftest(known):
    """Prove the checker can FAIL, not only pass.

    A validator that has never been seen to reject anything is indistinguishable
    from one whose matcher is broken -- every rule needs a positive AND a
    false-positive control (CORE_RULES; P24's validate_pbip.py lesson). These two
    fixtures are that pair, run on every invocation so they cannot rot.
    """
    good = ("mv_terminal_last_seen\n| summarize Value = countif(trusted_time > ago(1d))\n")
    bad = ("mv_terminal_last_seen\n| where terminal_status == 'dark'\n"
           "| project terminal_id, store_archetype\n")
    u_good, r_good = check_query(good, known)
    u_bad, _ = check_query(bad, known)
    ok = True
    if u_good or not r_good:
        print(f"SELFTEST FAILED: clean fixture flagged {sorted(u_good)}", file=sys.stderr)
        ok = False
    # store_archetype is the column the generator never persists (03_dim_estate_build
    # Rev 2); terminal_status never existed. Both MUST be caught.
    if not {"store_archetype", "terminal_status"} <= u_bad:
        print(f"SELFTEST FAILED: broken fixture not caught; flagged only "
              f"{sorted(u_bad)}", file=sys.stderr)
        ok = False
    return ok


def main():
    ddl_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DDL
    if not os.path.isdir(ddl_dir):
        print(f"FATAL: DDL directory not found: {ddl_dir}", file=sys.stderr)
        sys.exit(2)

    tables, mvs, funcs = parse_ddl(ddl_dir)
    fn_cols = function_output_columns(ddl_dir)

    known = set(tables) | set(mvs) | set(funcs)
    for cols in tables.values():
        known |= cols
    for cols in mvs.values():
        known |= cols
    for cols in fn_cols.values():
        known |= cols
    for params in funcs.values():
        known |= params

    print(f"catalogue from {ddl_dir}")
    print(f"  tables            : {len(tables)}")
    print(f"  materialized views: {len(mvs)}  ({', '.join(sorted(mvs))})")
    print(f"  functions         : {len(funcs)}")
    print(f"  known identifiers : {len(known)}")
    print()

    # FLOOR 1 -- the catalogue must not be empty
    if len(tables) < 10 or len(mvs) != 3 or len(funcs) < 12:
        print(
            "FLOOR FAILED: catalogue looks under-parsed "
            f"(tables={len(tables)}, mvs={len(mvs)}, funcs={len(funcs)}). "
            "Expected >=10 tables, exactly 3 MVs, >=12 functions.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not selftest(known):
        sys.exit(1)
    print("  selftest          : PASS (clean fixture accepted, broken fixture rejected)")

    if not selftest_retired():
        sys.exit(1)
    retired, retired_notes = load_retired(known)
    for n in retired_notes:
        print(f"  retired decl      : WARNING -- {n}", file=sys.stderr)
    print(f"  retired objects   : {len(retired)} declared "
          f"({', '.join(f'{k} -> {v}' for k, v in sorted(retired.items())) or 'none'})")
    print()

    qdir = os.path.join(HERE, "queries")
    files = sorted(f for f in os.listdir(qdir) if f.endswith(".kql"))
    problems, checked = 0, 0

    for f in files:
        with open(os.path.join(qdir, f), "r", encoding="utf-8") as fh:
            text = fh.read()
        unknown, resolved = check_query(text, known)
        checked += 1
        dead = check_retired(text, retired)
        if dead:
            print(f"  [DEAD] {f:34s} references RETIRED object(s): " +
                  ", ".join(f"{d} (use {retired[d]})" for d in dead), file=sys.stderr)
            problems += len(dead)
        status = "ok " if not unknown else "FAIL"
        print(f"  [{status}] {f:34s} resolved {len(resolved):2d}  " +
              (f"UNKNOWN: {', '.join(sorted(unknown))}" if unknown else ""))
        # FLOOR 2 -- a query that resolved nothing did not really get checked
        if not resolved:
            print(f"         FLOOR FAILED: {f} resolved zero estate identifiers",
                  file=sys.stderr)
            problems += 1
        problems += len(unknown)

    print()
    # FLOOR 3 -- must have actually read the expected number of tiles
    if checked < 15:
        print(f"FLOOR FAILED: only {checked} tile queries checked; expected >=15",
              file=sys.stderr)
        sys.exit(1)

    print(f"{checked} tile queries checked against the live DDL catalogue.")
    if problems:
        print(f"{problems} problem(s) -- unresolved identifiers and/or references to "
              "retired objects. Fix before generating JSON.", file=sys.stderr)
        sys.exit(1)
    print("0 unresolved identifiers, 0 references to retired objects.")


if __name__ == "__main__":
    main()
