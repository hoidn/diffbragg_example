Summary: Plan quaternion→misset plumbing and deterministic perturbation so Stage A clears the ≥5% gate with full telemetry.
Mode: none
Focus: TORCH-REFINE-002 — Stage A expansion — full crystal and orientation
Branch: integration
Mapped tests: pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --maxfail=1
Artifacts: plans/active/TORCH-REFINE-002/reports/2025-11-05T033936Z/

Do Now:
- TORCH-REFINE-002
  - Implement: dbex/nanobrag_refinement.py::run_nanobrag_refinement — map `orientation_vec` to a bounded quaternion→XYZ misset override, plumb it through `dbex/nanobrag_bridge.py::create_crystal_config` without reintroducing MOSFLM A* injection, and extend `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` with a deterministic refGeom perturbation that drives ≥5% masked-MSE improvement plus telemetry assertions for the new orientation deltas.
  - Validate: pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --maxfail=1
  - Artifacts: plans/active/TORCH-REFINE-002/reports/2025-11-05T033936Z/

How-To Map:
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion | tee plans/active/TORCH-REFINE-002/reports/2025-11-05T033936Z/collect_stage_a.log
3. KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --maxfail=1 | tee plans/active/TORCH-REFINE-002/reports/2025-11-05T033936Z/pytest_stage_a.log
4. (Optional) KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion -k telemetry_snapshot | tee plans/active/TORCH-REFINE-002/reports/2025-11-05T033936Z/pytest_stage_a_telemetry.log

Pitfalls To Avoid:
- Keep quaternion normalization differentiable; avoid `.detach()` when converting to misset angles.
- Do not reintroduce `mosflm_*` injection when tensor overrides are provided (GRADIENT-001).
- Bound orientation magnitude (e.g., tanh to ±3°) so LBFGS steps stay in the linear regime.
- Preserve existing ROI sampling/full validation cadence and telemetry key names.
- Deterministic perturbation must live in the test harness only; production defaults stay untouched.
- Capture all new logs in the designated artifacts directory; avoid clobbering prior runs.
- Ensure `pytest --collect-only` still reports ≥1 test for the mapped selector.
- Leave environment untouched per Environment Freeze—no new dependencies or installs.

If Blocked:
- Record the failure signature (traceback + last telemetry message) in plans/active/TORCH-REFINE-002/reports/2025-11-05T033936Z/blocked.md.
- Update docs/fix_plan.md Attempts History with blocker details and log the status in galph_memory before pausing.

Findings Applied (Mandatory):
- REFINE-001 (docs/findings.md:14) — Warm-start global scale and clamp before exponentiation.
- REFINE-002 (docs/findings.md:15) — Recognize nucleus improvement ceiling; wider gate now depends on added DoFs.
- REFINE-003 (docs/findings.md:34) — Orientation must flow through quaternion→misset without conflicting with cell overrides.
- REFINE-004 (docs/findings.md:35) — Use deterministic calibration perturbation in the smoke test to satisfy the ≥5% gate while keeping production defaults pristine.
- GRADIENT-001 (docs/findings.md:33) — Crystal parameter overrides stay as tensors; no `.item()` inside the refinement path.

Pointers:
- docs/spec-db-workflow.md:30 — Stage A parameterization and gate expectations.
- plans/nanobrag_integration_plan.md:176 — Stage A expansion contract for quaternion orientation and telemetry.
- docs/fix_plan.md:31 — Current TORCH-REFINE-002 status and attempts history.
- plans/active/TORCH-REFINE-002/implementation.md:12 — Phase checklist highlighting outstanding orientation/gate work.
- dbex/nanobrag_refinement.py:185 — Current Stage A parameter initialization (orientation_vec still unused).
- dbex/nanobrag_bridge.py:480 — Crystal config override plumbing that needs misset support.

Next Up (optional):
1. TORCH-REFINE-003 — Stage C detector microslip once Stage A gate lands.
