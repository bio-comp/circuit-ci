## Scope and owning issue

Issue:

## Verification

- [ ] Applicable local quality gates passed for the outgoing commit.
- [ ] Required CI checks passed for the current PR HEAD.

## Documentation audit (required for every PR)

- Paths inspected:
- Documentation changes (or evidence-based no-change rationale):
- Examples, CLI behavior and schema/contract claims checked against implementation:
- Local `uv run --locked zensical build --clean` and output-check results:
- Observed PR `documentation` check result and run link (pending until emitted):

- [ ] Documentation audit is recorded, and the documentation build and PR check pass.

A passing build validates supported links and anchors, not semantic accuracy.
Do not merge or close the owning issue before the audit and applicable gates pass.
