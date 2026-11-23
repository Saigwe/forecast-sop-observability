select sku, sku_name, family, discontinued_from from {{ ref('stg_skus') }}
