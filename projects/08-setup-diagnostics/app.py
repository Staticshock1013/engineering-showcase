"""Setup-diagnostics dashboard. Run with: streamlit run app.py"""

from __future__ import annotations

from datetime import date, timedelta

import plotly.graph_objects as go
import polars as pl
import streamlit as st
from plotly.subplots import make_subplots

from data_loader import inspect_source, load_bars, resolve_data_path, session_bounds
from metrics import REGIME_ORDER, by_setup, equity_frame, filter_trades, heatmap, kpis, regime_pnl
from strategy_engine import POINT_VALUE_USD, default_trades_path, run_setups, write_trades

PLOT_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=48, r=16, t=48, b=40),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
)


def _fmt_points(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:,.2f}"


def _fmt_ratio(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.2f}"


@st.cache_data(show_spinner="Loading bars and running placeholder setups…")
def cached_run(path: str, start_iso: str, end_iso: str, every: str) -> tuple[pl.DataFrame, dict, pl.DataFrame]:
    start = date.fromisoformat(start_iso)
    end = date.fromisoformat(end_iso)
    span = None if every == "1m" else every
    bars, meta = load_bars(path, start=start, end=end, every=span)
    trades = run_setups(bars)
    if not trades.is_empty():
        trades = trades.filter(
            (pl.col("entry_time").dt.date() >= start) & (pl.col("entry_time").dt.date() <= end)
        )
    write_trades(trades, default_trades_path())
    meta = dict(meta)
    meta["trade_rows"] = trades.height
    meta["trades_path"] = str(default_trades_path())
    return bars, meta, trades


def _options(frame: pl.DataFrame, column: str) -> list[str]:
    if frame.is_empty() or column not in frame.columns:
        return []
    return [str(value) for value in frame[column].drop_nulls().unique().sort().to_list()]


def _equity_figure(curve: pl.DataFrame) -> go.Figure:
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.72, 0.28],
        vertical_spacing=0.08,
    )
    if curve.is_empty():
        fig.update_layout(**PLOT_LAYOUT, title="Cumulative net points")
        return fig
    exit_time = curve["exit_time"].to_list()
    equity = curve["equity"].to_list()
    peak = curve["equity"].cum_max().to_list()
    drawdown = curve["drawdown"].to_list()
    fig.add_trace(
        go.Scatter(
            x=exit_time,
            y=peak,
            mode="lines",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=exit_time,
            y=equity,
            name="Cumulative net points",
            mode="lines",
            fill="tonexty",
            fillcolor="rgba(247, 118, 142, 0.28)",
            line=dict(color="#7aa2f7", width=2),
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=exit_time,
            y=drawdown,
            name="Drawdown (points)",
            mode="lines",
            fill="tozeroy",
            fillcolor="rgba(247, 118, 142, 0.35)",
            line=dict(color="#f7768e", width=1),
        ),
        row=2,
        col=1,
    )
    fig.update_yaxes(title_text="Cumulative net PnL (index points)", row=1, col=1)
    fig.update_yaxes(title_text="Drawdown (index points)", row=2, col=1)
    fig.update_xaxes(title_text="Exit time (America/New_York)", row=2, col=1)
    fig.update_layout(**PLOT_LAYOUT, title="Cumulative net points with drawdown")
    return fig


def _heatmap_figure(matrix: dict[str, object], title: str, zmid: float | None) -> go.Figure:
    fig = go.Figure(
        data=go.Heatmap(
            x=matrix["days"],
            y=[str(hour) for hour in matrix["hours"]],
            z=matrix["z"],
            text=matrix["text"],
            texttemplate="%{text}",
            colorscale=[[0.0, "#f7768e"], [0.5, "#3b4261"], [1.0, "#9ece6a"]],
            zmid=zmid,
            colorbar=dict(title="Win rate" if zmid == 0.5 else "Avg R"),
            hovertemplate="Hour %{y} ET · %{x}<br>value %{z}<extra></extra>",
        )
    )
    fig.update_layout(**PLOT_LAYOUT, title=title)
    fig.update_xaxes(title_text="Weekday (entry, America/New_York)")
    fig.update_yaxes(title_text="Hour of day (ET)", autorange="reversed")
    return fig


def _regime_figure(frame: pl.DataFrame, column: str, title: str) -> go.Figure:
    fig = go.Figure()
    if frame.is_empty():
        fig.update_layout(**PLOT_LAYOUT, title=title)
        return fig
    for setup in frame["setup_name"].unique().sort().to_list():
        part = frame.filter(pl.col("setup_name") == setup)
        order = {name: index for index, name in enumerate(REGIME_ORDER)}
        part = part.with_columns(pl.col(column).replace_strict(order, default=99).alias("_ord")).sort("_ord")
        fig.add_bar(name=setup, x=part[column].to_list(), y=part["net_pnl"].to_list())
    fig.update_layout(**PLOT_LAYOUT, barmode="group", title=title)
    fig.update_xaxes(title_text=column)
    fig.update_yaxes(title_text="Net PnL (index points)")
    return fig


