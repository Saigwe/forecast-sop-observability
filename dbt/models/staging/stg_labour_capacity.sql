select
    site_id,
    cast(week_start as date) as week_start,
    headcount,
    temporary_headcount,
    contracted_hours_per_head,
    planned_absence_rate,
    (headcount + temporary_headcount) * contracted_hours_per_head * (1 - planned_absence_rate) as available_hours
from {{ source('raw', 'labour_capacity') }}
