"""Replay explicit design prerequisites through the installed Circuit-CI reporter."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from pydantic import ValidationError

from circuit_ci.core.schemas import LinterResult, Status

# The legacy input deliberately represents each unmet requirement only as text.
# This tests propagation of missing evidence, not knowledge of either device.
CASES = {
    "gift": {
        "baseline": "board revision and initial bench measurements pending",
        "controller": "selected Ethernet MAC interface has no matching PHY evidence",
        "gpio": "exclusive display and Ethernet chip-select share pin",
        "poe": "no rated powered-device conversion path is present",
        "power": "demand exceeds the declared available supply",
        "part": "selected controller electrical limits absent",
        "credentials": "read-only service endpoint unavailable",
        "stale": "last service sample expired while disconnected",
        "visibility": "unmirrored access port cannot supply network-wide traffic",
    },
    "spd": {
        "baseline": "connector identity and bench supply verification pending",
        "generation": "DDR5 connector assignment supplied for DDR4 device",
        "voltage": "VDDSPD operating limit unsupported by exact module evidence",
        "pullups": "I2C pull-ups absent with open-drain pins",
        "truncated": "captured SPD shorter than required",
        "crc": "reference fixture checksum disagrees",
        "revision": "SPD major revision unsupported by decoder",
        "readfail": "module did not acknowledge read",
        "array": "requested DRAM verdict exceeds metadata-only scope",
        "spec": "module rails and sequencing unspecified",
    },
}
PARTS = {
    "gift": {"U1": ("display_mcu", "ESP32-S3"), "NET": ("interface", "unverified Ethernet option")},
    "spd": {"U1": ("mcu", "metadata reader"), "J1": ("socket", "260-pin SO-DIMM candidate")},
}
INTENT = {
    "gift": "Freenove display network companion",
    "spd": "portable SO-DIMM SPD identification",
}


def projection(family: str, case: str, prerequisite: str) -> bytes:
    components = {
        key: {"part_id": key, "kind": kind, "value": value}
        for key, (kind, value) in PARTS[family].items()
    }
    model = {
        "design_intent": INTENT[family],
        "version": case,
        "constraints": {"vin_v": 5},
        "components": components,
        "missing_prerequisites": [prerequisite],
    }
    return (json.dumps(model, indent=2, sort_keys=True) + "\n").encode()


def main() -> int:
    executable = shutil.which("cci")
    if executable is None:
        print("Run inside the locked uv environment to resolve cci.", file=sys.stderr)
        return 2
    mismatches = 0
    with TemporaryDirectory() as temp:
        for family, contrasts in CASES.items():
            for label, prerequisite in contrasts.items():
                case = f"{family}-{label}"
                raw = projection(family, case, prerequisite)
                path = Path(temp) / f"{case}.json"
                path.write_bytes(raw)
                try:
                    result = subprocess.run(
                        [executable, str(path), "--pack", "psu"],
                        capture_output=True,
                        timeout=10,
                        check=False,
                    )
                    if result.returncode != 0:
                        print(f"{case}: reporter exited {result.returncode}", file=sys.stderr)
                        return 2
                    report = LinterResult.model_validate_json(result.stdout)
                except (OSError, subprocess.TimeoutExpired, ValidationError) as exc:
                    print(f"{case}: reporter error: {exc}", file=sys.stderr)
                    return 2
                if report.audit.state_version != case:
                    print(f"{case}: result belongs to a different input", file=sys.stderr)
                    return 2
                mismatches += report.status != Status.MISSING_DATA
                print(case, hashlib.sha256(raw).hexdigest(), result.returncode, report.status.value)
    print(f"{mismatches} unexpected verdict(s); all projections require MISSING_DATA.")
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
