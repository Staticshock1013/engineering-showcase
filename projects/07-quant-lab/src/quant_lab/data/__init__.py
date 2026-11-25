"""Market data loaders, cache, and futures roll logic."""

from quant_lab.data.cache import DataCache
from quant_lab.data.massive import MassiveClient, MassiveConfigError
from quant_lab.data.robinhood import RobinhoodLoader, normalize_equity_frame
from quant_lab.data.roll import (
    ContinuousSeries,
    RollEvent,
    build_continuous_series,
    select_front_month,
)

__all__ = [
    "ContinuousSeries",
    "DataCache",
    "MassiveClient",
    "MassiveConfigError",
    "RobinhoodLoader",
    "RollEvent",
    "build_continuous_series",
    "normalize_equity_frame",
    "select_front_month",
]
