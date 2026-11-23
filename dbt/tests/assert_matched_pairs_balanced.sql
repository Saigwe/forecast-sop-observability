-- Matched comparisons must have the same keys for both sources.
select horizon_weeks, target_week, count(*) filter (where source = 'sensing') as s, count(*) filter (where source = 'consensus') as c
from {{ ref('fct_forecast_accuracy') }} where is_matched
group by all having s <> c
