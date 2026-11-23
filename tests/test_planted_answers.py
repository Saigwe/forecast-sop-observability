"""Every planted problem is found where the answer key says, and only there."""
import json

from conftest import RAW, one

KEY = json.loads((RAW / "answer_key.json").read_text(encoding="utf-8"))


def acc(con, level, source, h=4, window="all"):
    return one(con, f"""select wape, bias from gold.rpt_accuracy
                        where window_name = '{window}' and level = '{level}' and member = 'All' and source = '{source}' and horizon_weeks = {h}""")


def test_aggregate_and_sku_level_pick_different_sources(con):
    for h in (1, 4, 8):
        assert acc(con, "total", "sensing", h)[0] < acc(con, "total", "consensus", h)[0]
        assert acc(con, "sku_market", "consensus", h)[0] < acc(con, "sku_market", "sensing", h)[0]


def test_consensus_bias_is_positive_and_near_five_percent(con):
    bias = acc(con, "sku_market", "consensus")[1]
    assert 0.03 < bias < 0.08


def test_leaked_backfill_is_excluded_and_would_have_flattered(con):
    leak = KEY["leak"]
    row = one(con, "select source, snapshot_week, naive_snapshot_id, wape_naive, wape_asof from gold.rpt_leak_audit")
    assert row[0] == leak["source"] and str(row[1]) == leak["snapshot_week"] and row[2].endswith(f"-v{leak['version']}")
    assert row[3] < 0.02 < row[4]
    assert one(con, "select count(*) from gold.fct_forecast_accuracy where version = 3")[0] == 0
    assert one(con, "select count(*) from gold.rpt_leak_audit")[0] == 1


def test_missing_feed_is_flagged_and_shows_in_coverage(con):
    m = KEY["missing_feed"]
    rows = con.execute("select source, market, snapshot_week from gold.rpt_feed_completeness where status = 'missing'").fetchall()
    assert [(r[0], r[1], str(r[2])) for r in rows] == [(m["source"], m["market"], m["snapshot_week"])]
    cov = one(con, f"""select coverage from gold.rpt_coverage where source = 'sensing' and market = 'EU' and horizon_weeks = 4
                       and target_week = date '{m["snapshot_week"]}' + interval 4 week""")[0]
    assert cov == 0
    assert one(con, "select min(coverage) from gold.rpt_coverage where source = 'consensus'")[0] == 1


def test_late_actuals_are_flagged(con):
    late = KEY["late_actuals"]
    rows = con.execute("select market, week_start, status, hours_late, deliveries from gold.rpt_freshness_actuals where status <> 'ok'").fetchall()
    assert len(rows) == 1
    market, week, status, hours, deliveries = rows[0]
    assert (market, str(week), status, deliveries) == (late["market"], late["week"], "late", 2)
    assert hours >= 24 * (late["days_late"] - 1)


def test_inventory_decision_depends_on_the_forecast(con):
    rows = con.execute("""select distinct sku, site_id, status_consensus, status_sensing from gold.rpt_inventory_exceptions
                          where sources_disagree order by 1, 2""").fetchall()
    assert [r[:2] for r in rows] == [("NV-H330", "SITE-C"), ("NV-S210", "SITE-A"), ("NV-S210", "SITE-B"), ("NV-S210", "SITE-C")]
    assert {r[2] for r in rows} == {"ok"}
    assert dict(((r[0], r[1]), r[3]) for r in rows)[("NV-H330", "SITE-C")] == "shortage"
    assert {r[3] for r in rows if r[0] == "NV-S210"} == {"overage"}
    # the evidence points the same way as the sensing model: recent actuals fell for S210 and rose for H330 at Gamma
    s210 = one(con, "select max(actual_yoy_last_8w) from gold.rpt_inventory_exceptions where sku = 'NV-S210'")[0]
    h330 = one(con, "select min(actual_yoy_last_8w) from gold.rpt_inventory_exceptions where sku = 'NV-H330' and site_id = 'SITE-C'")[0]
    assert s210 < -0.2 and h330 > 0.3


def test_only_site_beta_is_over_capacity_in_the_base_plan(con):
    rows = dict(con.execute("select site_id, peak_utilisation from gold.rpt_capacity_outlook where scenario = 'base'").fetchall())
    assert rows[KEY["over_capacity_site"]] > 1
    assert all(v < 1 for k, v in rows.items() if k != KEY["over_capacity_site"])
    up = dict(con.execute("select site_id, peak_utilisation from gold.rpt_capacity_outlook where scenario = 'upside'").fetchall())
    assert all(up[k] > rows[k] for k in rows)
    unmet = one(con, f"select unmet_units from gold.rpt_capacity_outlook where scenario = 'constrained' and site_id = '{KEY['over_capacity_site']}'")[0]
    assert unmet > 0


def test_minutes_routing_is_converted_to_hours(con):
    site = KEY["minutes_routing_site"]
    src, hrs = one(con, f"select source_value, std_hours_per_unit from silver.stg_routings where site_id = '{site}' and family = 'Headphones'")
    assert abs(hrs - src / 60) < 1e-12 and 0.04 < hrs < 0.07


def test_discontinued_sku_follows_the_zero_actual_policy(con):
    d = KEY["discontinued"]
    n, ape_null, fc = one(con, f"""select count(*), count(*) filter (where ape is null), sum(forecast_units) from gold.fct_forecast_accuracy
                                   where sku = '{d["sku"]}' and target_week >= date '{d["from"]}'""")
    assert n > 0 and ape_null == n and fc > 0
    assert one(con, "select count(*) from gold.fct_forecast_accuracy where actual_units = 0 and sku <> 'NV-K100'")[0] == 0
