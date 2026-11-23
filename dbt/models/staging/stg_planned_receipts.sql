select sku, site_id, cast(receipt_week as date) as receipt_week, units
from {{ source('raw', 'planned_receipts') }}
