"""Backtest engine, cost model, and performance metrics (NQ futures research)."""

from quant_lab.backtest.costs import FuturesCostModel
from quant_lab.backtest.engine import BacktestResult, run_backtest
from quant_lab.backtest.lookahead import LookaheadError, assert_feature_uses_only_past
from quant_lab.backtest.metrics import PerformanceSummary, summarize

__all__ = [
    "BacktestResult",
    "FuturesCostModel",
    "LookaheadError",
    "PerformanceSummary",
    "assert_feature_uses_only_past",
    "run_backtest",
    "summarize",
]
