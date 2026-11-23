-- Each expected forecast delivery: did it arrive, on time and complete? Rows received are counted from the snapshots
-- themselves (version 1, base scenario), not taken from the manifest's own claim.
with received as (
    select source, market, snapshot_week, count(*) as rows_in_warehouse
    from {{ ref('stg_forecast_snapshots') }}
    where version = 1 and scenario = 'base' and exists_at_as_of
    group by all
)
select
    m.source, m.market, m.snapshot_week, m.expected_by, m.received_at, m.rows_expected,
    coalesce(r.rows_in_warehouse, 0) as rows_in_warehouse,
    case
        when m.received_at is null or coalesce(r.rows_in_warehouse, 0) = 0 then 'missing'
        when r.rows_in_warehouse < m.rows_expected then 'partial'
        when m.received_at > m.expected_by + interval {{ var('feed_grace_hours') }} hour then 'late'
        else 'ok'
    end as status
from {{ ref('stg_feed_manifest') }} m
left join received r using (source, market, snapshot_week)
where m.expected_by <= timestamp '{{ var("as_of") }}'
