-- Grain: source x snapshot week x SKU x market x target week, base scenario, frozen version.
select f.*, m.site_id, s.family
from {{ ref('int_forecast_frozen') }} f
join {{ ref('stg_markets') }} m using (market)
join {{ ref('stg_skus') }} s using (sku)
