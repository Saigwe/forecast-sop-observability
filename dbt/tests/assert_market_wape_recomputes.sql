-- Market-level SKU WAPE in the report must equal sum |error| / sum actual recomputed from the pairs.
with r as (
    select market, horizon_weeks, source, sum(abs_error_units) / sum(actual_units) as wape
    from {{ ref('fct_forecast_accuracy') }} where is_matched group by all
)
select * from {{ ref('rpt_accuracy') }} a
join r on r.market = a.member and r.horizon_weeks = a.horizon_weeks and r.source = a.source
where a.window_name = 'all' and a.level = 'sku_market' and abs(a.wape - r.wape) > 1e-9
