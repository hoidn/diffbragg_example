Summary: Instrument Stage B’s baseline validation so it reproduces Stage A’s canonical chi² and add a parity guard to unblock REFINE-FLOW-001.
Mode: none
Focus: ARCH-REFINE-001 — Refinement Engine Modularization & Torch IO
Branch: integration
Mapped tests: pytest --collect-only tests/dbex/test_torch_refine_smoke.py -k "test_stage_b_shell_modifiers or test_stage_c_detector_microslip" --smoke-detector-size=small; pytest -vv tests/dbex/test_torch_refine_smoke.py -k "test_stage_b_shell_modifiers or test_stage_c_detector_microslip" --smoke-detector-size=small
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T151425Z/
Do Now:
- Implement: dbex/refinement/stage_b_impl.py::_run_stage_b_lbfgs — inject Stage A canonical chi² + telemetry into the Stage B param dict, emit a JSON diff (per panel, total, % delta) when the initial `compute_loss_stage_b(... force_panel_eval=True)` result exceeds a 0.1% tolerance, and raise a targeted RuntimeError (“REFINE-FLOW-001 baseline drift”) to keep the guard loud.
- Implement: dbex/refinement/stage_b.py::StageB.run — thread the canonical baseline payload + new parity diagnostics through `param_values` and `telemetry_b` (e.g., `stage_b_baseline_rel_diff`, `stage_b_baseline_diff_path`) so tests can assert parity without parsing logs.
- Implement: tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers — assert the new telemetry field reports ≤1e-3 relative difference (and fails with the guard otherwise); extend the combined Stage B/C selector if needed to keep Stage C covering the guard.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-001/reports/2025-12-01T151425Z/telemetry_stage_bc_small.json pytest -vv tests/dbex/test_torch_refine_smoke.py -k "test_stage_b_shell_modifiers or test_stage_c_detector_microslip" --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T151425Z/pytest_stage_bc_small.log
How-To Map:
1. Add a helper inside `_run_stage_b_lbfgs` that ingests `canonical_baseline`, computes the per-panel chi² using the existing panel loop, serializes `stage_b_baseline_diff.json` into the artifacts directory, and records `stage_b_baseline_rel_diff` + file path on the telemetry dict before raising if `abs(rel_delta) > 1e-3`.
2. Extend `StageB.run` so `param_values` carries the canonical dict and the absolute Stage A chi²; ensure `telemetry_b` includes the new fields and that the dataclass is still convertible via `asdict`.
3. Update `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` to read the telemetry JSON emitted via `DBEX_SMOKE_TELEMETRY_PATH` and assert `stage_b_baseline_rel_diff <= 1e-3`; keep the test parametrization identical so we don’t add new data deps.
4. Commands:
   a. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py -k "test_stage_b_shell_modifiers or test_stage_c_detector_microslip" --smoke-detector-size=small > plans/active/ARCH-REFINE-001/reports/2025-12-01T151425Z/collect_stage_bc_small.log`
   b. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-001/reports/2025-12-01T151425Z/telemetry_stage_bc_small.json pytest -vv tests/dbex/test_torch_refine_smoke.py -k "test_stage_b_shell_modifiers or test_stage_c_detector_microslip" --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T151425Z/pytest_stage_bc_small.log`
Pitfalls To Avoid:
- Do not relax the 0.1% tolerance—if parity fails, emit the JSON diff and raise; no silent clamps.
- Keep the instrumentation device/dtype neutral so CPU fallback (Stage B full runs) still works.
- Don’t mutate Stage A telemetry; create new telemetry fields for Stage B parity instead of overwriting canonical values.
- No additional dependencies/scripts; emit JSON via stdlib only and write into the provided artifacts path.
- Preserve existing ROI/panel sampling logic—only the initial forced-panel baseline should feed the guard.
- Ensure the guard uses Stage A canonical chi² captured before Stage B modifies shells; later iterations shouldn’t overwrite the reference.
- When updating tests, reuse existing fixtures (telemetry JSON via `DBEX_SMOKE_TELEMETRY_PATH`); don’t add new data assets.
- Keep logging quiet (single JSON file) so CI output stays readable.
If Blocked:
- If parity still fails after the guard changes, capture the generated `stage_b_baseline_diff.json` plus failing pytest log, set ARCH-REFINE-001 Attempts History to "blocked on REFINE-FLOW-001 delta persists", and stop rather than downgrading the tolerance.
Findings Applied (Mandatory):
- REFINE-FLOW-001 — Guarded chi² parity between Stage A canonical results and Stage B baseline.
- ARCH-ENGINE-003 — Telemetry enrichment stays on the engine path; new fields must flow through RefinementTelemetry.
- PHYSICS-LOSS-001 — Baseline comparison uses variance-weighted chi², no alternate metrics.
- POLICY-001 — Environment stays frozen; diagnostics must use existing deps/data.
Pointers:
- docs/spec-db-workflow.md:54 — Stage B delegation rules (halo, interpolation, forced panel validations).
- docs/spec-db-core.md:106 — Variance-weighted chi² definition that the parity guard must honor.
- docs/findings.md:71 — REFINE-FLOW-001 details and the 0.1% tolerance requirement.
- docs/data_dependency_manifest.md:52 — refGeom_small + sigma-map assets required for the small-detector smoke.
- plans/active/ARCH-REFINE-001/implementation.md:106 — Phase E checklist covering Stage B baseline parity scope.
Next Up (optional): Phase E.2 — once instrumentation lands, adjust Stage B reconstruction so the guard passes without manual tolerances and rerun the same selectors.
