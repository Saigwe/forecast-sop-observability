select site_id, site_name, region from {{ ref('stg_sites') }}
