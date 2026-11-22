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


if __name__ == "__main__":
    app()
