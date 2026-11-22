"""Summary metrics for research backtests (no live trading claims)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from quant_lab.backtest.engine import BacktestResult


@dataclass(frozen=True)
class PerformanceSummary:
    """Compact performance snapshot. Always pair with cost assumptions."""

    bars: int
    gross_pnl: float
    net_pnl: float
    total_costs: float
    total_contracts_traded: float
    max_drawdown: float
    sharpe_per_bar: float
    cost_assumptions: dict[str, float]

    def as_dict(self) -> dict[str, float | int | dict[str, float]]:
        return {
            "bars": self.bars,
            "gross_pnl": self.gross_pnl,
            "net_pnl": self.net_pnl,
            "total_costs": self.total_costs,
            "total_contracts_traded": self.total_contracts_traded,
            "max_drawdown": self.max_drawdown,
            "sharpe_per_bar": self.sharpe_per_bar,
            "cost_assumptions": self.cost_assumptions,
        }


def max_drawdown(equity: pd.Series) -> float:
    """Peak-to-trough drawdown on the cumulative net equity curve (USD)."""
    if equity.empty:
        return 0.0
    running_max = equity.cummax()
    drawdown = equity - running_max
    return float(drawdown.min())


def sharpe_per_bar(net_pnl: pd.Series) -> float:
    """Mean/std of per-bar net PnL (not annualized — report bar frequency separately)."""
    clean = net_pnl.dropna()
    if len(clean) < 2:
        return 0.0
    std = float(clean.std(ddof=1))
    if std == 0.0:
        return 0.0
    return float(clean.mean() / std)


def summarize(result: BacktestResult) -> PerformanceSummary:
    ledger = result.ledger
    equity = ledger["equity"]
    return PerformanceSummary(
        bars=len(ledger),
        gross_pnl=result.gross_pnl,
        net_pnl=result.net_pnl,
        total_costs=result.total_costs,
        total_contracts_traded=float(ledger["contracts_traded"].sum()),
        max_drawdown=max_drawdown(equity),
        sharpe_per_bar=sharpe_per_bar(ledger["net_pnl"]),
        cost_assumptions=dict(result.cost_assumptions),
    )


def assert_costs_reduce_pnl(result: BacktestResult) -> None:
    """Sanity check used in tests: with any turnover, net < gross."""
    if result.ledger["contracts_traded"].sum() <= 0:
        return
    if not (result.net_pnl < result.gross_pnl - 1e-9):
        raise AssertionError("expected transaction costs to reduce net PnL vs gross")


def assert_finite_ledger(result: BacktestResult) -> None:
    nums = result.ledger.select_dtypes(include=[np.number])
    if not np.isfinite(nums.to_numpy()).all():
        raise AssertionError("ledger contains non-finite values")
