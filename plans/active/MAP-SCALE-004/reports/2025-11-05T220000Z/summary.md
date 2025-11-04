# MAP-SCALE-004 Planning Summary — 2025-11-05T220000Z

## Context
- MAP-SCALE-003 landed refined MTZ telemetry for the CLI (`dbex/refine_one.py:225-442`) and regression tests (`tests/dbex/test_refine_one_cli.py:348-576`), giving downstream tooling visibility into refined vs raw structure-factor usage.
- Zero-iteration helper `simulate_forward_once` remains the backbone of DB_AT_024 but only exposes `hkl_stats` in diagnostics; telemetry fields (`hkl_source`, counts, mean amplitude, MTZ path) are missing, so acceptance coverage cannot detect regressions that silently switch back to raw MTZ.
- DB_AT_024 currently prints a human-readable `hkl_source` string (derived from canonical asset lookup) without assertions, allowing refined telemetry regressions to pass unnoticed.

## Evidence
- `dbex/nanobrag_bridge.py:843-1120` — `simulate_forward_once` builds HKL grid and returns diagnostics dict without telemetry keys.
- `tests/dbex/test_mapping_consistency.py:199-347` — Acceptance test logs HKL source strings but lacks enforced assertions on telemetry or canonical MTZ usage.
- `docs/TESTING_GUIDE.md:71-99` — Registry documents DB_AT_024 thresholds yet does not mention telemetry guardrails for refined structure factors.

## Decisions
- Mirror the CLI telemetry payload inside `simulate_forward_once` (and the torch-return variant) so diagnostics always include `hkl_source`, reflection count, mean amplitude, and the MTZ path actually consumed.
- Harden DB_AT_024 to require telemetry when refined assets are present, failing fast if the helper reports `raw` or omits fields.
- Refresh selector documentation and artifacts to showcase the telemetry snapshot, ensuring downstream analysts can trace refined structure-factor provenance.

## Next Steps
1. Implement telemetry propagation in zero-iteration helpers and add unit coverage where appropriate.
2. Extend DB_AT_024 assertions + artifact capture to require telemetry for refined runs.
3. Synchronize selector docs (`docs/TESTING_GUIDE.md`, `docs/development/TEST_SUITE_INDEX.md`) and record any new guardrails in `docs/findings.md`.
