-- Actual load hours in the capacity fact must equal shipments x standard hours recomputed from staging.
with r as (
    select a.site_id, sum(a.units * r.std_hours_per_unit) as h
    from {{ ref('fct_actuals_weekly') }} a
    join {{ ref('stg_skus') }} s using (sku)
    join {{ ref('stg_routings') }} r on r.site_id = a.site_id and r.family = s.family
    group by all
), c as (
    select site_id, sum(load_hours) as h from {{ ref('fct_capacity_weekly') }} where scenario = 'actual' group by all
)
select * from r join c using (site_id) where abs(r.h - c.h) > 1e-6 * r.h
