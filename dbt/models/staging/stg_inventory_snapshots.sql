select cast(week_start as date) as week_start, sku, site_id, on_hand_units, backorder_units
from {{ source('raw', 'inventory_snapshots') }}
where cast(week_start as date) <= cast(timestamp '{{ var("as_of") }}' as date)
