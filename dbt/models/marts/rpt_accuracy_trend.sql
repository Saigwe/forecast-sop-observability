-- Weekly WAPE at the decision horizon, aggregate and SKU level, for the trend chart.
with p as (
    select * from {{ ref('fct_forecast_accuracy') }} where is_matched and horizon_weeks = {{ var('decision_horizon') }}
), t as (
    select source, target_week, sum(forecast_units) as f, sum(actual_units) as a, sum(abs_error_units) as sku_abs_error
    from p group by all
)
select source, target_week,
       abs(f - a) / nullif(a, 0) as wape_total,
       sku_abs_error / nullif(a, 0) as wape_sku_market,
       (f - a) / nullif(a, 0) as bias
from t
