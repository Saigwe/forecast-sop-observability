-- Weeks of cover and exception status by SKU and site under each source, and where the two sources disagree.
-- Cover = on hand / average forecast over the next four weeks. Shortage: cover below cover_shortage_weeks or a projected
-- stock-out within projection_weeks. Overage: cover above cover_overage_weeks. Demo assumptions, set in dbt_project.yml.
-- Evidence for a disagreement: growth on a year earlier, of recent actuals and of each source's next four weeks.
with p as (
    select * from {{ ref('rpt_inventory_projection') }}
), a as (
    select sku, site_id, week_start, sum(units) as units from {{ ref('fct_actuals_weekly') }} group by all
), last_w as (
    select max(week_start) as w from a
), recent as (
    select a.sku, a.site_id,
           sum(a.units) / nullif(sum(ly.units), 0) - 1 as actual_yoy_last_8w
    from a
    join a ly on ly.sku = a.sku and ly.site_id = a.site_id and ly.week_start = a.week_start - interval 364 day
    where a.week_start > (select w from last_w) - interval 8 week
    group by all
), s as (
    select p.source, p.sku, p.site_id,
           any_value(p.opening_on_hand) as on_hand_units,
           avg(p.forecast_units) filter (where p.week_ahead <= 4) as avg_forecast_4w,
           sum(p.forecast_units) filter (where p.week_ahead <= 4) / nullif(sum(ly.units) filter (where p.week_ahead <= 4), 0) - 1 as forecast_yoy_next_4w,
           min(p.projected_on_hand) filter (where p.week_ahead <= {{ var("projection_weeks") }}) as min_projected_window,
           min(p.week_start) filter (where p.projected_on_hand < 0 and p.week_ahead <= {{ var("projection_weeks") }}) as first_stockout_week
    from p
    left join a ly on ly.sku = p.sku and ly.site_id = p.site_id and ly.week_start = p.week_start - interval 364 day
    group by all
), st as (
    select s.*, r.actual_yoy_last_8w,
           s.on_hand_units / nullif(s.avg_forecast_4w, 0) as weeks_of_cover,
           case
               when s.min_projected_window < 0 or s.on_hand_units / nullif(s.avg_forecast_4w, 0) < {{ var('cover_shortage_weeks') }} then 'shortage'
               when s.on_hand_units / nullif(s.avg_forecast_4w, 0) > {{ var('cover_overage_weeks') }} then 'overage'
               else 'ok'
           end as status
    from s left join recent r using (sku, site_id)
)
select st.*,
       max(status) filter (where source = 'consensus') over (partition by sku, site_id) as status_consensus,
       max(status) filter (where source = 'sensing') over (partition by sku, site_id) as status_sensing,
       count(distinct status) over (partition by sku, site_id) > 1 as sources_disagree
from st
