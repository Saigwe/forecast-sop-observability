-- One row per SKU, market and week: the latest delivery wins.
select week_start, sku, market, units, delivered_at, delivery_id,
       count(*) over (partition by week_start, sku, market) as deliveries
from {{ ref('stg_actual_deliveries') }}
qualify row_number() over (partition by week_start, sku, market order by delivered_at desc) = 1
