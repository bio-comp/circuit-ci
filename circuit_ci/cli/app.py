from __future__ import annotations

import json
from datetime import date
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


class _StateLoader(yaml.SafeLoader):
    """Local safe-loader constructor registry for CircuitState ingress."""


def _invalid_scalar(node: ScalarNode) -> ConstructorError:
    return ConstructorError(None, None, f"invalid YAML scalar for {node.tag}", node.start_mark)


def _construct_number(loader: yaml.SafeLoader, node: ScalarNode) -> int | float:
    # PyYAML 6.0.4 indexes the scalar after removing underscores and,
    # for integers, after removing the leading sign.
    value: str = node.value
    if value.replace("_", "") in {"", "+", "-"}:
        raise _invalid_scalar(node)
    if node.tag == "tag:yaml.org,2002:int":
        try:
            return loader.construct_yaml_int(node)
        except ValueError as error:
            raise _invalid_scalar(node) from error
    try:
        return loader.construct_yaml_float(node)
    except (ValueError, OverflowError) as error:
        raise _invalid_scalar(node) from error


def _construct_bool(loader: yaml.SafeLoader, node: ScalarNode) -> bool:
    # Check the actual PyYAML vocabulary rather than catching arbitrary KeyError.
    value: str = node.value
    if value.lower() not in loader.bool_values:
        raise _invalid_scalar(node)
    return loader.construct_yaml_bool(node)


def _construct_timestamp(loader: yaml.SafeLoader, node: ScalarNode) -> date:
    # The upstream constructor dereferences the match without a None check.
    value: str = node.value
    if loader.timestamp_regexp.match(value) is None:
        raise _invalid_scalar(node)
    try:
        return loader.construct_yaml_timestamp(node)
    except ValueError as error:
        # Invalid calendar fields or timezone offset.
        raise _invalid_scalar(node) from error


_StateLoader.add_constructor("tag:yaml.org,2002:int", _construct_number)
_StateLoader.add_constructor("tag:yaml.org,2002:float", _construct_number)
_StateLoader.add_constructor("tag:yaml.org,2002:bool", _construct_bool)
_StateLoader.add_constructor("tag:yaml.org,2002:timestamp", _construct_timestamp)


def _load_state(path: Path) -> CircuitState:
    try:
        source = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise typer.BadParameter("input must be valid UTF-8", param_hint="state") from error

    try:
        loader = _StateLoader(source)
        try:
            root = loader.get_single_node()
            data: object = None
            if root is not None:
                _check_yaml_nodes(root)
                data = loader.construct_document(root)
        finally:
            loader.dispose()
    except yaml.YAMLError as error:
        raise typer.BadParameter(str(error), param_hint="state") from error
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
