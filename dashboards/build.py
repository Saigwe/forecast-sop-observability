"""Write the six dashboard pages and data.js. Run export.py first.

Usage: python dashboards/build.py [--data dashboards/site/data.json] [--site dashboards/site]
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ECHARTS = "https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js"
REPO = "https://github.com/Saigwe/forecast-sop-observability"

PAGES = [
    ("index.html", "scorecard", "S&amp;OP scorecard"),
    ("accuracy.html", "accuracy", "Forecast accuracy"),
    ("observability.html", "observability", "Feed observability"),
    ("capacity.html", "capacity", "Capacity"),
    ("inventory.html", "inventory", "Inventory"),
    ("checks.html", "checks", "Data checks"),
]


def card(cid: str, title: str, sub: str, src: str = "", wide: bool = False, tall: bool = False, chart: bool = True,
         extra: str = "") -> str:
    return f'''
    <section class="card{' wide' if wide else ''}" id="{cid}">
      <header><div><h2>{title}</h2><p class="sub">{sub}</p></div>{'<button class="tbl-btn" type="button" aria-pressed="false">Table</button>' if chart else ''}</header>
      {extra}{f'<div class="chart{" tall" if tall else ""}" role="img" aria-label="{title}"></div>' if chart else ''}
      <div class="table-view" hidden></div>
      <p class="src">{src or "Source: dbt gold marts on DuckDB"}</p>
    </section>'''


def scope(text: str) -> str:
    return f'\n  <div class="filters"><span class="scope">{text}</span></div>'


SITE_FILTER = '''
  <div class="filters" role="group" aria-label="Filters">
    <label>Site <span class="seg" id="f-site">
      <button type="button" data-v="SITE-B" aria-pressed="true">Site Beta (EU, UK)</button><button type="button" data-v="SITE-A" aria-pressed="false">Site Alpha (NA)</button><button type="button" data-v="SITE-C" aria-pressed="false">Site Gamma (APAC)</button></span></label>
    <span class="scope">Utilisation = planned load hours / available hours. Load = units x standard hours per unit. Alert line at 95%.</span>
  </div>'''

GRID_OPEN, GRID_CLOSE = '\n  <div class="tiles" id="tiles"></div>\n  <div class="grid">', '\n  </div>'

BODIES = {
    "scorecard": ("S&amp;OP scorecard",
                  "Forecast, capacity and inventory in one place for the planning meeting, with the decisions each page supports.",
                  scope("Northvale Devices (fictional): 16 SKUs, 4 markets, 3 sites. As of Monday 23 November 2026, 09:00. "
                        "Forecasts are scored only as they were knowable at decision time. Targets are demo assumptions. Synthetic data.") + GRID_OPEN +
                  card("sc-decisions", "Decisions for this meeting", "Each links to the page with the evidence.", "Computed from every page",
                       wide=True, chart=False, extra='<ul class="insights" id="insights"></ul>') +
                  card("sc-table", "Planning health", "Value against the demo target", "Source: rpt_sop_scorecard", chart=False,
                       extra='<div id="scorecard" class="table-view"></div>') +
                  card("sc-capacity", "Peak utilisation in the next 13 weeks", "By site and scenario. Over 100% means work the site cannot do") +
                  GRID_CLOSE),
    "accuracy": ("Forecast accuracy",
                 "Two forecast sources, compared on matched pairs at the horizon each decision is made. Which one to trust depends on the level you look at.",
                 scope("WAPE = sum |forecast - actual| / sum actual. Bias = sum (forecast - actual) / sum actual, positive = over-forecast. "
                       "Horizon = weeks between the snapshot and the target week. Matched pairs only; target weeks from March 2025.") + GRID_OPEN +
                 card("ac-level", "WAPE at four weeks out, by level of aggregation", "Total: all SKUs and markets summed per week. SKU x market: every row compared") +
                 card("ac-horizon", "SKU x market WAPE by horizon", "The level replenishment and staffing decisions are made at") +
                 card("ac-trend", "Weekly WAPE, four weeks out", "SKU x market (solid) and all SKUs summed (dashed)", wide=True) +
                 card("ac-tradeoff", "Bias against service: scaling the consensus plan", "Units short and in excess if stock equalled the forecast, as a share of demand. SKU x market, four weeks out, later half of history. Published plan: x1.00") +
                 card("ac-market", "SKU x market WAPE by market, four weeks out", "Ratios recomputed from each market's own pairs") +
                 GRID_CLOSE),
    "observability": ("Feed observability",
                      "Did every forecast and actuals feed arrive, on time and complete, and was anything scored that could not have been known?",
                      scope("Expected deliveries come from the feed manifest; rows are counted in the warehouse, not taken from the manifest. "
                            "A backfill created after its snapshot week is kept for audit and never scored.") + GRID_OPEN +
                      card("ob-feeds", "Forecast rows delivered, by feed and snapshot week", "Share of expected rows in the warehouse, last 26 weeks", wide=True) +
                      card("ob-coverage", "Forecast coverage four weeks out, sensing model", "Share of SKU x market keys with actuals that have a forecast") +
                      card("ob-fresh", "Actuals: hours late against the due time", "By market and week, last 26 weeks. Due Tuesday 12:00 after the week") +
                      card("ob-leak", "The leaked backfill", "What a naive latest-version model would have reported for the affected pairs", wide=True) +
                      GRID_CLOSE),
    "capacity": ("Capacity",
                 "Planned load against available labour hours by site: last year's actuals, and the next 13 weeks under base, upside and constrained plans.",
                 SITE_FILTER + GRID_OPEN +
                 card("cp-line", "Utilisation by week", "Actual history, then the latest consensus plan by scenario", wide=True) +
                 card("cp-outlook", "Next 13 weeks by scenario", "Peak, weeks above the alert line and unmet work", chart=False, extra='<div id="outlook" class="table-view"></div>') +
                 card("cp-hours", "Load and available hours, base plan", "Hours per week, the selected site") +
                 GRID_CLOSE),
    "inventory": ("Inventory",
                  "Stock positions projected under each forecast source: where the choice of forecast changes the decision.",
                  scope("Projected on hand = on hand + planned receipts - forecast, week by week from the 23 November snapshot. Cover = on hand / "
                        "average forecast over the next four weeks. Shortage: under 1.5 weeks of cover or a stock-out within six weeks. "
                        "Overage: over 12 weeks. Thresholds are demo assumptions.") + GRID_OPEN +
                  card("iv-table", "Positions where the two forecasts disagree", "And the evidence: growth on a year earlier, of recent actuals and of each forecast",
                       wide=True, chart=False, extra='<div id="disagree" class="table-view"></div>') +
                  card("iv-s210", "NV-S210 at Site Alpha: stock and projection", "Units on hand; projection under each source from 23 November") +
                  card("iv-h330", "NV-H330 at Site Gamma: stock and projection", "Units on hand; projection under each source from 23 November") +
                  card("iv-yoy", "Recent actuals against each forecast, growth on a year earlier", "Actuals: last 8 weeks. Forecasts: next 4 weeks", wide=True) +
                  GRID_CLOSE),
    "checks": ("Data checks",
               "What the pipeline found and handled, and the definitions it enforces on every build.",
               scope("dbt staging and tests, source contracts and pytest run on every push. Nothing is silently dropped.") + GRID_OPEN +
               card("ck-list", "Checks on the latest build", "From rpt_data_checks", wide=True, chart=False, extra='<div id="checks"></div>') +
               card("ck-rules", "Definitions this warehouse enforces", "Where each is tested", wide=True, chart=False, extra='<div id="rules"></div>') +
               GRID_CLOSE),
}


def ver(site: Path) -> str:
    h = hashlib.sha1()
    for f in ("assets/style.css", "assets/charts.js", "assets/pages.js", "data.js"):
        h.update((site / f).read_bytes())
    return h.hexdigest()[:10]


def page(key: str, v: str = "") -> str:
    title, lede, body = BODIES[key]
    nav = "".join(f'<a href="{f}"{" aria-current=page" if k == key else ""}>{label}</a>' for f, k, label in PAGES)
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title.replace("&amp;", "&")} · Forecast observability and S&amp;OP</title>
<meta name="description" content="Forecast snapshots scored as-of decision time, feed observability, capacity scenarios and inventory exceptions for a fictional company, on synthetic data.">
<link rel="stylesheet" href="assets/style.css?v={v}">
<script src="{ECHARTS}" defer></script>
<script src="assets/charts.js?v={v}" defer></script>
<script src="data.js?v={v}" defer></script>
<script src="assets/pages.js?v={v}" defer></script>
</head>
<body class="viz-root" data-page="{key}">
<div class="top"><div class="wrap">
  <div class="brand">Northvale Devices <span>· forecast and S&amp;OP · synthetic data</span></div>
  <nav class="tabs" aria-label="Dashboards">{nav}</nav>
  <button class="theme-btn" type="button">Dark mode</button>
</div></div>
<main class="wrap">
  <div class="page-head"><h1>{title}</h1><p>{lede}</p></div>
{body}
  <p class="footnote">Northvale Devices, its products, sites and every number here are invented. Demo results, not any company's figures.
  Built from dbt marts on DuckDB, rebuilt by CI on every change. Code: <a href="{REPO}">forecast-sop-observability</a>.
  Built by <a href="https://saigwe.github.io">Stanley Igwe</a>.</p>
</main>
</body>
</html>
'''


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(HERE / "site" / "data.json"))
    ap.add_argument("--site", default=str(HERE / "site"))
    a = ap.parse_args()
    site = Path(a.site)
    data = json.loads(Path(a.data).read_text(encoding="utf-8"))
    (site / "data.js").write_text("window.DASH = " + json.dumps(data, separators=(",", ":")) + ";\n", encoding="utf-8")
    v = ver(site)
    for fname, key, _ in PAGES:
        (site / fname).write_text(page(key, v), encoding="utf-8", newline="\n")
    print(f"wrote {len(PAGES)} pages to {site}")


if __name__ == "__main__":
    main()
