from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
import yaml

from ..core.schemas import CircuitState
from ..packs.opamp.pack import lint as lint_opamp
from ..packs.psu.pack import lint as lint_psu

app = typer.Typer(add_completion=False, help="Circuit-CI (cci): CI/CD for circuits")


def _load_state(path: Path) -> CircuitState:
    data = yaml.safe_load(path.read_text())
    return CircuitState.model_validate(data)


@app.command()
def lint(
    state: Path = typer.Argument(..., exists=True, readable=True, help="CircuitState YAML"),
    pack: str = typer.Option("psu", help="Pack: psu | opamp"),
    out: Optional[Path] = typer.Option(None, help="Write JSON result to file"),
) -> None:
    """Run deterministic lint checks."""
    st = _load_state(state)
    if pack == "psu":
        res = lint_psu(st)
    elif pack == "opamp":
        res = lint_opamp(st)
    else:
        raise typer.BadParameter("pack must be one of: psu, opamp")

    payload = json.loads(res.model_dump_json())
    text = json.dumps(payload, indent=2, sort_keys=True)
    if out:
        out.write_text(text)
        typer.echo(f"wrote {out}")
    else:
        typer.echo(text)


def main() -> None:
    app()
