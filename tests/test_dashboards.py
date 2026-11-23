"""The dashboard export runs on the warehouse and every page renders from it."""
import json
import subprocess
import sys

from conftest import DB, ROOT


def test_export_and_build(con, tmp_path):
    site = tmp_path / "site"
    (site / "assets").mkdir(parents=True)
    for f in ("style.css", "charts.js", "pages.js"):
        (site / "assets" / f).write_bytes((ROOT / "dashboards" / "site" / "assets" / f).read_bytes())
    data = site / "data.json"
    subprocess.run([sys.executable, str(ROOT / "dashboards" / "export.py"), "--db", str(DB), "--out", str(data)], check=True)
    d = json.loads(data.read_text(encoding="utf-8"))
    for key in ("acc", "trend", "tradeoff", "by_sku", "coverage", "leak", "feeds", "fresh", "capacity", "outlook", "inv", "proj", "scorecard", "checks"):
        assert d[key], key
    subprocess.run([sys.executable, str(ROOT / "dashboards" / "build.py"), "--data", str(data), "--site", str(site)], check=True)
    pages = sorted(p.name for p in site.glob("*.html"))
    assert pages == ["accuracy.html", "capacity.html", "checks.html", "index.html", "inventory.html", "observability.html"]
