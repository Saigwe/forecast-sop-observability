-- Accuracy by SKU and site at the decision horizon, over the whole history and over the last eight scored weeks.
-- Shows where the source that is better on average is not the one to trust for a particular position.
with p as (
    select * from {{ ref('fct_forecast_accuracy') }}
    where is_matched and horizon_weeks = {{ var('decision_horizon') }}
), last_w as (
    select max(target_week) as w from p
)
select
    source, sku, site_id,
    sum(abs_error_units) / nullif(sum(actual_units), 0) as wape_all,
    sum(error_units) / nullif(sum(actual_units), 0) as bias_all,
    sum(abs_error_units) filter (where target_week > (select w from last_w) - interval 8 week)
        / nullif(sum(actual_units) filter (where target_week > (select w from last_w) - interval 8 week), 0) as wape_last_8w,
    sum(error_units) filter (where target_week > (select w from last_w) - interval 8 week)
        / nullif(sum(actual_units) filter (where target_week > (select w from last_w) - interval 8 week), 0) as bias_last_8w,
    sum(actual_units) filter (where target_week > (select w from last_w) - interval 8 week) as actual_units_last_8w
from p
group by all
