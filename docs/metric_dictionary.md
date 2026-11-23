# Metric dictionary

All metrics are computed in the gold marts. Synthetic data; targets are demo assumptions.

| Metric | Definition | Grain and notes | Model |
|---|---|---|---|
| Horizon | Weeks between the snapshot week and the target week | 1 to 8 are scored; 4 is the decision horizon | `fct_forecast_accuracy` |
| Error | forecast - actual | Positive = over-forecast | `fct_forecast_accuracy` |
| WAPE | sum abs(forecast - actual) / sum actual | Recomputed at each level from its own pairs, never averaged | `rpt_accuracy` |
| Bias | sum (forecast - actual) / sum actual | Positive = over-forecast | `rpt_accuracy` |
| MAE | average abs(forecast - actual) | In units at the level's grain | `rpt_accuracy` |
| Level: total | Forecast and actual summed over every SKU and market per week, then compared | Errors cancel across SKUs | `rpt_accuracy` |
| Level: market | Summed per market and week | | `rpt_accuracy` |
| Level: SKU x market | Compared row by row | The grain stock is committed at | `rpt_accuracy` |
| Fill if stocked to forecast | 1 - sum max(actual - forecast, 0) / sum actual | A service proxy: the share of demand met if stock equalled the forecast | `rpt_accuracy`, `rpt_bias_tradeoff` |
| Excess units | sum max(forecast - actual, 0) / sum actual | Inventory carried if stock equalled the forecast | `rpt_accuracy`, `rpt_bias_tradeoff` |
| Coverage | keys with a frozen forecast / keys with actuals | By source, horizon, market and target week | `rpt_coverage` |
| Matched pair | A key and horizon both sources forecast | Source comparisons use matched pairs only | `fct_forecast_accuracy.is_matched` |
| Feed status | missing / partial / late / ok | Rows counted in the warehouse against the manifest; late = more than 24 hours after due | `rpt_feed_completeness` |
| Actuals freshness | Hours between the due time (Tuesday 12:00 after the week) and when every SKU had arrived | | `rpt_freshness_actuals` |
| Available hours | (headcount + temporary headcount) x contracted hours x (1 - planned absence) | Per site and week | `stg_labour_capacity` |
| Load hours | units x standard hours per unit | Routings converted to hours in staging | `fct_capacity_weekly` |
| Utilisation | load hours / available hours | Alert above 95% | `fct_capacity_weekly` |
| Unmet units | units x (load - available) / load, when load exceeds available | Constrained scenario only | `fct_capacity_weekly` |
| Projected on hand | on hand + cumulative planned receipts - cumulative forecast | From the latest stock snapshot, per source | `rpt_inventory_projection` |
| Weeks of cover | on hand / average forecast over the next four weeks | | `rpt_inventory_exceptions` |
| Shortage | Cover under 1.5 weeks, or a projected stock-out within six weeks | Demo assumption | `rpt_inventory_exceptions` |
| Overage | Cover over 12 weeks | Demo assumption | `rpt_inventory_exceptions` |

## Policies

- **Zero actuals.** The pair stays in WAPE: its absolute error adds to the numerator and its zero actual adds nothing
  to the denominator. Percentage error is undefined and excluded. A discontinued SKU therefore penalises a source that
  keeps forecasting it.
- **Missing forecast pairs.** Excluded from WAPE and reported as coverage. Comparisons use matched pairs, so a source is
  not rewarded for a feed that did not arrive.
- **Versions.** Within a snapshot week the latest version created before the week ended wins. A version created later
  (a backfill) is kept in silver and in the leak audit, never scored.
- **Actuals.** The latest delivery of a key wins; freshness is measured on when every SKU had arrived.
