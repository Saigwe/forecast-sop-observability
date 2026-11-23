select
    week_start,
    isoyear(week_start) as iso_year,
    weekofyear(week_start) as iso_week,
    date_trunc('month', week_start) as month_start,
    has_actuals,
    week_start > last_actual_week as is_future,
    last_actual_week
from {{ ref('int_weeks') }}
