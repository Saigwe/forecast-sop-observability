-- Forecast-actual pairs at SKU x market x target week x horizon, both sources. Actuals are joined at the forecast's own
-- grain before any error is computed. Error = forecast - actual, so positive means over-forecast.
-- is_matched: both sources have a forecast for this key and horizon; source comparisons use matched pairs only.
with pairs as (
    select
        f.source, f.horizon_weeks, f.snapshot_week, f.snapshot_id, f.version, f.created_at,
        f.sku, f.market, f.site_id, f.family, f.target_week,
        f.units as forecast_units,
        a.units as actual_units
    from {{ ref('fct_forecast_snapshot') }} f
    join {{ ref('fct_actuals_weekly') }} a
      on a.sku = f.sku and a.market = f.market and a.week_start = f.target_week
    where f.horizon_weeks between 1 and {{ var('max_scored_horizon') }}
      and f.target_week >= date '{{ var("accuracy_from") }}'
)
select
    *,
    forecast_units - actual_units as error_units,
    abs(forecast_units - actual_units) as abs_error_units,
    greatest(actual_units - forecast_units, 0) as shortfall_units,
    greatest(forecast_units - actual_units, 0) as excess_units,
    case when actual_units > 0 then abs(forecast_units - actual_units) / actual_units end as ape,  -- undefined at zero actuals
    count(*) over (partition by horizon_weeks, sku, market, target_week) = 2 as is_matched
from pairs
