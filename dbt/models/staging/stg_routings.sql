-- Standard handling time, converted to hours. Site Gamma's system reports minutes.
select
    site_id,
    family,
    uom as source_uom,
    std_time_per_unit as source_value,
    case uom when 'hours' then std_time_per_unit when 'minutes' then std_time_per_unit / 60.0 end as std_hours_per_unit
from {{ source('raw', 'routings') }}
