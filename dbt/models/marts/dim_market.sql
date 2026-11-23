select m.market, m.market_name, m.site_id, s.site_name from {{ ref('stg_markets') }} m join {{ ref('stg_sites') }} s using (site_id)
