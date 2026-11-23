select i.week_start, i.sku, i.site_id, s.family, i.on_hand_units, i.backorder_units
from {{ ref('stg_inventory_snapshots') }} i join {{ ref('stg_skus') }} s using (sku)
