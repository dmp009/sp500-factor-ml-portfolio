"""Star schema saved as parquet in data/snapshot/ and queried with DuckDB (one view per table).

Months are stored as the first day of the month (DuckDB reads dates natively); `load()` turns
them back into pandas monthly periods.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from factorml.config import SNAPSHOT

TABLES = ("dim_month", "dim_security", "dim_sector", "fact_membership", "fact_prices", "fact_fundamentals",
          "fact_features", "fact_predictions", "fact_holdings", "fact_performance", "fact_factors", "fact_shap",
          "fact_live")


def save(tables: dict[str, pd.DataFrame], snapshot: Path = SNAPSHOT) -> None:
    snapshot.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        out = df.copy()
        for c in out.columns:
            if isinstance(out[c].dtype, pd.PeriodDtype):
                out[c] = out[c].dt.to_timestamp()
        out.to_parquet(snapshot / f"{name}.parquet", index=False)


def load(name: str, snapshot: Path = SNAPSHOT) -> pd.DataFrame:
    df = pd.read_parquet(snapshot / f"{name}.parquet")
    if "month" in df:
        df["month"] = pd.to_datetime(df["month"]).dt.to_period("M")
    return df


def connect(snapshot: Path = SNAPSHOT) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    for t in TABLES:
        path = snapshot / f"{t}.parquet"
        if path.exists():
            con.execute(f"CREATE VIEW {t} AS SELECT * FROM read_parquet('{path}')")
    return con
