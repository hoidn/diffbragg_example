Summary: Derive HKL coverage metrics for the Stage A perturbation so we can design the grid rebuild that retires the xfail.
Mode: none
Focus: TORCH-REFINE-002D — Stage A HKL-aware perturbation dataset
Branch: integration
Mapped tests: pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --maxfail=1
Artifacts: plans/active/TORCH-REFINE-002D/reports/2025-11-05T044720Z/

Do Now:
- TORCH-REFINE-002D
  - Implement: plans/active/TORCH-REFINE-002D/bin/probe_hkl_hit_rate.py::main — add an analysis script that loads the refGeom assets, applies `create_perturbed_geometry`, projects original Miller indices through the perturbed A matrix to compute fractional HKL coordinates, and emits JSON metrics (baseline vs perturbed ranges, in-bounds fraction, max deviation) to `--out`.
  - Validate: pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --maxfail=1
  - Artifacts: plans/active/TORCH-REFINE-002D/reports/2025-11-05T044720Z/

How-To Map:
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. mkdir -p plans/active/TORCH-REFINE-002D/reports/2025-11-05T044720Z
3. python plans/active/TORCH-REFINE-002D/bin/probe_hkl_hit_rate.py --out plans/active/TORCH-REFINE-002D/reports/2025-11-05T044720Z/hkl_probe.json
4. KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion | tee plans/active/TORCH-REFINE-002D/reports/2025-11-05T044720Z/collect_stage_a.log
5. KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --maxfail=1 | tee plans/active/TORCH-REFINE-002D/reports/2025-11-05T044720Z/pytest_stage_a.log

Pitfalls To Avoid:
- Keep computations device-neutral (numpy/cctbx only); do not instantiate torch tensors in the probe.
- Do not mutate production HKL grids or commit regenerated artifacts; probe outputs live under the reports directory.
- Guard against missing refGeom assets; emit a clear error rather than recreating datasets.
- Ensure JSON metrics include baseline and perturbed ranges plus the fraction of reflections that stay within bounds.
- Preserve existing Stage A test structure; the probe is additive and must not adjust current assertions.
- Respect Environment Freeze — no package installs or MTZ regeneration.
- Document any anomalies (e.g., non-integer HKL projections) in the JSON output for follow-up loops.

If Blocked:
- Capture the failure signature (stack trace or missing asset message) in plans/active/TORCH-REFINE-002D/reports/2025-11-05T044720Z/blocked.md, update docs/fix_plan.md Attempts History, and log the block in galph_memory before switching focus.

Findings Applied (Mandatory):
- REFINE-004 — Dataset too well calibrated; perturbation helper must remain test-only and documented.
- REFINE-005 — HKL grid built from baseline crystal causes 0% hit rate when geometry is perturbed; probe must quantify this gap.
- REFINE-003 — Orientation overrides flow through CrystalConfig; ensure projections use the same quaternion-to-U construction as `create_perturbed_geometry`.
- GRADIENT-001 — Crystal overrides must stay tensor-capable; the probe should not introduce `.item()` or `.detach()` into production paths.

Pointers:
- docs/fix_plan.md:47 — TORCH-REFINE-002D entry with exit criteria.
- plans/active/TORCH-REFINE-002D/implementation.md:1 — Phase checklist for HKL-aware dataset work.
- plans/active/TORCH-REFINE-002/reports/2025-11-05T035905Z/blocked.md — Details of the 0% hit-rate failure.
- tests/dbex/test_torch_refine_smoke.py:63 — `create_perturbed_geometry` helper referenced by the probe.

Next Up (optional):
1. Extend probe to dump candidate change-of-basis matrices for review before implementing grid regeneration.
