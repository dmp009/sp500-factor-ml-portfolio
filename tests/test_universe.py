from pathlib import Path

import pandas as pd

from factorml import universe as u

FIX = Path(__file__).parent / "fixtures"
COMP = u.parse_components((FIX / "sp500_components_small.csv").read_text())


def months(*ms):
    return pd.PeriodIndex(list(ms), freq="M")


def members(month):
    m = u.membership(COMP, months(month))
    return set(m["ticker"])


def test_membership_uses_last_list_on_or_before_month_end():
    # EQIX joined on 2015-03-23: absent in the 2015-03-18 list, present at the March month-end
    assert "EQIX" in members("2015-03")
    assert "AVP" not in members("2015-03")  # removed on 2015-03-23
    assert "EQIX" not in set(COMP.loc[COMP["date"] == "2015-03-18", "ticker"])


def test_dual_class_two_members():
    assert {"GOOG", "GOOGL"} <= members("2014-04")


def test_rename_keeps_id():
    ids = u.security_ids(["FB", "META", "AAPL"])
    assert ids["FB"] == ids["META"] == "META" and ids["AAPL"] == "AAPL"


def test_member_count_band():
    assert 495 <= len(members("2022-06")) <= 510


def test_months_after_history_use_current_list():
    cur = u.parse_current((FIX / "sp500_current_small.html").read_text())
    m = u.membership(COMP, months("2022-06", "2030-01"), current=cur)
    assert set(m.loc[m["month"] == pd.Period("2030-01", "M"), "ticker"]) == set(cur["ticker"])


def test_parse_current_and_yahoo_symbol():
    cur = u.parse_current((FIX / "sp500_current_small.html").read_text())
    assert {"ticker", "name", "cik"} <= set(cur.columns)
    assert cur.loc[cur["ticker"] == "MMM", "cik"].iat[0] == "0000066740"
    assert u.yahoo_symbol("BRK.B") == "BRK-B"


def test_sector_of():
    assert u.sector_of(3571) == "Information Technology"
    assert u.sector_of(6022) == "Financials"
    assert u.sector_of(2000) == "Consumer Staples"
    assert u.sector_of(6798) == "Real Estate"  # REITs, not Financials
    assert u.sector_of(3711) == "Consumer Discretionary"  # motor vehicles
    assert u.sector_of(2834) == "Health Care"  # pharma, not Materials
    assert u.sector_of(9999) == "Other"
