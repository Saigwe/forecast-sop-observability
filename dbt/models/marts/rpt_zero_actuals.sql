-- Policy for zero actuals: the pair stays in WAPE (its absolute error counts, its actual adds nothing to the
-- denominator); percentage error is undefined and excluded. This shows what that policy affects.
select source, horizon_weeks, sku, count(*) as zero_actual_pairs, sum(forecast_units) as forecast_units_on_zero,
       count(*) filter (where ape is null) as ape_undefined
from {{ ref('fct_forecast_accuracy') }}
where actual_units = 0 and is_matched
group by all
