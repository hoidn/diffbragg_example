Summary: Cache the Stage A zero-iteration Bragg stack in StageAContext/artifacts and teach `build_final_bragg_from_stage_a_telemetry` to reuse it for `param_state="initial"` so bragg_before matches Stage A telemetry.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: integration
Mapped tests: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-15T150000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-15T150000Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-15T150000Z/

Do Now:
- Implement: `dbex/refinement/context.py::StageAContext` — add an optional `bragg_zero_iter` (np.ndarray) field (default `None`) to carry the zero-iteration Stage A Bragg stack.
- Implement: `dbex/refinement/stage_a.py` — in the warm-cache baseline block that already computes `bragg_stack_scaled = torch.stack(...) * sqrt_spot_scale`, stash a float32 CPU copy on the context whenever warm cache is active (e.g., `stage_a_ctx.bragg_zero_iter = bragg_stack_scaled.detach().cpu().numpy().astype(np.float32)`). Guard failures so cold-mode runs remain valid.
- Implement: `dbex/refinement/reconstruction.py::build_final_bragg_from_stage_a_telemetry` — before the warm/cold simulator path, detect when `param_state == "initial"` and `stage_a_ctx.bragg_zero_iter` is populated; if so, log the cache hit and return a copy of the cached array instead of rerunning simulators. Preserve existing behavior for legacy contexts and `param_state="final"`.
- Implement: extend `tests/dbex/test_artifact_parity.py` (or an adjacent parity test) with a coverage case that asserts `build_final_bragg_from_stage_a_telemetry(..., param_state="initial")` equals the cached zero-iteration array when Stage A artifacts provide one. This guards the new fast-path.
- Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-15T150000Z/stage_a_baseline_probe.json` (verify the report shows `bragg_vs_telem_model≈1.0`).
- Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-15T150000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-15T150000Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-15T150000Z/pytest_db_at_028_029.log`.

How-To Map:
1. Update `StageAContext` with the new optional field so all existing initializations remain valid (default `None`).
2. In `stage_a.py`, reuse the tensors already computed for baseline telemetry to populate the cache: after `bragg_stack_scaled` is available and before any log-scale adjustments, write a CPU copy to `stage_a_ctx.bragg_zero_iter`. Wrap in a `try/except` so cold-mode contexts simply leave the field `None`.
3. In `build_final_bragg_from_stage_a_telemetry`, inspect the context before touching simulators. If the cache is populated and we’re reconstructing the initial state, emit a short log (for debug) and return `np.array(stage_a_ctx.bragg_zero_iter, copy=True)` to avoid downstream mutation.
4. Extend the artifact-parity test: run a Stage A-only refinement (fixture already exists), assert that the helper returns the cached zero-iteration array when `param_state="initial"`. This ensures future refactors cannot regress the cache path.
5. After code compiles, rerun the baseline probe and DB-AT selectors with the new timestamp so the artifacts capture the improved masked-mean parity.

Pitfalls To Avoid:
- Do not store GPU tensors inside the cache — convert to CPU float32 numpy arrays before assigning to avoid lifetime/device issues.
- Keep the cache optional; cold-mode or CPU-only runs without warm cache must continue to fall back to the simulator path without failing assertions.
- Returning the cached array should produce a copy so downstream consumers (writers/tests) can mutate safely.
- Ensure the new parity test resets any global artifacts so other tests are unaffected.
- Remember that Stage A runs may package large arrays; avoid double-storage by reusing the computed tensor instead of rerunning simulations solely for caching.

If Blocked:
- If storing the cache triggers OOM or serialization issues, capture a short note plus the traceback under the new report directory and fall back to the existing simulator path for that loop (keep the instrumentation disabled), then notify me for reprioritization.
- If the parity test cannot reliably access the cached array (e.g., fixture lacks warm cache), add a minimal fixture that forces warm cache on, document it in the test module, and highlight any trade-offs in the report.

Findings Applied (Mandatory):
- SCALE-009 — Reconstruction helpers must replay Stage A telemetry faithfully; caching the actual zero-iteration Bragg stack keeps bragg_before aligned with Stage A’s masked intensity baseline.
- SCALE-008 — Stage A warm-cache data should remain authoritative for downstream consumers; avoid recomputation that drifts after warm-cache mutations.

Pointers:
- dbex/refinement/context.py
- dbex/refinement/stage_a.py (baseline telemetry block around lines 400–470)
- dbex/refinement/reconstruction.py::build_final_bragg_from_stage_a_telemetry
- tests/dbex/test_artifact_parity.py
- plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py
