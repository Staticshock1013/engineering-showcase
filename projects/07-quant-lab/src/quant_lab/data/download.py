"""Download / import market data into the local cache.

Default mode is fixture-based (no network, no secrets). Live Massive
downloads require MASSIVE_API_KEY and are opt-in. Robinhood data is always
imported from a local export directory — never fetched via an unofficial API.

Options / SPY 0DTE premium series are intentionally out of scope here.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd

from quant_lab.config import Settings
from quant_lab.data.cache import DataCache
from quant_lab.data.massive import (
    RESOLUTION_1DAY,
    RESOLUTION_1MIN,
    MassiveClient,
    MassiveConfigError,
    load_aggregates_fixture,
    load_session_volumes_fixture,
)
from quant_lab.data.robinhood import RobinhoodLoader
from quant_lab.data.roll import build_continuous_series

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "data" / "fixtures"


def fixture_paths() -> dict[str, Path]:
    return {
        "nq_session_volumes": FIXTURES_DIR / "nq_session_volumes.json",
        "nq_h6_1min": FIXTURES_DIR / "nq_h6_1min_aggs.json",
        "equity_spy": FIXTURES_DIR / "equity_spy_sample.csv",
    }


def download_fixtures(cache: DataCache, *, fixtures_dir: Path | None = None) -> dict[str, Path]:
    """Materialize committed fixtures into the gitignored cache."""
    root = fixtures_dir or FIXTURES_DIR
    written: dict[str, Path] = {}

    sessions = load_session_volumes_fixture(root / "nq_session_volumes.json")
    continuous = build_continuous_series(sessions, back_adjust=False)
    daily = continuous.bars.rename(columns={}).copy()
    # Align to bar schema for cache.
    daily_bars = daily.loc[:, ["timestamp", "open", "high", "low", "close", "volume", "symbol"]]
    written["nq_front_daily"] = cache.write_bars("nq_front_daily", daily_bars)

    minute = load_aggregates_fixture(root / "nq_h6_1min_aggs.json", symbol="NQH6")
    written["nq_h6_1min"] = cache.write_bars(
        "nq_h6_1min",
        minute.loc[:, ["timestamp", "open", "high", "low", "close", "volume", "symbol"]],
    )

    # Keep a copy of raw fixture JSON beside the cache for roll debugging.
    raw_dir = cache.root / "raw_fixtures"
    raw_dir.mkdir(parents=True, exist_ok=True)
    for name in ("nq_session_volumes.json", "nq_h6_1min_aggs.json", "equity_spy_sample.csv"):
        src = root / name
        if src.exists():
            shutil.copy2(src, raw_dir / name)

    equity = pd.read_csv(root / "equity_spy_sample.csv")
    from quant_lab.data.robinhood import normalize_equity_frame

    spy = normalize_equity_frame(equity, default_symbol="SPY")
    written["equity_spy"] = cache.write_bars("equity_spy", spy)
    return written


def import_robinhood_exports(settings: Settings, cache: DataCache) -> dict[str, Path]:
    """Normalize local Robinhood CSV/Parquet exports into the cache."""
    if settings.robinhood_data_dir is None:
        raise FileNotFoundError("ROBINHOOD_DATA_DIR is not set")
    loader = RobinhoodLoader(settings.robinhood_data_dir)
    written: dict[str, Path] = {}
    for symbol in loader.list_symbols():
        bars = loader.load_symbol(symbol)
        written[symbol] = cache.write_bars(f"equity_{symbol.lower()}", bars)
    return written


def download_massive_live(
    settings: Settings,
    cache: DataCache,
    *,
    ticker: str,
    resolution: str,
    window_start_gte: str,
    window_start_lte: str | None = None,
) -> Path:
    """Opt-in live Massive aggregate download. Requires MASSIVE_API_KEY."""
    client = MassiveClient(
        api_key=settings.massive_api_key,
        base_url=settings.massive_base_url,
    )
    if not client.has_credentials:
        raise MassiveConfigError(
            "Refusing live download: MASSIVE_API_KEY is unset. "
            "Use --source fixtures until the secret is configured."
        )
    if resolution not in {RESOLUTION_1MIN, RESOLUTION_1DAY}:
        raise ValueError(f"unsupported resolution for lab downloads: {resolution}")
    bars = client.get_aggregates(
        ticker,
        resolution=resolution,
        window_start_gte=window_start_gte,
        window_start_lte=window_start_lte,
    )
    name = f"massive_{ticker}_{resolution}".replace("/", "_")
    cols = ["timestamp", "open", "high", "low", "close", "volume", "symbol"]
    return cache.write_bars(name, bars.loc[:, cols])
