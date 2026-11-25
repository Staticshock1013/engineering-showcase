"""Lazy loader for Massive CME minute files and the front-month parquet.

Reads one parquet, one gzip, or a small directory. Refuses a folder of raw
daily files so a dashboard session cannot pull the full CME tree into RAM.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import date, timedelta
from pathlib import Path

import polars as pl

from sample_data import MANIFEST_NAME, write_sample

# Front-month file on the Mac inventory. Absent in cloud sessions.
MAC_FRONT_MONTH = Path(
    "/Users/zelly/market-takeover/backtests/stop-regime-v1/data/nq_front_1m_2023_2026.parquet"
)
PROJECT_DIR = Path(__file__).resolve().parent
SAMPLE_PATH = PROJECT_DIR / "data" / "sample_nq_1m.parquet"

# Four NQ yearly gzips are fine. A year of raw CME days is not.
MAX_FILES = 8
NQ_OUTRIGHT = r"^NQ[HMUZ]\d$"

OHLCV = ("open", "high", "low", "close", "volume")
TIME_ALIASES = {
    "window_start": "window_start",
    "timestamp": "timestamp",
    "ts": "ts",
}
SESSION_ALIASES = {
    "session_end_date": "session_end_date",
    "session_date": "session_end_date",
}
TICKER_ALIASES = {"ticker": "ticker", "symbol": "ticker"}


class SchemaError(ValueError):
    """Raised when a file does not carry the Massive OHLCV contract."""


class FileBudgetError(RuntimeError):
    """Raised when a path would scan more files than the dashboard allows."""


def session_expr(timestamp: str = "timestamp") -> pl.Expr:
    """CME-flavored session label in America/New_York.

    Hour is Int8. Multiply only after widening, or 9*60 overflows and every
    daytime bar is labeled Overnight.
    """
    hour = pl.col(timestamp).dt.hour().cast(pl.Int32)
    minute = pl.col(timestamp).dt.minute().cast(pl.Int32)
    minutes = hour * 60 + minute
    return (
        pl.when((hour >= 18) | (minutes < 8 * 60))
        .then(pl.lit("Overnight"))
        .when(minutes < 9 * 60 + 30)
        .then(pl.lit("Pre-market"))
        .when(minutes < 11 * 60)
        .then(pl.lit("NY Open"))
        .when(minutes < 14 * 60)
        .then(pl.lit("Midday"))
        .when(minutes < 17 * 60)
        .then(pl.lit("Close"))
        .otherwise(pl.lit("Halt"))
        .alias("session")
    )


def day_name_expr(timestamp: str = "timestamp") -> pl.Expr:
    """Weekday abbreviation. Polars weekday is Monday=1 .. Sunday=7."""
    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    expr = pl.lit(None, dtype=pl.String)
    for index, name in enumerate(names, start=1):
        expr = pl.when(pl.col(timestamp).dt.weekday() == index).then(pl.lit(name)).otherwise(expr)
    return expr.alias("day_of_week")


def resolve_data_path(explicit: str | None = None) -> tuple[Path, str]:
    """Pick an explicit path, SETUP_DATA_PATH, the Mac parquet, or the sample.

    Returns the path and a source tag: explicit, env, front_month, or synthetic.
    """
    if explicit:
        path = Path(explicit).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"data path does not exist: {path}")
        return path, "explicit"
    env = os.environ.get("SETUP_DATA_PATH")
    if env:
        path = Path(env).expanduser()
        if path.exists():
            return path, "env"
        raise FileNotFoundError(f"SETUP_DATA_PATH does not exist: {path}")
    if MAC_FRONT_MONTH.exists():
        return MAC_FRONT_MONTH, "front_month"
    if not SAMPLE_PATH.exists():
        write_sample(SAMPLE_PATH)
    return SAMPLE_PATH, "synthetic"


def source_is_synthetic(path: Path) -> bool:
    manifest = path.with_name(MANIFEST_NAME) if path.is_file() else path / MANIFEST_NAME
    if not manifest.exists():
        return False
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return bool(payload.get("synthetic"))


def _is_bar_file(path: Path) -> bool:
    name = path.name
    if name.startswith("."):
        return False
    return path.suffix == ".parquet" or name.endswith(".csv.gz") or name.endswith(".csv")


def list_data_files(path: Path) -> list[Path]:
    """Expand a file, directory, or glob into data files, enforcing the budget."""
    if any(char in str(path) for char in "*?["):
        files = sorted(Path(match) for match in _glob(str(path)))
    elif path.is_file():
        files = [path]
    elif path.is_dir():
        files = sorted(
            child
            for child in path.rglob("*")
            if child.is_file() and _is_bar_file(child)
        )
    else:
        raise FileNotFoundError(path)
    files = [child for child in files if _is_bar_file(child) and child.stat().st_size > 0]
    if not files:
        raise FileNotFoundError(f"no parquet or csv.gz files under {path}")
    if len(files) > MAX_FILES and os.environ.get("SETUP_ALLOW_WIDE_SCAN") != "1":
        raise FileBudgetError(
            f"Refusing to scan {len(files)} files under {path}. "
            "Point at the 25 MB front-month parquet or one NQ yearly gzip. "
            "Set SETUP_ALLOW_WIDE_SCAN=1 only if you intend a wide scan."
        )
    return files


def _glob(pattern: str) -> list[str]:
    import glob

    return glob.glob(pattern, recursive=True)


def inspect_source(path: str | Path, *, n_rows: int = 5) -> dict[str, object]:
    """Read only the first rows and report columns, dtypes, and a preview."""
    files = list_data_files(Path(path))
    frame = _read_head(files[0], n_rows)
    preview = frame.to_dicts()
    return {
        "path": str(files[0]),
        "file_count": len(files),
        "columns": frame.columns,
        "dtypes": {name: str(dtype) for name, dtype in frame.schema.items()},
        "preview": preview,
    }


def _read_head(path: Path, n_rows: int) -> pl.DataFrame:
    if path.suffix == ".parquet":
        return pl.read_parquet(path, n_rows=n_rows)
    return pl.read_csv(path, n_rows=n_rows, try_parse_dates=True)


def _scan_file(path: Path) -> pl.LazyFrame:
    if path.suffix == ".parquet":
        return pl.scan_parquet(path)
    return pl.scan_csv(path, try_parse_dates=True, infer_schema_length=10_000)


def _rename_known(lf: pl.LazyFrame) -> pl.LazyFrame:
    schema = lf.collect_schema().names()
    mapping: dict[str, str] = {}
    for name in schema:
        if name in SESSION_ALIASES and name != SESSION_ALIASES[name]:
            mapping[name] = SESSION_ALIASES[name]
        elif name in TICKER_ALIASES and name != "ticker":
            mapping[name] = "ticker"
    if mapping:
        lf = lf.rename(mapping)
    return lf


def _with_timestamp(lf: pl.LazyFrame) -> pl.LazyFrame:
    schema = lf.collect_schema()
    return lf.with_columns(_aware_timestamp(schema.names(), schema).alias("timestamp"))


def _aware_timestamp(names: list[str], schema: pl.Schema) -> pl.Expr:
    if "ts" in names and "window_start" not in names:
        source = "ts"
    elif "window_start" in names:
        source = "window_start"
    elif "timestamp" in names:
        source = "timestamp"
    else:
        raise SchemaError(f"missing a time column. Found: {names}")
    dtype = schema[source]
    if isinstance(dtype, pl.Datetime):
        if dtype.time_zone is None:
            expr = pl.col(source).dt.replace_time_zone("UTC")
        else:
            expr = pl.col(source).dt.convert_time_zone("UTC")
    else:
        expr = pl.from_epoch(pl.col(source).cast(pl.Int64), time_unit="ns").dt.replace_time_zone("UTC")
    return expr.dt.convert_time_zone("America/New_York")


def _require_ohlcv(names: list[str]) -> None:
    missing = [column for column in OHLCV if column not in names]
    if missing:
        raise SchemaError(f"missing columns {missing}. Found: {names}")


def load_bars(
    path: str | Path | None = None,
    *,
    start: date | None = None,
    end: date | None = None,
    ticker_regex: str = NQ_OUTRIGHT,
    every: str | None = None,
    warmup_days: int = 30,
) -> tuple[pl.DataFrame, dict[str, object]]:
    """Load, filter, and optionally resample bars.

    ``start`` / ``end`` filter ``session_end_date``. ``warmup_days`` extra
    sessions are included before ``start`` so volatility terciles have history.
    The returned frame is sorted by timestamp and limited to NQ outrights.
    """
    resolved, source = resolve_data_path(None if path is None else str(path))
    files = list_data_files(resolved)
    frames = [_rename_known(_scan_file(file)) for file in files]
    lf = frames[0] if len(frames) == 1 else pl.concat(frames, how="diagonal_relaxed")
    names = lf.collect_schema().names()
    _require_ohlcv(names)
    lf = _with_timestamp(lf)
    names = lf.collect_schema().names()
    if "ticker" not in names:
        lf = lf.with_columns(pl.lit("NQ").alias("ticker"))
    else:
        lf = lf.filter(pl.col("ticker").str.contains(ticker_regex))
    if "session_end_date" not in lf.collect_schema().names():
        local_date = pl.col("timestamp").dt.date()
        lf = lf.with_columns(
            pl.when(pl.col("timestamp").dt.hour() >= 18)
            .then(local_date + pl.duration(days=1))
            .otherwise(local_date)
            .alias("session_end_date")
        )
    else:
        lf = lf.with_columns(pl.col("session_end_date").cast(pl.Date))
    read_start = start - timedelta(days=warmup_days) if start is not None else None
    if read_start is not None:
        lf = lf.filter(pl.col("session_end_date") >= read_start)
    if end is not None:
        lf = lf.filter(pl.col("session_end_date") <= end)
    lf = lf.select(
        "ticker",
        "session_end_date",
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        pl.col("volume").cast(pl.Float64),
    )
    lf = lf.unique(subset=["ticker", "timestamp"], keep="last").sort("timestamp")
    if every and every not in {"1m", "1min"}:
        lf = _resample(lf, every)
    lf = lf.with_columns(
        session_expr(),
        day_name_expr(),
        pl.col("timestamp").dt.hour().alias("hour_of_day"),
    )
    frame = lf.collect()
    if frame.is_empty():
        raise SchemaError(
            f"no NQ outright bars in {resolved} for {start} .. {end}. "
            f"Outright filter is {ticker_regex}."
        )
    meta = {
        "path": str(resolved),
        "source": source,
        "synthetic": source == "synthetic" or source_is_synthetic(resolved if resolved.is_file() else files[0].parent),
        "files": len(files),
        "rows": frame.height,
        "tickers": frame["ticker"].unique().sort().to_list(),
        "session_min": str(frame["session_end_date"].min()),
        "session_max": str(frame["session_end_date"].max()),
        "every": every or "1m",
    }
    return frame, meta


def _resample(lf: pl.LazyFrame, every: str) -> pl.LazyFrame:
    span = {"5m": "5m", "15m": "15m", "5min": "5m", "15min": "15m"}.get(every)
    if span is None:
        raise ValueError(f"unsupported resample {every!r}. Use 1m, 5m, or 15m.")
    return (
        lf.group_by_dynamic(
            "timestamp",
            every=span,
            group_by=["ticker", "session_end_date"],
            closed="left",
            label="left",
        )
        .agg(
            pl.col("open").first(),
            pl.col("high").max(),
            pl.col("low").min(),
            pl.col("close").last(),
            pl.col("volume").sum(),
        )
        .sort("timestamp")
    )


def session_bounds(path: str | Path | None = None) -> tuple[date, date]:
    """Min and max session_end_date without loading every bar into the app."""
    resolved, _source = resolve_data_path(None if path is None else str(path))
    files = list_data_files(resolved)
    frames = []
    for file in files:
        lf = _rename_known(_scan_file(file))
        if "session_end_date" not in lf.collect_schema().names() and "session_date" not in lf.collect_schema().names():
            continue
        column = "session_end_date" if "session_end_date" in lf.collect_schema().names() else "session_date"
        stats = lf.select(
            pl.col(column).cast(pl.Date).min().alias("lo"),
            pl.col(column).cast(pl.Date).max().alias("hi"),
        ).collect()
        frames.append(stats)
    if not frames:
        bars, _meta = load_bars(path)
        return bars["session_end_date"].min(), bars["session_end_date"].max()
    joined = pl.concat(frames)
    return joined["lo"].min(), joined["hi"].max()


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect a Massive minute file.")
    parser.add_argument("path", nargs="?", help="Parquet, csv.gz, or a small directory.")
    parser.add_argument("--rows", type=int, default=5)
    args = parser.parse_args()
    target = args.path or str(resolve_data_path()[0])
    profile = inspect_source(target, n_rows=args.rows)
    print(json.dumps(profile, indent=2, default=str))


if __name__ == "__main__":
    main()
