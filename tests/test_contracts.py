"""Every raw file meets its source contract: columns, types and grain."""
from pathlib import Path

import duckdb
import pyarrow.parquet as pq
import pytest
import yaml

from conftest import RAW, ROOT

CONTRACTS = yaml.safe_load((ROOT / "contracts" / "sources.yml").read_text(encoding="utf-8"))
TYPES = {"string": ("string", "large_string"), "date": ("date32[day]", "timestamp[ns]", "timestamp[us]"),
         "timestamp": ("timestamp[ns]", "timestamp[us]"), "int": ("int64", "int32"), "float": ("double", "float")}


@pytest.mark.parametrize("table", sorted(CONTRACTS))
def test_contract(table):
    f = RAW / f"{table}.parquet"
    if not f.exists():
        pytest.skip("run `make data` first")
    schema = pq.read_schema(f)
    want = CONTRACTS[table]["columns"]
    assert list(schema.names) == list(want), f"{table}: columns differ from the contract"
    for col, t in want.items():
        assert str(schema.field(col).type) in TYPES[t], f"{table}.{col}: {schema.field(col).type} is not {t}"
    grain = ", ".join(CONTRACTS[table]["grain"])
    dup = duckdb.sql(f"select count(*) from (select {grain} from '{Path(f).as_posix()}' group by all having count(*) > 1)").fetchone()[0]
    assert dup == 0, f"{table}: grain {grain} is not unique"
