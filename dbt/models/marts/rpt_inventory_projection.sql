-- From the latest stock snapshot, project on-hand by week under each source's latest frozen forecast, with the same
-- planned receipts: projected = on hand + cumulative receipts - cumulative forecast.
with snap as (
    select max(week_start) as week_start from {{ ref('stg_inventory_snapshots') }}
), latest as (
    select source, max(snapshot_week) as snapshot_week
    from {{ ref('fct_forecast_snapshot') }} where created_at <= timestamp '{{ var("as_of") }}'
    group by all
), fc as (
    select f.source, f.sku, f.site_id, f.target_week as week_start, sum(f.units) as forecast_units
    from {{ ref('fct_forecast_snapshot') }} f
    join latest using (source, snapshot_week)
    where f.target_week >= (select week_start from snap)
    group by all
), rec as (
    select sku, site_id, receipt_week as week_start, sum(units) as receipt_units
    from {{ ref('stg_planned_receipts') }} group by all
), onhand as (
    select i.sku, i.site_id, i.on_hand_units
    from {{ ref('stg_inventory_snapshots') }} i join snap using (week_start)
)
select
    fc.source, fc.sku, fc.site_id, fc.week_start,
    date_diff('week', (select week_start from snap), fc.week_start) + 1 as week_ahead,
    o.on_hand_units as opening_on_hand,
    coalesce(r.receipt_units, 0) as receipt_units,
    fc.forecast_units,
    o.on_hand_units + sum(coalesce(r.receipt_units, 0) - fc.forecast_units)
        over (partition by fc.source, fc.sku, fc.site_id order by fc.week_start) as projected_on_hand
from fc
join onhand o using (sku, site_id)
left join rec r using (sku, site_id, week_start)
