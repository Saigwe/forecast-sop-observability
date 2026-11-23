select sku, sku_name, family, cast(discontinued_from as date) as discontinued_from
from {{ source('raw', 'skus') }}
