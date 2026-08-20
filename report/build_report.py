#!/usr/bin/env python3
# ============================================================================
# Project 25 (Meridian Pay) -- Session 6 -- PBIR report generator
#
# WHY A GENERATOR AND NOT HAND-WRITTEN JSON.
# The report is 5 pages / 30-odd visuals over a Direct Lake model whose measures
# all hang off ONE table (`alerts`) because Direct Lake forbids calculated
# tables. Every projection therefore repeats the same Entity name, and every
# caption has to stay in step with the measure it describes. Generating from a
# spec makes that mechanical instead of a proof-reading exercise, and it means a
# late measure rename is one edit, not thirty.
#
# EVERY SCHEMA VERSION AND EVERY JSON SHAPE HERE WAS HARVESTED, NOT REMEMBERED:
#   * $schema versions      -> Session 5, from P24's delivered report on disk
#   * visual JSON shapes    -> read back from P24's visual.json files this session
#   * decompositionTreeVisual roles + formatting property names + enum values
#                           -> `powerbi-report-author catalog describe` /
#                              `formatting describe-object`, this session.
#                              There is NO copyable sibling for this visual
#                              anywhere in this engine; the CLI is the source.
#   * every column name     -> read back from 02_KQL/*.kql DDL this session
#                              (spec reconciliation gate)
#
# OUTPUT: 06_Report/P25_MeridianPay.pbip + P25_MeridianPay.Report/
# Short names are deliberate -- P24 hit MAX_PATH and `git add` staged nothing.
# ============================================================================

import json
import os
import shutil
import uuid

# ---------------------------------------------------------------------------
# Harvested constants. Do not edit these from memory.
# ---------------------------------------------------------------------------
SCHEMA = {
    "visual": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.11.0/schema.json",
    "page": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
    "pages": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json",
    "report": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.3.0/schema.json",
    "version": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
    "pbir": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
    "pbip": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
    "platform": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
}

# Measured from the live tenant, 2026-08-19, via the workspace item list and the
# semantic model's own details URL. Not inferred.
WORKSPACE_NAME = "Real-Time Payment Risk"
WORKSPACE_ID = "bfea4167-0c4e-470a-b168-9bff5d3d2457"
MODEL_NAME = "SM_MeridianPay_DirectLake"
MODEL_ID = "fd7f0933-7635-4aa3-bfd2-ad14e4e7ae6e"

REPORT_NAME = "P25_MeridianPay"
THEME_FILE = "MyLifeInLegoBricks_Theme.json"

# MyLifeInLegoBricks -- Japanese Indigo (Bright). Read from the theme JSON, not
# invented. Standing Rule: no ad-hoc palette.
INK = "#27221F"
SEC = "#635E57"
TER = "#6E6961"
PAGE_BG = "#F2EFE6"
CARD_BG = "#FFFFFB"
BORDER = "#E1DACB"
D1 = "#165E83"   # primary indigo
D2 = "#33A6B8"   # teal        (theme "good")
D3 = "#1B3A5C"   # deep navy   (theme "maximum")
D4 = "#84B9CB"   # light blue  (theme "neutral")
D5 = "#B23A34"   # red         (theme "bad")
D6 = "#A98F3C"   # ochre

# Direct Lake forbids calculated tables, so there is no _Measures table.
# All 24 measures hang off `alerts`. MODEL_NOTES.md records why.
M_ENTITY = "alerts"

# ---------------------------------------------------------------------------
# Encoding helpers. Forms confirmed against `powerbi-report-author expr encode`.
# ---------------------------------------------------------------------------
def b(v):        return {"expr": {"Literal": {"Value": "true" if v else "false"}}}
def num(v):      return {"expr": {"Literal": {"Value": f"{v}D"}}}
def lng(v):      return {"expr": {"Literal": {"Value": f"{v}L"}}}
def s(v):        return {"expr": {"Literal": {"Value": f"'{v}'"}}}
def color(hexv): return {"solid": {"color": {"expr": {"Literal": {"Value": f"'{hexv}'"}}}}}


def measure(name):
    """A measure is always a bare {"Measure": {...}} -- never Aggregation-wrapped."""
    return {
        "field": {"Measure": {"Expression": {"SourceRef": {"Entity": M_ENTITY}},
                              "Property": name}},
        "queryRef": f"{M_ENTITY}.{name}",
        "nativeQueryRef": name,
        "active": True,
    }


def column(entity, prop):
    return {
        "field": {"Column": {"Expression": {"SourceRef": {"Entity": entity}},
                             "Property": prop}},
        "queryRef": f"{entity}.{prop}",
        "nativeQueryRef": prop,
        "active": True,
    }


def cat_filter(fname, entity, prop, values):
    """Visual-level categorical filter. filterConfig is a TOP-LEVEL sibling of
    `visual`, never nested inside it."""
    return {
        "filters": [{
            "name": fname,
            "field": {"Column": {"Expression": {"SourceRef": {"Entity": entity}},
                                 "Property": prop}},
            "type": "Categorical",
            "filter": {
                "Version": 2,
                "From": [{"Name": "f", "Entity": entity, "Type": 0}],
                "Where": [{"Condition": {"In": {
                    "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "f"}},
                                                "Property": prop}}],
                    "Values": [[{"Literal": {"Value": f"'{v}'"}}] for v in values],
                }}}],
            },
        }]
    }


