"""Local on-disk cache for research bars (under data/, gitignored)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from quant_lab.data.schema import BAR_COLUMNS


class DataCache:
    """Read/write Parquet caches. Never stores credentials."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, name: str) -> Path:
        safe = name.replace("/", "_").replace("..", "_")
        return self.root / f"{safe}.parquet"

    def write_bars(self, name: str, frame: pd.DataFrame) -> Path:
        missing = [c for c in BAR_COLUMNS if c not in frame.columns]
        if missing:
            raise ValueError(f"bars missing columns: {missing}")
        out = self.path_for(name)
        frame.loc[:, list(BAR_COLUMNS)].to_parquet(out, index=False)
        return out

    def read_bars(self, name: str) -> pd.DataFrame:
        path = self.path_for(name)
        if not path.exists():
            raise FileNotFoundError(f"cache miss: {path}")
        return pd.read_parquet(path)

    def exists(self, name: str) -> bool:
        return self.path_for(name).exists()
