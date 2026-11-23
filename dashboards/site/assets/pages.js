/* Page renderers. Data: window.DASH (data.js, written by dashboards/build.py). */
(function () {
  "use strict";
  const D = window.DASH;
  const { line, bar, heatmap, card, table, fmt, esc } = window.Viz;
  const sum = (a) => a.reduce((x, y) => x + (y || 0), 0);
  const uniq = (a) => [...new Set(a)];
  const mon = (s) => new Date(s.slice(0, 10) + "T00:00:00").toLocaleDateString("en-GB", { month: "short", year: "2-digit" });
  const day = (s) => new Date(s.slice(0, 10) + "T00:00:00").toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
  const SRC = { sensing: "Sensing model", consensus: "Consensus plan" };
  const SITE = Object.fromEntries(D.sites.map((s) => [s.site_id, s.site_name]));
  const MK = Object.fromEntries(D.markets.map((m) => [m.market, m.market_name]));
  const state = { site: "SITE-B" };
  const acc = (level, source, h = 4, member = "All", win = "all") =>
    D.acc.find((r) => r.window_name === win && r.level === level && r.member === member && r.source === source && r.horizon_weeks === h) || {};
  const out = (site, sc) => D.outlook.find((r) => r.site_id === site && r.scenario === sc) || {};
  const inv = (sku, site, src) => D.inv.find((r) => r.sku === sku && r.site_id === site && r.source === src) || {};

  function tiles(list) {
    const el = document.getElementById("tiles");
    if (!el) return;
    el.replaceChildren(...list.map((t) => {
      const d = document.createElement("div"); d.className = "tile";
      const k = document.createElement("div"); k.className = "k"; k.textContent = t.k;
      const v = document.createElement("div"); v.className = "v"; v.textContent = t.v;
      d.append(k, v);
      if (t.d) { const s = document.createElement("div"); s.className = "d"; s.textContent = t.d; d.append(s); }
      return d;
    }));
  }
  const insights = (items) => {
    document.getElementById("insights").innerHTML = items.map(([cls, label, text, href, where]) =>
      `<li><span class="status ${cls}"><i aria-hidden="true">${cls === "good" ? "✓" : "!"}</i>${label}</span><span>${text} <a class="where" href="${href}">${where} →</a></span></li>`).join("");
  };

  /* ---------- Scorecard ---------- */
  function scorecard() {
    const tot = { s: acc("total", "sensing"), c: acc("total", "consensus") }, sku = { s: acc("sku_market", "sensing"), c: acc("sku_market", "consensus") };
    const beta = out("SITE-B", "base"), betaC = out("SITE-B", "constrained");
    const dis = uniq(D.inv.filter((r) => r.sources_disagree).map((r) => r.sku + r.site_id)).length;
    const leak = D.leak[0], miss = D.feeds.filter((r) => r.status === "missing"), late = D.fresh.filter((r) => r.status !== "ok");
    const deb = D.tradeoff.find((r) => r.is_debiased), pub = D.tradeoff.find((r) => r.factor === 1 && !r.is_debiased);
    tiles([
      { k: "Consensus plan, SKU-level WAPE", v: fmt.pct(1)(sku.c.wape), d: `sensing model ${fmt.pct(1)(sku.s.wape)}, 4 weeks out` },
      { k: "Sensing model, all SKUs summed", v: fmt.pct(1)(tot.s.wape), d: `consensus plan ${fmt.pct(1)(tot.c.wape)}` },
      { k: "Site Beta peak utilisation", v: fmt.pct(0)(beta.peak_utilisation), d: `base plan, week of ${day(beta.peak_week)}` },
      { k: "Stock positions in dispute", v: String(dis), d: "the two forecasts call them differently" },
      { k: "Feed incidents, 26 weeks", v: String(miss.length + late.length + D.leak.length), d: "missing, late, leaked" },
    ]);
    const s210 = inv("NV-S210", "SITE-A", "sensing"), h330 = inv("NV-H330", "SITE-C", "sensing"), h330c = inv("NV-H330", "SITE-C", "consensus");
    insights([
      ["warning", "Decide", `<b>Use the consensus plan for SKU-level replenishment and staffing, not the sensing model.</b> Summed over every SKU the sensing model looks twice as accurate (${fmt.pct(1)(tot.s.wape)} against ${fmt.pct(1)(tot.c.wape)}), because its SKU errors cancel. At the SKU x market grain where stock is committed, four weeks out, the consensus plan's error is ${fmt.pct(1)(sku.c.wape)} against ${fmt.pct(1)(sku.s.wape)}.`, "accuracy.html", "Forecast accuracy"],
      ["critical", "Act", `<b>Site Beta needs ${fmt.int(beta.hours_over_capacity)} more labour hours, or ${fmt.int(betaC.unmet_units)} units slip.</b> It is over capacity in the weeks of ${D.capacity.filter((r) => r.site_id === "SITE-B" && r.scenario === "base" && r.utilisation > 1).map((r) => day(r.week_start).replace(/ \d{4}$/, "")).join(", ")}. The base plan peaks at ${fmt.pct(0)(beta.peak_utilisation)} of available hours in the week of ${day(beta.peak_week)}; the upside plan reaches ${fmt.pct(0)(out("SITE-B", "upside").peak_utilisation)}. Approve temporary staff for those weeks: Site Alpha cannot absorb the volume, as it peaks at ${fmt.pct(0)(out("SITE-A", "base").peak_utilisation)} itself.`, "capacity.html", "Capacity"],
      ["critical", "Act", `<b>Override the plan for four stock positions where demand has changed.</b> NV-S210 has sold ${fmt.pct(0)(-s210.actual_yoy_last_8w)} less than a year earlier at Site Alpha over the last eight weeks, while the consensus plan forecasts ${fmt.rel(0)(inv("NV-S210", "SITE-A", "consensus").forecast_yoy_next_4w)} on a year earlier: cut receipts. NV-H330 at Site Gamma is selling ${fmt.pct(0)(h330.actual_yoy_last_8w)} more than a year earlier; on the sensing forecast it runs out in the week of ${day(h330.first_stockout_week)}, while the plan shows ${fmt.num(1)(h330c.weeks_of_cover)} weeks of cover and no risk.`, "inventory.html", "Inventory"],
      ["warning", "Decide", `<b>The consensus plan runs ${fmt.rel(1)(sku.c.bias)} high.</b> Dividing it by its own earlier bias would cut WAPE from ${fmt.pct(1)(pub.wape)} to ${fmt.pct(1)(deb.wape)} and excess units from ${fmt.pct(1)(pub.excess_share)} to ${fmt.pct(1)(deb.excess_share)} of demand, but fill if stock equalled the forecast falls from ${fmt.pct(1)(pub.fill_if_stocked_to_forecast)} to ${fmt.pct(1)(deb.fill_if_stocked_to_forecast)}. Debias only where safety stock covers the gap.`, "accuracy.html", "Forecast accuracy"],
      ["warning", "Read with care", `<b>A backfill of the ${day(leak.snapshot_week)} consensus snapshot was created on ${day(leak.naive_created_at)}, with actuals in hand.</b> Scored naively it would claim ${fmt.pct(1)(leak.wape_naive)} WAPE on ${fmt.int(leak.pairs_affected)} pairs; the version planners actually saw scores ${fmt.pct(1)(leak.wape_asof)}. It is excluded. ${miss.length ? `The sensing feed for ${esc(miss[0].market)}, week of ${day(miss[0].snapshot_week)}, never arrived and is reported as a coverage gap.` : ""}`, "observability.html", "Feed observability"],
    ]);
    const unitFmt = (r) => r.unit === "count" ? fmt.int(r.value) : r.unit === "pct_abs" ? fmt.rel(1)(r.value) : fmt.pct(1)(r.value);
    const tgtFmt = (r) => r.unit === "count" ? fmt.int(r.target) : (r.direction === "min" ? "≥ " : r.direction === "abs_max" ? "within ±" : "≤ ") + fmt.pct(r.unit === "pct" && r.target > 0.99 ? 1 : 0)(r.target);
    document.getElementById("scorecard").innerHTML = `<table><thead><tr><th>Area</th><th>Metric</th><th>Value</th><th>Target</th><th>Status</th></tr></thead><tbody>${D.scorecard.map((r) =>
      `<tr><td>${esc(r.area)}</td><td><a href="${esc(r.page)}">${esc(r.metric)}</a></td><td><b>${esc(unitFmt(r))}</b></td><td>${esc(tgtFmt(r))}</td><td><span class="status ${r.status}"><i aria-hidden="true">${r.status === "good" ? "✓" : "!"}</i>${r.status === "good" ? "On target" : r.status === "warning" ? "Watch" : "Off target"}</span></td></tr>`).join("")}</tbody></table>`;
    const sites = D.sites.map((s) => s.site_id);
    card("sc-capacity", (el) => bar(el, { x: sites.map((s) => SITE[s]), yFmt: fmt.pct(0), series: [
      { name: "Base plan", data: sites.map((s) => out(s, "base").peak_utilisation), color: 0, labels: true },
      { name: "Upside", data: sites.map((s) => out(s, "upside").peak_utilisation), color: 1, labels: true }] }),
      { cols: [{ key: "site_id", label: "Site", fmt: (s) => SITE[s] }, { key: "scenario", label: "Scenario" }, { key: "peak_utilisation", label: "Peak", fmt: fmt.pct(0) }, { key: "peak_week", label: "Peak week" }, { key: "weeks_over_capacity", label: "Weeks over 100%" }, { key: "unmet_units", label: "Unmet units", fmt: fmt.int }], rows: D.outlook });
  }

  /* ---------- Accuracy ---------- */
  function accuracy() {
    const tot = { s: acc("total", "sensing"), c: acc("total", "consensus") }, sku = { s: acc("sku_market", "sensing"), c: acc("sku_market", "consensus") };
    tiles([
      { k: "All SKUs summed: sensing model", v: fmt.pct(1)(tot.s.wape), d: `consensus plan ${fmt.pct(1)(tot.c.wape)}` },
      { k: "SKU x market: consensus plan", v: fmt.pct(1)(sku.c.wape), d: `sensing model ${fmt.pct(1)(sku.s.wape)}` },
      { k: "Consensus plan bias", v: fmt.rel(1)(sku.c.bias), d: "over-forecast, 4 weeks out" },
      { k: "Matched pairs, 4 weeks out", v: fmt.int(sku.c.n_pairs), d: "per source, since March 2025" },
    ]);
    const levels = [["total", "All", "All SKUs summed"], ["market", "All", "By market"], ["sku_market", "All", "SKU x market"]];
    card("ac-level", (el) => bar(el, { x: levels.map((l) => l[2]), yFmt: fmt.pct(1), series: ["sensing", "consensus"].map((s, i) => ({ name: SRC[s], data: levels.map((l) => acc(l[0], s, 4, l[1]).wape), color: i, labels: true })) }),
      { cols: [{ key: "level", label: "Level" }, { key: "source", label: "Source", fmt: (s) => SRC[s] }, { key: "wape", label: "WAPE", fmt: fmt.pct(2) }, { key: "bias", label: "Bias", fmt: fmt.rel(2) }, { key: "mae", label: "MAE", fmt: fmt.int }, { key: "n_comparisons", label: "Comparisons", fmt: fmt.int }],
        rows: D.acc.filter((r) => r.window_name === "all" && r.member === "All" && r.horizon_weeks === 4) });
    const hs = [1, 2, 3, 4, 5, 6, 7, 8];
    card("ac-horizon", (el) => line(el, { x: hs.map(String), xFmt: (h) => h + " wk", yFmt: fmt.pct(0), yMin: 0, series: [
      { name: SRC.sensing, data: hs.map((h) => acc("sku_market", "sensing", h).wape), color: 0 },
      { name: SRC.consensus, data: hs.map((h) => acc("sku_market", "consensus", h).wape), color: 1 }] }),
      { cols: [{ key: "horizon_weeks", label: "Horizon" }, { key: "source", label: "Source", fmt: (s) => SRC[s] }, { key: "wape", label: "WAPE", fmt: fmt.pct(2) }, { key: "bias", label: "Bias", fmt: fmt.rel(2) }],
        rows: D.acc.filter((r) => r.window_name === "all" && r.level === "sku_market" && r.member === "All") });
    const weeks = uniq(D.trend.map((r) => r.target_week)).sort();
    const tr = (s, k) => weeks.map((w) => (D.trend.find((r) => r.target_week === w && r.source === s) || {})[k] ?? null);
    card("ac-trend", (el) => line(el, { x: weeks, xFmt: mon, yFmt: fmt.pct(0), yMin: 0, series: [
      { name: SRC.sensing + ", SKU", data: tr("sensing", "wape_sku_market"), color: 0 },
      { name: SRC.consensus + ", SKU", data: tr("consensus", "wape_sku_market"), color: 1 },
      { name: SRC.sensing + ", summed", data: tr("sensing", "wape_total"), color: 0, dashed: true },
      { name: SRC.consensus + ", summed", data: tr("consensus", "wape_total"), color: 1, dashed: true }] }),
      { cols: [{ key: "target_week", label: "Week" }, { key: "source", label: "Source", fmt: (s) => SRC[s] }, { key: "wape_sku_market", label: "SKU WAPE", fmt: fmt.pct(1) }, { key: "wape_total", label: "Summed WAPE", fmt: fmt.pct(1) }, { key: "bias", label: "Bias", fmt: fmt.rel(1) }], rows: D.trend });
    const to = D.tradeoff.filter((r) => !r.is_debiased), deb = D.tradeoff.find((r) => r.is_debiased);
    card("ac-tradeoff", (el) => line(el, { x: to.map((r) => r.factor.toFixed(2)), xFmt: (v) => "x" + v, yFmt: fmt.pct(0), yMin: 0, series: [
      { name: "Units short", data: to.map((r) => 1 - r.fill_if_stocked_to_forecast), color: 0 },
      { name: "Units in excess", data: to.map((r) => r.excess_share), color: 1 },
      { name: "WAPE", data: to.map((r) => r.wape), color: 2, dashed: true }] }),
      { cols: [{ key: "factor", label: "Factor", fmt: fmt.num(3) }, { key: "is_debiased", label: "Debiased", fmt: (v) => (v ? "yes" : "") }, { key: "wape", label: "WAPE", fmt: fmt.pct(1) }, { key: "bias", label: "Bias", fmt: fmt.rel(1) }, { key: "fill_if_stocked_to_forecast", label: "Fill", fmt: fmt.pct(1) }, { key: "excess_share", label: "Excess", fmt: fmt.pct(1) }], rows: D.tradeoff });
    const ms = D.markets.map((m) => m.market);
    card("ac-market", (el) => bar(el, { horizontal: true, x: ms.map((m) => MK[m]), yFmt: fmt.pct(1), series: ["sensing", "consensus"].map((s, i) => ({ name: SRC[s], data: ms.map((m) => acc("sku_market", s, 4, m).wape), color: i, labels: true })) }),
      { cols: [{ key: "member", label: "Market", fmt: (m) => MK[m] }, { key: "source", label: "Source", fmt: (s) => SRC[s] }, { key: "wape", label: "WAPE", fmt: fmt.pct(2) }, { key: "bias", label: "Bias", fmt: fmt.rel(2) }, { key: "actual_units", label: "Actual units", fmt: fmt.int }],
        rows: D.acc.filter((r) => r.window_name === "all" && r.level === "sku_market" && r.member !== "All" && r.horizon_weeks === 4) });
  }

  /* ---------- Observability ---------- */
  function observability() {
    const miss = D.feeds.filter((r) => r.status === "missing"), late = D.fresh.filter((r) => r.status !== "ok"), leak = D.leak[0];
    const cov = D.coverage.filter((r) => r.source === "sensing");
    tiles([
      { k: "Forecast feeds missing", v: String(miss.length), d: miss.map((r) => `${SRC[r.source]}, ${r.market}, ${day(r.snapshot_week)}`).join("; ") || "none" },
      { k: "Lowest coverage, 4 weeks out", v: fmt.pct(0)(Math.min(...cov.map((r) => r.coverage))), d: "one market-week for the sensing model" },
      { k: "Actuals weeks late", v: String(late.length), d: late.map((r) => `${r.market}, ${day(r.week_start)}, ${Math.round(r.hours_late / 24)} days`).join("; ") },
      { k: "Backfilled rows excluded", v: fmt.int(leak ? leak.pairs_affected : 0), d: "scored pairs a naive model would have used" },
    ]);
    const sw = uniq(D.feeds.map((r) => r.snapshot_week)).sort().slice(-26);
    const feeds = uniq(D.feeds.map((r) => r.source + "|" + r.market)).sort();
    const cells = [];
    feeds.forEach((f, yi) => sw.forEach((w, xi) => { const r = D.feeds.find((x) => x.source + "|" + x.market === f && x.snapshot_week === w); cells.push([xi, yi, r ? r.rows_in_warehouse / r.rows_expected : null]); }));
    card("ob-feeds", (el) => heatmap(el, { x: sw, y: feeds, cells, min: 0, max: 1, fmt: fmt.pct(0), xLabel: (w) => day(w).replace(/ \d{4}$/, ""), yLabel: (f) => `${SRC[f.split("|")[0]]} · ${f.split("|")[1]}` }),
      { cols: [{ key: "source", label: "Source", fmt: (s) => SRC[s] }, { key: "market", label: "Market" }, { key: "snapshot_week", label: "Snapshot week" }, { key: "expected_by", label: "Expected by" }, { key: "received_at", label: "Received" }, { key: "rows_in_warehouse", label: "Rows", fmt: fmt.int }, { key: "status", label: "Status" }],
        rows: D.feeds.filter((r) => r.status !== "ok").concat(D.feeds.filter((r) => r.status === "ok").slice(-16)) });
    const cw = uniq(cov.map((r) => r.target_week)).sort().slice(-30);
    card("ob-coverage", (el) => line(el, { x: cw, xFmt: (w) => day(w).replace(/ \d{4}$/, ""), yFmt: fmt.pct(0), yMin: 0, yMax: 1, series: D.markets.map((m, i) => ({ name: m.market, data: cw.map((w) => (cov.find((r) => r.target_week === w && r.market === m.market) || {}).coverage ?? null), color: i })) }),
      { cols: [{ key: "target_week", label: "Target week" }, { key: "market", label: "Market" }, { key: "keys_with_actuals", label: "Keys" }, { key: "keys_with_forecast", label: "With forecast" }, { key: "coverage", label: "Coverage", fmt: fmt.pct(0) }], rows: cov.filter((r) => r.coverage < 1) });
    const fw = uniq(D.fresh.map((r) => r.week_start)).sort().slice(-26);
    card("ob-fresh", (el) => bar(el, { x: fw, xFmt: (w) => day(w).replace(/ \d{4}$/, ""), yFmt: (v) => fmt.int(v) + " h", stack: false, series: D.markets.map((m, i) => ({ name: m.market, data: fw.map((w) => (D.fresh.find((r) => r.week_start === w && r.market === m.market) || {}).hours_late ?? null), color: i })) }),
      { cols: [{ key: "week_start", label: "Week" }, { key: "market", label: "Market" }, { key: "first_delivered_at", label: "First rows" }, { key: "complete_at", label: "Complete" }, { key: "deliveries", label: "Deliveries" }, { key: "hours_late", label: "Hours late" }, { key: "status", label: "Status" }], rows: D.fresh.filter((r) => r.status !== "ok" || r.deliveries > 1) });
    card("ob-leak", (el) => bar(el, { horizontal: true, x: ["What a naive model reports", "What planners could have known"], yFmt: fmt.pct(1), series: [{ name: "WAPE on the affected pairs", data: [leak.wape_naive, leak.wape_asof], colors: [1, 0], labels: true }] }),
      { cols: [{ key: "source", label: "Source", fmt: (s) => SRC[s] }, { key: "snapshot_week", label: "Snapshot week" }, { key: "naive_snapshot_id", label: "Naive picks" }, { key: "naive_created_at", label: "Created" }, { key: "asof_snapshot_id", label: "As-of picks" }, { key: "asof_created_at", label: "Created" }, { key: "pairs_affected", label: "Pairs" }, { key: "wape_naive", label: "Naive WAPE", fmt: fmt.pct(2) }, { key: "wape_asof", label: "As-of WAPE", fmt: fmt.pct(2) }], rows: D.leak });
  }

  /* ---------- Capacity ---------- */
  function capacity() {
    const s = state.site, rows = D.capacity.filter((r) => r.site_id === s);
    const b = out(s, "base"), u = out(s, "upside"), c = out(s, "constrained");
    tiles([
      { k: SITE[s] + ", peak, base plan", v: fmt.pct(0)(b.peak_utilisation), d: "week of " + day(b.peak_week) },
      { k: "Peak, upside plan", v: fmt.pct(0)(u.peak_utilisation), d: `${u.weeks_over_capacity} weeks over 100%` },
      { k: "Hours over capacity, base", v: fmt.int(b.hours_over_capacity), d: `${b.weeks_over_capacity} weeks` },
      { k: "Unmet units, constrained", v: fmt.int(c.unmet_units), d: "if no hours are added" },
    ]);
    const weeks = uniq(rows.map((r) => r.week_start)).sort();
    const ser = (sc) => weeks.map((w) => (rows.find((r) => r.week_start === w && r.scenario === sc) || {}).utilisation ?? null);
    card("cp-line", (el) => line(el, { x: weeks, xFmt: mon, yFmt: fmt.pct(0), yMin: 0, series: [
      { name: "Actual", data: ser("actual"), color: 0, markLine: { y: 0.95, label: "alert 95%" } },
      { name: "Base plan", data: ser("base"), color: 1 },
      { name: "Upside", data: ser("upside"), color: 2, dashed: true },
      { name: "Constrained", data: ser("constrained"), color: 3, dashed: true }] }),
      { cols: [{ key: "week_start", label: "Week" }, { key: "scenario", label: "Scenario" }, { key: "load_hours", label: "Load h", fmt: fmt.int }, { key: "available_hours", label: "Available h", fmt: fmt.int }, { key: "utilisation", label: "Utilisation", fmt: fmt.pct(1) }, { key: "unmet_units", label: "Unmet units", fmt: fmt.int }], rows: rows.filter((r) => r.scenario !== "actual") });
    table(document.getElementById("outlook"), [{ key: "scenario", label: "Scenario" }, { key: "peak_utilisation", label: "Peak", fmt: fmt.pct(0) }, { key: "peak_week", label: "Peak week", fmt: day }, { key: "weeks_above_alert", label: "Weeks > 95%" }, { key: "weeks_over_capacity", label: "Weeks > 100%" }, { key: "hours_over_capacity", label: "Hours over", fmt: fmt.int }, { key: "unmet_units", label: "Unmet units", fmt: fmt.int }],
      D.outlook.filter((r) => r.site_id === s));
    const fw = weeks.filter((w) => rows.some((r) => r.week_start === w && r.scenario === "base"));
    card("cp-hours", (el) => bar(el, { x: fw, xFmt: (w) => day(w).replace(/ \d{4}$/, ""), yFmt: fmt.int, series: [
      { name: "Load, base plan", data: fw.map((w) => rows.find((r) => r.week_start === w && r.scenario === "base").load_hours), color: 1 },
      { name: "Available", data: fw.map((w) => rows.find((r) => r.week_start === w && r.scenario === "base").available_hours), color: 0 }] }),
      { cols: [{ key: "week_start", label: "Week" }, { key: "load_hours", label: "Load h", fmt: fmt.int }, { key: "available_hours", label: "Available h", fmt: fmt.int }, { key: "utilisation", label: "Utilisation", fmt: fmt.pct(1) }], rows: rows.filter((r) => r.scenario === "base") });
  }

  /* ---------- Inventory ---------- */
  function inventory() {
    const dis = D.inv.filter((r) => r.sources_disagree);
    const pos = uniq(dis.map((r) => r.sku + "|" + r.site_id));
    tiles([
      { k: "Exceptions on the consensus plan", v: String(D.inv.filter((r) => r.source === "consensus" && r.status !== "ok").length), d: "of " + D.inv.filter((r) => r.source === "consensus").length + " SKU-site positions" },
      { k: "Exceptions on the sensing model", v: String(D.inv.filter((r) => r.source === "sensing" && r.status !== "ok").length), d: "same positions, same receipts" },
      { k: "Positions in dispute", v: String(pos.length), d: "the decision depends on the forecast" },
      { k: "Stock snapshot", v: day(D.inv_week), d: "projection runs 12 weeks" },
    ]);
    const rowsT = pos.map((p) => { const [sku, site] = p.split("|"); const c = inv(sku, site, "consensus"), s = inv(sku, site, "sensing");
      return { sku, site, on_hand: c.on_hand_units, ayoy: c.actual_yoy_last_8w, cyoy: c.forecast_yoy_next_4w, syoy: s.forecast_yoy_next_4w, ccov: c.weeks_of_cover, scov: s.weeks_of_cover, cst: c.status, sst: s.status, out: s.first_stockout_week }; });
    table(document.getElementById("disagree"), [{ key: "sku", label: "SKU" }, { key: "site", label: "Site", fmt: (s) => SITE[s] }, { key: "on_hand", label: "On hand", fmt: fmt.int },
      { key: "ayoy", label: "Actuals vs year ago", fmt: fmt.rel(0) }, { key: "cyoy", label: "Plan vs year ago", fmt: fmt.rel(0) }, { key: "syoy", label: "Sensing vs year ago", fmt: fmt.rel(0) },
      { key: "ccov", label: "Cover, plan (wks)", fmt: fmt.num(1) }, { key: "scov", label: "Cover, sensing (wks)", fmt: fmt.num(1) }, { key: "cst", label: "Plan says" }, { key: "sst", label: "Sensing says" }, { key: "out", label: "Stock-out (sensing)", fmt: (v) => (v ? day(v) : "") }], rowsT);
    const proj = (sku, site, el) => {
      const h = D.hist.filter((r) => r.sku === sku && r.site_id === site), p = D.proj.filter((r) => r.sku === sku && r.site_id === site);
      const weeks = uniq(h.map((r) => r.week_start).concat(p.map((r) => r.week_start))).sort();
      const pv = (src) => weeks.map((w) => w === D.inv_week ? (h.find((r) => r.week_start === w) || {}).on_hand_units : (p.find((r) => r.week_start === w && r.source === src && w > D.inv_week) || {}).projected_on_hand ?? null);
      line(el, { x: weeks, xFmt: (w) => day(w).replace(/ \d{4}$/, ""), yFmt: fmt.int, series: [
        { name: "On hand", data: weeks.map((w) => (h.find((r) => r.week_start === w) || {}).on_hand_units ?? null), color: 0 },
        { name: "Projected, consensus plan", data: pv("consensus"), color: 1, dashed: true },
        { name: "Projected, sensing model", data: pv("sensing"), color: 2, dashed: true, markLine: { y: 0, label: "stock-out" } }] });
    };
    const pspec = (sku, site) => ({ cols: [{ key: "week_start", label: "Week" }, { key: "source", label: "Source", fmt: (s) => SRC[s] }, { key: "receipt_units", label: "Receipts", fmt: fmt.int }, { key: "forecast_units", label: "Forecast", fmt: fmt.int }, { key: "projected_on_hand", label: "Projected", fmt: fmt.int }], rows: D.proj.filter((r) => r.sku === sku && r.site_id === site) });
    card("iv-s210", (el) => proj("NV-S210", "SITE-A", el), pspec("NV-S210", "SITE-A"));
    card("iv-h330", (el) => proj("NV-H330", "SITE-C", el), pspec("NV-H330", "SITE-C"));
    const lab = rowsT.map((r) => `${r.sku} · ${SITE[r.site].replace("Site ", "")}`);
    card("iv-yoy", (el) => bar(el, { x: lab, yFmt: fmt.rel(0), series: [
      { name: "Actuals, last 8 weeks", data: rowsT.map((r) => r.ayoy), color: 0, labels: true },
      { name: "Consensus plan, next 4 weeks", data: rowsT.map((r) => r.cyoy), color: 1, labels: true },
      { name: "Sensing model, next 4 weeks", data: rowsT.map((r) => r.syoy), color: 2, labels: true }] }),
      { cols: [{ key: "sku", label: "SKU" }, { key: "site", label: "Site", fmt: (s) => SITE[s] }, { key: "ayoy", label: "Actuals", fmt: fmt.rel(1) }, { key: "cyoy", label: "Plan", fmt: fmt.rel(1) }, { key: "syoy", label: "Sensing", fmt: fmt.rel(1) }], rows: rowsT });
  }

  /* ---------- Checks ---------- */
  function checks() {
    tiles([
      { k: "dbt models and tests", v: D.dbt ? `${D.dbt.passed} / ${D.dbt.nodes}` : "–", d: "passing" },
      { k: "Latest actuals week", v: day(D.last_actual), d: "the next week's actuals are not due yet" },
      { k: "Backfilled rows held out", v: fmt.int((D.checks.find((r) => /backfills/.test(r.check_name)) || {}).value), d: "kept in silver for audit" },
    ]);
    document.getElementById("checks").innerHTML = `<ul class="insights">${D.checks.map((r) => {
      const warn = /missing|late/.test(r.check_name) && r.value > 0;
      return `<li><span class="status ${warn ? "warning" : "good"}"><i aria-hidden="true">${warn ? "!" : "✓"}</i>${warn ? "Flagged" : "Handled"}</span><span><b>${esc(r.check_name)}:</b> ${fmt.int(r.value)}. ${esc(r.handling)}.</span></li>`;
    }).join("")}</ul>`;
    const rules = [
      ["A forecast is scored only if it was created before its snapshot week ended and before its target week began", "int_forecast_frozen; assert_no_future_snapshot_in_accuracy"],
      ["Sources are compared on matched pairs only; missing pairs are reported as coverage", "fct_forecast_accuracy.is_matched; assert_matched_pairs_balanced"],
      ["WAPE and bias are ratios of sums, recomputed at every level, never averaged", "assert_market_wape_recomputes; test_market_ratios_are_not_averages_of_sku_ratios"],
      ["Error = forecast - actual: positive bias means over-forecast", "test_bias_sign_convention"],
      ["Zero actuals stay in WAPE; percentage error is undefined there", "rpt_zero_actuals; test_discontinued_sku_follows_the_zero_actual_policy"],
      ["Load and capacity are both in hours; minutes are converted in staging", "stg_routings; assert_routing_in_hours; assert_capacity_load_reconciles"],
      ["The constrained plan never exceeds available hours and keeps every unit as delivered or unmet", "assert_constrained_within_capacity; test_capacity_scenarios"],
      ["Every raw file meets its source contract: columns, types, grain", "contracts/sources.yml; tests/test_contracts.py"],
      ["Rebuilding from the same seed reproduces every mart", "make rebuild (analysis/fingerprint.py)"],
    ];
    document.getElementById("rules").innerHTML = `<ul class="insights">${rules.map(([r, w]) => `<li><span class="status good"><i aria-hidden="true">✓</i>Tested</span><span><b>${esc(r)}.</b> <code>${esc(w)}</code></span></li>`).join("")}</ul>`;
  }

  const PAGES = { scorecard, accuracy, observability, capacity, inventory, checks };
  document.addEventListener("DOMContentLoaded", () => {
    const page = document.body.dataset.page;
    if (!window.echarts) { document.querySelector("main").insertAdjacentHTML("afterbegin", '<p class="callout critical">Charts could not load (no network to the chart library). Tables still work.</p>'); }
    if (page === "capacity") {
      const seg = document.getElementById("f-site");
      seg.addEventListener("click", (e) => {
        const b = e.target.closest("button"); if (!b) return;
        seg.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
        state.site = b.dataset.v; window.Viz.clear(); capacity();
      });
    }
    PAGES[page]();
  });
})();
