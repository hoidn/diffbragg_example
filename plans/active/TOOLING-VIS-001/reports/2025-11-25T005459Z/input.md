Summary: Implement DB-AT-028/029 Stage A loss-scale and structure gates using calibrated Stage A reconstruction.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity; tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T005459Z/

Do Now
- Implement: dbex/nanobrag_refinement.py::_build_final_bragg_from_stage_a_telemetry (and the Stage A reconstruction call in run_nanobrag_refinement) plus tests/dbex/test_stage_a_smoke_parity.py::{test_db_at_028_loss_scale_sanity,test_db_at_029_structure_parity} — align Stage A reconstruction with the calibrated mapping baseline, expose chi²-per-pixel and clamp metrics, reconstruct bragg_before/bragg_after for ROI parity, and emit DB-AT-028/029 metrics to DBAT028_ARTIFACT_DIR/DBAT029_ARTIFACT_DIR.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T005459Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T005459Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T005459Z/pytest_db_at_028_029.log; then AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T005459Z/pytest_db_at_028_029_collect.log.
- Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T005459Z/{db_at_028/db_at_028_metrics.json,db_at_029/db_at_029_metrics.json,pytest_db_at_028_029.log,pytest_db_at_028_029_collect.log,summary.md}

How-To Map
1) Export env + dirs: `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T005459Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T005459Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1` (dirs already created). Prefer CPU only if CUDA unavailable; otherwise use default device from the smoke fixtures.
2) Stage A reconstruction: make `_build_final_bragg_from_stage_a_telemetry` reuse the calibrated beam/crystal + HKL grid from Stage A warm cache for both `bragg_before` and `bragg_after`, honoring log_scale_baseline from calibration (no double sqrt scaling). Ensure Stage A telemetry exposes `variance_floor_masked_pixels`, `variance_floor_clamp_fraction`, and `chi_squared_trace_full` with the calibrated baseline.
3) DB-AT-028 test: add `test_db_at_028_loss_scale_sanity` that runs Stage A-only refinement on the canonical smoke fixture (small detector) with nearest-neighbor HKL sampling per spec (interpolation=False), captures chi2_per_pixel initial/final and clamp fraction, asserts ≤1e2 bounds + non-increasing χ² and clamp_fraction <0.5, and writes metrics JSON to $DBAT028_ARTIFACT_DIR.
4) DB-AT-029 test: in the same module, reconstruct `bragg_before`/`bragg_after` via the calibrated helper, compute ROI correlations vs data on loss_mask and scale_ratio_before=mean(model_before[mask])/mean(target[mask]), assert median(corr_before)≥0.2, median(corr_after)≥median(corr_before)-0.05, scale_ratio_before in [1e-2,1e2]; emit metrics JSON to $DBAT029_ARTIFACT_DIR.
5) Use existing smoke fixtures (`refinement_inputs`, `hkl_data`, `smoke_detector_size`, `smoke_sigma_source`) to avoid duplicating setup; keep Stage B/C disabled and reuse the deterministic perturbed geometry helper.
6) Run pytest per Validate step; after PASS, update docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md with the two selectors (status Active) and archive the new logs under the artifacts path.

Pitfalls To Avoid
- Do not call `create_unified_simulator` inside refinement closures (ARCH-FACTORY-001); keep direct simulator instantiation for autograd.
- Avoid double-applying `spot_scale_override` or log_scale deltas; baseline should be log_scale_baseline then bounded deltas.
- Keep Stage A HKL sampling at nearest-neighbor for DB-AT-028/029 (interpolation=False) even if other smokes use tricubic.
- Ensure ROI slicing uses loss_mask and trusted mask from the smoke inputs; do not recompute masks.
- Honor Environment Freeze (POLICY-001); no package installs or CLI flag relaxations.

If Blocked
- Save partial metrics JSONs + pytest output to the artifacts dir, log measured chi2_per_pixel/clamp fractions/ROI CCs in docs/fix_plan.md Attempts History, and mark TOOLING-VIS-001 blocked until reconstruction parity or sigma semantics are understood.

Findings Applied (Mandatory)
- STAGEA-001 — Calibration must remain threaded through Stage A reconstruction; DB-AT-027 evidence is the baseline.
- GEOMETRY-003/004 — Maintain mapping zero-point UB/misset invariants when rebuilding Stage A Bragg tensors.
- PHYSICS-LOSS-001/002/003 — Use the canonical variance-weighted chi² with sigma_floor clamp; keep numerator/denominator semantics consistent across stages.
- ARCH-FACTORY-001 — Unified simulator factory is forward-only; refinement paths must instantiate simulators directly.

Pointers
- docs/spec-db-conformance.md:280-340 — DB-AT-028/029 tolerances and procedures.
- plans/active/TOOLING-VIS-001/implementation.md:203 — Phase D.D checklist for loss-scale and structure gates.
- tests/dbex/test_torch_refine_smoke.py:309 — Reference Stage A smoke configuration (geometry perturbation, sigma policy).
- dbex/nanobrag_refinement.py::_build_final_bragg_from_stage_a_telemetry — Reconstruction path to align with calibrated warm cache.

Next Up (optional)
- After DB-AT-028/029, reassess Stage A visuals and consider tightening tolerances for full-detector runs if performance allows.

Doc Sync Plan (Conditional)
- After adding the new tests, run `pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T005459Z/pytest_db_at_028_029_collect.log`, then update docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md with the selectors and artifact pointers.

Mapped Tests Guardrail
- At least the two mapped selectors must collect (>0); if collection fails, author the missing tests before declaring done.

Hard Gate
- Do not finish until DB-AT-028/029 tolerances pass with artifacts under `plans/active/TOOLING-VIS-001/reports/2025-11-25T005459Z/`.

Normative Math/Physics
- Reference docs/spec-db-conformance.md:280-340 for DB-AT-028/029 definitions and docs/spec-db-core.md:84-90 for the variance-weighted χ² equation; do not paraphrase or relax these formulas.
