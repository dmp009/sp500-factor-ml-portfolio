from factorml.config import SNAPSHOT, model_params, settings


def test_settings_values():
    s = settings()
    assert s["portfolio"] == {"top_n": 50, "cost_bps_per_side": 10}
    assert s["calendar"]["first_feature_month"] == "2010-06"
    assert s["calendar"]["first_oos_month"] == "2013-01"
    assert s["gates"] == {"min_price_coverage": 0.95, "max_abs_monthly_return": 0.80,
                          "members_min": 495, "members_max": 510}


def test_paths_and_model_params():
    assert SNAPSHOT.name == "snapshot"
    assert "learning_rate" in model_params()
