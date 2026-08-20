#!/usr/bin/env python3
"""
Project 25 (Meridian Pay) -- Session 5, Phase 4
build_rtd_json.py -- emit RealTimeDashboard.json from rtd_spec.py + queries/*.kql

USAGE
    # Preferred -- envelope taken from a real exported dashboard:
    python build_rtd_json.py --skeleton skeleton.json --out RTD_MeridianPay.json

    # Fallback -- envelope from documented defaults, LOUDLY flagged:
    python build_rtd_json.py --out RTD_MeridianPay.json \
        --cluster-uri https://<eventhouse>.z0.kusto.fabric.microsoft.com \
        --database EH_MeridianPay

WHY A SKELETON.
The dashboard's ENVELOPE -- "$schema", "schema_version", the dataSource entry's
id / scopeId / clusterUri, and the top-level id / eTag -- is specific to this
tenant and to whatever RTD schema version the service is currently on. Writing
those from memory is the exact failure CORE_RULES Sec48a/Sec49a exists to prevent,
and the RTD equivalent of the contract's "grep P24's report folder for its
$schema versions; never hand-write them" instruction. A 60-second export of an
empty dashboard supplies all of them, verified, and this script copies them
across untouched.

The parts this script DOES author -- pages, tiles, queries, layout, KQL -- are
the parts that are ours and are reviewable in rtd_spec.py and queries/*.kql.

IDS. Every id is a deterministic UUIDv5 derived from a fixed namespace plus the
spec key, so re-running the builder produces byte-identical output and a re-import
updates tiles in place rather than deleting and recreating them (the Git doc's
own warning). Change a tile's `key` and you have declared a new tile on purpose.

VALIDATION. The builder enforces the two rules the Microsoft Git article calls
out explicitly, and refuses to write a file that breaks either:
  1. every queryId is referenced EXACTLY ONCE across tiles/baseQueries/parameters
  2. every id is a valid RFC 4122 UUID and unique within its category
It also refuses to emit a tile whose .kql file is missing or empty -- a broken
page must not be emittable (feedback_house_html_is_a_component, generalised).
"""

import argparse
import json
import os
import re
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from rtd_spec import PAGES, DASHBOARD_TITLE, TIME_PARAMETER, GRID_WIDTH  # noqa: E402

# Fixed namespace -> deterministic, reproducible ids across runs.
NS = uuid.UUID("6f2b1c4e-9a3d-5e7f-8b1a-25c0de7a1500")

# Documented defaults, used ONLY when no skeleton is supplied. These are the
# values this script is least sure of; --skeleton replaces all of them.
FALLBACK_SCHEMA = "https://dataexplorer.azure.com/static/d/schema/50/dashboard.json"
FALLBACK_SCHEMA_VERSION = "50"


NO_SUBTITLE = [False]


def det_id(*parts):
    return str(uuid.uuid5(NS, "|".join(parts)))


def load_query(name):
    path = os.path.join(HERE, "queries", name)
    if not os.path.exists(path):
        raise SystemExit(f"FATAL: tile query file missing: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    stripped = "\n".join(
        l for l in text.splitlines() if l.strip() and not l.strip().startswith("//")
    ).strip()
    if not stripped:
        raise SystemExit(f"FATAL: tile query file is comment-only/empty: {path}")
    return text.rstrip() + "\n", stripped


VAR_RE = re.compile(r"(_startTime|_endTime)\b")


def used_variables(query_text):
    return sorted(set(VAR_RE.findall(query_text)))


def read_skeleton(path):
    with open(path, "r", encoding="utf-8") as fh:
        sk = json.load(fh)
    ds = sk.get("dataSources") or []
    if not ds:
        raise SystemExit(
            "FATAL: the skeleton has no dataSources. Add the Eventhouse as a data "
            "source in the dashboard, save, then export again."
        )
    return {
        "schema": sk.get("$schema") or FALLBACK_SCHEMA,
        # NOT coerced to str. Measured 2026-08-19 from a real export: this tenant
        # writes schema_version as the INTEGER 78, and the fallback guessed the
        # string "50". Both the type and the value were wrong -- which is the whole
        # argument for taking the envelope from an export rather than memory.
        "schema_version": sk.get("schema_version", FALLBACK_SCHEMA_VERSION),
        "id": sk.get("id"),
        "eTag": sk.get("eTag"),
        # Copied verbatim. On this tenant the kind is "kusto-trident" (not
        # "manual-kusto") and `database` holds a GUID, not the display name --
        # rebuilding this object by hand would have produced a file that imports
        # and then reads nothing.
        "dataSources": ds,
        "autoRefresh": sk.get("autoRefresh"),
        "parameters": sk.get("parameters") or [],
        "embeddedApps": sk.get("embeddedApps"),
        "source": os.path.basename(path),
    }


