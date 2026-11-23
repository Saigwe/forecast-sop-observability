-- After the latest delivery wins, every scored week has every SKU in every market.
select week_start, market, count(*) as n
from {{ ref('fct_actuals_weekly') }}
group by all
having count(*) <> (select count(*) from {{ ref('stg_skus') }})
