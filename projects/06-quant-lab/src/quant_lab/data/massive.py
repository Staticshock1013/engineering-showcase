"""Massive (api.massive.com) futures client — research downloads only.

Confirmed against current Massive docs (2026):
- Base URL: https://api.massive.com
- Contracts: GET /futures/v1/contracts
- Aggregates: GET /futures/v1/aggs/{ticker}
- No continuous futures product series; build front-month via volume roll.

Live HTTP requires MASSIVE_API_KEY. Tests and default downloads use fixtures.
Never logs or prints the API key.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
from pydantic import SecretStr

from quant_lab.data.schema import BAR_COLUMNS, SESSION_VOLUME_COLUMNS

# Documented resolutions used by this lab.
RESOLUTION_1MIN = "1min"
RESOLUTION_1DAY = "1day"


class MassiveConfigError(RuntimeError):
    """Raised when live Massive access is requested without credentials."""


class MassiveClient:
    """Thin REST client for Massive futures contracts + aggregates."""

    def __init__(
        self,
        *,
        api_key: SecretStr | None,
        base_url: str = "https://api.massive.com",
        timeout_s: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s

    @property
    def has_credentials(self) -> bool:
        return self._api_key is not None and bool(self._api_key.get_secret_value())

    def _headers(self) -> dict[str, str]:
        if not self.has_credentials:
            raise MassiveConfigError(
                "MASSIVE_API_KEY is not set. Use fixtures or set the key in .env / CI secrets."
            )
        # Auth via query param is also supported by Massive; header keeps URLs out of logs.
        assert self._api_key is not None
        return {"Authorization": f"Bearer {self._api_key.get_secret_value()}"}

    def list_contracts(
        self,
        *,
        product_code: str,
        date: str,
        active: bool = True,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "product_code": product_code,
            "date": date,
            "active": str(active).lower(),
            "limit": 1000,
        }
        payload = self._get("/futures/v1/contracts", params)
        return list(payload.get("results") or [])

    def get_aggregates(
        self,
        ticker: str,
        *,
        resolution: str,
        window_start_gte: str | None = None,
        window_start_lte: str | None = None,
        limit: int = 50000,
    ) -> pd.DataFrame:
        params: dict[str, Any] = {
            "resolution": resolution,
            "limit": limit,
            "sort": "window_start.asc",
        }
        if window_start_gte is not None:
            params["window_start.gte"] = window_start_gte
        if window_start_lte is not None:
            params["window_start.lte"] = window_start_lte
        payload = self._get(f"/futures/v1/aggs/{ticker}", params)
        rows = payload.get("results") or []
        return aggregates_to_bars(rows, default_symbol=ticker)

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        with httpx.Client(timeout=self.timeout_s) as client:
            response = client.get(url, params=params, headers=self._headers())
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, dict):
            raise RuntimeError("unexpected Massive response shape")
        return data


def aggregates_to_bars(
    rows: list[dict[str, Any]],
    *,
    default_symbol: str,
) -> pd.DataFrame:
    """Normalize Massive aggregate rows into the lab bar schema."""
    if not rows:
        return pd.DataFrame(columns=list(BAR_COLUMNS))
    records: list[dict[str, Any]] = []
    for row in rows:
        ts = row.get("window_start")
        # Massive may return ns epoch ints or ISO strings depending on endpoint/version.
        if isinstance(ts, int | float):
            timestamp = pd.to_datetime(int(ts), unit="ns", utc=True)
        else:
            timestamp = pd.to_datetime(ts, utc=True)
        records.append(
            {
                "timestamp": timestamp,
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row.get("volume") or 0),
                "symbol": str(row.get("ticker") or default_symbol),
                "session_end_date": row.get("session_end_date"),
            }
        )
    frame = pd.DataFrame.from_records(records)
    return frame.sort_values("timestamp").reset_index(drop=True)


def load_session_volumes_fixture(path: Path) -> pd.DataFrame:
    """Load synthetic/session volume rows used for front-month roll tests."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    frame = pd.DataFrame(raw)
    missing = [c for c in SESSION_VOLUME_COLUMNS if c not in frame.columns]
    if missing:
        raise ValueError(f"session volume fixture missing columns: {missing}")
    frame["session_end_date"] = pd.to_datetime(frame["session_end_date"]).dt.strftime("%Y-%m-%d")
    return frame.loc[:, list(SESSION_VOLUME_COLUMNS)]


def load_aggregates_fixture(path: Path, *, symbol: str) -> pd.DataFrame:
    """Load a Massive-shaped aggregates JSON fixture into bar schema."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("results") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError(f"bad aggregates fixture: {path}")
    return aggregates_to_bars(rows, default_symbol=symbol)
