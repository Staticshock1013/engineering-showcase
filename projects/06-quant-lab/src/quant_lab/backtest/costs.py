"""Explicit transaction cost and slippage model for NQ futures research.

All assumptions are named fields — strategies must report them in SPEC.md.
Research only: no live order routing.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FuturesCostModel:
    """Per-side costs for CME equity-index futures (defaults sized for NQ)."""

    commission_per_side: float = 2.50
    """Broker commission in USD per contract per side (not round-trip)."""

    slippage_ticks: float = 1.0
    """Adverse ticks assumed on each fill."""

    tick_size: float = 0.25
    """Minimum price increment in index points (NQ = 0.25)."""

    point_value: float = 20.0
    """USD per index point per contract (NQ = $20)."""

    def slippage_per_side_usd(self) -> float:
        """Dollar slippage for one contract on one side."""
        return self.slippage_ticks * self.tick_size * self.point_value

    def cost_per_side_usd(self) -> float:
        """Total USD cost for one contract on one side (commission + slippage)."""
        return self.commission_per_side + self.slippage_per_side_usd()

    def cost_for_trade(self, contracts_traded: float) -> float:
        """USD cost for an absolute contract turnover on one side.

        ``contracts_traded`` is ``abs(delta_position)`` in contracts.
        Round-trip of 1 contract = two sides = ``2 * cost_per_side_usd()``.
        """
        if contracts_traded < 0:
            raise ValueError("contracts_traded must be non-negative")
        return float(contracts_traded) * self.cost_per_side_usd()

    def as_assumptions(self) -> dict[str, float]:
        """Serializable assumptions for experiment SPECs / result reports."""
        return {
            "commission_per_side_usd": self.commission_per_side,
            "slippage_ticks": self.slippage_ticks,
            "tick_size": self.tick_size,
            "point_value_usd": self.point_value,
            "cost_per_side_usd": self.cost_per_side_usd(),
            "round_trip_1_contract_usd": 2.0 * self.cost_per_side_usd(),
        }
