"""
Project 25 (Meridian Pay) -- Session 5, Phase 4
rtd_spec.py -- the Real-Time Dashboard specification, as DATA.

This file is the single source of truth for what the dashboard contains: pages,
tiles, layout, visual types and which .kql file backs each tile. build_rtd_json.py
turns it into RealTimeDashboard.json; it holds no dashboard content of its own.

WHY SPLIT THIS WAY. The tile *content* (KQL, titles, takeaways) is reviewable and
diffable here and in queries/*.kql. The *envelope* ($schema, schema_version,
dataSource ids, eTag) is tenant- and version-specific and must be taken from a
real exported dashboard, never hand-written -- the RTD analogue of CORE_RULES
Sec48a ("grep the working sibling; never write schema versions from memory").

-----------------------------------------------------------------------------
EVERYTHING BELOW WAS MEASURED FROM A REAL EXPORT, 2026-08-19, schema_version 78.
Three things the export corrected, all of which would have shipped broken:

 1. GRID WIDTH IS 16, NOT 24. Observed defaults: a KPI tile at x=0 w=4 and a
    table at x=4 w=9 (right edge 13), and their on-screen proportions (25% and
    ~56% of the canvas) only fit a 16-column grid. Every layout below is on 16.
    Had this stayed at 24, every tile would have overflowed.

 2. `kpi` IS A GAUGE, NOT A BIG-NUMBER CARD. The exported KPI tile carries
    kpi__visualType "gauge", min 0, max 100 and three conditional-formatting
    zones -- it rendered `1.5 K` on a 0-100 dial. The mockup's KPI row is eight
    plain big numbers, which is the LEGACY `stat` visual (present in the Add
    visual menu under "Legacy visuals"). `stat` is therefore the correct choice
    here, not the modern-sounding one.

 3. visualOptions ARE LEFT EMPTY, DELIBERATELY. The exported tiles carry deep,
    visual-specific option trees (kpi__conditionalFormatting.zone2.range,
    table__renderLinks, colorRulesDisabled...). Those property names cannot be
    invented safely, and an unknown key risks rejecting the whole import. Every
    tile below ships `{}` and lets the service apply its own defaults -- which
    for a well-shaped query means axes are inferred correctly anyway.
    CONSEQUENCE, stated rather than hidden: the Standing Rule's "no gridlines"
    is NOT applied by this file. It is a per-tile toggle in the designer and is
    listed as manual follow-up in SESSION_05_PORTAL_STEPS.md.

MINIMUM TILE SIZE IS 9x7 for the stat family -- MEASURED FROM THE IMPORT, 2026-08-19.
The first import rendered, then every 4x4 KPI tile threw "Current tile size (4, 4)
is smaller than the minimum supported tile size (9, 7)". On a 16-column grid that
allows at most ONE stat per row, so four separate KPI tiles would cost 28 rows of
vertical space for four numbers. The KPI rows are therefore ONE `multistat` tile
each, which is the visual designed for exactly this. Every tile below is now >=8
wide, and the two visuals that survived at 8 (column, pie) are left there because
they are confirmed working -- 8 is evidently under a different, lower minimum.

VISUAL TYPE NAMES still carry residual risk. `table` is confirmed from the
export. The rest are inferred from the Add visual menu's labels ("Anomaly chart",
"Heatmap", "Markdown", "Stat", "Bar chart", "Column chart", "Pie chart",
"Time Series") mapped onto the KQL render-operator vocabulary. If the import
rejects one, change it in THIS COLUMN ONLY and re-run the builder -- that is the
whole reason they live in one place instead of being scattered through JSON.
-----------------------------------------------------------------------------

TIME CONVENTION -- the design decision of this session, stated once.
Every time-relative tile reads the dashboard's built-in time-range parameter
(_startTime / _endTime) and uses `as_of = _endTime`. No tile carries a hardcoded
datetime literal. Consequence, and the point: the operator switches the whole
dashboard between "read the frozen backfill" (the absolute range ending
2026-08-17 00:35, now confirmed present in the export as a `fixed` defaultValue)
and "watch live replay" (a relative range, whose _endTime IS now()) with one
control, and no tile mixes the two conventions.
"""

GRID_WIDTH = 16  # measured, not assumed -- see header note 1

