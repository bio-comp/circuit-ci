"""Exercise the actual CLI YAML ingress, including ambiguous safe-YAML constructs."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

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
