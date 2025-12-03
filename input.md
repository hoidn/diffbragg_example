Summary: Rebuild DB-AT-028/029 so their "before" metrics use the Stage A telemetry baseline instead of raw simulate_forward_once output, eliminating the false failures after C.8.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: integration
Mapped tests: tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028, tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-13T120000Z/

Do Now:
- Implement: dbex/refinement/reconstruction.py::build_final_bragg_from_stage_a_telemetry — add a `param_state` (initial|final) switch that replays Stage A telemetry with either the initial or final param deltas, including log_scale baseline+delta math and misset/cell overrides, so we can rebuild the zero-iteration Bragg stack directly from telemetry.
- Implement: tests/dbex/test_stage_a_smoke_parity.py::stage_a_smoke_result — replace the `simulate_forward_once` call with two invocations of `build_final_bragg_from_stage_a_telemetry` (one with `param_state="initial"` for `bragg_before`, one with `param_state="final"` for `bragg_after`), keeping the existing diagnostics/metrics wiring intact.
- Update: tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity / test_db_at_029_structure_parity — ensure the fixtures still emit metrics under `DBAT028_ARTIFACT_DIR`/`DBAT029_ARTIFACT_DIR` and document in the metrics JSON that `bragg_before` now comes from telemetry so reviewers understand the new source.
- Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-13T120000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-13T120000Z/db_at_029 DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-13T120000Z/pytest_db_at_028_029.log`

How-To Map:
1. `mkdir -p plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-13T120000Z/{db_at_028,db_at_029}` before editing so pytest artifacts have a home.
2. In `dbex/refinement/reconstruction.py`, add a helper to fetch telemetry values by state (initial/final) and thread that through log_scale, cell deltas, angle deltas, and misset vectors. When `param_state="initial"`, use the `initial` entries from `param_deltas`; when telemetry lacks an `initial` value fall back to `final` but log a warning so we can follow up later. Keep the warm-cache shortcut working by retargeting simulators after you’ve applied the requested state.
3. In `tests/dbex/test_stage_a_smoke_parity.py::stage_a_smoke_result`, drop the `simulate_forward_once` call entirely. After `telemetry = engine.run(...)`, call `build_final_bragg_from_stage_a_telemetry(..., param_state="initial")` for `bragg_before` and the same helper with `param_state="final"` for `bragg_after`. Pass the perturbed detector/beam/crystal, the refinement inputs, HKL grid/metadata, and the same `config`/`device` objects so reconstruction matches Stage A. Keep the existing ROI correlation + metrics logic untouched.
4. Update the metrics dict written under `DBAT028_ARTIFACT_DIR`/`DBAT029_ARTIFACT_DIR` to include a note (e.g., `"bragg_before_source": "stage_a_telemetry_initial"`) so history shows why the numbers changed.
5. Run the pytest command above with the env vars shown; on success you should see `chi2_per_pixel_initial` and ROI median corr hit their spec bands. Keep the pytest log plus the refreshed metrics JSON in the report directory.

Pitfalls To Avoid:
- Do not remove or refactor `simulate_forward_once` outside this fixture; other tools still rely on it.
- Keep the telemetry replay device/dtype neutral (reuse the `config.device`/`config.dtype` and fall back gracefully if a tensor conversion fails).
- Make sure the helper handles telemetry emitted before `param_deltas['misset_xyz_deg']['initial']` existed (we still have older artifacts).
- Preserve Stage A warm-cache retargeting semantics; only fall back to the cold path when no cache exists.
- Do not relax DB-AT thresholds or try to short-circuit the tests; the goal is to fix the baseline logic, not downgrade the acceptance criteria.
- No environment tweaks per Environment Freeze—if nanobrag_torch throws, stop and log the error.
- Remember to `mkdir -p` the artifact dirs so pytest doesn’t skip when it tries to write metrics.

If Blocked:
- If the telemetry lacks the `initial` values needed to rebuild `bragg_before`, capture the offending telemetry JSON (dump to the report dir), leave the helper falling back to the legacy simulate_forward_once path temporarily, and mark the loop blocked in docs/fix_plan.md + galph_memory.md explaining which telemetry fields were missing.
- If DB-AT-028/029 still report chi²>1e2 after the change, archive the pytest log + metrics JSON under the new report path, note the exact numbers, and ping Galph so we can decide whether the test gates need their own update.

Findings Applied:
- SCALE-009 (docs/findings.md) — reconstruction/test harnesses must consume the same Stage A baseline telemetry so we don’t double-apply spot_scale.
- DIAG-OVERSAMPLE-001 (docs/findings.md) — keep the detector/simulator construction path untouched; we’re only changing how we replay telemetry.

Pointers:
- docs/fix_plan.md:133 — initiative summary + latest Attempts History.
- plans/active/ARCH-SIM-CONSTRUCTION-001/implementation.md:310 — Phase C.8 checklist (now includes the harness alignment bullet).
- docs/spec-db-conformance.md:280 — DB-AT-028/029 acceptance criteria we’re satisfying.

Next Up (optional):
1. If this passes quickly, re-run the scale-alignment probe with the updated helper to confirm `log_scale_delta_clamped` stays ≈0 and attach it to the report for regression tracking.
