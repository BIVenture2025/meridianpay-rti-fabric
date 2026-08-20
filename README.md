# Meridian Pay — real-time payments risk on Microsoft Fabric

**A card acquirer's fraud and availability platform, built end to end on Fabric Real-Time
Intelligence — and it grades its own alerts.**

Nine and three-quarter million payment events land in an Eventhouse — 5,386,869 authorisations,
4,337,068 telemetry rows and 6,715 disputes. Four detection rules fire on patterns in the
stream rather than on a schedule. A live dashboard shows an operator what is happening right now.
And when the chargebacks arrive thirty to sixty days later, the platform goes back over every alert
it raised and **publishes its own precision** — by cohort of how mature the evidence is, never as
one blended number.

**→ [Read the guided walkthrough](https://biventure2025.github.io/meridianpay-rti-fabric/docs/guide.html)** — plain English, nine steps, ~18 hours, no
prior Fabric experience assumed.

---

## What is unusual about this build

| | |
|---|---|
| **No notebooks in the transformation layer** | Three KQL update policies and three materialized views do what Bronze/Silver/Gold notebooks normally do. **One** Spark notebook in the entire build, and it only loads the backfill |
| **Direct Lake with no Gold layer beneath it** | The semantic model reads the Eventhouse's own OneLake availability through Lakehouse shortcuts |
| **The platform grades itself** | Precision and recall per maturity cohort, structurally guarded — the two *unguarded* precision measures are bound by **zero** visuals, and a lint rule proves it on every run |
| **The failures are published** | Two mandatory components were never built. A precision of 1.000 is recorded as inadmissible. A validator that reported a pass having checked nothing is written up in full |

## The estate, in numbers

| | |
|---|--:|
| Events through the pipeline | **29,158,765** |
| Terminals · stores · merchants | 1,500 · 927 · 600 |
| Planted ground-truth episodes | **137** |
| KQL tables · materialized views · functions | 20 · 3 · 24 |
| Stream data-quality rules | 6 |
| Activator reflexes | 4 |
| Real-Time Dashboard pages · Power BI pages | 3 · 5 |
| Spark notebooks | **1** |

Every figure above was read back from the running platform, not from the plan. The read-back is in
[`docs/E3_READ_BACK.md`](docs/E3_READ_BACK.md) — seven tables verified two-sided at delta 0 across
two independent engines, thirteen more reconciled by derivation, and the split stated rather than
averaged away.

## Repository layout

| Folder | What is in it |
|---|---|
| `notebooks/` | the event generator (seeded, versioned, byte-reproducible) and the backfill loader |
| `kql/` | 18 scripts in run order — tables, update policies, materialized views, functions, DQ rules, reflexes, grading |
| `rtd/` | the Real-Time Dashboard as source: a spec, one `.kql` per tile, a builder and a checker |
| `model/` | measures as code, the TMDL, and the guarded-measure declaration |
| `report/` | the Power BI report as a generator script |
| `docs/` | architecture, data contract, read-back, post-mortem, plan-vs-actual, cost — and the guide |

The entry points, if you only open three: `notebooks/generator/backfill.py` builds the estate,
`kql/01_update_policies.kql` is the transformation layer, and `kql/12_alert_grading.kql` is the part
that makes this a platform rather than a demo.

## Rebuild it

You need a Fabric trial on a **work or school** account. A personal Microsoft account cannot
activate one.

```bash
git clone https://github.com/BIVenture2025/meridianpay-rti-fabric.git
cd meridianpay-rti-fabric
pip install -r notebooks/requirements.txt
python -m generator.backfill --seed 250817 --out ./output     # from notebooks/
```

Then follow the [guided walkthrough](https://biventure2025.github.io/meridianpay-rti-fabric/docs/guide.html). The scripts in `kql/` are numbered in run
order and the guide says which one belongs to which step.

**Everything the guide tells you to run is in this repository**, with real endpoints and identifiers
replaced by placeholders. That is checked mechanically rather than by eye.

## What this does not do

- **The two Eventstreams were never built.** They are mandatory in the project's own contract, the
  workspace contains zero of them, and the component count finished at **10 of 11**. The Spark
  backfill route is proven end to end; the live-replay route has working code and nothing to replay
  into. Recorded as a degradation rather than reinterpreted as a success.
- **Reflex 2's precision of 1.000 is inadmissible** and is published as such — the alert set was
  built from the episode it is graded against.
- **Reflex 3 scores precision 0.163 with recall 60/60.** The false positives are long silences
  inside modelled trading hours, which implicates the trading-calendar model rather than the
  threshold. That diagnosis is untested and is labelled untested.
- **One data-quality anomaly was never closed** — a shortfall of 2 rows against an expected 8,233,
  raised in session three and carried to the end. An open question, never a pass.
- **The data is invented.** Meridian Pay is fictional. The shape is realistic; no figure represents
  a real company, a real merchant or a real cardholder, and every injected element is declared in
  [`notebooks/GENERATOR_SPEC.md`](notebooks/GENERATOR_SPEC.md).
- **Trial capacity only**, shared with another workspace throughout. Nothing here says what this
  would cost to run in production.

## The write-ups

| | |
|---|---|
| [Guided walkthrough](https://biventure2025.github.io/meridianpay-rti-fabric/docs/guide.html) | How to build it, step by step, with 17 traps already found |
| [Architecture](https://biventure2025.github.io/meridianpay-rti-fabric/docs/ARCHITECTURE.html) | What connects to what, and why |
| [Closure analysis](https://biventure2025.github.io/meridianpay-rti-fabric/docs/CLOSURE.html) | What it cost, what drifted, what broke, and what the numbers rest on |
| [`docs/POST_MORTEM.md`](docs/POST_MORTEM.md) | Phase by phase — including nine defects that detonated later than they were planted |
| [`docs/PLAN_VS_ACTUAL.md`](docs/PLAN_VS_ACTUAL.md) | Every contracted outcome classified, and the avoidable-versus-discovery split |
| [`docs/DO_BETTER.md`](docs/DO_BETTER.md) | Ranked, with the evidence for each |
| [`docs/COST_ANALYSIS.md`](docs/COST_ANALYSIS.md) | Read the caveats before the totals |

---

Built by **Yeong Wai Son**. Questions, corrections, or if you get further than I did — particularly
on the Eventstreams or the trading-calendar diagnosis — I would genuinely like to hear about it:
**waisonyeong@gmail.com**