def chrome(title=None, subtitle=None, alt=None, panel=True):
    """Shared visualContainerObjects. background/border/title/subTitle live HERE,
    never under /visual (retired pattern)."""
    vco = {}
    if panel:
        vco["background"] = [{"properties": {"show": b(True), "color": color(CARD_BG),
                                             "transparency": num(0)}}]
        vco["border"] = [{"properties": {"show": b(True), "color": color(BORDER),
                                         "radius": num(6)}}]
    else:
        vco["background"] = [{"properties": {"show": b(False)}}]
    if title:
        vco["title"] = [{"properties": {"show": b(True), "text": s(title), "fontSize": num(11),
                                        "bold": b(True), "fontColor": color(INK),
                                        "titleWrap": b(False)},
                         "selector": {"id": "default"}}]
    if subtitle:
        vco["subTitle"] = [{"properties": {"show": b(True), "text": s(subtitle),
                                           "fontSize": num(9), "fontColor": color(SEC)},
                            "selector": {"id": "default"}}]
    if alt:
        vco["general"] = [{"properties": {"altText": s(alt)}}]
    return vco


def pos(x, y, w, h, z, tab):
    return {"x": x, "y": y, "z": z, "height": h, "width": w, "tabOrder": tab}


# ---------------------------------------------------------------------------
# Visual constructors
# ---------------------------------------------------------------------------
def textbox(name, p, paragraphs, panel=False, pad=None):
    """paragraphs: list of (text, size_pt, hex, bold, italic)"""
    paras = []
    for text, size, col, bold, ital in paragraphs:
        style = {"fontSize": f"{size}pt", "color": {"solid": {"color": col}}}
        if bold:
            style["fontWeight"] = "bold"
        if ital:
            style["fontStyle"] = "italic"
        paras.append({"textRuns": [{"value": text, "textStyle": style}],
                      "horizontalTextAlignment": "left"})
    vco = {}
    if panel:
        vco["background"] = [{"properties": {"show": b(True), "color": color(CARD_BG),
                                             "transparency": num(0)}}]
        vco["border"] = [{"properties": {"show": b(True), "color": color(D1),
                                         "radius": num(8)}}]
        vco["padding"] = [{"properties": {"left": lng(14), "right": lng(14),
                                          "top": lng(12), "bottom": lng(12)}}]
    else:
        vco["background"] = [{"properties": {"show": b(False)}}]
    if pad and not panel:
        vco["padding"] = [{"properties": {"left": lng(pad), "right": lng(pad),
                                          "top": lng(4), "bottom": lng(4)}}]
    return {"$schema": SCHEMA["visual"], "name": name, "position": p,
            "visual": {"visualType": "textbox",
                       "objects": {"general": [{"properties": {"paragraphs": paras}}]},
                       "visualContainerObjects": vco}}


def nav(name, p):
    """Page-navigator pill bar. Retired: default/selected/hover objects -- use
    fill/text/outline with id selectors, as P24 does."""
    return {"$schema": SCHEMA["visual"], "name": name, "position": p,
            "visual": {
                "visualType": "pageNavigator",
                "objects": {
                    "pages": [{"properties": {"showHiddenPages": b(False)}}],
                    "shape": [{"properties": {"tileShape": s("pill")},
                               "selector": {"id": "default"}}],
                    "text": [
                        {"properties": {"fontSize": num(8), "fontColor": color(SEC)},
                         "selector": {"id": "default"}},
                        {"properties": {"fontColor": color(CARD_BG)},
                         "selector": {"id": "selected"}},
                        {"properties": {"fontColor": color(D1)},
                         "selector": {"id": "hover"}},
                    ],
                    "fill": [
                        {"properties": {"fillColor": color(CARD_BG)},
                         "selector": {"id": "default"}},
                        {"properties": {"fillColor": color(D3)},
                         "selector": {"id": "selected"}},
                        {"properties": {"fillColor": color(D4)},
                         "selector": {"id": "hover"}},
                    ],
                    "outline": [{"properties": {"lineColor": color(BORDER)},
                                 "selector": {"id": "default"}}],
                },
                "visualContainerObjects": {"background": [{"properties": {"show": b(False)}}]},
                "drillFilterOtherVisuals": True,
            },
            "howCreated": "InsertVisualButton"}


def rule(name, p):
    return {"$schema": SCHEMA["visual"], "name": name, "position": p,
            "visual": {"visualType": "shape",
                       "objects": {
                           "shape": [{"properties": {"tileShape": s("rectangleRoundedByPixel"),
                                                     "rectangleRoundedCurve": lng(0)}}],
                           "fill": [{"properties": {"show": b(True), "fillColor": color(BORDER)}}],
                       },
                       "visualContainerObjects": {"general": [{"properties": {"altText": s("")}}]}}}


def kpi_card(name, p, measures, alt, accent=D1):
    """Standing default 7: ONE multi-measure cardVisual per KPI row.
    cardVisual's bucket is `Data`, NOT `Values` -- `Values` is the legacy card."""
    return {"$schema": SCHEMA["visual"], "name": name, "position": p,
            "visual": {
                "visualType": "cardVisual",
                "query": {"queryState": {"Data": {"projections": [measure(m) for m in measures]}},
                          "sortDefinition": {"isDefaultSort": True}},
                "objects": {
                    "layout": [{"properties": {
                        "style": s("Cards"), "backgroundShow": b(True),
                        "backgroundFillColor": color(CARD_BG),
                        "rectangleRoundedCurve": lng(8), "borderWidth": num(1),
                        "borderColor": color(BORDER), "paddingUniform": lng(14),
                        "columnPadding": lng(12)}, "selector": {"id": "default"}}],
                    "accentBar": [{"properties": {
                        "show": b(True), "position": s("Left"), "color": color(accent),
                        "width": num(3)}, "selector": {"id": "default"}}],
                    "value": [{"properties": {"fontSize": num(19), "bold": b(True),
                                              "fontColor": color(D3)},
                               "selector": {"id": "default"}}],
                    "label": [{"properties": {"show": b(True), "fontSize": num(9),
                                              "fontColor": color(SEC), "textWrap": b(True)},
                               "selector": {"id": "default"}}],
                    "outline": [{"properties": {"show": b(False)}, "selector": {"id": "default"}}],
                },
                "visualContainerObjects": {
                    "background": [{"properties": {"show": b(False)}}],
                    "general": [{"properties": {"altText": s(alt)}}],
                },
            }}


