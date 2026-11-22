"""Explicit transaction cost and slippage model for futures research.

Defaults are for **NQ** (CME E-mini Nasdaq-100), not MNQ.
Commission is **USD per contract per side** (open or close), not round-trip.

Typical research assumption used here:
  - NQ: $2.50 commission per side
  - MNQ would use a different point value ($2) and usually a lower commission;
    do not reuse these NQ defaults for MNQ without changing ``contract``.

Research only: no live order routing.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FuturesCostModel:
    """Per-side costs for a named futures contract (default: NQ)."""

    contract: str = "NQ"
    """CME product code this model is calibrated for. Must be ``NQ`` for defaults."""

    commission_per_side: float = 2.50
    """Broker commission in USD per contract per side (NOT round-trip).

    For NQ this lab assumes $2.50 per side.
    This is not "$2.50 round trip for MNQ".
    """

    slippage_ticks: float = 1.0
    """Adverse ticks assumed on each fill."""

    tick_size: float = 0.25
    """Minimum price increment in index points (NQ = 0.25)."""

    point_value: float = 20.0
    """USD per index point per contract (NQ = $20; MNQ = $2)."""

    def __post_init__(self) -> None:
        if self.contract == "NQ":
            if self.point_value != 20.0:
                raise ValueError("NQ point_value must be 20.0")
            if self.tick_size != 0.25:
                raise ValueError("NQ tick_size must be 0.25")
        if self.contract == "MNQ":
            raise ValueError(
                "MNQ is not configured in this lab; use contract='NQ' or extend "
                "FuturesCostModel with MNQ point_value/commission explicitly"
            )

    def slippage_per_side_usd(self) -> float:
        """Dollar slippage for one contract on one side."""
        return self.slippage_ticks * self.tick_size * self.point_value

    def cost_per_side_usd(self) -> float:
        """Total USD cost for one contract on one side (commission + slippage)."""
        return self.commission_per_side + self.slippage_per_side_usd()

    def cost_for_trade(self, contracts_traded: float) -> float:
        """USD cost for an absolute contract turnover on one side.

        ``contracts_traded`` is ``abs(delta_position)`` in contracts.
        Round-trip of 1 NQ contract = two sides = ``2 * cost_per_side_usd()``.
        """
        if contracts_traded < 0:
            raise ValueError("contracts_traded must be non-negative")
        return float(contracts_traded) * self.cost_per_side_usd()

    def as_assumptions(self) -> dict[str, float | str]:
        """Serializable assumptions for experiment SPECs / result reports."""
        return {
            "contract": self.contract,
            "commission_basis": "usd_per_contract_per_side",
            "commission_per_side_usd": self.commission_per_side,
            "slippage_ticks": self.slippage_ticks,
            "tick_size": self.tick_size,
            "point_value_usd": self.point_value,
            "cost_per_side_usd": self.cost_per_side_usd(),
            "round_trip_1_contract_usd": 2.0 * self.cost_per_side_usd(),
            "note": (
                "NQ $2.50 per side — not MNQ; not $2.50 round-trip"
            ),
        }
