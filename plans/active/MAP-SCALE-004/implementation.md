# MAP-SCALE-004 — Zero-iteration telemetry parity

## Purpose
Carry the refined structure-factor telemetry contract landed in the CLI into the zero-iteration helper (`simulate_forward_once`) and DB_AT_024 acceptance tests so regressions that drop refined MTZ usage are caught automatically.

## References
- `dbex/nanobrag_bridge.py` — Zero-iteration helper (`simulate_forward_once`, `simulate_forward_once_torch`)
- `tests/dbex/test_mapping_consistency.py` — DB_AT_024 acceptance harness
- `docs/spec-db-workflow.md` §4 — Calibration & refined structure-factor workflow
- `docs/spec-db-tracing.md` §2 — Torch diagnostics artifact expectations
- `docs/findings.md` — SCALE-003, SCALE-004 guardrails
- `docs/TESTING_GUIDE.md` §2, `docs/development/TEST_SUITE_INDEX.md` — Selector registry

## Exit Criteria
1. `simulate_forward_once` (and the torch-return helper) surfaces structure-factor telemetry dict (`hkl_source`, `hkl_n_reflections`, `hkl_mean_amplitude`, `hkl_path`) in its diagnostics payload, matching CLI semantics and handling refined vs raw MTZ inputs.
2. DB_AT_024 test asserts on telemetry: fails when refined assets are provided but telemetry reports `raw`, or when telemetry fields are absent; artifacts capture telemetry snapshot alongside ROI metrics.
3. Updated documentation/test registry entries describe the telemetry contract; new pytest + DB_AT_024 logs are archived under this initiative, and any new guardrails are recorded in `docs/findings.md`.

## Phase Breakdown

- **Phase A — Telemetry design**
  - [ ] A1: Audit `simulate_forward_once` / `simulate_forward_once_torch` to identify where to compute telemetry and ensure device/dtype neutrality.
  - [ ] A2: Define telemetry payload shape and fallbacks (e.g., empty path when MTZ absent, reflection count from `hkl_indices`) consistent with CLI implementation.
  - [ ] A3: Document gaps in DB_AT_024 (current string logging) and decide assertion strategy for refined vs raw scenarios.

- **Phase B — Implementation & Tests**
  - [ ] B1: Update bridge helpers to return telemetry in diagnostics and propagate canonical MTZ path; add unit/utility coverage if needed.
  - [ ] B2: Extend `tests/dbex/test_mapping_consistency.py` to assert telemetry fields and regression-fail when refined MTZ usage is lost.
  - [ ] B3: Refresh DB_AT_024 artifacts (collect/run) confirming telemetry surfaces as expected with canonical assets.

- **Phase C — Documentation & Knowledge Base**
  - [ ] C1: Update `docs/TESTING_GUIDE.md` and `docs/development/TEST_SUITE_INDEX.md` referencing telemetry assertions and artifact locations.
  - [ ] C2: Append durable lesson to `docs/findings.md` if telemetry contract introduces new guardrails.
  - [ ] C3: Ensure fix plan attempts history and selector registry cross-links are current; archive obsolete MAP-SCALE-003 references after closeout.

## Artifacts Index
- Reports root: `plans/active/MAP-SCALE-004/reports/`
- Planned scripts (if promoted): `plans/active/MAP-SCALE-004/bin/`
