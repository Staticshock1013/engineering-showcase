"""Smoke tests for the quant-lab scaffold."""

from __future__ import annotations

from pathlib import Path

from quant_lab import __version__


def test_version_is_semver_like() -> None:
    parts = __version__.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)


def test_package_layout_exists() -> None:
    root = Path(__file__).resolve().parents[1]
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
        assert (root / rel).exists(), f"missing {rel}"


def test_env_example_has_no_secret_values() -> None:
    text = (Path(__file__).resolve().parents[1] / ".env.example").read_text(encoding="utf-8")
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        _, _, value = stripped.partition("=")
        # Allow non-secret defaults (URLs, paths, dates, symbol roots).
        assert "sk-" not in value.lower()
        assert "password" not in value.lower() or value == ""
