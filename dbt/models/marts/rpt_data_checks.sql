-- What the pipeline found and handled on this build.
select 'Forecast snapshots excluded as created too late to inform the decision (backfills)' as check_name,
       (select count(*) from {{ ref('stg_forecast_snapshots') }} where not is_knowable) as value,
       'Kept for audit in silver; never scored' as handling
union all
select 'Same-week corrections: snapshots with a later version that replaced version 1',
       (select count(distinct snapshot_id) from {{ ref('int_forecast_frozen') }} where version > 1),
       'Latest version created within the snapshot week wins'
union all
select 'Forecast deliveries missing', (select count(*) from {{ ref('rpt_feed_completeness') }} where status = 'missing'),
       'Pairs excluded from WAPE; coverage reported; comparisons use matched pairs'
union all
select 'Actuals weeks delivered late or partial', (select count(*) from {{ ref('rpt_freshness_actuals') }} where status <> 'ok'),
       'Latest delivery wins; freshness flagged'
union all
select 'Actuals rows replaced by a later delivery', (select count(*) from {{ ref('stg_actuals') }} where deliveries > 1),
       'Latest delivery wins'
union all
select 'Pairs with zero actuals', (select count(*) from {{ ref('fct_forecast_accuracy') }} where actual_units = 0),
       'In WAPE numerator; percentage error undefined and excluded'
union all
select 'Unmatched pairs left out of source comparisons', (select count(*) from {{ ref('fct_forecast_accuracy') }} where not is_matched),
       'Reported in coverage'
union all
select 'Routing rows converted from minutes to hours', (select count(*) from {{ ref('stg_routings') }} where source_uom = 'minutes'),
       'Converted in staging; tested to be in hours'
