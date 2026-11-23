-- Planned load against available hours, by site and week. Load hours = units x standard hours per unit (hours, after
-- converting any site that reports minutes). History uses actual shipments; the plan uses the latest consensus snapshot
-- that existed at the as-of time. Constrained = base load capped at available hours; the excess is unmet.
with routing as (
    select site_id, family, std_hours_per_unit from {{ ref('stg_routings') }}
), latest as (
    select max(snapshot_week) as snapshot_week
    from {{ ref('stg_forecast_snapshots') }}
    where source = 'consensus' and is_knowable and exists_at_as_of
), plan as (
    select f.scenario, f.target_week as week_start, f.sku, m.site_id, s.family, f.units
    from {{ ref('stg_forecast_snapshots') }} f
    join latest using (snapshot_week)
    join {{ ref('stg_markets') }} m using (market)
    join {{ ref('stg_skus') }} s using (sku)
    where f.source = 'consensus' and f.is_knowable and f.exists_at_as_of
      and f.target_week >= date_trunc('week', timestamp '{{ var("as_of") }}')   -- the plan from the as-of week forward
    qualify row_number() over (partition by f.scenario, f.target_week, f.sku, f.market order by f.version desc) = 1
), hist as (
    select 'actual' as scenario, a.week_start, a.sku, a.site_id, s.family, a.units
    from {{ ref('fct_actuals_weekly') }} a join {{ ref('stg_skus') }} s using (sku)
), u as (
    select * from plan union all select * from hist
), load as (
    select u.scenario, u.site_id, u.week_start, sum(u.units) as units, sum(u.units * r.std_hours_per_unit) as load_hours
    from u join routing r using (site_id, family)
    group by all
), base_plus as (
    select l.*, c.available_hours from load l
    join {{ ref('stg_labour_capacity') }} c using (site_id, week_start)
)
select scenario, site_id, week_start, units, load_hours, available_hours,
       load_hours / available_hours as utilisation, 0.0 as unmet_hours, 0.0 as unmet_units
from base_plus
union all
select 'constrained', site_id, week_start,
       units * least(load_hours, available_hours) / load_hours,
       least(load_hours, available_hours), available_hours,
       least(load_hours, available_hours) / available_hours,
       greatest(load_hours - available_hours, 0),
       units * greatest(load_hours - available_hours, 0) / load_hours
from base_plus where scenario = 'base'
