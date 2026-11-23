-- The planning horizon by site and scenario: the peak week, weeks above the alert level, and unmet work.
select
    scenario, site_id,
    count(*) as weeks,
    max(utilisation) as peak_utilisation,
    first(week_start order by round(utilisation, 9) desc, week_start) as peak_week,   -- earliest week on ties (constrained plans tie at 100%)
    count(*) filter (where utilisation > {{ var('capacity_alert') }}) as weeks_above_alert,
    count(*) filter (where utilisation > 1) as weeks_over_capacity,
    sum(greatest(load_hours - available_hours, 0)) as hours_over_capacity,
    sum(unmet_units) as unmet_units,
    sum(units) as units
from {{ ref('fct_capacity_weekly') }}
where scenario <> 'actual'
group by all
