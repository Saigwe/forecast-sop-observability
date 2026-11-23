# Decision memo: planning meeting, 23 November 2026

Northvale Devices (fictional). Synthetic data; demo results. Evidence: the live dashboards and
[analysis/forecast_comparison.md](../analysis/forecast_comparison.md).

## 1. Which forecast drives SKU-level commitments

**Use the consensus plan.** Leaders looking at the aggregate would pick the sensing model: summed over every SKU it is
3.1% WAPE four weeks out against 5.5%. That view hides the grain decisions are made at. At SKU x market, four weeks out,
the consensus plan is 8.5% against 17.8%, and it is better at every horizon from one to eight weeks. The sensing model is
right about market-wide swings and wrong about individual SKUs, and its SKU errors cancel when summed.

Keep the sensing model for what it is good at: total volume four weeks out (for example, carrier and network booking)
and spotting demand changes early.

## 2. Bias

The consensus plan runs about 5% high. Scaling it down by its own earlier bias, out of sample, would lower WAPE from 9.2%
to 8.0% and excess units from 7.4% to 4.4% of demand. The cost is service: fill if stock equalled the forecast falls from
98.3% to 96.5%. **Recommendation:** debias for SKUs where safety stock already covers the gap; keep the bias where
service is the priority, and record which is which.

## 3. Override the plan where demand has changed

Four positions depend on the forecast:

| Position | Recent actuals vs a year earlier | Consensus plan | Sensing model | Action |
|---|---|---|---|---|
| NV-S210, all three sites | about -30% to -37% | forecasts growth; 8 to 9 weeks of cover | about 15 weeks of cover: overage | Cut open receipts |
| NV-H330, Site Gamma | +74% | 2.0 weeks of cover, no risk | stock-out in the week of 28 Dec | Expedite supply |

In both cases recent actuals agree with the sensing model. The general rule from section 1 still holds; these are the
exceptions where a structural change has not reached the plan.

## 4. Labour at Site Beta

On the base plan Site Beta is over capacity in the weeks of 23 Nov, 30 Nov and 28 Dec, peaking at 121% of available hours:
731 hours short, or 16,538 units unmet if nothing changes. The upside plan reaches 140%. Site Alpha cannot absorb the
volume (it peaks at 99%). **Decision needed:** approve temporary hours for those three weeks, or agree which orders slip.

## 5. Data issues to raise with the feed owners

- The sensing feed for Europe, week of 10 August, never arrived. Ask for a completeness alert on the feed itself.
- Asia Pacific actuals for the week of 12 October arrived partial on time and complete about nine days late.
- A consensus snapshot was republished in September with actuals in hand. Backfills must carry a new snapshot week or be
  marked as such; until then the as-of rule keeps them out of accuracy.

## Assumptions

Decision horizon four weeks; shortage under 1.5 weeks of cover or a stock-out within six weeks; overage above 12 weeks;
capacity alert at 95%. All are dbt vars and can be changed.
