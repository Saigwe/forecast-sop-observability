select market, market_name, site_id from {{ source('raw', 'markets') }}
