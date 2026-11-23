-- Load and capacity must share a unit. Standard times outside 0.005 to 0.5 hours per unit mean a unit was not converted.
select * from {{ ref('stg_routings') }} where std_hours_per_unit not between 0.005 and 0.5