def _scatter(trades: pl.DataFrame, x_col: str, title: str, x_title: str) -> go.Figure:
    fig = go.Figure()
    palette = {"Setup_A_Breakout": "#7aa2f7", "Setup_B_MeanReversion": "#e0af68"}
    if trades.is_empty():
        fig.update_layout(**PLOT_LAYOUT, title=title)
        return fig
    for setup in trades["setup_name"].unique().sort().to_list():
        part = trades.filter(pl.col("setup_name") == setup)
        fig.add_trace(
            go.Scatter(
                x=part[x_col].to_list(),
                y=part["pnl_net"].to_list(),
                mode="markers",
                name=setup,
                marker=dict(color=palette.get(setup, "#c0caf5"), size=9, opacity=0.85),
                text=part["trade_id"].to_list(),
                hovertemplate="%{text}<br>" + x_title + " %{x:.2f}<br>PnL %{y:.2f}<extra>" + setup + "</extra>",
            )
        )
    fig.add_hline(y=0, line_width=1, line_color="#565f89")
    fig.update_layout(**PLOT_LAYOUT, title=title)
    fig.update_xaxes(title_text=x_title)
    fig.update_yaxes(title_text="Net PnL (index points)")
    return fig


def _candle_figure(bars: pl.DataFrame, trade: dict[str, object]) -> go.Figure:
    entry = trade["entry_time"]
    exit_ = trade["exit_time"]
    window = bars.filter(
        (pl.col("timestamp") >= entry - pl.duration(minutes=45))
        & (pl.col("timestamp") <= exit_ + pl.duration(minutes=20))
    )
    fig = go.Figure()
    if window.is_empty():
        fig.update_layout(**PLOT_LAYOUT, title=str(trade["trade_id"]))
        return fig
    fig.add_trace(
        go.Candlestick(
            x=window["timestamp"].to_list(),
            open=window["open"].to_list(),
            high=window["high"].to_list(),
            low=window["low"].to_list(),
            close=window["close"].to_list(),
            name="Price",
            increasing_line_color="#9ece6a",
            decreasing_line_color="#f7768e",
        )
    )
    if "ema_15m" in window.columns:
        fig.add_trace(
            go.Scatter(
                x=window["timestamp"].to_list(),
                y=window["ema_15m"].to_list(),
                name="15m EMA",
                mode="lines",
                line=dict(color="#bb9af7", width=1),
            )
        )
    if "vwap" in window.columns:
        fig.add_trace(
            go.Scatter(
                x=window["timestamp"].to_list(),
                y=window["vwap"].to_list(),
                name="Session VWAP",
                mode="lines",
                line=dict(color="#7dcfff", width=1),
            )
        )
    for y_value, label, color in (
        (trade["entry_price"], "Entry", "#7aa2f7"),
        (trade["exit_price"], "Exit", "#e0af68"),
        (trade["stop_price"], "Stop", "#f7768e"),
        (trade["target_price"], "Target", "#9ece6a"),
    ):
        fig.add_hline(y=y_value, line_dash="dot", line_color=color, annotation_text=label, annotation_font_color=color)
    fig.add_trace(
        go.Scatter(
            x=[entry, exit_],
            y=[trade["entry_price"], trade["exit_price"]],
            mode="markers",
            name="Entry / exit",
            marker=dict(size=11, color=["#7aa2f7", "#e0af68"], symbol=["circle", "diamond"]),
        )
    )
    fig.update_layout(
        **PLOT_LAYOUT,
        title=f"{trade['trade_id']} · {trade['direction']} · {trade['exit_reason']}",
        xaxis_rangeslider_visible=False,
    )
    fig.update_xaxes(title_text="Bar time (America/New_York)")
    fig.update_yaxes(title_text="Price (index points)")
    return fig


