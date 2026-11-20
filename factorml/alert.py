"""Turn a failed monthly run into a GitHub issue (title + body). The workflow opens the issue,
or comments on the open one, with the `gh` CLI; the next successful run closes it."""
from __future__ import annotations

import argparse
import json

import pandas as pd

from factorml.config import RAW

ERROR_FILE = RAW / "run_error.json"


def issue(step: str, run_url: str, error: str, month: str | None = None) -> tuple[str, str]:
    month = month or str(pd.Timestamp.today().to_period("M") - 1)
    title = f"Monthly refresh failed: {month}"
    body = "\n".join([
        f"The scheduled refresh for **{month}** stopped at step **`{step}`**. Nothing was written: the live",
        "portfolio and the dashboard still show the previous month.",
        "",
        "**Error**",
        "```",
        error.strip()[-3000:],
        "```",
        f"**Run log:** {run_url}",
        "",
        ("**What to do:** if the cause was temporary (Yahoo or SEC throttling, a network error), re-run: "
        "Actions > monthly > Run workflow. If a quality gate failed, check the data first; the gate message "
        "above says which check and by how much."),
        "",
        "This issue closes itself after the next successful run.",
    ])
    return title, body


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Write the alert issue title and body for a failed run")
    ap.add_argument("--run-url", required=True)
    a = ap.parse_args(argv)
    info = json.loads(ERROR_FILE.read_text()) if ERROR_FILE.exists() else {
        "step": "unknown", "error": "the job failed before the pipeline started", "month": None}
    title, body = issue(info["step"], a.run_url, info["error"], info.get("month"))
    (RAW / "alert_title.txt").write_text(title)
    (RAW / "alert_body.md").write_text(body)
    print(title)


if __name__ == "__main__":
    main()
