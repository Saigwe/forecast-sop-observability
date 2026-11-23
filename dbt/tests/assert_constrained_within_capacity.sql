select * from {{ ref('fct_capacity_weekly') }}
where scenario = 'constrained' and load_hours > available_hours + 1e-6
