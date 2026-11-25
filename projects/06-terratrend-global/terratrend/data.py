"""Fixture loading and validation."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from .registry import INDICATOR_REGISTRY

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "synthetic_observations.csv"
REQUIRED_COLUMNS = {
    "label",
    "region",
    "latitude",
    "longitude",
    "month",
    "indicator",
    "value",
    "baseline",
    "source",
}


def load_observations(path: Path = FIXTURE_PATH) -> list[dict[str, Any]]:
    """Load labeled synthetic observations and reject malformed records."""
    with path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    if not rows or set(rows[0]) != REQUIRED_COLUMNS:
        raise ValueError("Fixture must contain exactly the required columns.")

    observations = []
    for row in rows:
        if row["label"] != "SYNTHETIC — NOT REAL EARTH OBSERVATION DATA":
            raise ValueError("Every fixture row must carry the synthetic-data label.")
        if row["indicator"] not in INDICATOR_REGISTRY:
            raise ValueError(f"Unknown indicator: {row['indicator']}")
        if row["source"] != "Deterministic fixture":
            raise ValueError("Fixture source must identify deterministic fixture data.")
        observations.append(
            {
                **row,
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
                "value": float(row["value"]),
                "baseline": float(row["baseline"]),
            }
        )
    return observations
