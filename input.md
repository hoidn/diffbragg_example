Summary: Remove the inline Stage B/C execution branch so `run_nanobrag_refinement` always goes through RefinementEngine and proves Stage B + Stage C smokes still pass with telemetry intact.
Mode: Parity
Focus: ARCH-REFINE-001 — Refinement Engine Modularization & Torch IO
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py -k "test_stage_b_shell_modifiers or test_stage_c_detector_microslip" --smoke-detector-size=small
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T092807Z/
Do Now:
- Implement: dbex/nanobrag_refinement.py::run_nanobrag_refinement (plus dbex/refinement/stage_c.py::StageC.run and dbex/refinement/engine.py::RefinementEngine.run) — delete the inline Stage A/B/C branch, make engine delegation the only path (Stage lists derived from config flags), and surface Stage C’s `bragg_full` output through the engine so final Bragg reconstruction comes from `stage_c_impl` instead of the removed inline loop.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-001/reports/2025-12-01T092807Z/telemetry_stage_bc_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py -k "test_stage_b_shell_modifiers or test_stage_c_detector_microslip" --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T092807Z/pytest_stage_bc_small.log
How-To Map:
1. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py -k "test_stage_b_shell_modifiers or test_stage_c_detector_microslip" --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T092807Z/collect_stage_bc_small.log
2. Update `dbex/nanobrag_refinement.py::run_nanobrag_refinement` so it always instantiates `RefinementEngine([StageA(), StageB?, StageC?])`, removes `stage_a_only_mode/stage_a_b_mode` special cases, deletes the inline helper branch, and rebuilds final Bragg frames after the engine run via `_build_final_bragg_from_stage_a_telemetry` (Stage A only), `_build_final_bragg_from_stage_b_telemetry` (Stage A→B), or the Stage C bragg cache once that flow is wired. Preserve telemetry enrichment (`engine_protocol`, `stage_modes`) on the objects returned from the engine.
3. Modify `dbex/refinement/stage_c.py::StageC.run` to propagate the `bragg_full` array returned by `_run_stage_c_lbfgs` (e.g., attach it to the dict returned to the engine), and teach `dbex/refinement/engine.py::RefinementEngine.run` to capture/remove this field before constructing `RefinementTelemetry`, storing it (and a reference to the producing stage) so callers can access it after `run()`.
4. Remove or hard-deprecate `--use-engine-delegation` plumbing in `dbex/refine_one.py` and the smoke fixtures so tests exercise the new default path without needing an extra flag; make sure CLI args still honor `enable_stage_b/enable_stage_c` while always delegating to the engine.
5. Re-run the mapped smoke command with `DBEX_SMOKE_TELEMETRY_PATH` set to capture merged Stage B + C telemetry JSON in `plans/active/ARCH-REFINE-001/reports/2025-12-01T092807Z/telemetry_stage_bc_small.json`.
Pitfalls To Avoid:
- Do not drop Stage B CPU fallback logic (GRADIENT-003/PERF-WARM-011) when removing the inline branch; reuse the engine’s cached shell metadata and stage_a_ctx device cloning.
- Keep Stage C baseline-detector guards: raise early if `baseline_detector` is missing before appending `StageC()` to the stage list.
- Preserve PHYSICS-LOSS-001/002 telemetry fields and REFINE-007 improvement gates when plumbing bragg buffers through the engine; no shortcuts that skip variance-floor accounting.
- Maintain device/dtype neutrality; no `.cuda()` shortcuts when rebuilding Bragg arrays for Stage A/B reconstruction helpers.
- Keep `DBEX_SMOKE_*` env precedence aligned with docs/data_dependency_manifest.md; never hardcode dataset paths inside the refactor.
- Do not mutate environment/toolchain state (POLICY-001); treat missing imports as blockers and log them.
- Ensure tests and CLI defaults continue to request Stage B/C via config flags; do not silently force Stage C to run when config disables it.
- Update telemetry enrichment (ARCH-ENGINE-003) so new code paths still set `engine_protocol`/`stage_modes`.
- After the refactor, verify `rg -n "_build_stage_[ab]" dbex/nanobrag_refinement.py` only references helper imports (no leftover inline functions).
If Blocked:
- Capture the failing pytest log plus any stack traces under `plans/active/ARCH-REFINE-001/reports/2025-12-01T092807Z/`, note the failure signature + selector in `docs/fix_plan.md` Attempts History, and log the same context (including env vars and call stack) in `galph_memory.md` before marking the initiative blocked.
Findings Applied (Mandatory):
- REFINE-FLOW-001 — Final Bragg reconstruction after Stage B must match the inline helper semantics; reuse `_build_final_bragg_from_stage_b_telemetry` and engine caches to avoid chi² drift.
- REFINE-007 / REFINE-007-EXT — Stage C detector offsets must still deliver ≥80% improvement with telemetry parity between inline and engine paths.
- ARCH-ENGINE-002 / ARCH-ENGINE-003 — Stage wrappers must keep protocol + telemetry enrichment consistent; engine output keys must remain stable.
- PHYSICS-LOSS-001/002 — Variance-weighted chi² + masked-MSE traces and variance-floor counters are required; no telemetry fields can be dropped while rewiring.
- GRADIENT-003 — CPU fallback remains CUDA-only until we can rebuild HKL grids on CPU; do not attempt to enable Stage B CPU fallback beyond current guardrails.
Pointers:
- dbex/nanobrag_refinement.py:496 — `run_nanobrag_refinement` still contains the Stage A/B/C inline path that must be removed.
- dbex/refinement/stage_c.py:1 — Stage C wrapper currently discards the `bragg_full` buffer; update it to expose the final frame to the engine.
- dbex/refinement/engine.py:74 — Engine aggregation strips custom fields before constructing `RefinementTelemetry`; expand this logic to cache Stage C’s `bragg_full`.
- docs/spec-db-workflow.md:33 — Normative staging contract that mandates a single protocol engine rather than bespoke inline flows.
- docs/TESTING_GUIDE.md:161 — Canonical Stage B/C smoke selector, env expectations, and gating thresholds for validation.
- docs/data_dependency_manifest.md:25 — Source-of-truth for smoke dataset assets (`sp.proc/refGeom_*`), so the refactor does not silently swap inputs.
Next Up (optional):
1. Once engine-only routing ships, start Phase B (RefinementContext/JobContext builders) so Stage wrappers consume structured inputs instead of dicts.
2. Follow up on the RefinementConfig attribute drift noted in Phase A.3 (missing telemetry_output_dir / log_cell_max_delta) after this loop passes.
