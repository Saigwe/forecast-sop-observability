select a.week_start, a.sku, a.market, m.site_id, a.units, a.delivered_at, a.deliveries
from {{ ref('stg_actuals') }} a
join {{ ref('stg_markets') }} m using (market)
