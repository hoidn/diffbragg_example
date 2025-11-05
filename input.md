Summary: Expand Stage A refinement to cover full crystal logs/angles/orientation so the canonical run clears the ≥5% improvement gate with complete telemetry.
Mode: none
Focus: TORCH-REFINE-002 — Stage A expansion — full crystal and orientation
Branch: integration
Mapped tests: pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --maxfail=1
Artifacts: plans/active/TORCH-REFINE-002/reports/2025-11-05T031241Z/

Do Now:
- TORCH-REFINE-002
  - Implement: dbex/nanobrag_refinement.py::run_nanobrag_refinement — promote Stage A parameters to include log-cell deltas for a/b/c, bounded angle deltas (alpha/beta/gamma via tanh or clamp), and a 3-vector orientation perturbation mapped to a unit quaternion before feeding `create_crystal_config`. Warm-start from current geometry, extend rollback/telemetry snapshots to every new DoF, keep log_scale warm-start/clamp (REFINE-001), and enforce the ≥5% gate messaging.
  - Implement: tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion (rename from `test_loss_decreases`) — assert ≥5% loss improvement within ≤30 steps, verify telemetry contains deltas for scale, all cell lengths/angles, orientation components (norm≈1), and keep existing ROI/shape checks. Capture new artifacts under TORCH-REFINE-002 reports.
  - Validate: pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --maxfail=1
  - Artifacts: plans/active/TORCH-REFINE-002/reports/2025-11-05T031241Z/

How-To Map:
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion | tee plans/active/TORCH-REFINE-002/reports/2025-11-05T031241Z/collect_stage_a.log
3. KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --maxfail=1 | tee plans/active/TORCH-REFINE-002/reports/2025-11-05T031241Z/pytest_stage_a.log
4. (Optional sanity) KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/ | tee plans/active/TORCH-REFINE-002/reports/2025-11-05T031241Z/pytest_full_suite.log

Pitfalls To Avoid:
- Do not detach or convert tensors (no `.item()`, `.cpu()`) inside the LBFGS closure—follow GRADIENT-001.
- Keep all new deltas bounded (length exp clamp, angle tanh scaling, normalized quaternion) to prevent invalid crystals.
- Preserve global scale warm-start/clamp and ROI sampling logic from the nucleus.
- Ensure telemetry keys remain backward compatible; extend instead of replacing existing structures.
- Avoid expanding ROI sampling or touching Stage B/C surfaces in this loop.
- Maintain device/dtype neutrality; no hard-coded `.float()` or `.cuda()` conversions.
- Capture pytest logs to the artifact directory; do not overwrite prior TORCH-REFINE-001 artifacts.

If Blocked:
- Record failure signature plus relevant telemetry snippet in plans/active/TORCH-REFINE-002/reports/2025-11-05T031241Z/blocked.md.
- Update docs/fix_plan.md Attempts History with the blocker details and notify in galph_memory before pausing.

Findings Applied (Mandatory):
- REFINE-001 — Warm-start global scale from calibration hints and clamp exponent before `torch.exp`.
- REFINE-002 — ≥0.1% nucleus gate documented; use ≥5% only after Stage A expansion succeeds.
- GRADIENT-001 — Use `crystal_overrides` with tensor values to keep autograd paths intact.

Pointers:
- docs/spec-db-workflow.md:30 — Stage A staging parameters (logs/angles, quaternion orientation).
- plans/nanobrag_integration_plan.md:176 — Stage A expansion contract and telemetry requirements.
- docs/findings.md:14 — REFINE-001 clamp/warm-start guardrail.
- docs/findings.md:33 — GRADIENT-001 tensor override usage details.
- dbex/nanobrag_refinement.py:1 — Current Stage A nucleus implementation to expand.

Next Up (optional):
1. Once ≥5% gate holds, stage the detector microslip initiative (TORCH-REFINE-003).

Doc Sync Plan:
- After the renamed selector passes, update docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md with the new test id; archive `pytest --collect-only` output under this loop before editing docs.
