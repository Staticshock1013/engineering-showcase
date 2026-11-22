"""Tests for the pre-registered NQ MA study (hash gate + causal MAs)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from quant_lab.analysis.ma_study import detect_signals, holdout_pass
from quant_lab.analysis.run_ma_study import run_ma_study
from quant_lab.backtest.lookahead import assert_feature_uses_only_past
from quant_lab.experiments.spec import verify_spec_hash
from quant_lab.features.moving_averages import sma

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data" / "fixtures" / "nq_daily_synthetic.csv"


def test_frozen_spec_hash_matches() -> None:
    digest = verify_spec_hash(
        ROOT / "experiments" / "ma-study" / "SPEC.md",
        ROOT / "experiments" / "ma-study" / "HASH.txt",
    )
    assert len(digest) == 64


def test_sma_is_causal() -> None:
    prices = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
    feature = sma(prices, 3)

    def rebuild(p: pd.Series) -> pd.Series:
        return sma(p, 3)

    assert_feature_uses_only_past(prices, feature, rebuild=rebuild, name="sma3")


def test_detect_signals_requires_ma200_warmup() -> None:
    bars = pd.read_csv(FIXTURE).head(50)
    bars["timestamp"] = pd.to_datetime(bars["timestamp"], utc=True)
    signals = detect_signals(bars)
    # With <200 bars, MA200 is NaN so golden/death cannot fire.
    assert signals["golden_cross"].sum() == 0
    assert signals["death_cross"].sum() == 0


def test_holdout_pass_requires_edge_and_sample_size() -> None:
    from quant_lab.analysis.ma_study import EventStats

    fail = EventStats(
        signal_id="ma20_family",
        window="holdout",
        n=10,
        hit_rate=0.9,
        mean_net_pnl=0.0,
        baseline_hit_rate=0.5,
        baseline_mean_net_pnl=0.0,
        hit_rate_edge=0.4,
    )
    passed, _ = holdout_pass([fail])
    assert not passed

    ok = EventStats(
        signal_id="cross_family",
        window="holdout",
        n=30,
        hit_rate=0.55,
        mean_net_pnl=0.0,
        baseline_hit_rate=0.50,
        baseline_mean_net_pnl=0.0,
        hit_rate_edge=0.05,
    )
    passed, reason = holdout_pass([ok])
    assert passed
    assert "PASS" in reason


def test_run_ma_study_end_to_end(tmp_path: Path) -> None:
    if not FIXTURE.exists():
        pytest.skip("synthetic fixture missing")
    payload = run_ma_study(FIXTURE, output_dir=tmp_path)
    assert payload["spec_sha256"]
    assert payload["cost_assumptions"]["contract"] == "NQ"
    assert payload["cost_assumptions"]["commission_basis"] == "usd_per_contract_per_side"
    assert "holdout_decision" in payload
    assert (tmp_path / "results.json").exists()


def test_mutated_spec_refuses_to_run(tmp_path: Path) -> None:
    spec = tmp_path / "SPEC.md"
    digest_file = tmp_path / "HASH.txt"
    spec.write_text("hello\n", encoding="utf-8")
    digest_file.write_text("0" * 64 + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_spec_hash(spec, digest_file)