PAGES = [
    {
        "key": "estate_health",
        "name": "Estate Health",
        "tiles": [
            {
                "key": "p1_kpi_row",
                "title": "Estate at a glance",
                "subtitle": "Live / dark / trading / freshness, at the reference time",
                "visualType": "multistat",
                "query": "p1_t0_kpi_row.kql",
                "layout": {"x": 0, "y": 0, "width": 16, "height": 7},
            },
            {
                "key": "p1_status_by_tier",
                "title": "Terminal status by merchant tier",
                "subtitle": "Where the estate's silence concentrates, tier by tier",
                "visualType": "column",
                "query": "p1_t5_status_by_tier.kql",
                "layout": {"x": 0, "y": 7, "width": 8, "height": 7},
            },
            {
                "key": "p1_composition",
                "title": "Estate composition",
                "subtitle": "Off-hours silence is not an outage -- only silence during trading hours counts",
                "visualType": "pie",
                "query": "p1_t6_estate_composition.kql",
                "layout": {"x": 8, "y": 7, "width": 8, "height": 7},
            },
            {
                "key": "p1_reflex3_feed",
                "title": "Reflex 3 -- terminal dark, live feed",
                "subtitle": "Revenue loss, not fraud. Ordered by how long the terminal has been silent",
                "visualType": "table",
                "query": "p1_t7_reflex3_feed.kql",
                "layout": {"x": 0, "y": 14, "width": 16, "height": 8},
            },
            {
                "key": "p1_footer",
                "title": "",
                "visualType": "markdownCard",
                "markdown": (
                    "**Meridian Pay — Estate Health.** Synthetic data, seeded generator "
                    "`MASTER_SEED=250817`, `GENERATOR_VERSION=1.0.0`. Dark detection reads "
                    "`mv_terminal_last_seen`, which holds only each terminal's most recent row — it "
                    "answers *is this terminal dark relative to the reference time*, not *was it dark "
                    "historically*. Set the reference window's end at or after the data's true last "
                    "ingest, or every terminal reads live. Curated tables are deduplicated at export "
                    "checkpoints, not continuously; residual streaming duplicates run at ~0.4%."
                ),
                "layout": {"x": 0, "y": 22, "width": 16, "height": 3},
            },
        ],
    },
    {
        "key": "fraud_watch",
        "name": "Fraud Watch",
        "tiles": [
            {
                "key": "p2_kpi_row",
                "title": "Hot path at a glance",
                "subtitle": "Throughput, decline rate and reflex firings in the reference window",
                "visualType": "multistat",
                "query": "p2_t0_kpi_row.kql",
                "layout": {"x": 0, "y": 0, "width": 16, "height": 7},
            },
            {
                "key": "p2_decline_series",
                "title": "Decline rate, trailing window",
                "subtitle": "5-minute grain -- the grain mv_terminal_activity_5min actually holds",
                "visualType": "timechart",
                "query": "p2_t5_decline_series.kql",
                "layout": {"x": 0, "y": 7, "width": 16, "height": 7},
            },
            {
                "key": "p2_top_risk",
                "title": "Top at-risk terminals",
                "subtitle": "Minimum 20 auths, so a 1-of-1 decline cannot take the top slot",
                "visualType": "bar",
                "query": "p2_t6_top_at_risk.kql",
                "layout": {"x": 0, "y": 14, "width": 16, "height": 7},
            },
            {
                "key": "p2_alert_feed",
                "title": "Live alert feed",
                "subtitle": "Reads the persisted alerts_v2 table -- the same rows Session 6 grades",
                "visualType": "table",
                "query": "p2_t7_alert_feed.kql",
                "layout": {"x": 0, "y": 21, "width": 16, "height": 8},
            },
            {
                "key": "p2_footer",
                "title": "",
                "visualType": "markdownCard",
                "markdown": (
                    "**Meridian Pay — Fraud Watch.** Firing counts and the feed read `alerts_v2`, not the "
                    "reflex functions directly, so this page and the exported E2 evidence cannot "
                    "disagree. `alerts_v2` **is** the graded alerts table -- the Session 6 regrade rebuilt it under that name, the Lakehouse shortcut publishes it to OneLake as `alerts`, and the original `alerts` table was dropped 2026-08-19. Rows are ordered by `window_start` (when the signal happened), not by "
                    "`fired_at`, which carries a single constant stamp for every backfill-seeded row "
                    "and therefore cannot order anything. Thresholds sit with deliberate margin under "
                    "the generator's injection parameters — tuning them to the injection would prove "
                    "only that we can find what we planted."
                ),
                "layout": {"x": 0, "y": 29, "width": 16, "height": 3},
            },
        ],
    },
    {
        "key": "issuer_performance",
        "name": "Issuer Performance",
        "tiles": [
            {
                "key": "p3_anomaly_band",
                "title": "Approval rate by issuer, with anomaly band",
                "subtitle": "series_decompose_anomalies against each issuer's own baseline -- not a fixed threshold",
                "visualType": "anomalychart",
                "query": "p3_t1_issuer_anomaly_band.kql",
                "layout": {"x": 0, "y": 0, "width": 16, "height": 9},
            },
            {
                "key": "p3_heatmap",
                "title": "Issuer BIN health by hour of day",
                "subtitle": "Degradation clusters by hour, it does not scatter",
                "visualType": "heatmap",
                "query": "p3_t2_issuer_heatmap.kql",
                "layout": {"x": 0, "y": 9, "width": 16, "height": 8},
            },
            {
                "key": "p3_reflex4_feed",
                "title": "Reflex 4 firings -- issuer_degradation",
                "subtitle": "Each row is one hour an issuer fell below its own decomposed baseline",
                "visualType": "table",
                "query": "p3_t3_reflex4_feed.kql",
                "layout": {"x": 0, "y": 17, "width": 16, "height": 8},
            },
            {
                "key": "p3_footer",
                "title": "",
                "visualType": "markdownCard",
                "markdown": (
                    "**Meridian Pay — Issuer Performance.** The anomaly band is computed at query "
                    "time from `mv_issuer_baseline`, so the band moves with the data rather than being "
                    "a stored constant. `sigma = 2.5` and a 1-hour step are the same parameters "
                    "`fn_reflex4_issuer_degradation` uses, so this chart and the reflex that writes to "
                    "`alerts_v2` cannot drift apart. An hour with no traffic for an issuer renders as a "
                    "gap, not as a 0% approval rate."
                ),
                "layout": {"x": 0, "y": 25, "width": 16, "height": 3},
            },
        ],
    },
]

DASHBOARD_TITLE = "Meridian Pay — Real-Time Payments Risk"

TIME_PARAMETER = {
    "displayName": "Reference window",
    "beginVariableName": "_startTime",
    "endVariableName": "_endTime",
}
