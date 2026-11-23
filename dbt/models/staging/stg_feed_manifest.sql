select
    source,
    market,
    cast(snapshot_week as date) as snapshot_week,
    cast(expected_by as timestamp) as expected_by,
    cast(received_at as timestamp) as received_at,
    rows_received,
    rows_expected
from {{ source('raw', 'feed_manifest') }}
