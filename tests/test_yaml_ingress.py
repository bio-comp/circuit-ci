"""Exercise the actual CLI YAML ingress, including ambiguous safe-YAML constructs."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError
from typer.testing import CliRunner

import circuit_ci.cli.app as cli_module
from circuit_ci.cli.app import app

PSU = """design_intent: synthetic
version: test
constraints: {vin_v: 12}
components:
  R1: {part_id: R1, kind: resistor, value: 100, max_power_watts: 0.25}
  R2: {part_id: R2, kind: resistor, value: 1000, max_power_watts: 0.25}
  COUT: {part_id: COUT, kind: capacitor, value: 470uF, max_voltage: 16}
rule_evidence:
  divider: {topology: ideal_unloaded_series_r1_r2_across_vin, source: synthetic}
  output_cap:
    source: synthetic
    dc_voltage_v: 15
"""
OPAMP = """design_intent: synthetic
version: test
components:
  U1: {part_id: U1, kind: opamp, value: OPA1656}
  CDEC: {part_id: CDEC, kind: capacitor, value: 100nF}
rule_evidence:
  opamps:
    U1:
      source: synthetic
      decoupling: connected
      decoupling_capacitors: [CDEC]
      bias_return: present
"""
runner = CliRunner()


def fixture(tmp_path: Path, document: str) -> Path:
    path = tmp_path / "state.yaml"
    path.write_text(document, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("pack", "document", "status"),
    [
        ("psu", PSU, "AUTO_PASS"),
        ("psu", PSU.replace("dc_voltage_v: 15", "dc_voltage_v: 17"), "HARD_FAIL"),
        ("opamp", OPAMP, "AUTO_PASS"),
        ("opamp", OPAMP.replace("bias_return: present", "bias_return: absent"), "HARD_FAIL"),
        (
            "psu",
            PSU.replace("source: synthetic}", "source: &s synthetic}").replace(
                "    source: synthetic", "    source: *s"
            ),
            "AUTO_PASS",
        ),
        (
            "psu",
            PSU.replace("  output_cap:", "  output_cap: &cap") + "ignored_alias: *cap\n",
            "AUTO_PASS",
        ),
        (
            "opamp",
            OPAMP.replace(
                "  U1: {", "  U2: {part_id: U2, kind: opamp, value: OPA1656}\n  U1: {"
            ).replace("    U1:", "    U1: &evidence")
            + "    U2: *evidence\n",
            "AUTO_PASS",
        ),
        ("psu", PSU.replace("dc_voltage_v: 15", '"dc_voltage_v": 15'), "AUTO_PASS"),
    ],
)
def test_valid_declarations(tmp_path: Path, pack: str, document: str, status: str) -> None:
    result = runner.invoke(app, [str(fixture(tmp_path, document)), "--pack", pack])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["status"] == status


AMBIGUOUS = [
    (
        "opamp",
        OPAMP.replace("bias_return: present", "bias_return: absent\n      bias_return: present"),
    ),
    (
        "opamp",
        OPAMP.replace("bias_return: present", "bias_return: present\n      bias_return: absent"),
    ),
    ("psu", PSU.replace("dc_voltage_v: 15", "dc_voltage_v: 17\n    dc_voltage_v: 15")),
    ("psu", PSU.replace("dc_voltage_v: 15", "dc_voltage_v: 15\n    dc_voltage_v: 17")),
    (
        "psu",
        PSU.replace(
            "  output_cap:", "  output_cap: {source: synthetic, dc_voltage_v: 17}\n  output_cap:"
        ),
    ),
    ("psu", PSU.replace("max_voltage: 16", "max_voltage: 14, max_voltage: 16")),
    ("psu", PSU.replace("dc_voltage_v: 15", "dc_voltage_v: 15\n    dc_voltage_v: 15")),
    ("psu", PSU.replace("dc_voltage_v: 15", 'dc_voltage_v: 17\n    "dc_voltage_v": 15')),
    ("psu", PSU.replace("dc_voltage_v: 15", "&key dc_voltage_v: 17\n    *key: 15")),
    ("psu", PSU.replace("dc_voltage_v: 15", "<<: {dc_voltage_v: 17}\n    dc_voltage_v: 15")),
    ("psu", PSU.replace("dc_voltage_v: 15", "<<: [{dc_voltage_v: 17}, {dc_voltage_v: 15}]")),
    ("psu", PSU.replace("dc_voltage_v: 15", "<<: {dc_voltage_v: 15}")),
    ("psu", PSU.replace("dc_voltage_v: 15", "<<: *cap").replace("output_cap:", "output_cap: &cap")),
    ("psu", PSU + "ignored: [{x: 1, x: 2}]\n"),
    ("psu", PSU + "ignored: &a {x: 1, x: 2}\nignored_alias: *a\n"),
    ("psu", PSU + "ignored: {true: x, 1: y}\n"),
    ("psu", PSU + "ignored: !!pairs [{x: 1}, {x: 2}]\n"),
    ("psu", PSU + "ignored: !!omap [{x: 1}, {x: 2}]\n"),
    ("psu", PSU + "ignored: !!set {x: null, x: null}\n"),
    ("psu", PSU + "ignored: !!python/object/apply:builtins.str [unsafe]\n"),
    ("psu", PSU + "---\nversion: second\n"),
    ("psu", PSU.replace("dc_voltage_v: 15", "dc_voltage_v: 17\n    !!str dc_voltage_v: 15")),
    ("psu", PSU + "rule_evidence: {}\n"),
    ("psu", PSU + "ignored: {\n"),
    ("psu", PSU + "ignored: !!python/name:builtins.str ''\n"),
    ("psu", PSU + "ignored: &bad {x: 1, x: 2, self: *bad}\n"),
    ("psu", PSU.replace("  output_cap:", "  output_cap: &cap") + "ignored: {<<: *cap}\n"),
    ("psu", PSU + "ignored:\n  ? [x, y]\n  : z\n"),
]


@pytest.mark.parametrize(("pack", "document"), AMBIGUOUS)
def test_ambiguous_yaml_is_input_error(tmp_path: Path, pack: str, document: str) -> None:
    result = runner.invoke(app, [str(fixture(tmp_path, document)), "--pack", pack])
    assert result.exit_code == 2, result.output
    assert result.stdout == ""
    assert "Error" in result.output


@pytest.mark.parametrize(
    "document",
    [
        PSU.replace("dc_voltage_v: 15", 'dc_voltage_v: "15"'),
        PSU.replace("dc_voltage_v: 15", "dc_voltage_v: 15\n    unexpected: 1"),
        PSU.replace("dc_voltage_v: 15", "dc_voltage_v: true"),
        "",
    ],
)
def test_nested_pydantic_validation_preserved(tmp_path: Path, document: str) -> None:
    result = runner.invoke(app, [str(fixture(tmp_path, document))])
    assert result.exit_code != 0
    assert isinstance(result.exception, ValidationError)
    assert result.stdout == ""


@pytest.mark.parametrize("entrypoint", ["cci", "circuitci"])
@pytest.mark.parametrize(("pack", "document"), AMBIGUOUS[:5] + [AMBIGUOUS[9]])
def test_installed_cli_never_publishes_ambiguous_result(
    tmp_path: Path, entrypoint: str, pack: str, document: str
) -> None:
    path = fixture(tmp_path, document)
    output = tmp_path / "result.json"
    executable = Path(sys.executable).with_name(entrypoint)
    args = [str(executable), str(path), "--pack", pack]
    for extra in ([], ["--out", str(output)]):
        result = subprocess.run([*args, *extra], capture_output=True, text=True, check=False)
        assert result.returncode == 2, result.stderr
        assert result.stdout == ""
        assert not output.exists()
    sentinel = b"existing result must survive"
    output.write_bytes(sentinel)
    result = subprocess.run(
        [*args, "--out", str(output)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 2, result.stderr
    assert result.stdout == ""
    assert output.read_bytes() == sentinel


MALFORMED_SCALARS = [
    b"!!int not_a_number",
    b"!!float not_a_number",
    b"!!bool perhaps",
    b"!!int ''",
    b"!!float ''",
    b"!!timestamp not-a-date",
    b"!!timestamp 2026-02-31",
    b"!!int '+'",
    b"!!int '_'",
    b"!!float '_'",
    b"!!float '+'",
    b"!!int 0b",
    b"!!int 0x",
    b"!!timestamp 2026-01-01T12:00:00+99:00",
    b"2026-02-31",  # implicitly resolved invalid date
    b"!!float " + b":".join([b"1"] * 180),
    b"&invalid !!bool perhaps",  # referenced by an alias below
]
MALFORMED_BYTES = [
    PSU.encode("utf-8")
    + b"ignored: "
    + scalar
    + b"\n"
    + (b"ignored_alias: *invalid\n" if scalar.startswith(b"&invalid") else b"")
    for scalar in MALFORMED_SCALARS
] + [PSU.encode("utf-8") + b"ignored: \xff\n"]


@pytest.mark.parametrize("entrypoint", ["cci", "circuitci"])
@pytest.mark.parametrize("document", MALFORMED_BYTES)
def test_malformed_scalar_or_encoding_is_controlled_cli_error(
    tmp_path: Path, entrypoint: str, document: bytes
) -> None:
    path = tmp_path / "state.yaml"
    path.write_bytes(document)
    output = tmp_path / "result.json"
    executable = Path(sys.executable).with_name(entrypoint)
    args = [str(executable), str(path), "--pack", "psu"]

    def invoke(extra: list[str]) -> None:
        result = subprocess.run([*args, *extra], capture_output=True, check=False)
        assert result.returncode == 2, result.stderr
        assert result.stdout == b""
        assert b"Traceback" not in result.stderr
        expected = b"valid UTF-8" if b"\xff" in document else b"invalid YAML scalar"
        assert expected in result.stderr

    invoke([])
    invoke(["--out", str(output)])
    assert not output.exists()
    sentinel = b"prior result must survive"
    output.write_bytes(sentinel)
    invoke(["--out", str(output)])
    assert output.read_bytes() == sentinel


@pytest.mark.parametrize(
    ("pack", "document", "status"),
    [
        (
            "psu",
            PSU.replace("vin_v: 12", "vin_v: !!int 12").replace(
                "dc_voltage_v: 15", "dc_voltage_v: !!float 15"
            ),
            "AUTO_PASS",
        ),
        (
            "psu",
            PSU.replace("dc_voltage_v: 15", "dc_voltage_v: !!float 17.0"),
            "HARD_FAIL",
        ),
        (
            "opamp",
            OPAMP + "generated_at: !!timestamp 2026-11-26T12:00:00Z\nignored: !!bool TRUE\n",
            "AUTO_PASS",
        ),
        (
            "opamp",
            OPAMP.replace("bias_return: present", "bias_return: absent")
            + "generated_at: !!timestamp 2026-11-26T12:00:00+01:00\n"
            "ignored: !!bool off\n",
            "HARD_FAIL",
        ),
        (
            "psu",
            PSU.replace("vin_v: 12", "vin_v: !!int 0xC").replace(
                "dc_voltage_v: 15", "dc_voltage_v: !!float 1.5e1"
            )
            + "ignored: !!timestamp 2026-11-26\n",
            "AUTO_PASS",
        ),
    ],
)
def test_valid_explicit_scalar_tags(tmp_path: Path, pack: str, document: str, status: str) -> None:
    path = tmp_path / "state.yaml"
    path.write_bytes(document.encode("utf-8"))
    result = runner.invoke(app, [str(path), "--pack", pack])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["status"] == status
    if "generated_at:" in document:
        state = cli_module._load_state(path)
        assert state.generated_at.year == 2026
        assert state.generated_at.tzinfo is not None


def test_valid_tagged_bool_still_fails_strict_electrical_validation(tmp_path: Path) -> None:
    path = tmp_path / "state.yaml"
    path.write_bytes(PSU.replace("dc_voltage_v: 15", "dc_voltage_v: !!bool true").encode())
    result = runner.invoke(app, [str(path)])
    assert isinstance(result.exception, ValidationError)
    assert result.exit_code == 1
    assert result.stdout == ""


@pytest.mark.parametrize(
    ("method", "scalar", "error"),
    [
        ("construct_yaml_int", "!!int 12", IndexError("unexpected index error")),
        ("construct_yaml_float", "!!float 15", RuntimeError("unexpected runtime error")),
        ("construct_yaml_bool", "!!bool true", KeyError("unexpected missing key")),
        ("construct_yaml_timestamp", "!!timestamp 2026-11-26", AttributeError("unexpected")),
    ],
)
def test_unexpected_scalar_constructor_failure_propagates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, method: str, scalar: str, error: Exception
) -> None:
    path = tmp_path / "state.yaml"
    path.write_bytes((PSU + f"ignored: {scalar}\n").encode())

    def fail(*args: object, **kwargs: object) -> None:
        raise error

    monkeypatch.setattr(yaml.SafeLoader, method, fail)
    result = runner.invoke(app, [str(path)])
    assert result.exception is error
    assert result.exit_code == 1
    assert result.stdout == ""


@pytest.mark.parametrize(
    ("target", "method", "error"),
    [
        (yaml.SafeLoader, "construct_document", ValueError("internal construction bug")),
        (yaml.SafeLoader, "get_single_node", KeyError("internal composition bug")),
        (cli_module, "_check_yaml_nodes", IndexError("internal node check bug")),
        (cli_module.CircuitState, "model_validate", yaml.YAMLError("internal model bug")),
        (cli_module, "lint_psu", ValueError("internal rule bug")),
        (Path, "write_text", ValueError("internal persistence bug")),
    ],
)
def test_unexpected_non_scalar_failure_propagates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target: object, method: str, error: Exception
) -> None:
    path = tmp_path / "state.yaml"
    path.write_bytes(PSU.encode())

    def fail(*args: object, **kwargs: object) -> None:
        raise error

    monkeypatch.setattr(target, method, fail)
    result = runner.invoke(app, [str(path), "--out", str(tmp_path / "result.json")])
    assert result.exception is error
    assert result.exit_code == 1
    assert result.stdout == ""
    assert not (tmp_path / "result.json").exists()


@pytest.mark.parametrize("document", [PSU.encode(), MALFORMED_BYTES[0], MALFORMED_BYTES[2]])
def test_loader_is_disposed_after_scalar_construction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, document: bytes
) -> None:
    path = tmp_path / "state.yaml"
    path.write_bytes(document)
    disposed = []
    original = yaml.SafeLoader.dispose

    def dispose(loader: yaml.SafeLoader) -> None:
        disposed.append(loader)
        original(loader)

    monkeypatch.setattr(yaml.SafeLoader, "dispose", dispose)
    result = runner.invoke(app, [str(path)])
    assert result.exit_code == (0 if document == PSU.encode() else 2)
    assert len(disposed) == 1


def test_scalar_adapters_do_not_change_global_safe_loader() -> None:
    # PyYAML's original registry must remain untouched.
    with pytest.raises(KeyError):
        yaml.safe_load("!!bool perhaps")