def _overview(filtered: pl.DataFrame) -> None:
    stats = kpis(filtered)
    cols = st.columns(6)
    cols[0].metric("Net PnL (points)", _fmt_points(stats["net_pnl"]))
    cols[1].metric("Win rate", "—" if stats["win_rate"] is None else f"{stats['win_rate']:.1%}")
    cols[2].metric("Profit factor", _fmt_ratio(stats["profit_factor"]))
    cols[3].metric("Expectancy (R)", _fmt_ratio(stats["expectancy_r"]))
    cols[4].metric("Max drawdown (points)", _fmt_points(stats["max_drawdown"]))
    cols[5].metric("Sharpe (daily R)", _fmt_ratio(stats["sharpe"]))
    net = stats["net_pnl"] or 0.0
    st.caption(
        f"{stats['trades']} trades · ${net * POINT_VALUE_USD:,.0f} at ${POINT_VALUE_USD:.0f}/point, "
        "before scaling. Sharpe is the annualized mean/std of daily summed R, not a return series. "
        "Round-trip cost is 0.75 points ($2.50 commission per side plus 1 tick slip per side)."
    )
    st.plotly_chart(_equity_figure(equity_frame(filtered)), width="stretch")


def _diagnostics(filtered: pl.DataFrame) -> None:
    st.subheader("Performance by setup")
    summary = by_setup(filtered)
    if summary.is_empty():
        st.info("No trades in this filter.")
        return
    display = summary.with_columns(
        (pl.col("win_rate") * 100).round(1).alias("win_rate_pct"),
        pl.col("avg_r").round(3),
        pl.col("net_pnl").round(2),
        pl.col("profit_factor").round(2),
        pl.col("avg_mae").round(2),
        pl.col("avg_mfe").round(2),
    ).select("setup_name", "trades", "win_rate_pct", "avg_r", "net_pnl", "profit_factor", "avg_mae", "avg_mfe")
    st.dataframe(display.to_pandas(), hide_index=True, width="stretch")
    st.caption("win_rate_pct is the share of trades with pnl_net > 0. avg_r is the mean R-multiple after costs.")

    left, right = st.columns(2)
    win_matrix = heatmap(filtered, "win_rate")
    r_matrix = heatmap(filtered, "avg_r")
    with left:
        st.plotly_chart(
            _heatmap_figure(win_matrix, "Win rate by entry hour and weekday", 0.5),
            width="stretch",
        )
    with right:
        st.plotly_chart(
            _heatmap_figure(r_matrix, "Average R by entry hour and weekday", 0.0),
            width="stretch",
        )
    st.caption(
        "Cells with no trades are blank. Hours are America/New_York at entry. "
        "A red cluster is a time bucket that loses under the current rules."
    )
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(
            _regime_figure(
                regime_pnl(filtered, "atr_regime"),
                "atr_regime",
                "Net points by volatility regime",
            ),
            width="stretch",
        )
    with c2:
        st.plotly_chart(
            _regime_figure(
                regime_pnl(filtered, "trend_regime"),
                "trend_regime",
                "Net points by 15-minute EMA regime",
            ),
            width="stretch",
        )
    st.caption(
        "atr_regime is the tercile of that session's 08:00–09:30 ET high-low range "
        "versus the trailing 60 sessions. It is known before the 09:45 breakout. "
        "trend_regime is close versus the last completed 15-minute 20-EMA at entry: above or below."
    )


def _excursions(filtered: pl.DataFrame) -> None:
    st.caption(
        "MAE and MFE are positive point distances while the trade is open. "
        "Losses stacked on a small MAE mean the stop is being hit before the idea plays out. "
        "Losses with a large MFE mean price went far enough to pay and then gave it back."
    )
    left, right = st.columns(2)
    with left:
        st.plotly_chart(
            _scatter(filtered, "mae", "MAE versus net points", "MAE (points, adverse)"),
            width="stretch",
        )
    with right:
        st.plotly_chart(
            _scatter(filtered, "mfe", "MFE versus net points", "MFE (points, favorable)"),
            width="stretch",
        )


def _inspector(filtered: pl.DataFrame, bars: pl.DataFrame) -> None:
    if filtered.is_empty():
        st.info("No trades in this filter.")
        return
    ordered = filtered.sort("entry_time", descending=True)
    table = ordered.select(
        "trade_id",
        "setup_name",
        "direction",
        "entry_time",
        "exit_time",
        "entry_price",
        "exit_price",
        "pnl_net",
        "r_multiple",
        "session",
        "atr_regime",
        "trend_regime",
        "mae",
        "mfe",
        "exit_reason",
    )
    pandas_table = table.to_pandas()
    event = st.dataframe(
        pandas_table,
        hide_index=True,
        width="stretch",
        on_select="rerun",
        selection_mode="single-row",
        key="trade_table",
    )
    trade_ids = table["trade_id"].to_list()
    selected_rows = list(getattr(getattr(event, "selection", None), "rows", []) or [])
    if selected_rows:
        default_id = trade_ids[selected_rows[0]]
    else:
        default_id = trade_ids[0]
    choice = st.selectbox("Trade", trade_ids, index=trade_ids.index(default_id))
    row = ordered.filter(pl.col("trade_id") == choice).row(0, named=True)
    # Candles need feature columns. Rebuild them for the slice's parent frame.
    from strategy_engine import prepare_features

    featured = prepare_features(bars)
    st.plotly_chart(_candle_figure(featured, row), width="stretch")
    st.caption(
        f"Stop {row['stop_price']:.2f} · target {row['target_price']:.2f} · "
        f"risk {row['risk_points']:.2f} points · cost {row['commission_slippage']:.2f} points · "
        f"{row['symbol']} · {row['session']} · vol {row['atr_regime']} · trend {row['trend_regime']}"
    )


