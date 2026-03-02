# Benchmarks

Circuit-CI benchmarks compare:
- Baseline: LLM-only (freeform or weakly constrained)
- Circuit-CI: constrained edits + lint + staging + routing

Metrics:
- schema_valid_rate
- hard_violation_rate
- bluff_rate (claims success with missing prereqs)
- staging_pass_rate
- iterations_to_pass
- review_friction (# conflicts + # measurements)

v0 includes a small golden suite; expand to 30+ cases (PSU + opamp).
