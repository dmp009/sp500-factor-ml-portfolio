from factorml import alert


def test_alert_body():
    title, body = alert.issue("prices", "https://github.com/o/r/actions/runs/1", "Yahoo returned nothing", "2026-11")
    assert title == "Monthly refresh failed: 2026-11"
    assert "prices" in body and "https://github.com/o/r/actions/runs/1" in body and "Yahoo returned nothing" in body
    assert "Actions > monthly > Run workflow" in body


def test_alert_main_without_raw_dir(tmp_path, monkeypatch):
    """A job that fails before the pipeline runs has no data/raw/ yet; the alert must still be written."""
    raw = tmp_path / "raw"
    monkeypatch.setattr(alert, "RAW", raw)
    monkeypatch.setattr(alert, "ERROR_FILE", raw / "run_error.json")
    alert.main(["--run-url", "https://github.com/o/r/actions/runs/2"])
    assert (raw / "alert_title.txt").read_text().startswith("Monthly refresh failed")
    assert "the job failed before the pipeline started" in (raw / "alert_body.md").read_text()
