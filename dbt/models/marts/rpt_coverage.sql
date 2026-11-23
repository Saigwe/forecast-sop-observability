-- Forecast coverage: of the SKU x market keys with actuals in a target week, how many have a frozen forecast at each
-- horizon, by source. Missing pairs are excluded from WAPE and reported here instead.
with keys as (
    select a.week_start as target_week, a.sku, a.market
    from {{ ref('fct_actuals_weekly') }} a
    where a.week_start >= date '{{ var("accuracy_from") }}'
), grid as (
    select k.*, s.source, h.horizon_weeks
    from keys k
    cross join (values ('sensing'), ('consensus')) s(source)
    cross join range(1, {{ var('max_scored_horizon') }} + 1) h(horizon_weeks)
)
select g.source, g.horizon_weeks, g.market, g.target_week,
       count(*) as keys_with_actuals,
       count(f.units) as keys_with_forecast,
       count(f.units) / count(*) as coverage
from grid g
left join {{ ref('fct_forecast_snapshot') }} f
  on f.source = g.source and f.horizon_weeks = g.horizon_weeks and f.sku = g.sku and f.market = g.market and f.target_week = g.target_week
group by all
