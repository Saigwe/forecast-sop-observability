-- No scored forecast may have been created after its snapshot week ended or after its target week began.
select * from {{ ref('fct_forecast_accuracy') }}
where created_at >= snapshot_week + interval 7 day
   or created_at >= cast(target_week as timestamp)
   or snapshot_week + interval (7 * horizon_weeks) day <> target_week
