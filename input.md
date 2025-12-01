Summary: Move Stage C LBFGS helpers (params/closure/run + warm-cache retarget helper) into `dbex/refinement/stage_c_impl.py` so Stage C no longer depends on `dbex.nanobrag_refinement` and both inline + engine paths share one implementation.
Mode: Parity
Focus: ARCH-REFINE-001 — Refinement Engine Modularization & Torch IO
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T090517Z/
Do Now:
- Implement: dbex/refinement/stage_c_impl.py::_build_stage_c_params — create a Stage C helper module mirroring `stage_b_impl` (owning `_build_stage_c_params/_build_stage_c_lbfgs_closure/_run_stage_c_lbfgs` plus `_retarget_stage_a_detectors`), update `dbex/refinement/stage_c.py` and `dbex/nanobrag_refinement.py` to import from it, and ensure telemetry/perf counters + warm-cache semantics are identical for inline and engine paths (PHYSICS-LOSS-001/002, PERF-WARM-006).
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-001/reports/2025-12-01T090517Z/telemetry_stage_c_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T090517Z/pytest_stage_c_small.log
How-To Map:
1. mkdir -p plans/active/ARCH-REFINE-001/reports/2025-12-01T090517Z
2. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T090517Z/collect_stage_c_small.log
3. Implement the Stage C extraction:
   • Copy `_build_stage_c_params`, `_build_stage_c_lbfgs_closure`, `_run_stage_c_lbfgs`, and the `_retarget_stage_a_detectors` helper out of `dbex/nanobrag_refinement.py` into a new module `dbex/refinement/stage_c_impl.py`, keeping imports (nanobrag_torch, dbex.nanobrag_bridge, StageAContext APIs) lazy just like Stage B/A modules.
   • Update `dbex/refinement/stage_c.py` to import the helpers from `stage_c_impl` instead of `dbex.nanobrag_refinement` and remove any obsolete lazy imports.
   • Update `dbex/nanobrag_refinement.py` to import the helpers from `dbex.refinement.stage_c_impl`, delete the original helper definitions, and ensure Stage C inline branch + helper references (`_build_stage_c_params`, `_build_stage_c_lbfgs_closure`, `_run_stage_c_lbfgs`, `_retarget_stage_a_detectors`) only come from the new module (verify via `rg -n "_build_stage_c" dbex`).
   • Keep `_retarget_stage_a_detectors` available to both Stage C warm-cache code paths (LBFGS closure + final reconstruction loops) and maintain Stage A context mutation semantics documented in PERF-WARM-006.
4. Run the Stage C smoke: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-001/reports/2025-12-01T090517Z/telemetry_stage_c_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T090517Z/pytest_stage_c_small.log (ensure telemetry shows ≥80% offset reduction + ≤0.05% chi² regression per REFINE-007.)
Pitfalls To Avoid:
- Do not reintroduce circular imports (`stage_c_impl` must not import `dbex.nanobrag_refinement`); keep helper deps limited to StageAContext utilities + nanobrag_bridge.
- Preserve Stage C warm-cache retargeting semantics (`stage_a_ctx` mutation, ROI bookkeeping, PERF-WARM-006) so ROI vs panel metrics do not drift.
- Maintain PHYSICS-LOSS-001/002 telemetry fields (dual chi²/masked-MSE traces, variance-floor counters) and baseline detector distance bookkeeping when moving helpers.
- Keep CPU fallback/device-neutral tensor allocations; never call `.cuda()` or stash device-specific globals in the helper module.
- Don't touch environment/toolchain state (POLICY-001); treat missing imports or CUDA errors as blockers and log them.
- Ensure Stage C inline path and engine wrapper both import the same helper module so telemetry + regulator gates remain identical (REFINE-007-EXT, ARCH-ENGINE-002).
- Avoid touching other shared telemetry/dataclasses while relocating code; only Stage C helpers should move this loop.
- Keep `DBEX_SMOKE_TELEMETRY_PATH` artifacts unique per run; do not overwrite Stage B logs.
- After refactor, ensure `rg -n "_build_stage_c" dbex/nanobrag_refinement.py` returns only import lines (no stray definitions left behind).
If Blocked:
- Capture the stack trace or pytest failure plus relevant snippets (e.g., telemetry JSON, rg output) under the artifacts directory, append the blocker details to `docs/fix_plan.md` Attempts History, and log the same context in `galph_memory.md` before pausing.
Findings Applied (Mandatory):
- REFINE-007 (docs/findings.md:60) — Stage C smokes must prove ≥80% distance-offset reduction with ≤0.05% chi² regression; keep telemetry wiring intact.
- REFINE-007-EXT (docs/findings.md:74) — Engine + inline telemetry schemas must stay identical when Stage C helpers move.
- PERF-WARM-006 (docs/findings.md:22) — Warm caches must reuse Stage A detectors/masks; `_retarget_stage_a_detectors` extraction must preserve ROI cache semantics.
- PHYSICS-LOSS-001/002 (docs/findings.md:30-33) — Maintain variance-weighted chi² + masked-MSE traces and variance-floor counters when relocating helpers.
- POLICY-001 (docs/index.md:12) — Environment freeze; no package installs or toolchain changes.
Pointers:
- plans/active/ARCH-REFINE-001/implementation.md:51 — Phase A checklist calling for Stage C helper migration.
- dbex/nanobrag_refinement.py:254 — Current Stage C helper definitions that must move into stage_c_impl.
- dbex/refinement/stage_c.py:1 — Engine wrapper still lazy-imports helpers from `dbex.nanobrag_refinement` and needs rewiring.
- docs/spec-db-workflow.md:49 — Normative Stage B/C interpolation + detector rules to respect during refactor.
- docs/TESTING_GUIDE.md:161 — Canonical Stage B/C smoke selector with required env vars / gates.
- docs/data_dependency_manifest.md:1 — Smoke dataset and calibration asset provenance; keep Stage C test inputs aligned with manifest defaults.
Next Up (optional):
1. Re-run `test_stage_b_shell_modifiers` + per-reflection smokes to capture post-refactor telemetry once Stage C helpers land.
2. Start Phase B1 (`refinement/context.py`) once Stage C extraction and validation are stable.
