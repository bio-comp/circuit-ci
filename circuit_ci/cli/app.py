from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
import yaml
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

from ..core.schemas import CircuitState
from ..packs.opamp.pack import lint as lint_opamp
from ..packs.psu.pack import lint as lint_psu

app = typer.Typer(add_completion=False, help="Circuit-CI (cci): CI/CD for circuits")


def _check_yaml_nodes(root: Node) -> None:
    """Validate composed keys before safe construction can discard declarations."""
    pending = [root]
    seen: set[Node] = set()
    while pending:
        node = pending.pop()
        if node in seen:
            continue
        seen.add(node)
        if isinstance(node, MappingNode):
            if node.tag != "tag:yaml.org,2002:map":
                raise ConstructorError(None, None, "unsupported mapping tag", node.start_mark)
            keys: set[str] = set()
            pairs: list[tuple[Node, Node]] = node.value
            for key, value in pairs:
                if key.tag == "tag:yaml.org,2002:merge":
                    raise ConstructorError(
                        None, None, "YAML merge keys are not supported", key.start_mark
                    )
                if not isinstance(key, ScalarNode) or key.tag != "tag:yaml.org,2002:str":
                    raise ConstructorError(
                        None, None, "mapping keys must be strings", key.start_mark
                    )
                name: str = key.value
                if name in keys:
                    raise ConstructorError(None, None, "duplicate YAML mapping key", key.start_mark)
                keys.add(name)
                pending.append(value)
        elif isinstance(node, SequenceNode):
            if node.tag != "tag:yaml.org,2002:seq":
                raise ConstructorError(None, None, "unsupported sequence tag", node.start_mark)
            items: list[Node] = node.value
            pending.extend(items)


def _load_state(path: Path) -> CircuitState:
    loader = yaml.SafeLoader(path.read_text(encoding="utf-8"))
    try:
        root = loader.get_single_node()
        data: object = None
        if root is not None:
            _check_yaml_nodes(root)
            data = loader.construct_document(root)
    finally:
        loader.dispose()
    return CircuitState.model_validate(data)


@app.command()
def lint(
    state: Path = typer.Argument(..., exists=True, readable=True, help="CircuitState YAML"),
    pack: str = typer.Option("psu", help="Pack: psu | opamp"),
    out: Optional[Path] = typer.Option(None, help="Write JSON result to file"),
) -> None:
    """Run deterministic lint checks."""
    try:
        st = _load_state(state)
    except yaml.YAMLError as error:
        raise typer.BadParameter(str(error), param_hint="state") from error
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
