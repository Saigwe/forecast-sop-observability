# Forecast observability and S&OP

[![ci](https://github.com/Saigwe/forecast-sop-observability/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Saigwe/forecast-sop-observability/actions/workflows/ci.yml)
[![dashboards](https://github.com/Saigwe/forecast-sop-observability/actions/workflows/pages.yml/badge.svg?branch=main)](https://saigwe.github.io/forecast-sop-observability/)

**Live dashboards: [saigwe.github.io/forecast-sop-observability](https://saigwe.github.io/forecast-sop-observability/)**

One place for planning leaders to compare competing forecasts, see which forecast was actually knowable when a decision
was made, and understand what forecast error means for labour capacity and inventory. Forecast snapshots from two
sources are scored as-of decision time, feeds are monitored for completeness and freshness, and the S&OP scorecard turns
exceptions into decisions.

Built end to end: a seeded synthetic data generator, source contracts, a dbt warehouse on DuckDB, six web dashboards, a
reproducible forecast-comparison notebook, a decision memo and a DAX measure spec. The scenario is modelled on forecast
accuracy, forecast observability, business-planning and S&OP scorecard work at a global consumer-electronics company.

**Everything here is invented.** Northvale Devices, its products, markets, sites and every number come from
`generator/simulate.py`. The results are demo results on synthetic data, not any company's figures.

## The business

Northvale Devices sells 16 headphones, earbuds, speakers and accessories in four markets (North America, Europe, UK,
Asia Pacific), shipped from three sites. Two forecasts arrive every week, each a snapshot of the next 13 weeks:

- a **demand-sensing model** ("sensing"), published Monday morning, and
- a **consensus plan** from a Kinaxis-style planning system ("consensus"), published Tuesday afternoon.

Replenishment and staffing are committed four weeks out. The planning meeting is on Monday 23 November 2026.

## What the reports find

The generator plants known problems; `tests/test_planted_answers.py` checks the marts find each one, and only those.
From the current build ([analysis/forecast_comparison.md](analysis/forecast_comparison.md), regenerated on every build):

| Finding | Where |
|---|---|
| Summed over every SKU, the sensing model looks better (3.1% WAPE four weeks out against 5.5%). At the SKU x market grain where stock is committed, the consensus plan is twice as accurate (8.5% against 17.8%). The sensing model's SKU errors cancel in aggregate | Forecast accuracy |
| The consensus plan runs about 5% high. Debiasing it out of sample cuts WAPE from 9.2% to 8.0% and excess units from 7.4% to 4.4% of demand, but fill if stock equalled the forecast falls from 98.3% to 96.5% | Forecast accuracy |
| A backfill republished one consensus snapshot ten weeks later with actuals in hand. Scored naively it claims 0.8% WAPE on 512 pairs; the version planners saw scores 10.7%. The as-of join excludes it | Feed observability |
| One sensing feed (Europe, week of 10 Aug 2026) never arrived; coverage four weeks out drops to 0% for that market-week and the pairs are left out of the comparison, not counted as errors | Feed observability |
| Asia Pacific actuals for one week arrived partial on time and complete about nine days late; the freshness check flags it | Feed observability |
| Site Beta is over capacity in three of the next 12 weeks on the base plan, peaking at 121% of available hours: 731 hours short, or 16,538 units unmet in the constrained plan. The upside plan takes it to 140% | Capacity |
| Four stock positions depend on which forecast you believe. NV-S210 sells about a third less than a year ago; the consensus plan still forecasts growth, so the sensing model flags 15 weeks of cover at every site. NV-H330 at Site Gamma sells 74% more; on the sensing forecast it runs out in the week of 28 Dec, while the plan shows no risk | Inventory |

The decision this supports is in [docs/decision_memo.md](docs/decision_memo.md): use the consensus plan for SKU-level
commitments, override it where demand has visibly changed, and add labour at Site Beta.

## How it fits together

```
generator/simulate.py  ->  data/raw/*.parquet (10 tables + answer key)
contracts/sources.yml  ->  columns, types and grain every feed must meet (tests/test_contracts.py)
dbt/ (DuckDB)          ->  silver: staging (latest delivery, minutes to hours), frozen and naive forecast views
                       ->  gold:   dims, snapshot, accuracy, actuals, capacity and inventory facts, 14 report marts
                                   (37 models, 25 tests)
dashboards/            ->  export.py -> data.json -> build.py -> 6 static pages (ECharts), GitHub Pages
analysis/              ->  forecast_comparison.py (notebook) -> forecast_comparison.md, fingerprint.py
bi/                    ->  DAX measures and report spec
docs/                  ->  metric dictionary, design decisions, decision memo, demo script
```

Grain of the core facts:

| Model | Grain |
|---|---|
| `fct_forecast_snapshot` | source x snapshot week x SKU x market x target week (base scenario, the version knowable that week) |
| `fct_forecast_accuracy` | source x horizon x SKU x market x target week, joined to actuals at that grain |
| `fct_actuals_weekly` | SKU x market x week, latest delivery |
| `fct_capacity_weekly` | scenario x site x week (actual, base, upside, constrained) |
| `fct_inventory_weekly` | SKU x site x week |

## What is tested

- **No leakage.** A forecast is scored only if it was created before its snapshot week ended and before its target week
  began. A dbt test fails the build otherwise; the leaked backfill is audited, not scored.
- **Matched pairs.** Sources are compared on the same keys; missing pairs are reported as coverage, never as error.
- **Ratios recompute.** WAPE and bias are ratios of sums at every level; market figures equal sums over their own pairs,
  never averages of SKU ratios.
- **Sign convention.** Error = forecast - actual, so positive bias is over-forecast.
- **Zero actuals.** A discontinued SKU's pairs stay in WAPE; percentage error is undefined there and excluded.
- **Units.** Load and capacity are both in hours. One site reports routings in minutes; staging converts them and a test
  rejects any standard time outside a plausible range in hours. Actual load reconciles to shipments x routings.
- **Scenarios.** The constrained plan never exceeds available hours, and delivered plus unmet units equal the base plan.
- **Source contracts.** Every raw file is checked for columns, types and grain.
- **Completeness and freshness.** Every expected forecast delivery and every actuals week is checked against the manifest
  and the due time; the planted gaps are the only ones flagged.
- **Rebuild consistency.** CI regenerates from the same seed, rebuilds, and compares a fingerprint of every gold mart.

## Run it

```bash
pip install -r requirements.txt
make all        # generate, dbt build, dashboards and the comparison notebook (about a minute)
make rebuild    # regenerate and rebuild: every gold mart must be identical
make test       # pytest against the built warehouse
make serve      # dashboards on http://localhost:8000
```

On Windows without `make`, run the commands in the `Makefile` in order.

Demo assumptions (decision horizon, cover thresholds, capacity alert, freshness due times) are dbt vars in
`dbt/dbt_project.yml`; change one and rebuild to see its effect.

## Licence

MIT. Synthetic data only.
