"""Front-month roll: highest session volume wins."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from quant_lab.data.massive import load_session_volumes_fixture
from quant_lab.data.roll import build_continuous_series, detect_rolls, select_front_month

FIXTURES = Path(__file__).resolve().parents[1] / "data" / "fixtures"


def test_select_front_month_picks_highest_volume() -> None:
    sessions = load_session_volumes_fixture(FIXTURES / "nq_session_volumes.json")
    front = select_front_month(sessions)
    by_date = dict(zip(front["session_end_date"], front["ticker"], strict=True))
    assert by_date["2024-03-11"] == "NQH6"
    assert by_date["2024-03-12"] == "NQH6"
    assert by_date["2024-03-13"] == "NQH6"
    assert by_date["2024-03-14"] == "NQM6"
    assert by_date["2024-03-15"] == "NQM6"


def test_detect_rolls_emits_single_switch() -> None:
    sessions = load_session_volumes_fixture(FIXTURES / "nq_session_volumes.json")
    front = select_front_month(sessions)
    rolls = detect_rolls(front)
    assert len(rolls) == 1
    assert rolls[0].session_end_date == "2024-03-14"
    assert rolls[0].from_ticker == "NQH6"
    assert rolls[0].to_ticker == "NQM6"


def test_continuous_series_unadjusted_keeps_contract_closes() -> None:
    sessions = load_session_volumes_fixture(FIXTURES / "nq_session_volumes.json")
    series = build_continuous_series(sessions, back_adjust=False)
    assert not series.adjusted
    assert len(series.bars) == 5
    assert list(series.bars["symbol"]) == ["NQH6", "NQH6", "NQH6", "NQM6", "NQM6"]
    # Unadjusted: roll-day close is the new contract close (jump expected).
    roll_row = series.bars.loc[series.bars["session_end_date"] == "2024-03-14"].iloc[0]
    assert float(roll_row["close"]) == 17820.0


def test_back_adjust_shifts_history_by_roll_gap() -> None:
    sessions = load_session_volumes_fixture(FIXTURES / "nq_session_volumes.json")
    raw = build_continuous_series(sessions, back_adjust=False)
    adj = build_continuous_series(sessions, back_adjust=True)
    assert adj.adjusted
    roll = adj.rolls[0]
    gap = roll.to_close - roll.from_close
    # Sessions before the roll should be shifted by the gap; roll day onward unchanged.
    pre = adj.bars["session_end_date"] < roll.session_end_date
    pd.testing.assert_series_equal(
        adj.bars.loc[pre, "close"].reset_index(drop=True),
        (raw.bars.loc[pre, "close"] + gap).reset_index(drop=True),
        check_names=False,
    )
    post = ~pre
    pd.testing.assert_series_equal(
        adj.bars.loc[post, "close"].reset_index(drop=True),
        raw.bars.loc[post, "close"].reset_index(drop=True),
        check_names=False,
    )


def test_volume_tie_breaks_by_ticker_ascending() -> None:
    sessions = pd.DataFrame(
        [
            {
                "session_end_date": "2024-01-02",
                "ticker": "NQM6",
                "volume": 100,
                "open": 1,
                "high": 1,
                "low": 1,
                "close": 1,
            },
            {
                "session_end_date": "2024-01-02",
                "ticker": "NQH6",
                "volume": 100,
                "open": 1,
                "high": 1,
                "low": 1,
                "close": 1,
            },
        ]
    )
    front = select_front_month(sessions)
    assert front.iloc[0]["ticker"] == "NQH6"
