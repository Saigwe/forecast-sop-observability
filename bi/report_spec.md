# Report spec (Power BI equivalent)

The static dashboards are the reference. A Power BI build over the same gold marts would use:

| Page | Visuals | Measures | Filters |
|---|---|---|---|
| S&OP scorecard | Decision list (text from measures), scorecard table with conditional icons, peak utilisation by site and scenario | WAPE SKU 4 Weeks, Bias, Peak Utilisation, Positions In Dispute | As-of date (fixed) |
| Forecast accuracy | WAPE by level (clustered bar), WAPE by horizon (line), weekly WAPE (line), bias trade-off (line), WAPE by market | WAPE SKU, WAPE Summed, Bias, Fill If Stocked To Forecast, Excess Share | Source, horizon, market, window |
| Feed observability | Feed delivery matrix (source x market by snapshot week), coverage line, actuals hours late, leak audit | From rpt_feed_completeness, rpt_coverage, rpt_freshness_actuals, rpt_leak_audit | Last 26 weeks |
| Capacity | Utilisation line by scenario with 95% reference line, outlook table, load vs available | Utilisation, Peak Utilisation, Hours Over Capacity | Site, scenario |
| Inventory | Disputed positions table, projected on hand by source, year-on-year bars | From rpt_inventory_exceptions and rpt_inventory_projection | SKU, site |
| Data checks | Check list, rules | From rpt_data_checks | |

Model notes:

- `FcAccuracy` relates to `Sku`, `Market` and `Week` (on target_week). Horizon and source are columns, used as slicers.
- WAPE and bias are defined as ratios of sums so they stay correct under any slicer; never average a WAPE column.
- `WAPE Summed` iterates target weeks so the total-level comparison matches the mart.
- Capacity and inventory are separate fact tables at their own grain; do not relate them to `FcAccuracy`.
