"""Collect what the dashboard pages show into one JSON document, from the gold marts.

Usage: python dashboards/export.py --db warehouse/planning.duckdb --out dashboards/site/data.json
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path

import duckdb

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def rows(con, sql: str) -> list[dict]:
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    out = []
    for r in cur.fetchall():
        rec = {}
        for k, v in zip(cols, r):
            if isinstance(v, datetime):
                v = v.isoformat(sep=" ")[:16]
            elif isinstance(v, date):
                v = v.isoformat()[:10]
            elif isinstance(v, float):
                v = round(v, 6)
            elif v is not None and not isinstance(v, (int, str, bool)):
                v = float(v)
            rec[k] = v
        out.append(rec)
    return out


def collect(con) -> dict:
    d: dict = {}
    d["skus"] = rows(con, "select * from gold.dim_sku order by sku")
    d["sites"] = rows(con, "select * from gold.dim_site order by site_id")
    d["markets"] = rows(con, "select * from gold.dim_market order by market")
    d["acc"] = rows(con, "select * from gold.rpt_accuracy order by window_name, level, member, source, horizon_weeks")
    d["trend"] = rows(con, "select * from gold.rpt_accuracy_trend order by target_week, source")
    d["tradeoff"] = rows(con, "select * from gold.rpt_bias_tradeoff order by factor")
    d["by_sku"] = rows(con, "select * from gold.rpt_accuracy_by_sku order by sku, site_id, source")
    d["coverage"] = rows(con, "select * from gold.rpt_coverage where horizon_weeks = 4 order by target_week, source, market")
    d["leak"] = rows(con, "select * from gold.rpt_leak_audit")
    d["feeds"] = rows(con, "select * from gold.rpt_feed_completeness order by snapshot_week, source, market")
    d["fresh"] = rows(con, "select * from gold.rpt_freshness_actuals order by week_start, market")
    d["capacity"] = rows(con, "select * from gold.fct_capacity_weekly where week_start >= date '2025-09-01' order by week_start, site_id, scenario")
    d["outlook"] = rows(con, "select * from gold.rpt_capacity_outlook order by site_id, scenario")
    d["inv"] = rows(con, "select * from gold.rpt_inventory_exceptions order by sku, site_id, source")
    d["proj"] = rows(con, """select p.* from gold.rpt_inventory_projection p
                             where (p.sku, p.site_id) in (select (sku, site_id) from gold.rpt_inventory_exceptions where sources_disagree)
                             order by sku, site_id, source, week_start""")
    d["hist"] = rows(con, """select i.week_start, i.sku, i.site_id, i.on_hand_units from gold.fct_inventory_weekly i
                             where (i.sku, i.site_id) in (select (sku, site_id) from gold.rpt_inventory_exceptions where sources_disagree)
                               and i.week_start >= date '2026-05-04' order by week_start""")
    d["zero"] = rows(con, "select source, sum(zero_actual_pairs) as pairs, sum(forecast_units_on_zero) as forecast_units from gold.rpt_zero_actuals group by all")
    d["scorecard"] = rows(con, "select * from gold.rpt_sop_scorecard")
    d["checks"] = rows(con, "select * from gold.rpt_data_checks")
    d["last_actual"] = rows(con, "select max(week_start) as w from gold.fct_actuals_weekly")[0]["w"]
    d["inv_week"] = rows(con, "select max(week_start) as w from gold.fct_inventory_weekly")[0]["w"]
    return d


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(ROOT / "warehouse" / "planning.duckdb"))
    ap.add_argument("--out", default=str(HERE / "site" / "data.json"))
    ap.add_argument("--dbt-results", default=str(ROOT / "dbt" / "target" / "run_results.json"))
    a = ap.parse_args()
    with duckdb.connect(a.db, read_only=True) as con:
        data = collect(con)
    rr = Path(a.dbt_results)
    if rr.exists():
        results = json.loads(rr.read_text(encoding="utf-8"))["results"]
        data["dbt"] = {"nodes": len(results), "passed": sum(r["status"] in ("pass", "success") for r in results),
                       "tests": sum(r["unique_id"].startswith("test.") for r in results)}
    Path(a.out).write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {a.out} ({Path(a.out).stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
