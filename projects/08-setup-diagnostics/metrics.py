"""Trade-log metrics for the diagnostic dashboard. PnL is in index points."""

from __future__ import annotations

from datetime import date
from math import sqrt

import polars as pl

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]
REGIME_ORDER = ["Low", "Med", "High"]


def filter_trades(
    trades: pl.DataFrame,
    *,
    setups: list[str] | None = None,
    sessions: list[str] | None = None,
    atr_regimes: list[str] | None = None,
    trend_regimes: list[str] | None = None,
    directions: list[str] | None = None,
    days: list[str] | None = None,
    start: date | None = None,
    end: date | None = None,
) -> pl.DataFrame:
    """Apply sidebar filters. An empty list means the filter matches nothing."""
    if trades.is_empty():
        return trades
    frame = trades
    if setups is not None:
        frame = frame.filter(pl.col("setup_name").is_in(setups))
    if sessions is not None:
        frame = frame.filter(pl.col("session").is_in(sessions))
    if atr_regimes is not None:
        frame = frame.filter(pl.col("atr_regime").is_in(atr_regimes))
    if trend_regimes is not None:
        frame = frame.filter(pl.col("trend_regime").is_in(trend_regimes))
    if directions is not None:
        frame = frame.filter(pl.col("direction").is_in(directions))
    if days is not None:
        frame = frame.filter(pl.col("day_of_week").is_in(days))
    if start is not None:
        frame = frame.filter(pl.col("entry_time").dt.date() >= start)
    if end is not None:
        frame = frame.filter(pl.col("entry_time").dt.date() <= end)
    return frame


def kpis(trades: pl.DataFrame) -> dict[str, float | None]:
    """Net points, win rate, profit factor, expectancy in R, max drawdown, Sharpe."""
    empty = {
        "trades": 0,
        "net_pnl": 0.0,
        "win_rate": None,
        "profit_factor": None,
        "expectancy_r": None,
        "max_drawdown": None,
        "sharpe": None,
    }
    if trades.is_empty():
        return empty
    pnl = trades["pnl_net"].to_numpy()
    wins = pnl[pnl > 0].sum()
    losses = -pnl[pnl < 0].sum()
    equity = pnl.cumsum()
    peak = equity.cummax() if hasattr(equity, "cummax") else _cummax(equity)
    drawdown = float((peak - equity).max()) if len(equity) else None
    profit_factor = float(wins / losses) if losses > 0 else None
    sharpe = _sharpe(trades)
    return {
        "trades": int(trades.height),
        "net_pnl": float(pnl.sum()),
        "win_rate": float((pnl > 0).mean()),
        "profit_factor": profit_factor,
        "expectancy_r": float(trades["r_multiple"].mean()),
        "max_drawdown": drawdown,
        "sharpe": sharpe,
    }


def _cummax(values):
    import numpy as np

    return np.maximum.accumulate(values)


def _sharpe(trades: pl.DataFrame) -> float | None:
    """Annualized Sharpe of daily summed R. Needs at least two active days."""
    daily = trades.group_by(pl.col("exit_time").dt.date()).agg(pl.col("r_multiple").sum())
    if daily.height < 2:
        return None
    values = daily["r_multiple"]
    std = float(values.std())
    if std == 0.0 or std != std:
        return None
    return float(values.mean() / std * sqrt(252))


def equity_frame(trades: pl.DataFrame) -> pl.DataFrame:
    """Cumulative net points and drawdown, ordered by exit time."""
    if trades.is_empty():
        return pl.DataFrame({"exit_time": [], "equity": [], "drawdown": []})
    ordered = trades.sort("exit_time").select("exit_time", "pnl_net")
    equity = ordered["pnl_net"].cum_sum()
    peak = equity.cum_max()
    return ordered.with_columns(equity.alias("equity"), (equity - peak).alias("drawdown")).drop("pnl_net")


def by_setup(trades: pl.DataFrame) -> pl.DataFrame:
    if trades.is_empty():
        return pl.DataFrame()
    return (
        trades.group_by("setup_name")
        .agg(
            pl.len().alias("trades"),
            (pl.col("pnl_net") > 0).mean().alias("win_rate"),
            pl.col("r_multiple").mean().alias("avg_r"),
            pl.col("pnl_net").sum().alias("net_pnl"),
            pl.col("pnl_net").filter(pl.col("pnl_net") > 0).sum().alias("gross_win"),
            (-pl.col("pnl_net").filter(pl.col("pnl_net") < 0).sum()).alias("gross_loss"),
            pl.col("mae").mean().alias("avg_mae"),
            pl.col("mfe").mean().alias("avg_mfe"),
        )
        .with_columns(
            pl.when(pl.col("gross_loss") > 0)
            .then(pl.col("gross_win") / pl.col("gross_loss"))
            .otherwise(None)
            .alias("profit_factor")
        )
        .select("setup_name", "trades", "win_rate", "avg_r", "net_pnl", "profit_factor", "avg_mae", "avg_mfe")
        .sort("setup_name")
    )


def regime_pnl(trades: pl.DataFrame, column: str) -> pl.DataFrame:
    if trades.is_empty():
        return pl.DataFrame({"setup_name": [], column: [], "net_pnl": []})
    return (
        trades.group_by(["setup_name", column])
        .agg(pl.col("pnl_net").sum().alias("net_pnl"), pl.len().alias("trades"))
        .sort(["setup_name", column])
    )


def heatmap(trades: pl.DataFrame, metric: str) -> dict[str, object]:
    """Hour-of-day by weekday matrix. Missing cells stay null, not zero."""
    hours = trades["hour_of_day"].unique().sort().to_list() if not trades.is_empty() else []
    z: list[list[float | None]] = []
    text: list[list[str]] = []
    counts: list[list[int]] = []
    for hour in hours:
        row: list[float | None] = []
        labels: list[str] = []
        count_row: list[int] = []
        for day in WEEKDAYS:
            part = trades.filter((pl.col("hour_of_day") == hour) & (pl.col("day_of_week") == day))
            count_row.append(part.height)
            if part.is_empty():
                row.append(None)
                labels.append("")
                continue
            if metric == "win_rate":
                value = float((part["pnl_net"] > 0).mean())
                row.append(value)
                labels.append(f"{value:.0%}")
            else:
                value = float(part["r_multiple"].mean())
                row.append(value)
                labels.append(f"{value:.2f}")
        z.append(row)
        text.append(labels)
        counts.append(count_row)
    return {"hours": hours, "days": WEEKDAYS, "z": z, "text": text, "counts": counts}
