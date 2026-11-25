"""Loader contract: Massive columns, ET timestamps, and the file budget."""

from __future__ import annotations

import gzip
from datetime import date, datetime, timezone
from pathlib import Path

import polars as pl
import pytest

from data_loader import FileBudgetError, inspect_source, list_data_files, load_bars
from sample_data import write_sample

KNOWN_NS = 1_672_700_400_000_000_000  # 2023-01-02 18:00 America/New_York


def _ohlcv(**overrides: object) -> dict[str, object]:
    row = {
        "ticker": "NQH4",
        "session_end_date": date(2024, 6, 4),
        "window_start": 0,
        "open": 18000.0,
        "high": 18001.0,
        "low": 17999.0,
        "close": 18000.5,
        "volume": 10,
    }
    row.update(overrides)
    return row


def test_known_epoch_is_eighteen_hundred_et(tmp_path: Path) -> None:
    frame = pl.DataFrame([_ohlcv(window_start=KNOWN_NS, session_end_date=date(2023, 1, 3))])
    path = tmp_path / "one.parquet"
    frame.write_parquet(path)
    profile = inspect_source(path)
    assert profile["columns"][:3] == ["ticker", "session_end_date", "window_start"]
    bars, _meta = load_bars(path, warmup_days=0)
    stamp = bars["timestamp"][0]
    assert stamp.hour == 18
    assert stamp.minute == 0
    assert stamp.date() == date(2023, 1, 2)
    assert str(stamp.tzinfo) in {"America/New_York", "EST"} or "New_York" in str(stamp.tzinfo)


def test_edt_eighteen_hundred_and_spread_filter(tmp_path: Path) -> None:
    utc = datetime(2024, 6, 3, 22, 0, tzinfo=timezone.utc)
    ns = int(utc.timestamp()) * 1_000_000_000
    frame = pl.DataFrame(
        [
            _ohlcv(window_start=ns, ticker="NQM4", session_end_date=date(2024, 6, 4)),
            _ohlcv(window_start=ns, ticker="NQM4-NQU4", session_end_date=date(2024, 6, 4)),
            _ohlcv(window_start=ns, ticker="6AM9-6AH9", session_end_date=date(2024, 6, 4)),
        ]
    )
    path = tmp_path / "mixed.parquet"
    frame.write_parquet(path)
    bars, _meta = load_bars(path, warmup_days=0)
    assert bars.height == 1
    assert bars["ticker"][0] == "NQM4"
    stamp = bars["timestamp"][0]
    assert stamp.hour == 18
    assert stamp.utcoffset().total_seconds() == -4 * 3600


def test_derives_session_date_from_clock(tmp_path: Path) -> None:
    utc = datetime(2024, 1, 2, 23, 0, tzinfo=timezone.utc)  # 18:00 EST
    ns = int(utc.timestamp()) * 1_000_000_000
    row = _ohlcv(window_start=ns)
    del row["session_end_date"]
    path = tmp_path / "no_session.parquet"
    pl.DataFrame([row]).write_parquet(path)
    bars, _meta = load_bars(path, warmup_days=0)
    assert bars["session_end_date"][0] == date(2024, 1, 3)
    assert bars["session"][0] == "Overnight"


def test_daytime_session_labels_do_not_overflow(tmp_path: Path) -> None:
    """Hour is Int8. 9*60 must not wrap, or 09:45 is labeled Overnight."""
    path = write_sample(tmp_path / "sessions.parquet", sessions=2)
    bars, _meta = load_bars(path, warmup_days=0)
    at_open = bars.filter(
        (pl.col("timestamp").dt.hour() == 9) & (pl.col("timestamp").dt.minute() == 45)
    )
    at_mid = bars.filter(pl.col("timestamp").dt.hour() == 12)
    assert at_open["session"].unique().to_list() == ["NY Open"]
    assert at_mid["session"].unique().to_list() == ["Midday"]


def test_refuses_a_wide_raw_directory(tmp_path: Path) -> None:
    header = "ticker,window_start,open,high,low,close,volume\nNQH4,1,1,1,1,1,1\n"
    for index in range(MAX_PLUS := 9):
        target = tmp_path / f"2024-01-{index + 1:02d}.csv.gz"
        with gzip.open(target, "wt", encoding="utf-8") as handle:
            handle.write(header)
    with pytest.raises(FileBudgetError):
        list_data_files(tmp_path)


def test_resample_and_sample_profile(tmp_path: Path) -> None:
    path = write_sample(tmp_path / "sample.parquet", sessions=5)
    profile = inspect_source(path, n_rows=5)
    assert profile["columns"] == [
        "ticker",
        "session_end_date",
        "window_start",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]
    assert len(profile["preview"]) == 5
    one_min, _ = load_bars(path, warmup_days=0)
    five_min, _ = load_bars(path, warmup_days=0, every="5m")
    assert five_min.height < one_min.height
    assert five_min.height > 0
