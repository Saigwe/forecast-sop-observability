-- Monday weeks from the first scored target to the end of the planning horizon.
with bounds as (
    select min(week_start) as first_week, max(week_start) as last_actual_week from {{ ref('stg_actuals') }}
), horizon as (
    select max(target_week) as last_week from {{ ref('stg_forecast_snapshots') }} where exists_at_as_of
)
select
    cast(w as date) as week_start,
    cast(w as date) <= (select last_actual_week from bounds) as has_actuals,
    (select last_actual_week from bounds) as last_actual_week
from bounds, horizon, generate_series(cast(first_week as timestamp), cast(last_week as timestamp), interval 7 day) as t(w)
