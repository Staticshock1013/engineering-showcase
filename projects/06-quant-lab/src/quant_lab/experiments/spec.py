"""Pre-registration helpers: SHA-256 freeze and verify for experiment SPECs."""

from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_file(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest()


def freeze_spec_hash(spec_path: Path, hash_path: Path) -> str:
    digest = sha256_file(spec_path)
    hash_path.write_text(digest + "\n", encoding="utf-8")
    return digest


def verify_spec_hash(spec_path: Path, hash_path: Path) -> str:
    """Return the digest if HASH.txt matches SPEC.md; raise otherwise."""
    expected = hash_path.read_text(encoding="utf-8").strip()
    actual = sha256_file(spec_path)
    if actual != expected:
        raise ValueError(
            f"SPEC hash mismatch for {spec_path}: expected {expected}, got {actual}. "
            "Refusing to run results against a mutated SPEC."
        )
    return actual
