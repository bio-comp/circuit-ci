"""Foundation/packaging regressions; legacy circuit-rule oracles remain unqualified."""

from __future__ import annotations

import json
from importlib.metadata import distribution
from pathlib import Path

from typer.testing import CliRunner

from circuit_ci.cli.app import app

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "docs" / "example_state_psu.yaml"
runner = CliRunner()


def test_distribution_license_matches_mit_file() -> None:
    dist = distribution("circuit-ci")
    assert dist.metadata["License-Expression"] == "MIT"
    assert (ROOT / "LICENSE").read_text(encoding="utf-8").startswith("MIT License")


def test_both_console_entrypoints_are_packaged() -> None:
    entries = {entry.name: entry.value for entry in distribution("circuit-ci").entry_points}
    assert entries["cci"] == "circuit_ci.cli.app:main"
    assert entries["circuitci"] == "circuit_ci.cli.app:main"


def test_cli_help_exposes_legacy_root_state_argument() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "CircuitState YAML" in result.stdout


def test_cli_emits_parseable_json_without_diagnostics() -> None:
    result = runner.invoke(app, [str(EXAMPLE), "--pack", "psu"])
    assert result.exit_code == 0, result.output
    parsed = json.loads(result.stdout)
    assert parsed["audit"]["pack_id"] == "electronics_psu"
    assert parsed["audit"]["state_version"] == "demo-1"
    assert parsed["status"] == "MISSING_DATA"
    assert [f["rule_id"] for f in parsed["findings"]] == [
        "PSU_DIVIDER_TOPOLOGY_UNKNOWN",
        "PSU_CAP_VOLTAGE_UNKNOWN",
    ]


def test_cli_writes_result_file(tmp_path: Path) -> None:
    output = tmp_path / "result.json"
    result = runner.invoke(app, [str(EXAMPLE), "--pack", "psu", "--out", str(output)])
    assert result.exit_code == 0, result.output
    assert result.stdout.strip() == f"wrote {output}"
    assert json.loads(output.read_text(encoding="utf-8"))["audit"]["pack_id"] == "electronics_psu"


def test_cli_rejects_unknown_pack() -> None:
    result = runner.invoke(app, [str(EXAMPLE), "--pack", "not_a_pack"])
    assert result.exit_code != 0
    assert "pack must be one of" in result.output


def test_cli_rejects_missing_input_file(tmp_path: Path) -> None:
    result = runner.invoke(app, [str(tmp_path / "does-not-exist.yaml")])
    # Rich truncates long paths differently across terminal widths and OSes.
    # Click's usage-error exit status is the stable negative-control contract.
    assert result.exit_code == 2
    assert "Error" in result.output


def test_cli_rejects_invalid_state(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.yaml"
    invalid.write_text("design_intent: incomplete\n", encoding="utf-8")
    result = runner.invoke(app, [str(invalid)])
    assert result.exit_code != 0


def test_cli_hard_fail_remains_json_reporter(tmp_path: Path) -> None:
    fixture = tmp_path / "hard.yaml"
    fixture.write_text(
        """design_intent: synthetic DC voltage fixture
version: cli-hard
components:
  COUT: {part_id: COUT, kind: capacitor, value: 470uF, max_voltage: 10}
rule_evidence:
  output_cap: {dc_voltage_v: 13.8, source: synthetic DC terminal voltage}
""",
        encoding="utf-8",
    )
    result = runner.invoke(app, [str(fixture), "--pack", "psu"])
    assert result.exit_code == 0, result.output
    parsed = json.loads(result.stdout)
    assert parsed["status"] == "HARD_FAIL"
    assert [f["severity"] for f in parsed["findings"]] == ["MISSING_DATA", "HARD"]