def cartesian(name, vtype, p, cat, ys, title, subtitle, alt,
              colors=None, sort=None, legend=False, labels=True, filt=None):
    """columnChart / barChart / lineChart / clusteredColumnChart.
    lineChart uses `Category` (never the retired `Axis`) and ALWAYS carries a
    sortDefinition."""
    q = {"queryState": {"Category": {"projections": [cat]},
                        "Y": {"projections": ys}}}
    if sort is not None:
        q["sortDefinition"] = sort
    else:
        q["sortDefinition"] = {"isDefaultSort": True}

    objs = {
        "valueAxis": [{"properties": {"gridlineShow": b(False), "show": b(False)},
                       "selector": {"id": "default"}}],
        "categoryAxis": [{"properties": {"gridlineShow": b(False), "fontSize": num(9),
                                         "labelColor": color(INK)},
                          "selector": {"id": "default"}}],
        "labels": [{"properties": {"show": b(labels), "fontSize": num(9),
                                   "color": color(INK)}}],
        "legend": [{"properties": {"show": b(legend), "fontSize": num(9),
                                   "labelColor": color(SEC)}}],
    }
    if colors:
        if len(colors) == 1:
            objs["dataPoint"] = [{"properties": {"fill": color(colors[0])}}]
        else:
            objs["dataPoint"] = [
                {"properties": {"fill": color(c)},
                 "selector": {"metadata": ys[i]["queryRef"]}}
                for i, c in enumerate(colors)
            ]
    if vtype == "lineChart":
        objs["lineStyles"] = [{"properties": {"strokeWidth": num(3), "showMarker": b(False),
                                              "lineStyle": s("solid")}}]

    v = {"$schema": SCHEMA["visual"], "name": name, "position": p,
         "visual": {"visualType": vtype, "query": q, "objects": objs,
                    "visualContainerObjects": chrome(title, subtitle, alt),
                    "drillFilterOtherVisuals": True}}
    if filt:
        v["filterConfig"] = filt
    return v


def donut(name, p, cat, y, title, subtitle, alt):
    return {"$schema": SCHEMA["visual"], "name": name, "position": p,
            "visual": {
                "visualType": "donutChart",
                "query": {"queryState": {"Category": {"projections": [cat]},
                                         "Y": {"projections": [y]}},
                          "sortDefinition": {"isDefaultSort": True}},
                "objects": {
                    "legend": [{"properties": {"show": b(True), "position": s("Right"),
                                               "fontSize": num(9), "labelColor": color(SEC)}}],
                    "labels": [{"properties": {"show": b(True), "fontSize": num(9),
                                               "color": color(INK),
                                               "labelStyle": s("Data value, percent of total")}}],
                    "slices": [{"properties": {"innerRadiusRatio": num(60)}}],
                },
                "visualContainerObjects": chrome(title, subtitle, alt),
                "drillFilterOtherVisuals": True,
            }}


def matrix(name, p, rows, values, title, subtitle, alt, filt=None):
    """matrix is the default tabular visual for row-header + measure grids."""
    # Property names below are exactly what `formatting describe-object matrix <obj>`
    # returns. A matrix has NO per-object fontSize -- text size is one number on
    # `general`, and value font colour is split odd/even (Primary/Secondary), not
    # a single `fontColor`. Writing the plausible names produced 24 of this
    # build's 26 first-pass validator errors; all 24 were in this one block.
    # `subTotals` here carries only outline/fontColor/backColor -- the
    # rowSubtotals/columnSubtotals toggles are not in this schema, so row
    # subtotals stay a Desktop follow-up rather than a guessed property.
    objs = {
        "general": [{"properties": {"textSize": num(9)}}],
        "columnHeaders": [{"properties": {"fontColor": color(SEC),
                                          "backColor": color(CARD_BG),
                                          "outline": s("BottomOnly")}}],
        "rowHeaders": [{"properties": {"fontColor": color(INK),
                                       "outline": s("None"),
                                       "wordWrap": b(False)}}],
        "values": [{"properties": {"fontColorPrimary": color(INK),
                                   "fontColorSecondary": color(INK)}}],
        "grid": [{"properties": {"gridVertical": b(False), "gridHorizontal": b(True),
                                 "gridHorizontalColor": color(BORDER),
                                 "rowPadding": num(6)}}],
    }
    v = {"$schema": SCHEMA["visual"], "name": name, "position": p,
         "visual": {"visualType": "matrix",
                    "query": {"queryState": {"Rows": {"projections": rows},
                                             "Values": {"projections": values}},
                              "sortDefinition": {"isDefaultSort": True}},
                    "objects": objs,
                    "visualContainerObjects": chrome(title, subtitle, alt)}}
    if filt:
        v["filterConfig"] = filt
    return v


def table_ex(name, p, cols, title, subtitle, alt, sort=None, filt=None):
    """tableEx: single flat `Values` bucket. NEVER carries drillFilterOtherVisuals."""
    q = {"queryState": {"Values": {"projections": cols}}}
    q["sortDefinition"] = sort if sort else {"isDefaultSort": True}
    v = {"$schema": SCHEMA["visual"], "name": name, "position": p,
         "visual": {"visualType": "tableEx", "query": q,
                    "objects": {
                        "columnHeaders": [{"properties": {"fontColor": color(SEC),
                                                          "backColor": color(CARD_BG),
                                                          "fontSize": num(9), "bold": b(True)}}],
                        "values": [{"properties": {"fontColor": color(INK), "fontSize": num(9)}}],
                        "grid": [{"properties": {"gridVertical": b(False),
                                                 "gridHorizontalColor": color(BORDER),
                                                 "rowPadding": num(5)}}],
                    },
                    "visualContainerObjects": chrome(title, subtitle, alt)}}
    if filt:
        v["filterConfig"] = filt
    return v


