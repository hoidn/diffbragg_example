Summary: Plumb the deterministic Stage A misset into the refinement loop so the smoke can exercise the perturbation while staying on nearest-neighbor HKL.
Mode: none
Focus: TORCH-REFINE-002D — Stage A HKL-aware perturbation dataset
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion
Artifacts: plans/active/TORCH-REFINE-002D/reports/2025-11-05T070500Z/

Do Now:
- TORCH-REFINE-002D
  - Implement: dbex/nanobrag_refinement.py::run_nanobrag_refinement — extract the refGeom→perturbed misset (U_delta) as torch tensors, add it to the quaternion-derived orientation delta before calling `create_crystal_config`, and set `crystal_model.interpolate = False` both inside the LBFGS closure and during the final full-image render.
  - Implement: tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion — feed `create_perturbed_geometry` back into the smoke, assert telemetry reports the deterministic misset angles, and keep the ≥5% gate guarded with an updated xfail rationale until the HKL-aware dataset lands.
  - Validate: pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --maxfail=1
  - Artifacts: plans/active/TORCH-REFINE-002D/reports/2025-11-05T070500Z/

How-To Map:
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. mkdir -p plans/active/TORCH-REFINE-002D/reports/2025-11-05T070500Z
3. KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion | tee plans/active/TORCH-REFINE-002D/reports/2025-11-05T070500Z/collect_stage_a.log
4. KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --maxfail=1 | tee plans/active/TORCH-REFINE-002D/reports/2025-11-05T070500Z/pytest_stage_a.log

Pitfalls To Avoid:
- Keep Stage A on nearest-neighbor |F| (do not enable tricubic) but ensure interpolation is explicitly disabled on the Crystal instance.
- Derive the baseline misset from U_perturbed @ U_base^{-1}; do not reuse the absolute U or you will double-count the lattice rotation.
- Preserve gradient flow: keep misset tensors on the refinement device/dtype without `.item()`/`.detach()` in the optimization path (GRADIENT-001).
- Leave the perturbation helper deterministic and confined to the smoke test; no production assets or HKL grids may be mutated (REFINE-004/005).
- Update the xfail rationale to reflect the remaining HKL dataset dependency so the report stays truthful once misset telemetry is live.
- Respect Environment Freeze; no external installs or MTZ regeneration.

If Blocked:
- Capture the failure signature (stack trace, tensor device mismatch, or missing refGeom asset) in plans/active/TORCH-REFINE-002D/reports/2025-11-05T070500Z/blocked.md, update docs/fix_plan.md Attempts History with the timestamp, and log the block in galph_memory before switching focus.

Findings Applied (Mandatory):
- REFINE-003 — Orientation overrides must flow through misset_deg rather than A*; reconstruct the baseline misset from U_delta.
- REFINE-004 — Perturbation stays test-only; document the deterministic angles while we work toward restoring the ≥5% gate.
- REFINE-005 — HKL grid is still built from the baseline crystal; keep the xfail and record hit-rate metrics until the dataset rebuild lands.
- GRADIENT-001 — Maintain tensor-valued overrides without `.item()` to keep Stage A differentiable.

Pointers:
- docs/fix_plan.md:60 — TORCH-REFINE-002D attempts and exit criteria.
- plans/active/TORCH-REFINE-002D/implementation.md:18 — Phase 1/2 tasks for HKL-aware perturbation.
- tests/dbex/test_torch_refine_smoke.py:63 — Deterministic perturbation helper details.
- dbex/nanobrag_refinement.py:300 — Current crystal override plumbing and TODO to disable interpolation.

Next Up (optional):
1. Measure gradient magnitudes after misset plumbing to size the HKL grid rebuild or perturbation amplitude adjustments.
