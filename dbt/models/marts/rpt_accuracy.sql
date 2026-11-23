-- WAPE, bias, MAE, fill and excess by source, horizon and level of aggregation, on matched pairs.
--   level total:      forecasts and actuals summed over every SKU and market per week, then compared
--   level market:     summed per market and week
--   level sku_market: compared row by row (the grain decisions are made at)
-- WAPE = sum |F - A| / sum A. Bias = sum (F - A) / sum A, positive = over-forecast. Ratios are recomputed from
-- their components at every level, never averaged.
with p as (
    select * from {{ ref('fct_forecast_accuracy') }} where is_matched
), mw as (
    select market, source, horizon_weeks, target_week, sum(forecast_units) as f, sum(actual_units) as a, count(*) as n_pairs
    from p group by all
), lv as (
    select 'total' as level, 'All' as member, source, horizon_weeks, target_week,
           sum(forecast_units) as f, sum(actual_units) as a, count(*) as n_pairs
    from p group by all
    union all
    select 'market', market, source, horizon_weeks, target_week, f, a, n_pairs from mw
    union all
    select 'market', 'All', source, horizon_weeks, target_week, f, a, n_pairs from mw
    union all
    select 'sku_market', 'All', source, horizon_weeks, target_week, forecast_units, actual_units, 1 from p
    union all
    select 'sku_market', market, source, horizon_weeks, target_week, forecast_units, actual_units, 1 from p
), last_week as (
    select max(target_week) as w from p
), windows as (
    select 'all' as window_name, date '1900-01-01' as from_week from last_week
    union all
    select 'last_13w', cast(w - interval 12 week as date) from last_week
)
select
    window_name, level, member, source, horizon_weeks,
    count(*) as n_comparisons,
    sum(n_pairs) as n_pairs,
    sum(a) as actual_units,
    sum(f) as forecast_units,
    sum(abs(f - a)) as abs_error_units,
    sum(abs(f - a)) / nullif(sum(a), 0) as wape,
    sum(f - a) / nullif(sum(a), 0) as bias,
    avg(abs(f - a)) as mae,
    1 - sum(greatest(a - f, 0)) / nullif(sum(a), 0) as fill_if_stocked_to_forecast,
    sum(greatest(f - a, 0)) / nullif(sum(a), 0) as excess_share
from lv join windows on lv.target_week >= windows.from_week
group by all
