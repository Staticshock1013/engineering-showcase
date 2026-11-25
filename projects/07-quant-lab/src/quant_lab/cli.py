"""CLI entrypoint (research commands only — no order placement)."""

from __future__ import annotations

import typer

app = typer.Typer(
    name="quant-lab",
    help="Research-only backtesting and analysis. No live trading.",
    add_completion=False,
)


@app.callback()
def main() -> None:
    """quant-lab research toolkit."""


@app.command("version")
def version() -> None:
    """Print package version."""
    from quant_lab import __version__

    typer.echo(__version__)


@app.command("download-data")
def download_data(
    source: str = typer.Option(
        "fixtures",
        "--source",
        help="fixtures (default, offline) | robinhood (local exports) | massive (requires API key)",
    ),
    ticker: str | None = typer.Option(None, help="Massive contract ticker, e.g. NQH6"),
    resolution: str = typer.Option("1day", help="Massive resolution: 1min or 1day"),
    window_start_gte: str | None = typer.Option(
        None, help="Massive window_start.gte (YYYY-MM-DD)"
    ),
    window_start_lte: str | None = typer.Option(
        None, help="Massive window_start.lte (YYYY-MM-DD)"
    ),
) -> None:
    """Download or import research data into the local cache (never commits it)."""
    from quant_lab.config import Settings
    from quant_lab.data.cache import DataCache
    from quant_lab.data.download import (
        download_fixtures,
        download_massive_live,
        import_robinhood_exports,
    )

    settings = Settings()
    settings.ensure_dirs()
    cache = DataCache(settings.quant_lab_cache_dir)

    if source == "fixtures":
        written = download_fixtures(cache)
        typer.echo(f"Wrote {len(written)} fixture cache entries under {cache.root}")
        return

    if source == "robinhood":
        written = import_robinhood_exports(settings, cache)
        typer.echo(f"Imported {len(written)} Robinhood export(s) into {cache.root}")
        return

    if source == "massive":
        if not ticker or not window_start_gte:
            raise typer.BadParameter("massive source requires --ticker and --window-start-gte")
        path = download_massive_live(
            settings,
            cache,
            ticker=ticker,
            resolution=resolution,
            window_start_gte=window_start_gte,
            window_start_lte=window_start_lte,
        )
        typer.echo(f"Wrote Massive bars to {path}")
        return

    raise typer.BadParameter(f"unknown source: {source}")


@app.command("run-ma-study")
def run_ma_study_cmd() -> None:
    """Run the pre-registered NQ ma-study experiment (verifies SPEC hash first)."""
    from quant_lab.analysis.run_ma_study import run_ma_study

    payload = run_ma_study()
    decision = payload["holdout_decision"]
    typer.echo(f"SPEC SHA-256: {payload['spec_sha256']}")
    typer.echo(f"Holdout: {'PASS' if decision['passed'] else 'FAIL'} — {decision['reason']}")
    typer.echo(f"Wrote {payload['results_path']}")
    typer.echo(f"Summary {payload['summary_path']}")


if __name__ == "__main__":
    app()
