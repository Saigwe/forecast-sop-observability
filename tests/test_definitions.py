"""Metric definitions hold: ratios recompute from components, signs follow the convention, scenarios are consistent."""
from conftest import one


def test_total_wape_sums_before_comparing(con):
    """Total-level WAPE compares summed forecast with summed actual per week; it is not the SKU-level WAPE."""
    rep = one(con, "select wape from gold.rpt_accuracy where window_name='all' and level='total' and member='All' and source='sensing' and horizon_weeks=4")[0]
    calc = one(con, """with w as (select target_week, sum(forecast_units) f, sum(actual_units) a from gold.fct_forecast_accuracy
                                  where is_matched and source='sensing' and horizon_weeks=4 group by 1)
                       select sum(abs(f - a)) / sum(a) from w""")[0]
    sku = one(con, "select sum(abs_error_units) / sum(actual_units) from gold.fct_forecast_accuracy where is_matched and source='sensing' and horizon_weeks=4")[0]
    assert abs(rep - calc) < 1e-12 and sku > 3 * calc


def test_market_ratios_are_not_averages_of_sku_ratios(con):
    rep = one(con, "select wape from gold.rpt_accuracy where window_name='all' and level='sku_market' and member='EU' and source='consensus' and horizon_weeks=4")[0]
    ratio = one(con, "select sum(abs_error_units)/sum(actual_units) from gold.fct_forecast_accuracy where is_matched and market='EU' and source='consensus' and horizon_weeks=4")[0]
    assert abs(rep - ratio) < 1e-12


def test_bias_sign_convention(con):
    """Error = forecast - actual: a forecast above the actual gives positive bias."""
    e = one(con, "select min(error_units * sign(forecast_units - actual_units)) from gold.fct_forecast_accuracy")[0]
    assert e >= 0


def test_scored_pairs_never_use_later_snapshots(con):
    assert one(con, "select count(*) from gold.fct_forecast_accuracy where created_at >= cast(target_week as timestamp)")[0] == 0
    assert one(con, "select max(horizon_weeks), min(horizon_weeks) from gold.fct_forecast_accuracy") == (8, 1)


def test_debiasing_trades_fill_for_excess(con):
    pub = one(con, "select wape, fill_if_stocked_to_forecast, excess_share from gold.rpt_bias_tradeoff where factor = 1 and not is_debiased")
    deb = one(con, "select factor, wape, fill_if_stocked_to_forecast, excess_share from gold.rpt_bias_tradeoff where is_debiased")
    assert deb[0] < 1 and deb[1] < pub[0] and deb[2] < pub[1] and deb[3] < pub[2]


def test_capacity_scenarios(con):
    assert one(con, "select count(*) from gold.fct_capacity_weekly where scenario='constrained' and utilisation > 1 + 1e-9")[0] == 0
    a, b = one(con, """select sum(c.units + c.unmet_units), sum(b.units) from gold.fct_capacity_weekly c
                       join gold.fct_capacity_weekly b using (site_id, week_start)
                       where c.scenario='constrained' and b.scenario='base'""")
    assert abs(a - b) < 1e-6 * b
    assert one(con, "select count(*) from gold.fct_capacity_weekly where scenario='actual' and week_start > (select max(week_start) from gold.fct_actuals_weekly)")[0] == 0


def test_scorecard_is_complete(con):
    rows = con.execute("select metric, value, status from gold.rpt_sop_scorecard").fetchall()
    assert len(rows) == 12 and all(r[1] is not None and r[2] in ("good", "warning", "critical") for r in rows)
