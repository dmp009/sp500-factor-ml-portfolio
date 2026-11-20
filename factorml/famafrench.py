"""Fama-French 5 factors + momentum (Kenneth R. French data library), monthly, as decimals."""
from __future__ import annotations

import io
import re
import zipfile

import pandas as pd
import requests

from factorml.config import settings

NAMES = {"Mkt-RF": "mkt_rf", "SMB": "smb", "HML": "hml", "RMW": "rmw", "CMA": "cma", "RF": "rf", "Mom": "mom"}
MONTH_ROW = re.compile(r"^\s*(\d{6})\s*,(.*)$")


def parse_french_csv(text: str) -> pd.DataFrame:
    """Monthly block only (the annual block below it is ignored); percent -> decimal; index = month."""
    header, rows = None, []
    for line in text.splitlines():
        if "annual" in line.lower() and rows:
            break
        if line.strip().startswith(","):
            header = [NAMES.get(c.strip(), c.strip().lower()) for c in line.split(",")[1:]]
        elif (m := MONTH_ROW.match(line)) and header:
            rows.append([m.group(1)] + [float(x) for x in m.group(2).split(",")])
    df = pd.DataFrame(rows, columns=["month", *header])
    df["month"] = pd.PeriodIndex(df["month"], freq="M")
    df = df.set_index("month")
    return df.where(df > -99) / 100  # -99.99 / -999 mean missing


def factors(ff5_text: str, mom_text: str) -> pd.DataFrame:
    ff5, mom = parse_french_csv(ff5_text), parse_french_csv(mom_text)
    out = ff5.join(mom, how="inner")
    return out.reset_index()[["month", "mkt_rf", "smb", "hml", "rmw", "cma", "mom", "rf"]]


def _unzip_csv(content: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        return z.read(z.namelist()[0]).decode("latin-1")


def download() -> tuple[str, str]:
    src = settings()["sources"]
    texts = []
    for key in ("french_ff5", "french_mom"):
        r = requests.get(src[key], timeout=60)
        r.raise_for_status()
        texts.append(_unzip_csv(r.content))
    return texts[0], texts[1]
