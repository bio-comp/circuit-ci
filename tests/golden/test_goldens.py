import yaml

from circuit_ci.core.schemas import CircuitState
from circuit_ci.packs.opamp.pack import lint as lint_opamp
from circuit_ci.packs.psu.pack import lint as lint_psu


def _load(path: str):
    return yaml.safe_load(open(path, "r", encoding="utf-8").read())


def test_psu_goldens():
    cases = _load("benchmarks/golden/psu_cases.yaml")
    for c in cases:
        st = CircuitState.model_validate(c["state"])
        res = lint_psu(st)
        assert res.status.value == c["expect"]["status"], c["id"]
        assert [f.rule_id for f in res.findings] == c["expect"]["rules"], c["id"]


def test_opamp_goldens():
    cases = _load("benchmarks/golden/opamp_cases.yaml")
    for c in cases:
        st = CircuitState.model_validate(c["state"])
        res = lint_opamp(st)
        assert res.status.value == c["expect"]["status"], c["id"]
        assert [f.rule_id for f in res.findings] == c["expect"]["rules"], c["id"]
