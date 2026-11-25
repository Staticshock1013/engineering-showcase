"""Massive client helpers and fixture-only download path."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import SecretStr

from quant_lab.data.cache import DataCache
from quant_lab.data.download import download_fixtures
from quant_lab.data.massive import (
    MassiveClient,
    MassiveConfigError,
    load_aggregates_fixture,
)

FIXTURES = Path(__file__).resolve().parents[1] / "data" / "fixtures"


def test_aggregates_fixture_normalizes_to_bars() -> None:
    bars = load_aggregates_fixture(FIXTURES / "nq_h6_1min_aggs.json", symbol="NQH6")
    assert len(bars) == 3
    assert bars["symbol"].unique().tolist() == ["NQH6"]
    assert bars["timestamp"].is_monotonic_increasing
    assert float(bars.iloc[0]["open"]) == 17800.0


def test_massive_client_requires_key_for_live_calls() -> None:
    client = MassiveClient(api_key=None)
    assert not client.has_credentials
    with pytest.raises(MassiveConfigError):
        client.list_contracts(product_code="NQ", date="2024-03-11")


def test_massive_client_does_not_expose_secret_in_repr() -> None:
    client = MassiveClient(api_key=SecretStr("super-secret-key-value"))
    text = repr(client)
    assert "super-secret-key-value" not in text


def test_download_fixtures_writes_cache(tmp_path: Path) -> None:
    cache = DataCache(tmp_path / "cache")
    written = download_fixtures(cache, fixtures_dir=FIXTURES)
    assert "nq_front_daily" in written
    assert "nq_h6_1min" in written
    assert "equity_spy" in written
    daily = cache.read_bars("nq_front_daily")
    assert len(daily) == 5
    assert cache.exists("nq_h6_1min")
