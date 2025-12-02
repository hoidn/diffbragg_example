Summary: Hoist Stage A/C stage-wrapper dependencies to module scope so LBFGS closures stop importing config factories and standard libs on every iteration, then re-run the Stage A smokes plus the known-failing Stage C smoke to confirm no new regressions.
Mode: none
InitiativeType: architecture
Focus: ARCH-LAZY-IMPORTS-001 — Lazy imports / process-noise hygiene
Branch: integration
Mapped tests:
- KMP_DUPLICATE_LIB_OK=TRUE DBEX_SMOKE_DETECTOR_SIZE=small pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion
- KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_engine_delegation_telemetry
- KMP_DUPLICATE_LIB_OK=TRUE DBEX_SMOKE_DETECTOR_SIZE=small pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip (expected ARCH-TELEMETRY-001 failure; capture log + assertion text)
Artifacts: plans/active/ARCH-LAZY-IMPORTS-001/reports/2025-12-04T010500Z/
Do Now:
- Implement: dbex/refinement/stage_a.py::_build_lbfgs_closure — add module-scope imports for `create_detector_config`, `create_beam_config`, `create_crystal_config`, and `compute_baseline_misset_deg` plus `os/json/sys`; drop the inline import blocks inside the closure and per-panel diagnostics writer so the Stage A loop just references the top-level names.
- Implement: dbex/refinement/stage_a.py::telemetry JSON writers — reuse the module-level `json`, `Path`, and `sys` imports instead of re-importing per call, keeping the existing exception handling/logging intact.
- Implement: dbex/refinement/stage_c.py::_build_lbfgs_closure/compute_loss_stage_c — add module-scope `import os` (shared with Stage A), rely on the existing module-scope Detector/Crystal/Simulator/config factory imports, remove the inline `import math`/`from nanobrag_torch...` blocks, and make sure the warm-cache diagnostics still emit under the ARCH-TELEMETRY-001 guard.
- Validate: run the three mapped selectors (Stage A smokes expected PASS, Stage C smoke expected to fail with the known `loss_trace_sample` assertion) and save each log under the artifacts directory.
How-To Map:
1. After editing, verify no remaining non-exempt inline imports: `rg -n "^\s+import " dbex/refinement/stage_a.py dbex/refinement/stage_c.py | grep -v derive_orientation | grep -v quaternion_to_matrix` (allowlist the documented geometry helpers only).
2. `KMP_DUPLICATE_LIB_OK=TRUE DBEX_SMOKE_DETECTOR_SIZE=small pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion | tee plans/active/ARCH-LAZY-IMPORTS-001/reports/2025-12-04T010500Z/pytest_stage_a_expansion.log`
3. `KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_engine_delegation_telemetry | tee plans/active/ARCH-LAZY-IMPORTS-001/reports/2025-12-04T010500Z/pytest_stage_a_engine_telemetry.log`
4. `KMP_DUPLICATE_LIB_OK=TRUE DBEX_SMOKE_DETECTOR_SIZE=small pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip | tee plans/active/ARCH-LAZY-IMPORTS-001/reports/2025-12-04T010500Z/pytest_stage_c_smoke.log` (annotate the log noting the expected ARCH-TELEMETRY-001 failure signature: `AssertionError: Stage C sample loss trace empty`).
Pitfalls To Avoid:
- Do not move the optional geometry helper imports (`derive_orientation_from_quaternion_delta`, `matrix_to_quaternion`, etc.); those stay lazy per ARCH-ENGINE-002 exceptions.
- Keep telemetry semantics untouched—only change where the imports live. Chi-squared logging and perf counters must match previous behavior.
- Leave Stage B files alone; this loop targets only Stage A/C wrappers.
- Stage C smoketest currently fails upstream; treat any new failure signature as a regression and capture it.
- Maintain Environment Freeze: no new dependencies or build steps—just Python edits/tests.
- Respect existing typing/comment structure; avoid changing docstrings beyond import cleanup.
If Blocked:
- If Stage A selectors fail or Stage C emits a *different* assertion than the known empty `loss_trace_sample`, stop, capture the log in the artifacts directory, and update docs/fix_plan.md + galph_memory.md describing the new signature so we can escalate to ARCH-TELEMETRY-001.
Findings Applied (Mandatory):
- ARCH-ENGINE-002 — Stage wrappers must expose dependencies at module scope unless explicitly exempted.
- GEOMETRY-001 — Detector/beam configs derived via config factories must remain authoritative when hoisting imports.
- RUNTIME-001 — Keep torch.compile/gradcheck guardrails intact by avoiding new runtime branching in the closures.
Pointers:
- plans/active/ARCH-LAZY-IMPORTS-001/implementation.md:72 (Phase B.3 checklist + validation expectations for this loop).
- docs/fix_plan.md:147 (initiative entry, attempts history, and problems-ledger linkage).
- docs/spec-db-workflow.md:49 (refinement protocol architecture governing Stage A/C responsibilities while editing the wrappers).
Next Up (optional):
- Once these eager-import changes land, the next obvious follow-up is tackling Phase C process-noise cleanup (docstrings + hygiene selector) before moving on to the Stage C telemetry collector fix tracked under ARCH-TELEMETRY-001.