def main() -> None:
    st.set_page_config(page_title="Setup diagnostics", layout="wide")
    st.title("Setup diagnostics")
    st.caption("Placeholder NQ breakout and VWAP-fade rules on 1-minute bars. Research only. Not a live system.")

    default_path, default_source = resolve_data_path()
    with st.sidebar:
        st.header("Data")
        path = st.text_input("Bars path", value=str(default_path))
        every = st.selectbox("Execution bars", ["1m", "5m", "15m"], index=0)
        try:
            lo, hi = session_bounds(path)
        except Exception as exc:  # shown below; keep the widgets usable
            st.error(str(exc))
            return
        if (hi - lo).days > 120:
            lo_default = hi - timedelta(days=90)
        else:
            lo_default = lo
        picked = st.date_input("Session range", value=(lo_default, hi), min_value=lo, max_value=hi)
        if isinstance(picked, tuple) and len(picked) == 2:
            start, end = picked
        else:
            start, end = lo_default, hi
        st.caption(
            "The loader reads warmup bars before the start date and drops trades outside this range. "
            "It will not scan a directory of raw daily CME files."
        )

    try:
        bars, meta, trades = cached_run(path, start.isoformat(), end.isoformat(), every)
    except Exception as exc:
        st.error(str(exc))
        return

    source_label = "Synthetic sample" if meta.get("synthetic") or default_source == "synthetic" else "Local file"
    st.caption(
        f"{source_label} · {meta['rows']:,} bars · {meta['session_min']} → {meta['session_max']} · "
        f"{', '.join(meta['tickers'])} · trades written to `{meta['trades_path']}`"
    )
    if meta.get("synthetic"):
        st.warning(
            "These bars are fictional NQ minute data generated so the dashboard runs without the Mac "
            "flat files. Point the path at nq_front_1m_2023_2026.parquet when you are on that machine."
        )
    if meta["rows"] > 250_000:
        st.warning(f"Loaded {meta['rows']:,} bars. Narrow the session range if the app feels heavy.")

    with st.expander("Source profile (first rows)"):
        try:
            profile = inspect_source(path, n_rows=5)
        except Exception as exc:
            st.write(str(exc))
        else:
            st.write({"columns": profile["columns"], "dtypes": profile["dtypes"], "files": profile["file_count"]})
            st.dataframe(pl.DataFrame(profile["preview"]).to_pandas(), hide_index=True, width="stretch")

    with st.sidebar:
        st.header("Filters")
        setup_options = _options(trades, "setup_name") or ["Setup_A_Breakout", "Setup_B_MeanReversion"]
        session_options = _options(trades, "session") or ["NY Open", "Midday", "Close"]
        atr_options = _options(trades, "atr_regime") or REGIME_ORDER
        trend_options = _options(trades, "trend_regime") or ["above", "below"]
        direction_options = _options(trades, "direction") or ["Long", "Short"]
        day_options = [day for day in ["Mon", "Tue", "Wed", "Thu", "Fri"] if day in set(_options(trades, "day_of_week"))]
        if not day_options:
            day_options = ["Mon", "Tue", "Wed", "Thu", "Fri"]
        setups = st.multiselect("Setup", setup_options, default=setup_options)
        sessions = st.multiselect("Session", session_options, default=session_options)
        atrs = st.multiselect("ATR regime", atr_options, default=atr_options)
        trends = st.multiselect("Trend regime", trend_options, default=trend_options)
        directions = st.multiselect("Direction", direction_options, default=direction_options)
        days = st.multiselect("Day of week", day_options, default=day_options)

    filtered = filter_trades(
        trades,
        setups=setups,
        sessions=sessions,
        atr_regimes=atrs,
        trend_regimes=trends,
        directions=directions,
        days=days,
        start=start,
        end=end,
    )

    overview, diagnostics, excursions, inspector = st.tabs(
        ["Overview", "Setup failure diagnostics", "MAE / MFE", "Trade inspector"]
    )
    with overview:
        _overview(filtered)
    with diagnostics:
        _diagnostics(filtered)
    with excursions:
        _excursions(filtered)
    with inspector:
        _inspector(filtered, bars)


if __name__ == "__main__":
    main()