def slicer(name, p, field, alt, sync=None):
    v = {"$schema": SCHEMA["visual"], "name": name, "position": p,
         "visual": {
             "visualType": "slicer",
             "query": {"queryState": {"Values": {"projections": [field]}}},
             "objects": {
                 "data": [{"properties": {"mode": s("Dropdown")}}],
                 "header": [{"properties": {"show": b(True), "textSize": num(9),
                                            "fontColor": color(SEC),
                                            "background": color(CARD_BG)},
                             "selector": {"id": "default"}}],
                 "items": [{"properties": {"textSize": num(9), "fontColor": color(INK)}}],
                 "general": [{"properties": {}}],
             },
             "visualContainerObjects": {
                 "background": [{"properties": {"show": b(True), "color": color(CARD_BG)}}],
                 "border": [{"properties": {"show": b(True), "color": color(BORDER),
                                            "radius": num(6)}}],
                 "general": [{"properties": {"altText": s(alt)}}],
             },
         }}
    if sync:
        # syncGroup is a SIBLING of visualType inside "visual", never in objects.
        v["visual"]["syncGroup"] = {"groupName": sync, "fieldChanges": True,
                                    "filterChanges": True}
    return v


def decomp_tree(name, p, analyze, explain_by, title, subtitle, alt, filt=None):
    """decompositionTreeVisual.

    NO COPYABLE SIBLING EXISTS ANYWHERE IN THIS ENGINE -- P24's 115 visuals do
    not contain one, PBIP_GENERATION_GUIDE.md has zero occurrences, and _ENGINE
    mentions it only in prose. Every role name, formatting object name, property
    name and enum value below came from the official CLI this session:

      powerbi-report-author catalog describe decompositionTreeVisual
        roles: Analyze (Measure, maxPerRole 1) | ExplainBy (Grouping) | Tooltips
        requiredRoles: ["Analyze"]
        formattingObjects: analysis categoryLabels dataBars dataLabels general
                           insights levelHeader tree

      powerbi-report-author formatting describe-object decompositionTreeVisual tree
        density(enum: dense|default|sparse) accentColor(fill)
        connectorDefaultColor(fill) connectorType(enum: curve|round)
        responsiveLayout(bool) barsPerLevel(integer) defaultClickAction(enum)

      powerbi-report-author formatting describe-object decompositionTreeVisual analysis
        aiEnabled(bool) aiMode(enum: absolute|relative)

    aiEnabled is set FALSE deliberately: gate C4 recorded that this tenant has no
    Copilot licence, so AI splits would either not render or render an empty
    affordance. Better an honest tree than a broken button.
    """
    v = {"$schema": SCHEMA["visual"], "name": name, "position": p,
         "visual": {
             "visualType": "decompositionTreeVisual",
             "query": {"queryState": {
                 "Analyze": {"projections": [analyze]},
                 "ExplainBy": {"projections": explain_by},
             }},
             "objects": {
                 "tree": [{"properties": {
                     "density": s("default"),
                     "accentColor": color(D1),
                     "connectorDefaultColor": color(BORDER),
                     "connectorType": s("curve"),
                     "responsiveLayout": b(True),
                     "barsPerLevel": lng(8),
                     "defaultClickAction": s("select"),
                 }}],
                 "analysis": [{"properties": {"aiEnabled": b(False)}}],
             },
             "visualContainerObjects": chrome(title, subtitle, alt),
             "drillFilterOtherVisuals": True,
         }}
    if filt:
        v["filterConfig"] = filt
    return v


# ---------------------------------------------------------------------------
# Page shell -- standing default 3: Title / PillNav / Divider / Body / Disclaimer
# ---------------------------------------------------------------------------
DISCLAIMER = ("Meridian Pay  |  Real-Time Payments Risk  |  Live Direct Lake connection to "
              "SM_MeridianPay_DirectLake over Eventhouse OneLake availability  |  "
              "Synthetic data, generated from a fixed seed (MASTER_SEED=250817) -- no real "
              "cardholder, merchant or issuer data exists  |  Portfolio build, not a "
              "production system")


def shell(page_kicker, title, takeaway, disc_z=8000):
    """Returns the six chrome visuals every page carries."""
    return [
        # Heights are at the validator's textbox floors, not eyeballed:
        # 9pt needs >=34px and 17pt needs >=43px once 8+8 padding is counted,
        # or the control renders a scrollbar over the text.
        textbox("Kick", pos(24, 10, 780, 34, 4000, 100),
                [(page_kicker, 9, D1, True, False)]),
        textbox("Title", pos(24, 44, 780, 44, 3000, 200),
                [(title, 17, INK, True, False)]),
        textbox("Take", pos(24, 88, 780, 34, 2000, 300),
                [(takeaway, 9, SEC, False, False)]),
        nav("Nav", pos(24, 128, 1232, 30, 6000, 500)),
        rule("Rule", pos(24, 162, 1232, 2, 5000, 600)),
        textbox("Disc", pos(24, 664, 1232, 40, disc_z, 9000),
                [(DISCLAIMER, 8, TER, False, True)]),
    ]


