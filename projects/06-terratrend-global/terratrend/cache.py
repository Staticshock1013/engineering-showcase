"""Registry-backed access to verified, credential-free processed caches."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .mod11a2 import load_processed_composite
from .registry import VERIFIED_DATA_REGISTRY

PROCESSED_DIRECTORY = Path(__file__).parent / "processed"


def load_verified_cache_registry(directory: Path = PROCESSED_DIRECTORY) -> list[dict[str, Any]]:
    """Load only product/status-matched caches for the dashboard's verified-data panel."""
    entries = []
    for path in sorted(directory.glob("*.json")):
        payload = load_processed_composite(path)
        product_key = payload.get("data_product_key")
        definition = VERIFIED_DATA_REGISTRY.get(product_key)
        if not definition:
            raise ValueError(f"Unknown processed-data registry key in {path.name}.")
        provenance = payload.get("provenance", {})
        if (
            payload.get("data_status") != definition.data_status
            or provenance.get("product_short_name") != definition.product_short_name
            or provenance.get("product_version") != definition.version
        ):
            raise ValueError(f"Processed cache does not match its registry definition: {path.name}.")
        entries.append({**payload, "cache_path": path.name})
    return sorted(
        entries,
        key=lambda entry: (entry["composite"]["city"], entry["composite"]["time_start"]),
    )
