-- The S&OP landing page: one row per metric, with the demo target and a status.
with acc as (
    select * from {{ ref('rpt_accuracy') }}
    where window_name = 'last_13w' and horizon_weeks = {{ var('decision_horizon') }} and member = 'All'
), cov as (
    select source, sum(keys_with_forecast) / sum(keys_with_actuals) as coverage
    from {{ ref('rpt_coverage') }}
    where horizon_weeks = {{ var('decision_horizon') }}
      and target_week > (select max(target_week) - interval 13 week from {{ ref('rpt_coverage') }})
    group by all
), feeds as (
    select count(*) filter (where status <> 'ok') as incidents from {{ ref('rpt_feed_completeness') }}
    where snapshot_week > cast(timestamp '{{ var("as_of") }}' as date) - interval 26 week
), fresh as (
    select count(*) filter (where status <> 'ok') as incidents from {{ ref('rpt_freshness_actuals') }}
    where week_start > cast(timestamp '{{ var("as_of") }}' as date) - interval 26 week
), cap as (
    select * from {{ ref('rpt_capacity_outlook') }} where scenario = 'base'
), inv as (
    select count(*) filter (where status <> 'ok' and source = 'consensus') as exceptions_consensus,
           count(*) filter (where status <> 'ok' and source = 'sensing') as exceptions_sensing,
           count(distinct sku || site_id) filter (where sources_disagree) as disagreements
    from {{ ref('rpt_inventory_exceptions') }}
), m as (
    select 'Forecast' as area, 'WAPE, consensus plan, SKU x market, 4 weeks out, last 13 weeks' as metric,
           (select wape from acc where level = 'sku_market' and source = 'consensus') as value, 0.10 as target, 'pct' as unit, 'max' as direction, 'accuracy.html' as page
    union all select 'Forecast', 'WAPE, sensing model, SKU x market, 4 weeks out, last 13 weeks',
           (select wape from acc where level = 'sku_market' and source = 'sensing'), 0.10, 'pct', 'max', 'accuracy.html'
    union all select 'Forecast', 'WAPE, sensing model, all SKUs summed, 4 weeks out, last 13 weeks',
           (select wape from acc where level = 'total' and source = 'sensing'), 0.10, 'pct', 'max', 'accuracy.html'
    union all select 'Forecast', 'Bias, consensus plan, 4 weeks out, last 13 weeks (positive = over-forecast)',
           (select bias from acc where level = 'sku_market' and source = 'consensus'), 0.03, 'pct_abs', 'abs_max', 'accuracy.html'
    union all select 'Data', 'Forecast coverage, sensing model, 4 weeks out, last 13 weeks',
           (select coverage from cov where source = 'sensing'), 0.995, 'pct', 'min', 'observability.html'
    union all select 'Data', 'Forecast feed incidents, last 26 weeks', (select incidents from feeds), 0, 'count', 'max', 'observability.html'
    union all select 'Data', 'Actuals freshness incidents, last 26 weeks', (select incidents from fresh), 0, 'count', 'max', 'observability.html'
    union all select 'Capacity', 'Peak utilisation, ' || d.site_name || ', base plan, next ' || c.weeks || ' weeks',
           c.peak_utilisation, {{ var('capacity_alert') }}, 'pct', 'max', 'capacity.html'
           from cap c join {{ ref('dim_site') }} d using (site_id)
    union all select 'Inventory', 'SKU-site exceptions on the consensus plan', (select exceptions_consensus from inv), 0, 'count', 'max', 'inventory.html'
    union all select 'Inventory', 'SKU-site positions where the two forecasts disagree', (select disagreements from inv), 0, 'count', 'max', 'inventory.html'
)
select *,
       case direction
           when 'max' then case when value <= target then 'good' when value <= target * 1.25 + (case when unit = 'count' then 1 else 0 end) then 'warning' else 'critical' end
           when 'min' then case when value >= target then 'good' when value >= target - 0.02 then 'warning' else 'critical' end
           when 'abs_max' then case when abs(value) <= target then 'good' when abs(value) <= 2 * target then 'warning' else 'critical' end
       end as status
from m
