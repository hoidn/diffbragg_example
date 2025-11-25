Summary: Isolate the CUDA vs CPU mapping forward divergence for DB-AT-028/029 by adding a CPU/GPU parity probe and rerunning the Stage A smoke gates with diagnostics.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity; tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T053220Z/

Do Now
- Implement: plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py::main — add a T2 probe that builds `build_mapping_stage_a_context` on CPU and CUDA (metadata sigma smoke dataset), computes ROI CC/scale ratios and mean_abs/max_abs diffs between CPU/GPU bragg_zero_iter, and writes JSON + log under the artifacts path.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T053220Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T053220Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-25T053220Z/mapping_cpu_gpu | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T053220Z/mapping_cpu_gpu/probe.log; then run pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T053220Z/pytest_db_at_028_029.log; finally run pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T053220Z/pytest_db_at_028_029_collect.log.
- Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T053220Z/{mapping_cpu_gpu/probe.log,mapping_cpu_gpu/mapping_forward_cpu_gpu.json,pytest_db_at_028_029.log,pytest_db_at_028_029_collect.log,summary.md}

How-To Map
1) Export env: `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T053220Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T053220Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1`.
2) Implement the probe script in plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py using the metadata sigma smoke dataset (same selection as tests/conftest.py when DBEX_SMOKE_SIGMA_SOURCE=metadata, detector_size=small→full) to compute ROI CC/scale ratios and CPU↔CUDA bragg diffs; save JSON + stdout log under the artifacts path.
3) Run the probe command above; verify `mapping_forward_cpu_gpu.json` captures CPU vs CUDA metrics (ROI CC/scale ratios, log_scale_baseline/global_scale_hint, mean_abs/max_abs diffs).
4) Run `pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` with the same env to refresh DBAT028/029 metrics; then run the collect-only command to confirm selectors register (>0); keep both logs under the artifacts path.
5) Record any CPU/GPU deltas (ROI CC, scale_ratio, bragg diffs) and DB-AT-028/029 failure signatures in summary.md for follow-up.

Pitfalls To Avoid
- Do not change dataset selection: keep metadata sigma + nearest-neighbor HKL (no refined.mtz overrides or calibration swaps).
- Keep CPU and CUDA runs on identical inputs/loss_mask/panel_slices; no reshaping or mask regeneration between devices.
- Persist diagnostics before assertions so artifacts exist even when gates fail.
- Do not relax DB-AT-028/029 tolerances; log discrepancies only.
- Avoid environment changes or new dependencies (Environment Freeze).
- Honor device/dtype neutrality (CUDA float32) and disable torch.compile via NANOBRAGG_DISABLE_COMPILE=1.
- Ensure probe handles missing CUDA gracefully (record blocked state instead of failing unhandled).
- Do not mutate mapping_context between CPU and CUDA comparisons; rebuild cleanly for each device.

If Blocked
- Capture probe log/JSON and pytest logs; document the blocking signature in docs/fix_plan.md Attempts History and summary.md, mark TOOLING-VIS-001 blocked on mapping CPU↔CUDA parity if CUDA is unavailable or results remain divergent without a clear cause.

Findings Applied (Mandatory)
- STAGEA-001 — Preserve calibrated mapping baseline and emit diagnostics before gating; reuse mapping_context inputs as the zero-point truth.
- GEOMETRY-003/GEOMETRY-004 — Keep zero-point tied to mapping UB baseline (incremental UB parameterization, no refined HKL overrides).
- PHYSICS-LOSS-001 — Maintain canonical variance-weighted chi² semantics when computing ROI CC/scale ratios.
- CONFORMANCE-001 — DB-AT selectors are authoritative; archive logs even on failure.

Pointers
- docs/spec-db-conformance.md:280-366 (DB-AT-028/029 tolerances)
- docs/TESTING_GUIDE.md:150-190 (DB-AT env/commands)
- tests/conftest.py:60-115 (smoke dataset paths for metadata/full)
- dbex/vis/mapping.py:60-220,335-420 (mapping context + diagnostics helper)
- tests/dbex/test_stage_a_smoke_parity.py:66-210 (Stage A smoke fixture + metrics)

Next Up (optional)
- If CPU vs CUDA mapping matches but DB-AT-028/029 still fail, diff Stage A vs mapping ROI slices in a follow-on T2 probe to isolate per-ROI structure mismatches.

Doc Sync Plan (Conditional)
- Only if DB-AT-028/029 status changes: update docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md after tests pass; archive collect-only logs under this loop’s artifacts.

Mapped Tests Guardrail
- Keep the collect-only log; ensure both DB-AT-028/029 selectors collect (>0) before closing the loop.

Hard Gate
- Do not declare done unless CPU vs CUDA mapping JSON and DBAT028/029 metrics/logs are present under the artifacts path and any divergence is summarized in summary.md.

Normative Math/Physics
- Use docs/spec-db-conformance.md §280-366 and docs/spec-db-core.md §84-90 directly for chi²/variance/ROI CC definitions; do not paraphrase or relax tolerances.
