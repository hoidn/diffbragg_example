Summary: Instrument Stage A smoke parity (DB-AT-028/029) to pinpoint the scaling/HKL mismatch by comparing bragg_before/after to the mapping forward model and logging scale diagnostics.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity; tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T034523Z/

Do Now
- Implement: tests/dbex/test_stage_a_smoke_parity.py::stage_a_smoke_result (emit log_scale_effective init/final, bragg mean/std/max, ROI CC baselines, and optional mapping-forward snapshot into DBAT028/029 metrics before asserts) and plans/active/TOOLING-VIS-001/bin/compare_stage_a_mapping_parity.py (T2 probe that runs Stage A engine on the smoke fixture, reconstructs bragg_before/after via `_build_final_bragg_from_stage_a_telemetry`, and computes parity vs a mapping forward stack with identical HKL/calibration).
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T034523Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T034523Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/TOOLING-VIS-001/bin/compare_stage_a_mapping_parity.py --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-25T034523Z/parity_probe --device cpu --sigma-source metadata; then run `pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T034523Z/pytest_db_at_028_029.log; finally run `pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T034523Z/pytest_db_at_028_029_collect.log.
- Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T034523Z/{parity_probe/,db_at_028/db_at_028_metrics.json,db_at_029/db_at_029_metrics.json,pytest_db_at_028_029.log,pytest_db_at_028_029_collect.log,summary.md}

How-To Map
1) Export env: `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T034523Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T034523Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1`.
2) Implement the T2 probe `plans/active/TOOLING-VIS-001/bin/compare_stage_a_mapping_parity.py` with CLI flags `--out-dir`, `--device`, `--sigma-source`; it should load the smoke fixture (same as tests), run Stage A engine with use_engine_delegation=True (nearest-neighbor HKL), reconstruct bragg_before/after plus a mapping forward stack (simulate_forward_once or build_mapping_stage_a_context), and emit JSON metrics (log_scale_effective init/final, scale ratios, ROI CCs, HKL source).
3) Enhance `stage_a_smoke_result` to compute log_scale_effective using telemetry.param_deltas (baseline + clamped delta), log bragg mean/std/max for before/after/mapping if available, and persist these fields into DBAT028/029 metrics ahead of assertions so artifacts survive failures.
4) Run the probe: `python plans/active/TOOLING-VIS-001/bin/compare_stage_a_mapping_parity.py --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-25T034523Z/parity_probe --device cpu --sigma-source metadata`.
5) Run pytest per Validate; if failures persist, leave artifacts in place. Then run collect-only for registry guardrail.
6) After PASS (or once diagnostics captured), update docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md with DB-AT-028/029 status and artifact pointers; keep STAGEA-001 finding referenced.

Pitfalls To Avoid
- Do not relax DB-AT-028/029 tolerances; goal is diagnosis, not gate weakening.
- Avoid reintroducing refined_mtz HKL swaps unless explicitly justified; prefer mapping HKL provenance for parity.
- Keep nearest-neighbor HKL sampling (enable_hkl_interpolation=False) per spec-db-conformance DB-AT-028/029.
- Do not double-apply spot_scale_override; log_scale_effective should be baseline + bounded delta only.
- Always persist metrics JSONs even on failing assertions; artifacts are required for analysis.
- Environment freeze: no package installs or cache clears; use existing deps only.

If Blocked
- Capture probe output + pytest logs to the artifacts dir, record observed chi²/pixel and ROI CCs in docs/fix_plan.md Attempts History, and mark TOOLING-VIS-001 blocked pending diagnosis of forward-model vs HKL/calibration alignment.

Findings Applied (Mandatory)
- STAGEA-001 — Calibration threading and log_scale_baseline must mirror DB-AT-027; retain baseline when reconstructing bragg_before/after.

Pointers
- docs/spec-db-conformance.md:280-366 — DB-AT-028/029 definitions and tolerances.
- plans/active/TOOLING-VIS-001/implementation.md:203-224 — Phase D.D checklist.
- docs/spec-db-core.md:84-90 — Variance-weighted χ² and sigma_floor semantics.
- tests/dbex/test_stage_a_smoke_parity.py::stage_a_smoke_result — current DB-AT-028/029 harness.

Next Up (optional)
- If diagnostics isolate HKL vs scale mismatch, follow-up loop implements the concrete fix (HKL provenance swap or scale application change) then reruns DB-AT-028/029.

Doc Sync Plan (Conditional)
- After adding/updating selectors, run `pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` and archive the log; then update docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md with selector status and artifact pointers once tests PASS or are xfail with rationale.

Mapped Tests Guardrail
- Ensure both selectors collect (>0); if collection fails, fix the tests before closing the loop.

Hard Gate
- Do not declare done unless DB-AT-028/029 parity metrics are captured and analyzed (PASS or explicit block) under `plans/active/TOOLING-VIS-001/reports/2025-11-25T034523Z/`.

Normative Math/Physics
- Use docs/spec-db-conformance.md:280-366 for gate definitions and docs/spec-db-core.md:84-90 for χ²; avoid paraphrasing or relaxing formulas.