# ---------------------------------------------------------------------------
# PAGE 1 -- Home
# ---------------------------------------------------------------------------
def page_home():
    v = shell(
        "MERIDIAN PAY  ·  SE-ASIA ACQUIRER  ·  1,500 TERMINALS  ·  SYNTHETIC ESTATE",
        "The hot path decides in seconds. The cold path marks its homework.",
        "Authorisations and device telemetry land in an Eventhouse within seconds and four "
        "reflexes fire on patterns, not schedules. Then the chargebacks arrive 30-60 days "
        "later and the same platform grades every alert it raised.")

    v.append(textbox("TakeBox", pos(830, 10, 426, 112, 0, 400), [
        ("WHAT MAKES THIS DIFFERENT", 9, D1, True, False),
        ("Nobody demos the second half. A real-time system that publishes its own precision "
         "has to survive being wrong in public -- and this one shows which cohorts it is not "
         "yet entitled to score.", 9, INK, False, False),
    ], panel=True))

    v.append(kpi_card("Kpi", pos(24, 174, 1232, 104, 7000, 700),
                      ["Total Auths", "Approval Rate %", "Alerts Raised",
                       "Disputes Matured", "Reflex Types Fired"],
                      "Headline KPI row on the Home page: authorisation volume, approval "
                      "rate, alerts raised, matured disputes and reflex types fired."))

    v.append(kpi_card("Estate", pos(24, 288, 604, 96, 1000, 800),
                      ["Merchants", "Stores", "Terminals"],
                      "Estate size read from dim_estate, never hand-typed.", accent=D2))

    v.append(textbox("Basis", pos(648, 288, 608, 96, 1100, 850), [
        ("Basis and scale", 9, D1, True, False),
        ("90-day authorisation backfill, 30-day telemetry, disputes matured as of SIM_NOW "
         "2026-08-17. Disputes read low against the eventual total because only the T-90 to "
         "T-30 cohorts have had time to charge back -- that is a maturity effect, not a "
         "shortfall, and the Alert Precision page is built around it.", 9, SEC, False, False),
    ], panel=False, pad=2))

    v.append(cartesian("ByReflex", "columnChart", pos(24, 396, 604, 256, 1200, 900),
                       column("alerts", "reflex_type"), [measure("Alerts Raised")],
                       "Where the alerts come from",
                       "Alerts raised by reflex. Volume is not quality -- the next page grades them.",
                       "Column chart of alerts raised by reflex type on the Home page.",
                       colors=[D1],
                       sort={"sort": [{"field": {"Measure": {"Expression": {"SourceRef": {"Entity": M_ENTITY}},
                                                            "Property": "Alerts Raised"}},
                                       "direction": "Descending"}]}))

    v.append(donut("ByCohort", pos(648, 396, 608, 256, 1300, 1000),
                   column("alerts", "maturity_cohort"), measure("Alerts Raised"),
                   "How much of it is gradeable yet",
                   "Alerts by maturity cohort. Only the fully matured cohort is entitled to a precision number.",
                   "Donut chart of alerts by maturity cohort on the Home page."))
    return v


# ---------------------------------------------------------------------------
# PAGE 2 -- Alert Precision (the pitch page)
# ---------------------------------------------------------------------------
def page_precision():
    v = shell(
        "THE PITCH  ·  A REAL-TIME SYSTEM THAT MEASURES ITS OWN PRECISION",
        "Alert Precision, by maturity cohort -- never blended.",
        "Precision is only reported for the cohort old enough to have been graded. Every "
        "other cohort renders blank and is labelled, because a zero would read as a "
        "confident wrong answer.")

    v.append(slicer("SlCohort", pos(1058, 10, 198, 76, 10000, 450),
                    column("alerts", "maturity_cohort"),
                    "Maturity cohort filter on the Alert Precision page.",
                    sync="CohortSync"))

    # The cohort grid. Cohort Status is what renders where a percentage must not.
    v.append(matrix("MxCohort", pos(24, 174, 620, 212, 1000, 700),
                    [column("alerts", "maturity_cohort")],
                    [measure("Alerts Raised"),
                     measure("Alerts Matched (Ground Truth)"),
                     measure("Alerts Confirmed (Disputes)"),
                     measure("Precision (Reportable)"),
                     measure("Cohort Status")],
                    "Precision is a property of a cohort, not of a detector",
                    "Blank precision plus a status label -- the two together make blending structurally impossible.",
                    "Matrix of alerts, matches and reportable precision by maturity cohort."))

    # THE strongest thing this project has to say, given its own visual.
    v.append(cartesian("GapViz", "clusteredColumnChart", pos(664, 174, 592, 212, 1100, 800),
                       column("alerts", "reflex_type"),
                       [measure("Alerts Matched (Ground Truth)"),
                        measure("Alerts Confirmed (Disputes)")],
                       "Two graders, the same alerts, different answers",
                       "Ground truth is an oracle only synthetic data has. Disputes are what a real acquirer actually gets.",
                       "Clustered column chart comparing ground-truth matches against "
                       "dispute confirmations for each reflex.",
                       colors=[D1, D6], legend=True))

    v.append(cartesian("ColPrec", "columnChart", pos(24, 398, 620, 254, 1200, 900),
                       column("alerts", "reflex_type"), [measure("Precision (Reportable)")],
                       "Reportable precision, graded cohort only",
                       "Bound to the guarded measure. A reflex with no graded rows renders blank, not zero.",
                       "Column chart of reportable precision by reflex type, filtered to "
                       "the fully graded T-90 to T-60 cohort.",
                       colors=[D2],
                       filt=cat_filter("fPrecCohort", "alerts", "maturity_cohort",
                                       ["graded_T90_T60"])))

    v.append(matrix("RecallTbl", pos(664, 398, 356, 254, 1300, 1000),
                    [column("alerts", "reflex_type")],
                    [measure("Episodes In Scope"), measure("Episodes Detected"),
                     measure("Recall (Ground Truth)")],
                    "Recall, by reflex type only",
                    "A planted episode has no maturity cohort, so a per-cohort recall would have no honest denominator.",
                    "Matrix of planted episodes, episodes detected and recall by reflex type."))

    v.append(textbox("Caveats", pos(1040, 398, 216, 254, 1400, 1100), [
        ("READ THESE BEFORE THE NUMBERS", 8, D5, True, False),
        ("Terminal compromise's 1.000 is a demonstration, not a measurement -- the episode "
         "was chosen because it satisfied both detector gates, then the lookback was tuned "
         "to its duration.", 8, INK, False, False),
        ("Terminal dark: precision 0.163, recall 1.000 (60/60), measured 2026-08-19 with the "
         "time-travel variant reading telemetry_curated directly -- the shipped arg_max "
         "materialized view cannot be graded against a frozen backfill. Shifting every window "
         "back 180 days returns 0 matches, so the overlap test binds.", 8, INK, False, False),
        ("That 0.163 is NOT a threshold artefact. Precision is flat from 20 to 45 minutes "
         "(0.163 / 0.161 / 0.189) while recall falls to 0.767, so the 309 unmatched firings are "
         "long darkness inside modelled trading hours, not heartbeat jitter. 20 minutes is the "
         "measured best operating point of the three.", 8, INK, False, False),
        ("Dispute-only grading systematically under-counts. A team grading on chargebacks "
         "alone would call this detector 57% wrong when it was right every time.",
         8, INK, False, False),
    ], panel=True))
    return v


