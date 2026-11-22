"""Smoke tests for the quant-lab scaffold."""

from __future__ import annotations

from pathlib import Path

from quant_lab import __version__

ROOT = Path(__file__).resolve().parents[1]


def test_version_is_semver_like() -> None:
    parts = __version__.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)


def test_package_layout_exists() -> None:
    for rel in (
        "src/quant_lab/data",
        "src/quant_lab/features",
        "src/quant_lab/backtest",
        "src/quant_lab/models",
        "src/quant_lab/analysis",
        "experiments",
        "data/fixtures",
        ".env.example",
    ):
        assert (ROOT / rel).exists(), f"missing {rel}"


def test_env_example_keeps_secrets_blank() -> None:
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "ROBINHOOD_DATA_DIR=" in text
    assert "MASSIVE_API_KEY=" in text
    assert "ROBINHOOD_PASSWORD" not in text
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        if key.endswith("API_KEY") or key.endswith("PASSWORD"):
            assert value == "", f"{key} must be blank in .env.example"
