-- Rows a naive "latest version" model would use but that did not exist in time to inform the decision.
-- Compares the accuracy a naive model would report on the affected pairs with the as-of accuracy.
with naive as (
    select n.*, a.units as actual_units
    from {{ ref('int_forecast_naive') }} n
    join {{ ref('fct_actuals_weekly') }} a on a.sku = n.sku and a.market = n.market and a.week_start = n.target_week
    where n.horizon_weeks between 1 and {{ var('max_scored_horizon') }}
), frozen as (
    select * from {{ ref('fct_forecast_accuracy') }}
), j as (
    select n.source, n.snapshot_week, n.snapshot_id as naive_snapshot_id, n.created_at as naive_created_at,
           f.snapshot_id as asof_snapshot_id, f.created_at as asof_created_at,
           n.actual_units, n.units as naive_units, f.forecast_units as asof_units
    from naive n
    join frozen f using (source, snapshot_week, sku, market, target_week)
    where n.snapshot_id <> f.snapshot_id and n.created_at >= n.snapshot_week + interval 7 day
)
select source, snapshot_week, naive_snapshot_id, asof_snapshot_id,
       min(naive_created_at) as naive_created_at, min(asof_created_at) as asof_created_at,
       count(*) as pairs_affected,
       sum(abs(naive_units - actual_units)) / sum(actual_units) as wape_naive,
       sum(abs(asof_units - actual_units)) / sum(actual_units) as wape_asof
from j group by all
