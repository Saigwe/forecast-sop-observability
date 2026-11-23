# Design decisions

## Score forecasts as they were knowable

A forecast snapshot is identified by source, snapshot week and version, and carries the time it was created. The
frozen view (`int_forecast_frozen`) keeps, for each snapshot week, the latest version created before the next snapshot
week began and before the as-of time. Horizon is the number of weeks between snapshot and target. A naive view
(`int_forecast_naive`) takes the latest version regardless, and exists only so the leak audit can show what it would
have reported. A singular test fails the build if any scored forecast was created after its target week began.

## Join actuals at the forecast's grain, then aggregate

Pairs are formed at SKU x market x target week. Every higher level sums forecasts and actuals first and then computes
the ratio. Market and total figures are therefore never averages of SKU ratios, and a test recomputes the market figures
from the pairs.

## Compare on matched pairs

A source that missed a delivery would otherwise be scored on fewer, possibly easier, weeks. Comparisons use the keys
both sources forecast; coverage is reported separately.

## Keep history and plan apart

Forecast evaluation uses frozen snapshots and actuals. The capacity outlook uses only the latest consensus snapshot that
existed at the as-of time, from the as-of week forward, with base and upside scenarios from the source and a constrained
scenario derived in SQL so its assumption (cap load at available hours) is visible and testable.

## One unit for load and capacity

Capacity is in hours. Routings arrive per site with their own unit of measure; staging converts minutes to hours and
leaves any unknown unit null, which fails a not-null test. A range test catches a conversion that was missed.

## Inventory decisions under both sources

The projection applies each source's latest forecast to the same stock and the same planned receipts, so the only
difference is the forecast. Positions where the status differs are the decisions that depend on which forecast you
believe. Growth on a year earlier, of recent actuals and of each forecast, is shown next to them as the evidence.

## Contracts at the edge

`contracts/sources.yml` declares columns, types and grain for every raw file; pytest checks them before anything else is
trusted. The feed manifest says what was expected; the warehouse counts what arrived.

## Lineage

```
raw.forecast_snapshots -> stg_forecast_snapshots -> int_forecast_frozen -> fct_forecast_snapshot -> fct_forecast_accuracy
                                                 -> int_forecast_naive  -> rpt_leak_audit
fct_forecast_accuracy -> rpt_accuracy, rpt_accuracy_trend, rpt_accuracy_by_sku, rpt_bias_tradeoff, rpt_zero_actuals
raw.feed_manifest + stg_forecast_snapshots -> rpt_feed_completeness
raw.actuals_weekly -> stg_actual_deliveries -> stg_actuals -> fct_actuals_weekly ; -> rpt_freshness_actuals
raw.labour_capacity, raw.routings + snapshots + actuals -> fct_capacity_weekly -> rpt_capacity_outlook
raw.inventory_snapshots, raw.planned_receipts + fct_forecast_snapshot -> rpt_inventory_projection -> rpt_inventory_exceptions
everything -> rpt_sop_scorecard, rpt_data_checks
```
