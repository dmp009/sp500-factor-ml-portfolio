"""Paths and YAML config. Every path is relative to the repo root."""
from __future__ import annotations

from functools import cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data/snapshot"
RAW = ROOT / "data/raw"


@cache
def load(name: str) -> dict:
    return yaml.safe_load((ROOT / "config" / f"{name}.yaml").read_text(encoding="utf-8"))


def settings() -> dict:
    return load("settings")


def model_params() -> dict:
    return load("model")["params"]
