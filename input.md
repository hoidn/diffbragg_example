Summary:
- Repoint Stage wrappers, StageA context helpers, and the reconstruction fast paths to consume `RefinementInputs` and the config builders from `dbex.refinement/{inputs,config_factories}.py` so the bridge re-export becomes a pure orchestration shim.

Mode: Parity

InitiativeType: architecture

Focus: ARCH-BRIDGE-RESP-001 — Writer / bridge responsibility split

Branch: integration

Mapped tests:
- tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion
- tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers
- tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip
- tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_runs_simulator
- tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata

Artifacts: plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-02T100041Z/

Do Now:
- Implement: `dbex/refinement/stage_a_impl.py::_build_stage_a_context` and `_compute_panel_loss` — import `create_detector_config`, `create_beam_config`, and `create_crystal_config` from `dbex.refinement.config_factories` at module scope (StageA context no longer pulls the bridge shim), keep `compute_baseline_misset_deg` sourced from `dbex.nanobrag_bridge`, and remove the duplicate local imports sprinkled inside helper functions.
- Implement: `dbex/refinement/stage_a.py::StageA.run` — drop the late-bound `dbex.nanobrag_bridge` import for config builders, import them from `dbex.refinement.config_factories`, and ensure the log-scale/telemetry logic continues to use the new modules while still calling `compute_baseline_misset_deg` from the bridge.
- Implement: `dbex/refinement/stage_b.py::StageB._build_lbfgs_closure` and `dbex/refinement/stage_c.py::StageC._build_lbfgs_closure` — switch the config imports to `dbex.refinement.config_factories` but continue to import geometry helpers (baseline misset, quaternion transforms) from the bridge. Verify warm-cache shims and CPU fallback paths both use the new factories.
- Implement: `dbex/refinement/reconstruction.py::{build_stage_a_bragg,build_stage_b_bragg}` — update their lazy imports so Detector/Crystal configs come from `dbex.refinement.config_factories` while `compute_baseline_misset_deg` still comes from the bridge. Confirm the reconstruction code paths used by Stage A/B artifact tests continue to emit the same Bragg tensors.
- Implement/tests: search `tests/dbex/test_refine_one_cli.py` for `@patch('dbex.nanobrag_bridge.` occurrences that intercept `prepare_refinement_inputs` or the config builders and retarget them to `dbex.refinement.inputs` / `dbex.refinement.config_factories` so the patched symbols match the new import sites inside the CLI.
- Validate: capture Stage A/B/C small-detector smoketests plus the targeted CLI selectors listed above under `plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-02T100041Z/` (stash logs and any telemetry JSONs next to the pytest outputs).

How-To Map:
1. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-02T100041Z/stage_a_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --maxfail=1`
2. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --maxfail=1`
3. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_STAGE_C_CACHE_DEBUG_PATH=plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-02T100041Z/stage_c_cache_debug_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --maxfail=1`
4. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_runs_simulator tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata --maxfail=1`

Pitfalls To Avoid:
- Do not move `compute_baseline_misset_deg`, quaternion math, or HKL helpers out of `dbex.nanobrag_bridge` in this loop; the focus is only on input/config wiring.
- Keep Stage A/B/C imports eager at module scope to honor the ARCH-REFINE-001 lazy-import cleanup—no new inline imports unless circular dependencies require it.
- Preserve dtype/device neutrality when swapping factories; do not introduce `.cuda()` or float downcasts while touching the stage helpers.
- CLI tests still expect deterministic DetectorConfig mask tensors (see DIAGNOSTICS-001/CLI-001); do not regress mask dtype/polarity when rewiring.
- Stage B per-reflection smoke remains blocked by ARCH-STAGE-CONTEXT-001 findings—only run the shell-mode selector listed above.
- Stage C full-detector smoke is still blocked by PERF-WARM-SIM-001; limit validation to the small-detector variant and record any ROI-mode failures as known issues.
- Ensure the reconstruction helpers still honor the calibration metadata path (`StageAArtifacts` uses these outputs); re-run if you touch the scale baseline math.
- Keep environment freeze in mind: no edits to `nanobrag_torch` or dependency installs.

If Blocked:
- If swapping the imports exposes a missing dependency (e.g., circular import that cannot be resolved), log the call stack and offending module in `plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-02T100041Z/blockers.md`, cite the exact traceback, and restore the previous import so the branch stays runnable.
- If any of the smoketests fail with a new signature (not the known Stage B per-reflection or Stage C full-detector issues), capture the pytest log under the artifacts directory, annotate the failure in docs/fix_plan.md (Attempts History), and halt for supervisor guidance instead of guessing at additional fixes.

Findings Applied (Mandatory):
- GEOMETRY-001/002/003 — detector/crystal mappings must stay DIALS-aligned when swapping factories.
- CONFIG-001 — maintain trusted-mask polarity and ADU↔photon handling in `RefinementInputs` when moving imports.
- DIAGNOSTICS-001 & PHYSICS-LOSS-001/002/003 — writer telemetry and variance-weighted loss expectations remain unchanged after the refactor.

Pointers:
- dbex/refinement/stage_a.py:184 (current bridge import block inside StageA.run)
- dbex/refinement/stage_b.py:42 (bridge imports used by StageB)
- dbex/refinement/reconstruction.py:68 (lazy import block feeding `build_stage_a_bragg`)
- docs/config_crosswalk.md:30-95 (mapping rules that the config factories already enforce)
- docs/TESTING_GUIDE.md:120-165 (env vars for Stage A/B/C smoketests)

Next Up (optional):
- Once these modules read directly from `dbex.refinement.{inputs,config_factories}`, we can plan Phase C.6 to delete the bridge re-export shim and update the remaining tooling/tests accordingly.
