import pandas as pd
import pytest

from factorml import quality as q

M = pd.Period("2016-04", "M")
AFTER = pd.Timestamp("2016-05-02")


def case(n_members=500, n_prices=500, big=0.05, n_big=1):
    tickers = [f"T{i}" for i in range(n_members)]
    members = pd.DataFrame({"month": M, "ticker": tickers})
    rets = pd.DataFrame({"month": M, "ticker": tickers[:n_prices], "ret": 0.01})
    rets.loc[: n_big - 1, "ret"] = big
    feats = pd.DataFrame({"month": M, "ticker": tickers})
    return members, rets, feats


def test_all_pass():
    rows = q.gates(M, *case(), today=AFTER)
    assert all(ok for _, ok, _ in rows) and len(rows) == 5


def test_partial_batch_fails_coverage():
    with pytest.raises(q.GateError) as e:
        q.enforce(M, *case(n_prices=450), today=AFTER)
    assert e.value.gate == "price_coverage"


def test_crazy_return_fails():
    with pytest.raises(q.GateError) as e:
        q.enforce(M, *case(big=3.5), today=AFTER)  # +350% in a month: a data error
    assert e.value.gate == "max_abs_return"


def test_many_big_moves_fail_but_a_few_real_ones_pass():
    rows = q.enforce(M, *case(big=1.4, n_big=3), today=AFTER)  # e.g. SNDK +143% in 2026-01
    assert "T0" in {g: d for g, _, d in rows}["max_abs_return"]
    with pytest.raises(q.GateError):
        q.enforce(M, *case(big=0.9, n_big=4), today=AFTER)


def test_open_month_fails():
    with pytest.raises(q.GateError) as e:
        q.enforce(M, *case(), today=pd.Timestamp("2016-04-29"))
    assert e.value.gate == "month_closed"


def test_member_band():
    with pytest.raises(q.GateError) as e:
        q.enforce(M, *case(n_members=480, n_prices=480), today=AFTER)
    assert e.value.gate == "member_count"
