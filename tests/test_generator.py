"""The generator is deterministic: the same seed writes the same data."""
import hashlib
import subprocess
import sys

import pandas as pd

from conftest import ROOT


def digest(d):
    h = hashlib.sha1()
    for name in ("forecast_snapshots", "actuals_weekly", "inventory_snapshots", "labour_capacity"):
        df = pd.read_parquet(d / f"{name}.parquet")
        h.update(pd.util.hash_pandas_object(df, index=False).values.tobytes())
    return h.hexdigest()


def test_same_seed_same_data(tmp_path):
    for run in ("a", "b"):
        subprocess.run([sys.executable, str(ROOT / "generator" / "simulate.py"), "--out", str(tmp_path / run)], check=True)
    assert digest(tmp_path / "a") == digest(tmp_path / "b")
    assert (tmp_path / "a" / "answer_key.json").read_text() == (tmp_path / "b" / "answer_key.json").read_text()
