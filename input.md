Summary: Restore DB-AT-028/029 by comparing Stage A outputs to the mapping forward stack and fixing the parity probe/HKL path so scale + ROI CC diagnostics are trustworthy.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity; tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T040828Z/

Do Now
- Implement: plans/active/TOOLING-VIS-001/bin/compare_stage_a_mapping_parity.py::main (fix simulate_forward_once usage, add mapping forward pass with shared HKL/calibration, log HKL provenance + ROI/scale metrics even on failure) and tests/dbex/test_stage_a_smoke_parity.py::stage_a_smoke_result (force mapping HKL/calibration path, emit mapping-forward ROI CC + scale ratios into DBAT028/029 metrics before assertions).
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T040828Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T040828Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/TOOLING-VIS-001/bin/compare_stage_a_mapping_parity.py --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-25T040828Z/parity_probe --device cpu --sigma-source metadata | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T040828Z/parity_probe.log; then run `pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T040828Z/pytest_db_at_028_029.log; finally run `pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T040828Z/pytest_db_at_028_029_collect.log.
- Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T040828Z/{parity_probe/,db_at_028/db_at_028_metrics.json,db_at_029/db_at_029_metrics.json,pytest_db_at_028_029.log,pytest_db_at_028_029_collect.log,summary.md}

How-To Map
1) Export env: `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T040828Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T040828Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1`.
2) Update `compare_stage_a_mapping_parity.py` to call `simulate_forward_once` with the correct signature (no hkl_grid kw), reuse mapping HKL/calibration, and write `parity_metrics.json` under `parity_probe/` with HKL source, log_scale_effective, chi²/pixel, scale ratios, and ROI CCs; ensure non-zero exit still writes metrics.
3) Update `stage_a_smoke_result` to disable refined_mtz swaps for this fixture, reuse mapping HKL + calibration metadata, and persist mapping-forward ROI CC + scale_ratio_baseline into DBAT028/029 metrics prior to assertions so artifacts survive failures.
4) Run the parity probe command above and inspect `parity_metrics.json` for mapping vs Stage A gaps; leave log in `parity_probe.log`.
5) Run pytest selectors per Validate (then collect-only); if failures persist, keep artifacts and note signatures in summary.md.

Pitfalls To Avoid
- Keep enable_hkl_interpolation=False (DB-AT-028/029 require nearest-neighbor HKL).
- Do not reintroduce refined_mtz HKL unless mapping HKL parity is proven; default to mapping HKL+calibration for smoke fixture.
- Avoid double-applying spot_scale_override; log_scale_effective = baseline + delta only.
- Persist parity_metrics.json and DBAT028/029 metrics even on assertion failure; do not skip artifact writes.
- No environment changes (POLICY-001); use existing deps and avoid installing packages.

If Blocked
- Capture parity_probe.log, parity_metrics.json (if any), and pytest logs to artifacts; record chi²/pixel and ROI CC signatures in docs/fix_plan.md Attempts History and mark TOOLING-VIS-001 blocked pending HKL/scale alignment diagnosis.

Findings Applied (Mandatory)
- STAGEA-001 — Calibration baseline (spot_scale_override) must be threaded and logged; log_scale_effective should include baseline + clamped delta.

Pointers
- docs/spec-db-conformance.md:280-366 — DB-AT-028/029 tolerances.
- plans/active/TOOLING-VIS-001/implementation.md:203-224 — Phase D.D checklist.
- docs/spec-db-core.md:84-90 — Variance-weighted χ² and sigma_floor semantics.
- docs/architecture/calibration_scaling.md — calibration precedence and spot_scale handling.
- tests/dbex/test_stage_a_smoke_parity.py::stage_a_smoke_result — harness to adjust.

Next Up (optional)
- If parity metrics implicate HKL source or scale baseline, follow-up loop applies the specific fix (HKL provenance lock or scale application change) and reruns DB-AT-028/029.

Doc Sync Plan (Conditional)
- None unless selector status changes; if DB-AT-028/029 status updates, refresh docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md after tests pass.

Mapped Tests Guardrail
- Ensure both selectors collect (>0); use the collect-only command above to confirm before closing the loop.

Hard Gate
- Do not declare done unless parity_metrics.json plus DBAT028/029 metrics are captured under `plans/active/TOOLING-VIS-001/reports/2025-11-25T040828Z/` (PASS or explicit failure signature).

Normative Math/Physics
- Use docs/spec-db-conformance.md:280-366 and docs/spec-db-core.md:84-90 directly; do not paraphrase or relax formulas.