# ---------------------------------------------------------------------------
# PAGE 3 -- Merchant & Terminal Risk (carries the C1 degradation deliverable)
# ---------------------------------------------------------------------------
def page_merchant():
    v = shell(
        "ESTATE HIERARCHY  ·  MERCHANT -> STORE -> TERMINAL -> REFLEX",
        "Merchant & Terminal Risk.",
        "The decomposition tree over dim_estate is what replaced Digital Twin Builder when "
        "gate C1 failed in Phase 0. It resolves every alert to a merchant and a store, "
        "which is the capability the twin was there to provide.")

    v.append(slicer("SlReflex", pos(1058, 10, 198, 76, 10000, 450),
                    column("alerts", "reflex_type"),
                    "Reflex type filter on the Merchant & Terminal Risk page."))

    # entity_type guard is load-bearing: reflex-4 rows carry an ISSUER BIN in
    # entity_id, which matches no terminal and would land in the blank member.
    v.append(decomp_tree("Tree", pos(24, 174, 836, 478, 1000, 700),
                         measure("Alerts Raised"),
                         [column("dim_estate", "merchant_id"),
                          column("dim_estate", "store_id"),
                          column("dim_estate", "terminal_id"),
                          column("alerts", "reflex_type")],
                         "Which merchant, which store, which terminal",
                         "Alerts raised, decomposed down the estate hierarchy. Terminal-scoped reflexes only -- issuer alerts carry a BIN, not a terminal.",
                         "Decomposition tree of alerts raised, explained by merchant, "
                         "store, terminal and reflex type.",
                         filt=cat_filter("fTreeEntity", "alerts", "entity_type",
                                         ["terminal"])))

    # THE GUARD WAS MISSING HERE AND ONLY HERE (fixed 2026-08-19, Session 7).
    # `Tree` and `TopTerm` both carry cat_filter on entity_type; this one did not,
    # so the 95 issuer-degradation alerts -- whose entity_id is a BIN, not a
    # terminal -- fell into dim_estate's blank member and every tier rendered the
    # ungrouped total of 186. Both validators passed it, because "does this measure
    # resolve" and "does this number mean what the title says" are different
    # questions (CORE_RULES_ESSENTIAL SS4 Step 0). Caught only by reading the
    # rendered page. Measured after the fix: large 41 / medium 23 / small 27 = 91.
    v.append(cartesian("ByTier", "barChart", pos(880, 174, 376, 228, 1100, 800),
                       column("dim_estate", "merchant_tier"), [measure("Alerts Raised")],
                       "Alerts by merchant tier",
                       "Terminal-scoped alerts only (91 of 186) -- issuer alerts carry a BIN and resolve to no merchant. A big tier raising more is arithmetic, not risk.",
                       "Bar chart of terminal-scoped alerts raised by merchant tier.",
                       colors=[D3],
                       filt=cat_filter("fTierEntity", "alerts", "entity_type", ["terminal"]),
                       sort={"sort": [{"field": {"Measure": {"Expression": {"SourceRef": {"Entity": M_ENTITY}},
                                                            "Property": "Alerts Raised"}},
                                       "direction": "Descending"}]}))

    v.append(matrix("TopTerm", pos(880, 414, 376, 238, 1200, 900),
                    [column("alerts", "entity_id")],
                    [measure("Alerts Raised"), measure("Alerts Matched (Ground Truth)")],
                    "Terminals raising the most alerts",
                    "Sorted by volume. Matched shows how many of them were real.",
                    "Matrix of the terminals raising the most alerts.",
                    filt=cat_filter("fTermEntity", "alerts", "entity_type", ["terminal"])))
    return v


