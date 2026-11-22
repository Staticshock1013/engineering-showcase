"""Vectorized NQ futures backtest engine (research only).

Execution rule (no lookahead):
  - ``signal[t]`` is formed from information available at the close of bar ``t``.
  - Position held over bar ``t+1`` equals ``signal[t]`` (fill at next bar).
  - Gross PnL accrues from close-to-close point changes while the position is held.
  - Transaction costs are charged on absolute position changes when the new
    position takes effect (bar ``t+1``).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import pandas as pd

from quant_lab.backtest.costs import FuturesCostModel
from quant_lab.backtest.lookahead import shift_signal_for_execution
from quant_lab.data.schema import BAR_COLUMNS


@dataclass(frozen=True)
class BacktestResult:
    """Per-bar ledger plus cost assumptions used for the run."""

    ledger: pd.DataFrame
    cost_assumptions: dict[str, float]
    contracts: float

    @property
    def net_pnl(self) -> float:
        return float(self.ledger["net_pnl"].sum())

    @property
    def gross_pnl(self) -> float:
        return float(self.ledger["gross_pnl"].sum())

    @property
    def total_costs(self) -> float:
        return float(self.ledger["cost_usd"].sum())


def _validate_bars(bars: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in BAR_COLUMNS if c not in bars.columns]
    if missing:
        raise ValueError(f"bars missing columns: {missing}")
    if bars.empty:
        raise ValueError("bars must be non-empty")
    out = bars.sort_values("timestamp").reset_index(drop=True).copy()
    if not out["timestamp"].is_monotonic_increasing:
        raise ValueError("timestamps must be strictly sortable ascending")
    if out["timestamp"].duplicated().any():
        raise ValueError("duplicate timestamps are not allowed")
    return out


def run_backtest(
    bars: pd.DataFrame,
    signal: pd.Series | Sequence[float],
    *,
    cost_model: FuturesCostModel | None = None,
    contracts: float = 1.0,
) -> BacktestResult:
    """Run a vectorized NQ-style futures backtest.

    Parameters
    ----------
    bars:
        OHLCV frame with the lab bar schema (NQ front-month or single contract).
    signal:
        Desired position in contracts *units* after each bar close
        (e.g. -1, 0, +1). Length must match ``bars``.
    cost_model:
        Explicit commission + slippage assumptions (defaults to NQ-sized model).
    contracts:
        Multiplier applied to the signal (number of contracts per unit signal).
    """
    if contracts <= 0:
        raise ValueError("contracts must be positive")
    model = cost_model or FuturesCostModel()
    frame = _validate_bars(bars)
    sig = pd.Series(signal, index=frame.index, dtype=float)
    if len(sig) != len(frame):
        raise ValueError("signal length must match bars")

    position = shift_signal_for_execution(sig) * float(contracts)
    point_change = frame["close"].diff().fillna(0.0)
    gross_pnl = position * point_change * model.point_value

    # Turnover when the new position becomes active (same bar as position).
    prior_position = position.shift(1).fillna(0.0)
    traded = (position - prior_position).abs()
    cost_usd = traded.map(model.cost_for_trade)
    net_pnl = gross_pnl - cost_usd

    ledger = pd.DataFrame(
        {
            "timestamp": frame["timestamp"],
            "symbol": frame["symbol"],
            "close": frame["close"],
            "signal": sig.to_numpy(),
            "position": position.to_numpy(),
            "point_change": point_change.to_numpy(),
            "gross_pnl": gross_pnl.to_numpy(),
            "contracts_traded": traded.to_numpy(),
            "cost_usd": cost_usd.to_numpy(),
            "net_pnl": net_pnl.to_numpy(),
            "equity": net_pnl.cumsum().to_numpy(),
        }
    )
    return BacktestResult(
        ledger=ledger,
        cost_assumptions=model.as_assumptions(),
        contracts=float(contracts),
    )
