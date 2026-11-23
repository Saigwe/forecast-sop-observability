select site_id, site_name, region from {{ source('raw', 'sites') }}
