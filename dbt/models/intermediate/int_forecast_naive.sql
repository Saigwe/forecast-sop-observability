-- What a model that simply takes the latest version of each snapshot would score. Kept only for the leak audit.
select snapshot_id, source, snapshot_week, version, created_at, sku, market, target_week, horizon_weeks, units
from {{ ref('stg_forecast_snapshots') }}
where scenario = 'base' and exists_at_as_of
qualify row_number() over (partition by source, snapshot_week, sku, market, target_week order by version desc) = 1
