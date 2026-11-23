-- Actuals freshness by market and week: when the first rows arrived, and when every SKU had arrived.
with d as (
    select market, week_start, sku, min(delivered_at) as first_at
    from {{ ref('stg_actual_deliveries') }}
    group by all
), skus as (
    select count(*) as n from {{ ref('stg_skus') }}
), per_delivery as (
    select market, week_start, delivered_at, count(distinct sku) as skus_in_delivery
    from {{ ref('stg_actual_deliveries') }} group by all
)
select
    d.market, d.week_start,
    (select min(delivered_at) from per_delivery p where p.market = d.market and p.week_start = d.week_start) as first_delivered_at,
    max(d.first_at) as complete_at,
    count(*) as skus_received,
    any_value(skus.n) as skus_expected,
    d.week_start + interval {{ var('actuals_due_hours') }} hour as due_at,
    greatest(date_diff('hour', d.week_start + interval {{ var('actuals_due_hours') }} hour, max(d.first_at)), 0) as hours_late,
    case
        when count(*) < any_value(skus.n) then 'incomplete'
        when max(d.first_at) > d.week_start + interval {{ var('actuals_due_hours') }} hour + interval {{ var('feed_grace_hours') }} hour then 'late'
        else 'ok'
    end as status,
    (select count(*) from per_delivery p where p.market = d.market and p.week_start = d.week_start) as deliveries
from d, skus
group by d.market, d.week_start
