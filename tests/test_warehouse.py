import pandas as pd

from factorml import warehouse as wh


def test_views_exist_and_months_round_trip(tmp_path):
    m = pd.Period("2016-04", "M")
    tables = {t: pd.DataFrame({"month": [m], "ticker": ["A"], "x": [1.0]}) for t in wh.TABLES}
    wh.save(tables, tmp_path)
    con = wh.connect(tmp_path)
    for t in wh.TABLES:
        assert con.execute(f"SELECT count(*) FROM {t}").fetchone()[0] == 1
    assert wh.load("fact_features", tmp_path)["month"].iat[0] == m
