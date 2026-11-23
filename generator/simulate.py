"""Synthetic planning feeds for Northvale Devices, a fictional consumer-electronics company.

Writes, as the source systems would deliver them:
  forecast_snapshots   weekly forecast snapshots from two sources: a demand-sensing model ("sensing") and a
                       Kinaxis-style consensus plan ("consensus"). One row per snapshot x version x SKU x market x
                       target week x scenario, with the time the snapshot was created
  feed_manifest        what each forecast feed was expected to deliver and what arrived
  actuals_weekly       shipped units by SKU, market and week, as delivered (a late and a partial delivery included)
  labour_capacity      headcount, contracted hours and planned absence by site and week
  routings             standard handling time per unit by site and product family (one site reports minutes)
  inventory_snapshots  on-hand and backordered units by SKU, site and week
  planned_receipts     open supply by SKU, site and receipt week, from the as-of date forward
  skus, markets, sites
  answer_key.json      what was planted, for the tests

Planted:
  * The sensing model tracks market-wide swings but is noisy per SKU; the consensus plan knows SKU-level orders but
    runs about 5% high and misses market swings. In aggregate the sensing model looks better; at SKU level and the
    four-week decision horizon the consensus plan is better.
  * A backfill republished consensus snapshot 2026-07-06 as version 3 on 2026-09-15, built with actuals in hand.
  * The sensing feed for EU, snapshot week 2026-08-10, never arrived.
  * APAC actuals for week 2026-10-12 arrived partial on time and complete nine days late.
  * NV-S210 demand drops 40% from 2026-08-03; the sensing model sees it in two weeks, the consensus plan does not.
  * NV-H330 demand in APAC rises 60% from 2026-10-05 (a new retail listing); only the sensing model sees it.
  * NV-K100 is discontinued from 2026-06-01: actuals are zero while the consensus plan keeps forecasting it.
  * Site Beta (EU and UK) runs over capacity in the December peak; Site Gamma's routing file is in minutes.
Every name and number is invented.
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 11
SNAP_START = date(2024, 11, 4)        # first snapshot week (Monday)
FIRST_TARGET = date(2025, 1, 6)       # first week with actuals
AS_OF = datetime(2026, 11, 23, 9, 0)  # extract time, Monday morning
LATEST_SNAP = date(2026, 11, 16)
LAST_ACTUAL = date(2026, 11, 9)       # actuals arrive eight days after the week starts
MAX_H = 12
FAMILY_STD_HOURS = {"Headphones": 0.050, "Earbuds": 0.030, "Speakers": 0.080, "Accessories": 0.020}

MARKETS = pd.DataFrame([
    ("NA", "North America", "SITE-A", 1.00), ("EU", "Europe", "SITE-B", 0.80),
    ("UK", "United Kingdom", "SITE-B", 0.35), ("APAC", "Asia Pacific", "SITE-C", 0.50)],
    columns=["market", "market_name", "site_id", "size"])
SITES = pd.DataFrame([
    ("SITE-A", "Site Alpha", "North America", 30, 37.5, 0.45), ("SITE-B", "Site Beta", "Europe", 36, 37.5, 0.20),
    ("SITE-C", "Site Gamma", "Asia Pacific", 15, 40.0, 0.52)],
    columns=["site_id", "site_name", "region", "headcount", "contracted_hours", "peak_temp_share"])
SKUS = [
    ("NV-H310", "Northvale Studio 310", "Headphones", 1400), ("NV-H320", "Northvale Studio 320", "Headphones", 1100),
    ("NV-H330", "Northvale Studio 330", "Headphones", 900), ("NV-H340", "Northvale Studio 340", "Headphones", 600),
    ("NV-E410", "Northvale Pods 410", "Earbuds", 2400), ("NV-E420", "Northvale Pods 420", "Earbuds", 1900),
    ("NV-E430", "Northvale Pods 430", "Earbuds", 1300), ("NV-E440", "Northvale Pods 440", "Earbuds", 800),
    ("NV-S210", "Northvale Boom 210", "Speakers", 1000), ("NV-S220", "Northvale Boom 220", "Speakers", 800),
    ("NV-S230", "Northvale Boom 230", "Speakers", 550), ("NV-S240", "Northvale Boom 240", "Speakers", 350),
    ("NV-K100", "Northvale Cable Kit", "Accessories", 700), ("NV-K110", "Northvale Travel Case", "Accessories", 900),
    ("NV-K120", "Northvale Charger", "Accessories", 1200), ("NV-K130", "Northvale Ear Tips", "Accessories", 500),
]
S210_DROP = date(2026, 8, 3)
H330_SPIKE = date(2026, 10, 5)
K100_END = date(2026, 6, 1)
LEAK = {"source": "consensus", "snapshot_week": date(2026, 7, 6), "version": 3, "created_at": datetime(2026, 9, 15, 10, 30)}
MISSING = {"source": "sensing", "market": "EU", "snapshot_week": date(2026, 8, 10)}
LATE = {"market": "APAC", "week": date(2026, 10, 12), "partial_share": 0.6, "days_late": 9}


def mondays(a: date, b: date) -> list[date]:
    return [a + timedelta(weeks=i) for i in range((b - a).days // 7 + 1)]


def season(d: date) -> float:
    if d.month == 11 and d.day >= 21 or d.month == 12 and d.day <= 1:
        return 2.0                    # Black Friday weeks
    return {1: 0.80, 2: 0.85, 3: 0.95, 4: 0.95, 5: 1.0, 6: 1.0, 7: 0.95, 8: 0.95, 9: 1.0, 10: 1.05, 11: 1.35, 12: 1.55}[d.month]


def level(sku: str, market: str, t: date) -> float:
    """True demand level multiplier from planted events."""
    m = 1.0
    if sku == "NV-S210" and t >= S210_DROP:
        m *= 0.6
    if sku == "NV-H330" and market == "APAC" and t >= H330_SPIKE:
        m *= 1.6
    if sku == "NV-K100" and t >= K100_END:
        m *= 0.0
    return m


def known_level(source: str, sku: str, market: str, s: date, t: date) -> float:
    """The level a source believes for target t at snapshot s."""
    m = 1.0
    lag = {"sensing": 2, "consensus": 999}
    if sku == "NV-S210" and t >= S210_DROP and s >= S210_DROP + timedelta(weeks=lag[source]):
        m *= 0.6
    if sku == "NV-H330" and market == "APAC" and t >= H330_SPIKE and s >= H330_SPIKE + timedelta(weeks=1 if source == "sensing" else 999):
        m *= 1.6
    if sku == "NV-K100" and t >= K100_END:
        if source == "sensing" and s >= K100_END + timedelta(weeks=1):
            m *= 0.0
        elif source == "consensus":     # the plan keeps a tail of 30% for eight weeks, then stops
            m *= 0.0 if s >= K100_END + timedelta(weeks=8) else 0.3
    return m


def simulate(out: Path) -> dict:
    rng = np.random.default_rng(SEED)
    out.mkdir(parents=True, exist_ok=True)
    weeks = mondays(SNAP_START, LATEST_SNAP + timedelta(weeks=MAX_H))
    widx = {w: i for i, w in enumerate(weeks)}
    mk = list(MARKETS.market)
    size = dict(zip(MARKETS.market, MARKETS["size"]))
    sku_ids = [s[0] for s in SKUS]
    base = {s[0]: s[3] for s in SKUS}
    fam = {s[0]: s[2] for s in SKUS}

    # market-wide swings (AR(1)) and SKU-level noise, drawn for every week including the future
    M = {}
    for m in mk:
        x, series = 0.0, []
        for _ in weeks:
            x = 0.5 * x + rng.normal(0, 0.075)
            series.append(x)
        M[m] = np.array(series)
    EPS = {(s, m): rng.normal(0, 0.085, len(weeks)) for s in sku_ids for m in mk}

    def expected(s, m, t):
        yrs = (t - FIRST_TARGET).days / 365.25
        return base[s] * size[m] * season(t) * (1 + 0.08 * yrs)

    # ---- actuals
    act = []
    for s in sku_ids:
        for m in mk:
            for t in mondays(FIRST_TARGET, LATEST_SNAP):
                i = widx[t]
                u = expected(s, m, t) * level(s, m, t) * (1 + M[m][i]) * (1 + EPS[(s, m)][i])
                act.append((t, s, m, max(0, int(round(u)))))
    shipped = pd.DataFrame(act, columns=["week_start", "sku", "market", "units"])  # what really shipped, through the as-of week
    actuals = shipped[shipped.week_start <= LAST_ACTUAL].copy()                      # what the actuals feed has delivered
    actuals["delivered_at"] = pd.to_datetime(actuals.week_start) + pd.Timedelta(days=8, hours=7)
    late = (actuals.market == LATE["market"]) & (actuals.week_start == LATE["week"])
    lat = actuals[late].copy()
    keep_first = rng.random(len(lat)) < LATE["partial_share"]
    first = lat[keep_first].copy()                                  # on-time partial delivery
    lat["delivered_at"] = lat["delivered_at"] + pd.Timedelta(days=LATE["days_late"])  # the complete one, late
    actuals = pd.concat([actuals[~late], first, lat], ignore_index=True)
    actuals["delivery_id"] = "ACT-" + actuals.delivered_at.dt.strftime("%Y%m%d%H")

    # ---- forecast snapshots
    rows = []
    manifest = []
    for src in ("sensing", "consensus"):
        for sw in mondays(SNAP_START, LATEST_SNAP):
            created = datetime.combine(sw, datetime.min.time()) + (timedelta(hours=6) if src == "sensing" else timedelta(days=1, hours=14))
            for m in mk:
                missing = src == MISSING["source"] and m == MISSING["market"] and sw == MISSING["snapshot_week"]
                n0 = len(rows)
                for h in range(MAX_H + 1):
                    t = sw + timedelta(weeks=h)
                    i = widx[t]
                    for s in sku_ids:
                        e = EPS[(s, m)][i]
                        mm = M[m][i]
                        kl = known_level(src, s, m, sw, t)
                        if src == "sensing":
                            f_m = 1.0 if h <= 1 else 0.75 if h <= 4 else 0.45
                            f = expected(s, m, t) * kl * (1 + f_m * mm) * (1 + rng.normal(0, 0.16 + 0.01 * h))
                        else:
                            f_e = 0.75 if h <= 4 else 0.45
                            f = expected(s, m, t) * kl * 1.05 * (1 + 0.15 * mm) * (1 + f_e * e) * (1 + rng.normal(0, 0.03 + 0.004 * h))
                        if missing:
                            continue
                        rows.append((src, sw, 1, created, s, m, t, h, "base", max(0.0, round(f, 1))))
                        if src == "consensus" and sw == LATEST_SNAP:
                            up = 1.15 if t.month in (11, 12) else 1.08
                            rows.append((src, sw, 1, created, s, m, t, h, "upside", max(0.0, round(f * up, 1))))
                manifest.append((src, m, sw, created if not missing else None, 0 if missing else len(rows) - n0,
                                 (MAX_H + 1) * len(sku_ids)))
    fc = pd.DataFrame(rows, columns=["source", "snapshot_week", "version", "created_at", "sku", "market", "target_week",
                                     "horizon_weeks", "scenario", "units"])

    # same-day corrections: a handful of consensus snapshots republished three hours later as version 2
    corr_weeks = [date(2025, 4, 14), date(2025, 9, 22), date(2026, 3, 9)]
    corr = fc[(fc.source == "consensus") & fc.snapshot_week.isin(corr_weeks)].copy()
    corr["version"] = 2
    corr["created_at"] = corr["created_at"] + pd.Timedelta(hours=3)
    corr["units"] = (corr["units"] * 1.01).round(1)

    # the leak: a backfill of snapshot 2026-07-06 run on 2026-09-15, which used actuals for the weeks already shipped
    a_idx = actuals.drop_duplicates(["week_start", "sku", "market"], keep="last").set_index(["week_start", "sku", "market"]).units
    leak = fc[(fc.source == LEAK["source"]) & (fc.snapshot_week == LEAK["snapshot_week"])].copy()
    leak["version"] = LEAK["version"]
    leak["created_at"] = LEAK["created_at"]
    known = [(t, s, m) in a_idx.index and t < LEAK["created_at"].date() for t, s, m in zip(leak.target_week, leak.sku, leak.market)]
    leak.loc[known, "units"] = [round(a_idx[(t, s, m)] * (1 + rng.normal(0, 0.01)), 1)
                                for t, s, m in zip(leak.target_week[known], leak.sku[known], leak.market[known])]
    fc = pd.concat([fc, corr, leak], ignore_index=True)
    fc["snapshot_id"] = fc.source.str[:3].str.upper() + "-" + pd.to_datetime(fc.snapshot_week).dt.strftime("%Y%m%d") + "-v" + fc.version.astype(str)
    fc = fc[["snapshot_id", "source", "snapshot_week", "version", "created_at", "sku", "market", "target_week",
             "horizon_weeks", "scenario", "units"]]
    manifest = pd.DataFrame(manifest, columns=["source", "market", "snapshot_week", "received_at", "rows_received", "rows_expected"])
    manifest["expected_by"] = pd.to_datetime(manifest.snapshot_week) + pd.to_timedelta(np.where(manifest.source == "sensing", 12, 48), unit="h")

    # ---- capacity
    cap = []
    for sid, _, _, hc, hrs, temp in SITES.itertuples(index=False):
        for t in mondays(FIRST_TARGET, LATEST_SNAP + timedelta(weeks=MAX_H)):
            absence = 0.08 + (0.15 if (t.month == 12 and t.day >= 22) or (t.month == 1 and t.day <= 4) else 0.0) + \
                      (0.06 if t.month in (7, 8) else 0.0)
            growth = 1 + 0.05 * ((t - FIRST_TARGET).days / 365.25)
            peak = t.month == 12 or (t.month == 11 and t.day >= 10)
            cap.append((sid, t, int(round(hc * growth)), int(round(hc * growth * temp)) if peak else 0, hrs,
                        round(absence + rng.normal(0, 0.01), 3)))
    capacity = pd.DataFrame(cap, columns=["site_id", "week_start", "headcount", "temporary_headcount", "contracted_hours_per_head",
                                          "planned_absence_rate"])
    rout = []
    for sid in SITES.site_id:
        for f, hrs in FAMILY_STD_HOURS.items():
            if sid == "SITE-C":
                rout.append((sid, f, round(hrs * 60 * 1.1, 2), "minutes"))    # Gamma is 10% slower, and reports minutes
            else:
                rout.append((sid, f, hrs if sid == "SITE-A" else round(hrs * 1.05, 4), "hours"))
    routings = pd.DataFrame(rout, columns=["site_id", "family", "std_time_per_unit", "uom"])

    # ---- inventory: replenished on the consensus plan's four-week forecast, as the company does today
    site_of = dict(zip(MARKETS.market, MARKETS.site_id))
    f4 = fc[(fc.source == "consensus") & (fc.horizon_weeks == 4) & (fc.scenario == "base") & (fc.version == 1)]
    f4 = f4.assign(site_id=f4.market.map(site_of)).groupby(["sku", "site_id", "target_week"]).units.sum()
    a_site = shipped.assign(site_id=lambda d: d.market.map(site_of)).groupby(["sku", "site_id", "week_start"]).units.sum()
    inv, rec = [], []
    inv_weeks = mondays(FIRST_TARGET, LATEST_SNAP + timedelta(weeks=1))  # snapshots through the as-of week
    for s in sku_ids:
        for sid in SITES.site_id:
            mks = [m for m in mk if site_of[m] == sid]
            onhand = 3.5 * sum(expected(s, m, FIRST_TARGET) for m in mks)
            for t in inv_weeks:
                oh = max(0.0, onhand)
                inv.append((t, s, sid, int(round(oh)), int(round(max(0.0, -onhand)))))
                receipt = f4.get((s, sid, t), 0.0) * 1.02
                onhand = onhand + receipt - a_site.get((s, sid, t), 0)
            # open supply from the as-of week: the latest consensus plan, base scenario, ordered four weeks out
            last = fc[(fc.source == "consensus") & (fc.snapshot_week == LATEST_SNAP) & (fc.scenario == "base") & (fc.sku == s) &
                      fc.market.isin(mks) & (fc.horizon_weeks >= 1)].groupby("target_week").units.sum()
            for t, u in last.items():
                rec.append((s, sid, t, int(round(u * 1.02))))
    inventory = pd.DataFrame(inv, columns=["week_start", "sku", "site_id", "on_hand_units", "backorder_units"])
    receipts = pd.DataFrame(rec, columns=["sku", "site_id", "receipt_week", "units"])

    skus = pd.DataFrame([(s, n, f, K100_END if s == "NV-K100" else None) for s, n, f, _ in SKUS],
                        columns=["sku", "sku_name", "family", "discontinued_from"])
    tables = {
        "forecast_snapshots": fc, "feed_manifest": manifest, "actuals_weekly": actuals, "labour_capacity": capacity,
        "routings": routings, "inventory_snapshots": inventory, "planned_receipts": receipts, "skus": skus,
        "markets": MARKETS.drop(columns="size"), "sites": SITES.drop(columns=["headcount", "contracted_hours", "peak_temp_share"]),
    }
    for name, df in tables.items():
        df.to_parquet(out / f"{name}.parquet", index=False)

    key = {
        "as_of": AS_OF.isoformat(), "latest_snapshot": LATEST_SNAP.isoformat(), "last_actual_week": LAST_ACTUAL.isoformat(),
        "aggregate_winner": "sensing", "sku_level_winner": "consensus", "decision_horizon_weeks": 4,
        "consensus_bias_approx": 0.05,
        "leak": {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in LEAK.items()},
        "missing_feed": {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in MISSING.items()},
        "late_actuals": {"market": LATE["market"], "week": LATE["week"].isoformat(), "days_late": LATE["days_late"]},
        "overstock": {"sku": "NV-S210", "drop_from": S210_DROP.isoformat()},
        "shortage": {"sku": "NV-H330", "site_id": "SITE-C", "spike_from": H330_SPIKE.isoformat()},
        "discontinued": {"sku": "NV-K100", "from": K100_END.isoformat()},
        "over_capacity_site": "SITE-B", "minutes_routing_site": "SITE-C",
        "rows": {k: len(v) for k, v in tables.items()},
    }
    (out / "answer_key.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    return key


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/raw")
    a = ap.parse_args()
    key = simulate(Path(a.out))
    print("wrote", ", ".join(f"{k} {v:,}" for k, v in key["rows"].items()))


if __name__ == "__main__":
    main()
