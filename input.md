Summary: Stand up Stage C detector microslip LBFGS stage with per-panel distance offsets and a deterministic smoke test hitting the ≥5% gate.
Mode: none
Focus: TORCH-REFINE-003 — Stage C detector microslip
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip, tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion
Artifacts: plans/active/TORCH-REFINE-003/reports/2025-11-05T110500Z/

Do Now:
- TORCH-REFINE-003
  - Implement: dbex/nanobrag_refinement.py::RefinementConfig — add Stage C toggles (enable flag, max distance delta, dedicated LBFGS tolerances) without regressing Stage A defaults.
  - Implement: dbex/nanobrag_refinement.py::run_nanobrag_refinement — introduce Stage C detector-distance LBFGS loop with bounded per-panel offsets, reuse ROI sampling, and emit multi-stage telemetry (stage "C" + per-panel deltas) while preserving Stage A behaviour.
  - Implement: dbex/nanobrag_bridge.py::create_detector_config — accept tensor overrides for `distance_mm` so Stage C gradients propagate through DetectorConfig/Detector.
  - Implement: tests/dbex/test_torch_refine_smoke.py::create_perturbed_geometry — extend helper to apply deterministic detector normal offsets used by the Stage C smoke.
  - Implement: tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip — author Stage C acceptance test asserting ≥5% improvement, telemetry completeness, and non-increasing full-loss trace.
  - Implement: plans/active/TORCH-REFINE-003/bin/dump_stage_c_metrics.py — T2 script dumping Stage C telemetry (loss traces, per-panel offsets) to JSON under the reports directory.
  - Validate: KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --maxfail=1 | tee plans/active/TORCH-REFINE-003/reports/2025-11-05T110500Z/pytest_stage_c.log
  - Artifacts: plans/active/TORCH-REFINE-003/reports/2025-11-05T110500Z/

How-To Map:
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. mkdir -p plans/active/TORCH-REFINE-003/reports/2025-11-05T110500Z
3. KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip | tee plans/active/TORCH-REFINE-003/reports/2025-11-05T110500Z/collect_stage_c.log
4. KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion | tee plans/active/TORCH-REFINE-003/reports/2025-11-05T110500Z/collect_stage_a.log
5. KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --maxfail=1 | tee plans/active/TORCH-REFINE-003/reports/2025-11-05T110500Z/pytest_stage_c.log
6. KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --maxfail=1 | tee plans/active/TORCH-REFINE-003/reports/2025-11-05T110500Z/pytest_stage_a.log
7. python plans/active/TORCH-REFINE-003/bin/dump_stage_c_metrics.py --out-json plans/active/TORCH-REFINE-003/reports/2025-11-05T110500Z/telemetry_stage_c.json

Pitfalls To Avoid:
- Preserve Stage A defaults (0.2% gate, interpolation toggle) while adding Stage C; no behaviour changes when `enable_stage_c=False`.
- Keep detector distance offsets differentiable tensors; do not detach or cast to numpy inside the closure (GRADIENT-001).
- Bound distance adjustments (e.g., tanh scaling) to avoid negative distances or large jumps; clamp final distance > 0 mm.
- Maintain per-panel normal direction; translate strictly along odet_vec to avoid inadvertently rotating the detector.
- Ensure Stage C loop freezes Stage A parameters (no accidental grads on crystal/scale).
- Emit telemetry for both stages; do not overwrite Stage A traces when introducing Stage C metadata.
- Respect Environment Freeze: no editing refGeom assets or installing dependencies.
- Archive all logs/JSON artifacts listed above before marking the attempt complete.

If Blocked:
- Capture failing pytest logs (stage_c + stage_a), serialize current telemetry to `plans/active/TORCH-REFINE-003/reports/2025-11-05T110500Z/blocked_stage_c.json`, update docs/fix_plan.md Attempts History with the failure signature, and note the block plus remediation hypothesis in galph_memory.md before pivoting.

Findings Applied (Mandatory):
- REFINE-001 — Warm-start global scale and respect LBFGS guardrails when Stage C reuses Stage A outputs.
- REFINE-003 — Orientation telemetry pathways must remain intact; do not regress misset reporting while layering Stage C.
- REFINE-006 — Stage A maintains the ≥0.2% gate; Stage C builds on that baseline for the ≥5% detector improvement.
- CONFIG-001 — Detector geometry mapping (distance, axes) must continue to follow config_crosswalk.md; only odet-aligned translations are permitted.
- DIAGNOSTICS-001 — Expand `/torch_diagnostics` without dropping existing fields; include Stage C telemetry additions.
- GRADIENT-001 — All Stage C parameter overrides must remain on the autograd path.

Pointers:
- docs/spec-db-workflow.md:35 — Stage C detector translation contract.
- plans/nanobrag_integration_plan.md:157 — Stage C strategy and LBFGS expectations.
- plans/active/TORCH-REFINE-003/implementation.md:19 — Phase checklist for detector microslip initiative.
- dbex/nanobrag_refinement.py:1 — Stage A LBFGS nucleus to extend with Stage C.
- dbex/nanobrag_bridge.py:250 — DetectorConfig construction to extend for distance overrides.
- tests/dbex/test_torch_refine_smoke.py:63 — Geometry perturbation helper to augment for Stage C.

Next Up (optional):
1. TORCH-REFINE-004 — Stage B Fhkl modifier scaffolding once Stage C smoke is green.

Doc Sync Plan:
- After tests pass, run `pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip` (log already captured in step 3), then update docs/TESTING_GUIDE.md Section 2 and docs/development/TEST_SUITE_INDEX.md with the new selector referencing the Stage C artifacts.

Mapped Tests Guardrail:
- Confirm `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip` collects exactly one test in step 3; do not mark the initiative done if collection drops to zero.
