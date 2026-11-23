-- Every snapshot row, every version. A row is knowable for decisions in its snapshot week only if it was created
-- before the next snapshot week began; a later re-run (a backfill) is kept for audit but never scored.
select
    snapshot_id,
    source,
    cast(snapshot_week as date) as snapshot_week,
    version,
    cast(created_at as timestamp) as created_at,
    sku,
    market,
    cast(target_week as date) as target_week,
    horizon_weeks,
    scenario,
    cast(units as double) as units,
    cast(created_at as timestamp) < cast(snapshot_week as date) + interval 7 day as is_knowable,
    cast(created_at as timestamp) <= timestamp '{{ var("as_of") }}' as exists_at_as_of
from {{ source('raw', 'forecast_snapshots') }}
