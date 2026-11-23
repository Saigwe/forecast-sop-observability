-- What scaling the consensus plan would do, at SKU x market and the decision horizon: each row multiplies every
-- forecast by a factor and reports WAPE, bias, fill if stock equalled the forecast, and excess units. Factor 1 is
-- the plan as published; the debiased row divides by one plus the plan's bias measured on the earlier half of history.
with p as (
    select * from {{ ref('fct_forecast_accuracy') }}
    where is_matched and source = 'consensus' and horizon_weeks = {{ var('decision_horizon') }}
), mid as (
    select min(target_week) + cast(date_diff('week', min(target_week), max(target_week)) / 2 as integer) * 7 as split_week from p
), train as (
    select sum(error_units) / sum(actual_units) as bias from p where target_week < (select split_week from mid)
), factors as (
    select round(0.90 + 0.01 * i, 2) as factor, false as is_debiased from range(0, 17) t(i)
    union all
    select 1 / (1 + bias), true from train
)
select
    f.factor, f.is_debiased,
    sum(abs(p.forecast_units * f.factor - p.actual_units)) / sum(p.actual_units) as wape,
    sum(p.forecast_units * f.factor - p.actual_units) / sum(p.actual_units) as bias,
    1 - sum(greatest(p.actual_units - p.forecast_units * f.factor, 0)) / sum(p.actual_units) as fill_if_stocked_to_forecast,
    sum(greatest(p.forecast_units * f.factor - p.actual_units, 0)) / sum(p.actual_units) as excess_share
from p cross join factors f
where p.target_week >= (select split_week from mid)   -- evaluated on the later half only, so the debiased factor is out of sample
group by all
