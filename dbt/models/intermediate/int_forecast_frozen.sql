-- The forecast a planner could have seen: for each source, snapshot week and key, the latest version created before the
-- next snapshot week began, and before the as-of time. Horizon h means it was made h weeks before the target week.
select snapshot_id, source, snapshot_week, version, created_at, sku, market, target_week, horizon_weeks, units
from {{ ref('stg_forecast_snapshots') }}
where scenario = 'base' and is_knowable and exists_at_as_of
qualify row_number() over (partition by source, snapshot_week, sku, market, target_week order by version desc) = 1
