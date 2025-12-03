Summary: Capture Stage A telemetry vs reconstructed bragg_before baselines so we can identify the first divergence that keeps DB-AT-028/029 at chi²≈2.1e5 before attempting further fixes.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: integration
Mapped tests: tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028, tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-13T190000Z/

Do Now:
- Implement: plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py — add a T2 probe that rebuilds the Stage A smoke pipeline (reuse build_mapping_stage_a_context + RefinementEngine) and records telemetry fields (`target_mean_masked`, `model_mean_masked`, `log_scale_effective`), masked/unmasked means from the reconstructed `bragg_before` tensor, and chi²-per-pixel numbers computed with the same loss mask so we can compare them in one JSON artifact.
- Update: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-13T190000Z/summary.md — summarize the probe output and correlate it with the DB-AT failures (cite which value diverges) so the next loop can either patch Stage A baseline math or escalate a spec/test mismatch.
- Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-13T190000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-13T190000Z/db_at_029 DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-13T190000Z/pytest_db_at_028_029.log`

How-To Map:
1. `mkdir -p plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-13T190000Z/{db_at_028,db_at_029}` so the script + pytest runs can drop JSON/telemetry artifacts without skips.
2. Implement `compare_stage_a_baseline.py` by copying the Stage A smoke setup from `tests/dbex/test_stage_a_smoke_parity.stage_a_smoke_result`: build the mapping context + perturbations, run `RefinementEngine([StageA()])`, collect `telemetry = result["stage_a"]`, and then call `build_final_bragg_from_stage_a_telemetry(..., param_state="initial")` to reconstruct `bragg_before`. Compute `(bragg_before[loss_mask].mean(), target[loss_mask].mean(), chi2_per_pixel_initial, log_scale_effective['initial'])` and emit a JSON payload plus stdout table so we can diff telemetry vs reconstructed values easily.
3. After the script runs, rerun DB-AT-028/029 with the env vars above. Make sure `pytest` logs end up beside the probe JSON so we can tie the new diagnostics directly to the failing selectors.

Pitfalls To Avoid:
- Keep the probe script in `plans/active/.../bin/` (T2 scope) and avoid touching shipped modules; it should import helpers but not mutate prod code.
- Reuse the same env vars (`DBEX_SMOKE_*`, `AUTHORITATIVE_CMDS_DOC`) that the tests expect so the probe and pytest operate on identical data/calibration.
- Ensure the script reports both masked and unmasked means; the masked version must use `inputs.loss_mask` so comparisons line up with the chi² gate.
- Do not change DB-AT thresholds or telemetry wiring—this loop is purely diagnostic.
- Watch GPU/CPU device handling: convert tensors to CPU before serializing to JSON to avoid dtype/device issues.
- Respect Environment Freeze: if the probe needs extra numpy/scipy bits, limit to stdlib + installed deps.

If Blocked:
- If the script cannot import the Stage A helpers (e.g., fixture dependencies missing), capture the traceback, drop it in `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-13T190000Z/probe_failure.log`, and note the failure in docs/fix_plan.md so we can decide whether to factor the fixture into a reusable helper.
- If DB-AT-028/029 still fail without producing artifacts (pytest skip), record the missing env var or error message in the same report dir and ping Galph before attempting another rerun.

Findings Applied:
- SCALE-009 (docs/findings.md) — treat Stage A scale telemetry as the source of truth when analyzing reconstruction failures.
- SCALE-005 (docs/findings.md) — include `apply_calibration_n_cells` and calibration metadata in the probe so intensity comparisons respect the same gating.

Pointers:
- plans/active/ARCH-SIM-CONSTRUCTION-001/implementation.md: Phase C.9 checklist for this probe loop.
- docs/fix_plan.md §ARCH-SIM-CONSTRUCTION-001 Attempts History (2025-12-13T190000Z entry) — rationale for the diagnostic pass.
- docs/spec-db-conformance.md:319-366 — DB-AT-028/029 acceptance thresholds that remain unmet.

Next Up (optional):
1. If the probe reveals the exact mismatch (e.g., telemetry masked mean differs from reconstructed masked mean), queue a follow-up loop to patch Stage A baseline math or open a spec-change initiative depending on the finding.
