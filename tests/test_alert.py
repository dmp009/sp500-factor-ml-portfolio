from factorml import alert


def test_alert_body():
    title, body = alert.issue("prices", "https://github.com/o/r/actions/runs/1", "Yahoo returned nothing", "2026-11")
    assert title == "Monthly refresh failed: 2026-11"
    assert "prices" in body and "https://github.com/o/r/actions/runs/1" in body and "Yahoo returned nothing" in body
    assert "Actions > monthly > Run workflow" in body