# ---------------------------------------------------------------------------
# PAGE 4 -- Estate Health (PBI)
# ---------------------------------------------------------------------------
def page_estate():
    v = shell(
        "STREAM DATA QUALITY  ·  SIX RULES  ·  PERSISTED PER RUN",
        "Estate Health and stream data quality.",
        "Every DQ rule persists a row per run and is only counted as passed when it both "
        "found what it was looking for and proved it read something. 'The cell didn't "
        "error' is not a pass.")

    v.append(kpi_card("DqKpi", pos(24, 174, 1232, 100, 1000, 700),
                      ["DQ Rules Passed", "DQ Rows Flagged", "Terminals with Alerts",
                       "Estate Coverage %"],
                      "Data-quality KPI row: rules passed on the latest run, rows flagged "
                      "across all six rules, terminals with at least one alert, and the "
                      "share of the estate that has ever raised one. 'Rows flagged' is "
                      "deliberately not called faults -- rule 5 contributes 2,151,584 of "
                      "the 2,185,579 and its own detail JSON calls those rows carrying the "
                      "v2 sca_flag, which is a population, not a fault.", accent=D2))

    v.append(table_ex("DqTbl", pos(24, 286, 800, 366, 1100, 800),
                      [column("dq_results", "run_time"),
                       column("dq_results", "rule_number"),
                       column("dq_results", "rule_name"),
                       column("dq_results", "rows_checked"),
                       column("dq_results", "faults_found"),
                       column("dq_results", "independent_check_passed"),
                       column("dq_results", "floor_satisfied")],
                      "Six stream DQ rules, every run retained",
                      "Newest first. dq_results is never overwritten. NOTE: run_time is stamped PER RULE (6 distinct values, 1 run_id) -- group or filter on run_id, never on run_time.",
                      "Table of stream data-quality rule results, newest run first.",
                      sort={"sort": [
                          {"field": {"Column": {"Expression": {"SourceRef": {"Entity": "dq_results"}},
                                                "Property": "run_time"}},
                           "direction": "Descending"},
                          {"field": {"Column": {"Expression": {"SourceRef": {"Entity": "dq_results"}},
                                                "Property": "rule_number"}},
                           "direction": "Ascending"}]}))

    v.append(cartesian("CovTier", "columnChart", pos(840, 286, 416, 366, 1200, 900),
                       column("dim_estate", "merchant_tier"),
                       [measure("Estate Coverage %")],
                       "Share of each tier that ever raised an alert",
                       "Low is good news. A tier at zero means no terminal there has ever tripped a reflex.",
                       "Column chart of estate coverage percentage by merchant tier.",
                       colors=[D4]))
    return v


# ---------------------------------------------------------------------------
# PAGE 5 -- Report guide + data dictionary (standing default 6, the "+1 page")
# ---------------------------------------------------------------------------
def page_guide():
    v = shell(
        "REPORT GUIDE  ·  DATA DICTIONARY  ·  KNOWN LIMITATIONS",
        "How to read this report, and what it is not claiming.",
        "Written as part of the build rather than bolted on, because most of what is "
        "interesting here is a caveat.")

    v.append(textbox("G1", pos(24, 174, 404, 304, 1000, 700), [
        ("HOW TO READ IT", 9, D1, True, False),
        ("Home sizes the estate and the alert volume. Alert Precision is the argument. "
         "Merchant & Terminal Risk resolves an alert to a place. Estate Health is the "
         "data-quality evidence.", 9, INK, False, False),
        ("Precision (Reportable) is the only precision measure bound to a visual. It "
         "returns blank for any cohort that is not fully graded and for any mixed "
         "selection. If a bar is missing, that is the guard working.", 9, INK, False, False),
        ("Recall is reported by reflex type and never by maturity cohort. A planted "
         "episode has no cohort, so a per-cohort recall would divide a filtered numerator "
         "by an unfiltered denominator.", 9, INK, False, False),
    ], panel=True))

    v.append(textbox("G2", pos(444, 174, 404, 304, 1100, 800), [
        ("DATA DICTIONARY", 9, D1, True, False),
        ("alerts -- one row per reflex firing, written by Activator. Carries "
         "maturity_cohort, and the two grading columns gt_episode_id and "
         "dispute_confirmed added by 12_alert_grading.kql.", 9, INK, False, False),
        ("ground_truth -- the injected episode register: 137 episodes across four types. "
         "Deliberately disconnected from alerts; the match is an interval overlap resolved "
         "in KQL, not a relationship.", 9, INK, False, False),
        ("dim_estate -- one row per terminal, resolving terminal to store to merchant with "
         "tier and MCC. Zero orphan terminals, checked by query.", 9, INK, False, False),
        ("dq_results -- one row per DQ rule per run, never overwritten.", 9, INK, False, False),
        ("dispute_curated / auth_curated / telemetry_curated -- the KQL update-policy "
         "outputs. There is no Gold notebook underneath this model.", 9, INK, False, False),
    ], panel=True))

    v.append(textbox("G3", pos(864, 174, 392, 304, 1200, 900), [
        ("KNOWN LIMITATIONS, STATED UP FRONT", 9, D5, True, False),
        ("All data is synthetic, generated from a fixed seed. No real cardholder, merchant "
         "or issuer data exists anywhere in this build.", 9, INK, False, False),
        ("Terminal compromise's precision is circular -- see the Alert Precision page.",
         9, INK, False, False),
        ("Terminal dark's precision could not be measured from the shipped materialized view "
         "-- an arg_max MV has already collapsed to one row per terminal, so no query can "
         "recover the history. A time-travel variant reading telemetry_curated directly grades "
         "it at precision 0.163 and recall 1.000 (60/60), measured 2026-08-19, with a "
         "180-day shifted-window control returning 0.", 9, INK, False, False),
        ("The right-censored tail this grading excludes is 219 terminals -- those dark at the "
         "backfill boundary while their store was open. Not the 1,498 whose last heartbeat is "
         "simply stale, most of which are closed stores at 00:35.", 9, INK, False, False),
        ("Issuer degradation's 0.021 is a real measurement, not a bug: the detector is "
         "tuned to fire early on a statistical deviation, and most deviations are not "
         "planted episodes.", 9, INK, False, False),
    ], panel=True))

    v.append(textbox("G4", pos(24, 490, 1232, 162, 1300, 1000), [
        ("WHAT WAS DELIBERATELY NOT DONE", 9, D1, True, False),
        ("No calculated columns and no calculated tables anywhere in this model. Adding "
         "either would drop it out of Direct Lake into DirectQuery fallback and quietly "
         "void the claim that there is no Gold notebook underneath it. That is also why "
         "there is no DAX Calendar table -- the engine's standing default -- and why "
         "alert grading is done in KQL, which is where this project's transformation layer "
         "lives by design.", 9, INK, False, False),
        ("No new theme JSON was generated. This report uses "
         "Themes/MyLifeInLegoBricks_Theme.json, the standing default, unmodified apart "
         "from the filename-matching name field the registration format requires.",
         9, INK, False, False),
    ], panel=True))
    return v


