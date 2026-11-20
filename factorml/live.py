"""The live track record is append-only: a month, once recorded, never changes."""
from __future__ import annotations

import pandas as pd


def append(existing: pd.DataFrame, new_rows: pd.DataFrame) -> pd.DataFrame:
    """Existing rows + new months. Re-sending an identical month is a no-op; a different one raises."""
    if existing is None or existing.empty:
        return new_rows.reset_index(drop=True)
    old = existing.reset_index(drop=True)
    seen = new_rows[new_rows["month"].isin(old["month"])]
    for _, row in seen.iterrows():
        before = old[old["month"] == row["month"]].iloc[0]
        same = all((pd.isna(before[c]) and pd.isna(row[c])) or before[c] == row[c] for c in new_rows.columns)
        if not same:
            raise ValueError(f"live record for {row['month']} already exists with different content")
    fresh = new_rows[~new_rows["month"].isin(old["month"])]
    return pd.concat([old, fresh], ignore_index=True) if len(fresh) else old
