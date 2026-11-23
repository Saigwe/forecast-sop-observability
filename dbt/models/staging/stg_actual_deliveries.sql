-- Every delivered actuals row, kept so freshness can be measured.
select
    cast(week_start as date) as week_start, sku, market, cast(units as bigint) as units,
    cast(delivered_at as timestamp) as delivered_at, delivery_id
from {{ source('raw', 'actuals_weekly') }}
where cast(delivered_at as timestamp) <= timestamp '{{ var("as_of") }}'