# ---------------------------------------------------------------------------
# Assemble
# ---------------------------------------------------------------------------
PAGES = [
    ("Home", "1 | Home", page_home),
    ("Precision", "2 | Alert Precision", page_precision),
    ("Merchant", "3 | Merchant & Terminal Risk", page_merchant),
    ("Estate", "4 | Estate Health", page_estate),
    ("Guide", "5 | Guide & Data Dictionary", page_guide),
]


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def build(out_root, theme_src):
    rep = os.path.join(out_root, f"{REPORT_NAME}.Report")
    if os.path.isdir(rep):
        shutil.rmtree(rep)

    # ---- .pbip -----------------------------------------------------------
    write_json(os.path.join(out_root, f"{REPORT_NAME}.pbip"), {
        "$schema": SCHEMA["pbip"], "version": "1.0",
        "artifacts": [{"report": {"path": f"{REPORT_NAME}.Report"}}],
        "settings": {"enableAutoRecovery": True},
    })

    # ---- .platform (Fabric Git integration, component 11) -----------------
    logical = str(uuid.uuid5(uuid.NAMESPACE_URL,
                             f"https://p25.meridianpay/report/{REPORT_NAME}"))
    write_json(os.path.join(rep, ".platform"), {
        "$schema": SCHEMA["platform"],
        "metadata": {"type": "Report", "displayName": REPORT_NAME},
        "config": {"version": "2.0", "logicalId": logical},
    })

    # ---- definition.pbir : byConnection to the Direct Lake model ----------
    conn = (f"Data Source=powerbi://api.powerbi.com/v1.0/myorg/{WORKSPACE_NAME};"
            f"initial catalog={MODEL_NAME};access mode=readonly;"
            f"integrated security=ClaimsToken;semanticmodelid={MODEL_ID}")
    write_json(os.path.join(rep, "definition.pbir"), {
        "$schema": SCHEMA["pbir"], "version": "4.0",
        "datasetReference": {"byConnection": {"connectionString": conn}},
    })

    # ---- version.json ----------------------------------------------------
    write_json(os.path.join(rep, "definition", "version.json"),
               {"$schema": SCHEMA["version"], "version": "2.0.0"})

    # ---- theme: registered resource --------------------------------------
    # CORE_RULES_ESSENTIAL 2.2 -- the JSON's internal "name" must equal the
    # filename INCLUDING .json. The source theme's name is its human title, so
    # it is rewritten on copy. Nothing else about the theme is touched.
    with open(theme_src, encoding="utf-8") as fh:
        theme = json.load(fh)
    theme["name"] = THEME_FILE
    write_json(os.path.join(rep, "StaticResources", "RegisteredResources", THEME_FILE), theme)

    # ---- report.json -----------------------------------------------------
    write_json(os.path.join(rep, "definition", "report.json"), {
        "$schema": SCHEMA["report"],
        "themeCollection": {"customTheme": {
            "name": THEME_FILE,
            # 3-key OBJECT, never a string.
            "reportVersionAtImport": {"visual": "2.11.0", "report": "3.3.0", "page": "2.1.0"},
            "type": "RegisteredResources",
        }},
        "objects": {
            "section": [{"properties": {"verticalAlignment": s("Top")}}],
            "outspacePane": [{"properties": {"expanded": b(False)}}],
        },
        "resourcePackages": [{
            "name": "RegisteredResources", "type": "RegisteredResources",
            "items": [{"name": THEME_FILE, "path": THEME_FILE, "type": "CustomTheme"}],
        }],
        "settings": {
            "useStylableVisualContainerHeader": True,
            "exportDataMode": "AllowSummarized",
            "defaultDrillFilterOtherVisuals": True,
            "allowChangeFilterTypes": True,
            "useEnhancedTooltips": True,
            "useDefaultAggregateDisplayName": True,
        },
    })

    # ---- pages -----------------------------------------------------------
    order = [p[0] for p in PAGES]
    write_json(os.path.join(rep, "definition", "pages", "pages.json"), {
        "$schema": SCHEMA["pages"], "pageOrder": order,
        "activePageName": order[0], "landingPageName": order[0],
    })

    counts = {}
    for name, display, fn in PAGES:
        pdir = os.path.join(rep, "definition", "pages", name)
        # page.json NEVER contains a `visuals` array.
        write_json(os.path.join(pdir, "page.json"), {
            "$schema": SCHEMA["page"], "name": name, "displayName": display,
            "displayOption": "FitToPage", "height": 720, "width": 1280,
        })
        vis = fn()
        for v in vis:
            write_json(os.path.join(pdir, "visuals", v["name"], "visual.json"), v)
        counts[name] = len(vis)
    return rep, counts


if __name__ == "__main__":
    import sys
    out = sys.argv[1]
    theme = sys.argv[2]
    rep, counts = build(out, theme)
    total = sum(counts.values())
    print(f"built {rep}")
    for k, n in counts.items():
        print(f"  {k:<10} {n:>2} visuals")
    print(f"  {'TOTAL':<10} {total:>2} visuals across {len(counts)} pages")
