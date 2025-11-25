Summary: Capture masked mapping diagnostics and reconcile probe vs fixture ROI CC/scale stats so DB-AT-028/029 can target the real physics gap.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity; tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T055039Z/

Do Now
- Implement: tests/dbex/test_stage_a_smoke_parity.py::stage_a_smoke_result — compute mapping scale_ratio using the loss_mask (masked mean for Bragg + target), persist masked vs unmasked stats/log_scale_baseline in db_at_028/db_at_029 metrics, and ensure mapping_context diagnostics capture the masked scale ratio before assertions.
- Implement: plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py::compute_cpu_gpu_mapping_metrics — emit masked vs unmasked scale ratios, log spot_scale_override/calibration + HKL source/path, and persist the same diagnostics the pytest fixture records so probe vs fixture can be compared directly on the metadata-sigma dataset.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T055039Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T055039Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-25T055039Z/mapping_cpu_gpu | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T055039Z/mapping_cpu_gpu/probe.log; then pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T055039Z/pytest_db_at_028_029.log; then pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T055039Z/pytest_db_at_028_029_collect.log.
- Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T055039Z/{mapping_cpu_gpu/,db_at_028/,db_at_029/,pytest_db_at_028_029.log,pytest_db_at_028_029_collect.log,summary.md}

How-To Map
1) Export env: `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T055039Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T055039Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1`.
2) Update `tests/dbex/test_stage_a_smoke_parity.py::stage_a_smoke_result` to compute masked scale ratios (Bragg + target) and emit masked/unmasked stats + log_scale_baseline in DB-AT-028/029 metrics before assertions.
3) Extend `plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py::compute_cpu_gpu_mapping_metrics` to log masked/unmasked scale ratios, spot_scale_override/calibration, and HKL source/path, writing JSON under `plans/active/TOOLING-VIS-001/reports/2025-11-25T055039Z/mapping_cpu_gpu/`.
4) Run the probe command above; confirm JSON includes masked vs unmasked metrics and calibration/HKL metadata.
5) Run `pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` and the collect-only command; ensure mapping_context diagnostics and updated metrics land in db_at_028/db_at_029 even on failure.
6) Summarize masked vs unmasked scale ratios and ROI CCs (probe vs fixture) plus DB-AT-028/029 failure signatures in summary.md under the artifacts path.

Pitfalls To Avoid
- Keep dataset fixed: metadata sigma + nearest-neighbor HKL; do not swap refined.mtz or change detector size.
- Use the same loss_mask for all masked means (target and bragg) so scale ratios are comparable; do not mix masked/unmasked stats in the same metric.
- Persist diagnostics before assertions; do not exit early without writing JSON/logs.
- Leave DB-AT-028/029 tolerances untouched; no gate weakening.
- Avoid regenerating masks or altering mapping_context inputs between CPU/GPU comparisons.
- No environment/package changes (Environment Freeze) and keep torch.compile disabled.

If Blocked
- Capture probe JSON/log + pytest logs to the artifacts path, note the exact ROI CC/scale ratios (masked + unmasked) in summary.md and docs/fix_plan.md Attempts History, and mark TOOLING-VIS-001 blocked on mapping baseline mismatch if CUDA is unavailable or metrics remain contradictory.

Findings Applied (Mandatory)
- STAGEA-001 — Preserve calibrated mapping baselines; reuse mapping_context inputs and record diagnostics before gating.
- GEOMETRY-003 / GEOMETRY-004 — Maintain mapping zero-point invariants and HKL provenance when comparing Stage A vs mapping.
- PHYSICS-LOSS-001 — Keep variance-weighted chi² semantics; masked pixel counts must use the loss mask.
- POLICY-001 — Environment freeze: no new dependencies or system changes during probes/tests.

Pointers
- docs/spec-db-conformance.md:280-366 (DB-AT-028/029 tolerances and procedures)
- docs/TESTING_GUIDE.md:150-190 (DB-AT env/commands, artifact expectations)
- tests/dbex/test_stage_a_smoke_parity.py:1-220 (Stage A smoke fixture + metrics/diagnostics)
- plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py (current mapping probe structure)
- docs/findings.md#L9 (STAGEA-001 calibration baseline handling)

Next Up (optional)
- If masked probe/fixture metrics agree but ROI CC stays ~-0.04, add a follow-on probe to dump per-ROI correlation histograms (data vs mapping) to pinpoint structural mismatches.

Doc Sync Plan (Conditional)
- If DB-AT-028/029 status changes (xfail/active), update docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md after tests pass; archive collect-only logs under this loop’s artifacts.

Mapped Tests Guardrail
- Ensure `pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` collects both selectors (>0); keep the collect-only log in artifacts.

Hard Gate
- Do not close the loop without masked vs unmasked metrics in mapping_cpu_gpu.json and db_at_028/db_at_029 artifacts plus a summary.md note of the observed ROI CC/scale ratios; if selectors regress to 0 collected, treat as a blocker.

Normative Math/Physics
- Use docs/spec-db-conformance.md §280-366 and docs/spec-db-core.md §84-90 directly for χ²/variance/ROI CC definitions; no tolerance relaxation or paraphrased equations.