def synth_envelope(cluster_uri, database):
    if not cluster_uri or not database:
        raise SystemExit(
            "FATAL: without --skeleton you must supply both --cluster-uri and "
            "--database. Get the URI from the KQL database's Database details "
            "pane -> Copy URI -> Query URI."
        )
    ds_id = det_id("datasource", database)
    return {
        "schema": FALLBACK_SCHEMA,
        "schema_version": FALLBACK_SCHEMA_VERSION,
        "id": det_id("dashboard", "p25"),
        "eTag": None,
        "dataSources": [
            {
                "id": ds_id,
                "name": database,
                "clusterUri": cluster_uri,
                "database": database,
                "kind": "manual-kusto",
                "scopeId": "kusto",
            }
        ],
        "autoRefresh": None,
        "parameters": [],
        "source": "FALLBACK DEFAULTS -- NOT VERIFIED AGAINST THIS TENANT",
    }


def build(env, warn):
    ds_id = env["dataSources"][0]["id"]

    pages, tiles, queries = [], [], []

    for p_idx, page in enumerate(PAGES):
        page_id = det_id("page", page["key"])
        pages.append({"id": page_id, "name": page["name"]})

        for tile in page["tiles"]:
            tile_id = det_id("tile", page["key"], tile["key"])
            entry = {
                "id": tile_id,
                "pageId": page_id,
                "title": tile.get("title", ""),
                "visualType": tile["visualType"],
                "layout": tile["layout"],
                "visualOptions": dict(tile.get("visualOptions") or {}),
            }
            # `subtitle` is the one authored key NOT confirmed by the measured
            # export -- both exported tiles were untitled, so an empty subtitle may
            # simply be omitted rather than unsupported. Kept by default because the
            # contract's Standing Rule requires takeaway subtitles; --no-subtitle
            # folds them into the title instead if the import rejects the key.
            if tile.get("subtitle"):
                if NO_SUBTITLE[0]:
                    entry["title"] = f"{tile.get('title', '')} — {tile['subtitle']}".strip(" —")
                else:
                    entry["subtitle"] = tile["subtitle"]

            if tile["visualType"] in ("markdown", "markdownCard"):
                # A text tile carries its content inline and has no query, so it
                # must not consume a queryId -- doing so would break the
                # "referenced exactly once" rule for a query that never exists.
                # markdownText belongs at the TILE ROOT, not inside visualOptions.
                # Measured from the import validator, 2026-08-19, in two steps:
                #   pass 1 (visualType "markdown"): missing queryRef + "must match
                #     'else' schema" -> the type was unrecognised and fell through
                #     to the generic tile branch.
                #   pass 2 (visualType "markdownCard"): "must match 'THEN' schema"
                #     + "must have required property 'markdownText'" + visualOptions
                #     .markdownText "must NOT have unevaluated properties".
                # Matching the *then* branch is the tell that markdownCard IS the
                # right type; the remaining errors say the property is required one
                # level up from where an earlier revision put it -- which had removed
                # it from the root precisely because it looked like an unknown key.
                # Guessing "safer" cost a round trip; the validator settled it.
                entry["markdownText"] = tile["markdown"]
            else:
                q_id = det_id("query", page["key"], tile["key"])
                text, _ = load_query(tile["query"])
                queries.append(
                    {
                        "id": q_id,
                        "text": text,
                        "dataSource": {"kind": "inline", "dataSourceId": ds_id},
                        "usedVariables": used_variables(text),
                    }
                )
                entry["queryRef"] = {"kind": "query", "queryId": q_id}

            tiles.append(entry)

    # Parameters: reuse the skeleton's if it already has a time-range parameter,
    # otherwise declare one. Reusing is strictly safer -- an exported parameter
    # carries this schema version's exact defaultValue shape.
    params = env["parameters"]
    if not params:
        warn(
            "no time-range parameter found in the envelope; emitting a minimal one. "
            "If Replace-with-file rejects it, add the parameter in the UI instead, "
            "re-export, and re-run with --skeleton."
        )
        params = [
            {
                "id": det_id("param", "timerange"),
                "kind": "duration",
                "displayName": TIME_PARAMETER["displayName"],
                "beginVariableName": TIME_PARAMETER["beginVariableName"],
                "endVariableName": TIME_PARAMETER["endVariableName"],
                "defaultValue": {"kind": "dynamic", "count": 90, "unit": "days"},
            }
        ]

    dash = {
        "$schema": env["schema"],
        "id": env["id"] or det_id("dashboard", "p25"),
        "schema_version": env["schema_version"],
        "title": DASHBOARD_TITLE,
        "tiles": tiles,
        "baseQueries": [],
        "parameters": params,
        "dataSources": env["dataSources"],
        "pages": pages,
        "queries": queries,
    }
    if env.get("eTag"):
        dash["eTag"] = env["eTag"]
    if env.get("autoRefresh"):
        dash["autoRefresh"] = env["autoRefresh"]
    if env.get("embeddedApps") is not None:
        dash["embeddedApps"] = env["embeddedApps"]
    return dash


UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.I
)


def validate(dash):
    """Refuse to emit a file that breaks the documented RTD rules."""
    errs = []

    def check_uuids(items, label):
        seen = set()
        for it in items:
            i = it.get("id")
            if not i or not UUID_RE.match(str(i)):
                errs.append(f"{label}: id is not a valid RFC 4122 UUID: {i!r}")
            if i in seen:
                errs.append(f"{label}: duplicate id {i}")
            seen.add(i)

    check_uuids(dash["tiles"], "tiles")
    check_uuids(dash["queries"], "queries")
    check_uuids(dash["pages"], "pages")
    check_uuids(dash["dataSources"], "dataSources")
    check_uuids(dash["parameters"], "parameters")

    # Rule: every queryId referenced exactly once across tiles/baseQueries/parameters
    refs = []
    for t in dash["tiles"]:
        qr = t.get("queryRef") or {}
        if qr.get("queryId"):
            refs.append(qr["queryId"])
    for b in dash["baseQueries"]:
        if b.get("id"):
            refs.append(b["id"])
    defined = {q["id"] for q in dash["queries"]}
    for q in defined:
        n = refs.count(q)
        if n != 1:
            errs.append(f"queryId {q} referenced {n} times; must be exactly 1")
    for r in refs:
        if r not in defined:
            errs.append(f"tile references undefined queryId {r}")

    # Every tile must belong to a declared page
    page_ids = {p["id"] for p in dash["pages"]}
    for t in dash["tiles"]:
        if t["pageId"] not in page_ids:
            errs.append(f"tile {t['id']} references unknown pageId {t['pageId']}")

    # Layout must fit the measured grid, and tiles must not overlap. Both of these
    # fail silently in the designer -- an overflowing tile is clamped and an
    # overlapping pair is reflowed, so the board renders "fine" but not as designed.

    occupied = {}
    for t in dash["tiles"]:
        lo = t["layout"]
        if lo["x"] + lo["width"] > GRID_WIDTH:
            errs.append(
                f"tile {t.get('title') or t['id']}: x={lo['x']} + width={lo['width']} "
                f"exceeds the {GRID_WIDTH}-column grid"
            )
        for dx in range(lo["width"]):
            for dy in range(lo["height"]):
                cell = (t["pageId"], lo["x"] + dx, lo["y"] + dy)
                if cell in occupied:
                    errs.append(
                        f"tiles {occupied[cell]} and {t.get('title') or t['id']} "
                        f"overlap at column {lo['x'] + dx}, row {lo['y'] + dy}"
                    )
                    return errs  # one report is enough; the rest would cascade
                occupied[cell] = t.get("title") or t["id"]

    # Floors -- a check that "nothing" cannot satisfy (CORE_RULES Appendix C 12).
    #
    # The tile floor is DERIVED FROM THE SPEC, not a magic number. An earlier
    # revision hardcoded ">= 15" and correctly refused to write when the eight 4x4
    # stat tiles were consolidated into two multistat tiles -- but it was refusing a
    # deliberate redesign, not a defect. A count taken from PAGES catches the thing
    # that actually matters (a tile silently failing to emit) and stays correct
    # across redesigns.
    expected_tiles = sum(len(p["tiles"]) for p in PAGES)
    expected_queries = sum(
        1 for p in PAGES for t in p["tiles"]
        if t["visualType"] not in ("markdown", "markdownCard")
    )
    if len(dash["tiles"]) != expected_tiles:
        errs.append(
            f"floor: {len(dash['tiles'])} tiles emitted, spec declares {expected_tiles}"
        )
    if len(dash["queries"]) != expected_queries:
        errs.append(
            f"floor: {len(dash['queries'])} queries emitted, spec declares {expected_queries}"
        )
    # An absolute lower bound as well, so an emptied spec cannot satisfy the above
    # by matching zero against zero.
    if len(dash["tiles"]) < 10:
        errs.append(f"floor: only {len(dash['tiles'])} tiles; a real board has >= 10")
    if len(dash["pages"]) != 3:
        errs.append(f"floor: {len(dash['pages'])} pages built; contract commits to 3")

    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skeleton", help="an exported RealTimeDashboard.json to take the envelope from")
    ap.add_argument("--cluster-uri", help="fallback only: the KQL database Query URI")
    ap.add_argument("--database", help="fallback only: the KQL database name")
    ap.add_argument("--out", default=os.path.join(HERE, "RTD_MeridianPay.json"))
    ap.add_argument(
        "--no-markdown",
        action="store_true",
        help="omit the 3 disclaimer-footer tiles. Use ONLY if the import rejects "
             "visualType 'markdown' -- it is the least-confirmed type in the spec, "
             "and dropping it costs a footer rather than the whole dashboard.",
    )
    ap.add_argument(
        "--no-subtitle",
        action="store_true",
        help="fold each tile's takeaway subtitle into its title. Use ONLY if the "
             "import rejects the `subtitle` key -- it is the one authored key the "
             "measured export did not confirm.",
    )
    args = ap.parse_args()
    NO_SUBTITLE[0] = args.no_subtitle

    if args.no_markdown:
        for page in PAGES:
            page["tiles"] = [t for t in page["tiles"] if t["visualType"] not in ("markdown", "markdownCard")]

    warnings = []

    def warn(msg):
        warnings.append(msg)

    if args.skeleton:
        env = read_skeleton(args.skeleton)
    else:
        env = synth_envelope(args.cluster_uri, args.database)
        warn(
            "NO SKELETON SUPPLIED. $schema, schema_version and the dataSource id "
            "are UNVERIFIED defaults. Export an empty dashboard and re-run with "
            "--skeleton before trusting this file."
        )

    dash = build(env, warn)
    errs = validate(dash)
    if errs:
        print("REFUSING TO WRITE -- validation failed:", file=sys.stderr)
        for e in errs:
            print("  x " + e, file=sys.stderr)
        sys.exit(1)

    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(dash, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    # Read it back -- an export that has not been read back is not an export.
    with open(args.out, "r", encoding="utf-8") as fh:
        rt = json.load(fh)

    print(f"wrote {args.out}")
    print(f"  envelope source : {env['source']}")
    print(f"  $schema         : {rt['$schema']}")
    print(f"  schema_version  : {rt['schema_version']}")
    print(f"  cluster         : {rt['dataSources'][0].get('clusterUri')}")
    print(f"  database        : {rt['dataSources'][0].get('database')}")
    print(f"  pages           : {len(rt['pages'])}")
    print(f"  tiles           : {len(rt['tiles'])}  "
          f"({sum(1 for t in rt['tiles'] if t['visualType'] in ('markdown', 'markdownCard'))} markdown)")
    print(f"  queries         : {len(rt['queries'])}")
    print("  visual types    : " + ", ".join(sorted({t["visualType"] for t in rt["tiles"]})))
    print("  json.load()     : OK, re-read from disk")
    for w in warnings:
        print("  ! WARNING: " + w)


if __name__ == "__main__":
    main()
