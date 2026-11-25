"""Run the pre-registered ma-study experiment (verifies SPEC hash first)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from quant_lab.analysis.ma_study import (
    FAMILY_MEMBERS,
    detect_signals,
    evaluate_family,
    evaluate_signal,
    holdout_pass,
)
from quant_lab.backtest.costs import FuturesCostModel
from quant_lab.experiments.spec import verify_spec_hash

ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT_DIR = ROOT / "experiments" / "ma-study"
DEFAULT_DATA = ROOT / "data" / "fixtures" / "nq_daily_synthetic.csv"


def run_ma_study(
    data_path: Path = DEFAULT_DATA,
    *,
    output_dir: Path | None = None,
) -> dict:
    digest = verify_spec_hash(EXPERIMENT_DIR / "SPEC.md", EXPERIMENT_DIR / "HASH.txt")
    bars = pd.read_csv(data_path)
    bars["timestamp"] = pd.to_datetime(bars["timestamp"], utc=True)
    signals = detect_signals(bars)
    cost_model = FuturesCostModel(contract="NQ")

    rows: list[dict] = []
    for window, seed in (("development", 42), ("holdout", 43)):
        for signal_id in (
            "price_cross_ma20_up",
            "price_cross_ma20_down",
            "golden_cross",
            "death_cross",
        ):
            stats = evaluate_signal(
                signals, signal_id, window=window, rng_seed=seed, cost_model=cost_model
            )
            rows.append(stats.__dict__)
        for family in FAMILY_MEMBERS:
            stats = evaluate_family(
                signals, family, window=window, rng_seed=seed, cost_model=cost_model
            )
            rows.append(stats.__dict__)

    holdout_families = [
        evaluate_family(
            signals, family, window="holdout", rng_seed=43, cost_model=cost_model
        )
        for family in FAMILY_MEMBERS
    ]
    passed, reason = holdout_pass(holdout_families)

    payload = {
        "experiment": "ma-study",
        "spec_sha256": digest,
        "data_path": str(data_path),
        "data_note": "synthetic NQ daily fixture unless overridden",
        "cost_assumptions": cost_model.as_assumptions(),
        "results": rows,
        "holdout_decision": {"passed": passed, "reason": reason},
    }

    out_dir = output_dir or (ROOT / "outputs" / "ma-study")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "results.json"
    out_path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    # Also copy a summary next to the experiment for reviewers (not raw market data).
    summary_path = EXPERIMENT_DIR / "RESULTS.md"
    summary_path.write_text(_format_results_md(payload), encoding="utf-8")
    payload["results_path"] = str(out_path)
    payload["summary_path"] = str(summary_path)
    return payload


def _format_results_md(payload: dict) -> str:
    lines = [
        "# ma-study results",
        "",
        f"- SPEC SHA-256: `{payload['spec_sha256']}`",
        f"- Data: `{payload['data_path']}` ({payload['data_note']})",
        f"- Contract / costs: `{payload['cost_assumptions']}`",
        f"- Holdout decision: **{'PASS' if payload['holdout_decision']['passed'] else 'FAIL'}** — "
        f"{payload['holdout_decision']['reason']}",
        "",
        "| window | signal | n | hit_rate | baseline | edge | mean_net_pnl | baseline_net |",
        "|--------|--------|---|----------|----------|------|--------------|--------------|",
    ]
    for row in payload["results"]:
        lines.append(
            "| {window} | {signal_id} | {n} | {hit_rate:.4f} | {baseline_hit_rate:.4f} | "
            "{hit_rate_edge:.4f} | {mean_net_pnl:.2f} | {baseline_mean_net_pnl:.2f} |".format(
                **{
                    **row,
                    "hit_rate": row["hit_rate"] if row["n"] else float("nan"),
                    "baseline_hit_rate": row["baseline_hit_rate"]
                    if row["n"]
                    else float("nan"),
                    "hit_rate_edge": row["hit_rate_edge"] if row["n"] else float("nan"),
                    "mean_net_pnl": row["mean_net_pnl"] if row["n"] else float("nan"),
                    "baseline_mean_net_pnl": row["baseline_mean_net_pnl"]
                    if row["n"]
                    else float("nan"),
                }
            )
        )
    lines.append("")
    lines.append(
        "Development window is spent. Holdout was evaluated once against the frozen threshold."
    )
    lines.append("")
    return "\n".join(lines) + "\n"
