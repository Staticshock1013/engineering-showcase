"""Load equity bars from a local Robinhood CSV/Parquet export directory.

Research only — no Robinhood API client and no order placement.
Robinhood minute history is typically short (~2 weeks); longer equity
history (e.g. SPY) should come from Massive once a key is configured.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from quant_lab.data.schema import BAR_COLUMNS

_COLUMN_ALIASES: dict[str, str] = {
    "timestamp": "timestamp",
    "datetime": "timestamp",
    "date": "timestamp",
    "time": "timestamp",
    "open": "open",
    "high": "high",
    "low": "low",
    "close": "close",
    "volume": "volume",
    "symbol": "symbol",
    "ticker": "symbol",
}


def normalize_equity_frame(raw: pd.DataFrame, default_symbol: str | None) -> pd.DataFrame:
    renamed: dict[str, str] = {}
    for col in raw.columns:
        key = str(col).strip().lower()
        if key in _COLUMN_ALIASES:
            renamed[col] = _COLUMN_ALIASES[key]
    frame = raw.rename(columns=renamed).copy()
    if "symbol" not in frame.columns:
        if not default_symbol:
            raise ValueError("equity file has no symbol column and no default_symbol was given")
        frame["symbol"] = default_symbol
    missing = [c for c in BAR_COLUMNS if c not in frame.columns]
    if missing:
        raise ValueError(f"equity bars missing columns after normalize: {missing}")
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    for col in ("open", "high", "low", "close", "volume"):
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    frame["symbol"] = frame["symbol"].astype(str)
    out = frame.loc[:, list(BAR_COLUMNS)].dropna(subset=["timestamp", "close"])
    return out.sort_values("timestamp").reset_index(drop=True)


class RobinhoodLoader:
    """Reads bars from ROBINHOOD_DATA_DIR exports (CSV or Parquet)."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        if not self.data_dir.exists():
            raise FileNotFoundError(f"ROBINHOOD_DATA_DIR does not exist: {self.data_dir}")

    def list_symbols(self) -> list[str]:
        symbols: list[str] = []
        for path in sorted(self.data_dir.iterdir()):
            if path.suffix.lower() in {".csv", ".parquet"} and path.is_file():
                symbols.append(path.stem.upper())
        return symbols

    def load_symbol(self, symbol: str) -> pd.DataFrame:
        symbol_u = symbol.upper()
        candidates = [
            self.data_dir / f"{symbol_u}.csv",
            self.data_dir / f"{symbol_u}.parquet",
            self.data_dir / f"{symbol.lower()}.csv",
            self.data_dir / f"{symbol.lower()}.parquet",
        ]
        path = next((p for p in candidates if p.exists()), None)
        if path is None:
            raise FileNotFoundError(
                f"no CSV/Parquet export for {symbol_u} under {self.data_dir}"
            )
        raw = pd.read_csv(path) if path.suffix.lower() == ".csv" else pd.read_parquet(path)
        return normalize_equity_frame(raw, default_symbol=symbol_u)
