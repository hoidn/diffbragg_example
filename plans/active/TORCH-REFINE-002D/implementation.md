# TORCH-REFINE-002D — Stage A HKL-aware Perturbation Dataset

## Purpose
Rebuild the structure-factor grid (or generate a derivative dataset) that remains valid when applying the deterministic Stage A perturbation (cell stretch + orientation misset) so the ≥5% masked-MSE gate can run without `xfail`. This retires the temporary guard introduced in TORCH-REFINE-002, validates orientation telemetry against a meaningful perturbation, and clears findings REFINE-004/005.

## References
- docs/spec-db-workflow.md:30-86 — Stage A gate contract, ROI telemetry expectations
- docs/config_crosswalk.md:40-102 — Crystal/HKL mapping, MTZ provenance
- plans/nanobrag_integration_plan.md:176-233 — Stage A expansion strategy and perturbation headroom notes
- plans/active/TORCH-REFINE-002/reports/2025-11-05T035905Z/blocked.md — HKL miss-rate analysis for perturbed geometry
- docs/findings.md:34-36 — REFINE-003/004/005 constraints to reconcile

## Exit Criteria (mirror fix_plan)
1) Deterministic perturbation helper (`create_perturbed_geometry`) retains the REFINE-004 magnitudes and feeds a regenerated HKL grid (or reindexed reflections) with ≥95% hit rate when Stage A runs on the canonical dataset. Grid rebuild must stay differentiable and device-neutral.
2) Stage A smoke test re-enables the ≥5% masked-MSE assertion (no `xfail`), demonstrating ≥5% ROI improvement within ≤30 LBFGS iterations while asserting non-zero orientation telemetry.
3) REFINE-004 and REFINE-005 are updated (closed or downgraded) with artifact references; `docs/fix_plan.md` Attempts History captures the grid rebuild, and Stage A selector logs are archived under `plans/active/TORCH-REFINE-002D/reports/<timestamp>/`.

## Phase Breakdown
- Phase 0 — Diagnosis Refresh
  - [x] P0.1: Capture current HKL metadata (ranges, hit rate) for the baseline grid and for the perturbation helper via a lightweight probe; stash under reports for comparison. ✅ `plans/active/TORCH-REFINE-002D/reports/2025-11-05T044720Z/hkl_probe.json`
- Phase 1 — HKL Grid Halo & Interpolation Enablement
  - [ ] P1.1: Add optional ±1 halo support to `dbex.nanobrag_bridge.build_structure_factor_grid` so tricubic interpolation can sample fractional HKL coordinates without triggering `default_F`.
  - [ ] P1.2: Extend Stage A refinement config to toggle interpolation; update `run_nanobrag_refinement` to honor the flag while preserving nearest-neighbor fallback for datasets lacking a halo.
  - [ ] P1.3: Rebuild the Stage A smoke harness (`test_stage_a_expansion`) to request the haloed grid, enable interpolation, and log the new HKL metadata for regression triage.
- Phase 2 — Stage A Gate Restoration
  - [ ] P2.1: Remove the interim `pytest.xfail`, assert ≥5% masked-MSE improvement, and record the achieved improvement + iteration count in telemetry artifacts.
  - [ ] P2.2: Verify orientation telemetry remains deterministic (initial misset ≈ [0,0,1.5]°) with interpolation enabled; update acceptance messaging if tolerances change.
- Phase 3 — Docs & Findings
  - [ ] P3.1: Update `docs/findings.md` entries REFINE-004/005 with resolution notes and artifact links.
  - [ ] P3.2: Refresh `docs/fix_plan.md` Attempts History and, if selectors change, sync `docs/TESTING_GUIDE.md` / `docs/development/TEST_SUITE_INDEX.md`.

## Mapped Tests (planned)
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` — must pass without `xfail` and assert ≥5% improvement with orientation telemetry coverage.
- Follow-on sanity (as needed): `pytest -v tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_uses_refined_mtz` to guarantee HKL telemetry compatibility.

## Artifacts
- `plans/active/TORCH-REFINE-002D/reports/<YYYY-MM-DDTHHMMSSZ>/`
  - `collect_stage_a.log`
  - `pytest_stage_a.log`
  - `hkl_probe.json` (Phase 0 statistics)
  - `summary.md`

## How-To (initial)
- `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md`
- `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`
- `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --maxfail=1`

## Next Up (after completion)
- TORCH-REFINE-003 — Stage C detector microslip (depends on Stage A gate being live)
- Dataset initiative (TBD) to generalize HKL rebuild tooling across other perturbation scenarios
