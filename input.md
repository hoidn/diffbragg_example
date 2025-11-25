Summary: Fix mapping forward HKL/calibration wiring so Stage A parity probe + DB-AT-028/029 produce mapping metrics and clear the chi²/ROI CC gates.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity; tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T042456Z/

Do Now
- Implement: plans/active/TOOLING-VIS-001/bin/compare_stage_a_mapping_parity.py::main and tests/dbex/test_stage_a_smoke_parity.py::stage_a_smoke_result — fix the mapping forward path so refined/raw HKL indices + amplitudes (with required hkl_list/metadata) are passed into simulate_forward_once without KeyError, reuse calibrated log_scale_baseline and HKL provenance, and persist mapping ROI CC/scale metrics to artifacts even on failure.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T042456Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T042456Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/TOOLING-VIS-001/bin/compare_stage_a_mapping_parity.py --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-25T042456Z/parity_probe --device cpu --sigma-source metadata | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T042456Z/parity_probe.log; then run `pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T042456Z/pytest_db_at_028_029.log; finally run `pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T042456Z/pytest_db_at_028_029_collect.log.
- Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T042456Z/{parity_probe/,db_at_028/db_at_028_metrics.json,db_at_029/db_at_029_metrics.json,pytest_db_at_028_029.log,pytest_db_at_028_029_collect.log,summary.md}

How-To Map
1) Export env: `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T042456Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T042456Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1`.
2) Update `compare_stage_a_mapping_parity.py::main` to pass explicit HKL indices/amplitudes + metadata (including any required hkl_list/asu_map) into `simulate_forward_once`, set `hkl_path` so telemetry reports refined vs scaled MTZ, and ensure mapping metrics write even if the mapping pass fails.
3) Update `stage_a_smoke_result` in `tests/dbex/test_stage_a_smoke_parity.py` to mirror the corrected mapping forward path (no refined HKL swaps unless available, include hkl_path, propagate calibration/log_scale_baseline) and persist mapping ROI CC/scale metrics before assertions.
4) Run the parity probe command above; confirm `parity_metrics.json` reports `mapping_forward_success=true` with finite ROI CC/scale ratios; leave log in `parity_probe.log`.
5) Run pytest selectors per Validate (then collect-only). If either selector still fails, keep artifacts and note the exact chi²/pixel and ROI CC signatures in summary.md.

Pitfalls To Avoid
- Keep `enable_hkl_interpolation=False` (DB-AT-028/029 require nearest-neighbor HKL).
- Do not drop calibration/log_scale_baseline threading (STAGEA-001); avoid double-applying spot_scale_override.
- Ensure simulate_forward_once calls return bragg arrays (unpack diagnostics) to avoid tuple/KeyError handling mistakes.
- Preserve HKL provenance tagging (hkl_source/path) so mapping vs refined telemetry remains visible in artifacts.
- No environment changes or new dependencies (POLICY-001). Avoid touching unrelated production modules.

If Blocked
- Capture parity_probe.log, parity_metrics.json, db_at_028/db_at_029 metrics, and pytest logs; record chi²/pixel + ROI CC signatures in docs/fix_plan.md Attempts History and mark TOOLING-VIS-001 blocked pending HKL mapping fix.

Findings Applied (Mandatory)
- STAGEA-001 — Reuse calibrated spot_scale/log_scale_baseline from mapping; log mapping vs Stage A metrics before asserting gates.

Pointers
- docs/spec-db-conformance.md:280-366 — DB-AT-028/029 tolerances and ROI CC/scale bands.
- plans/active/TOOLING-VIS-001/implementation.md:203-224 — Phase D.D checklist for parity probes and gates.
- parity probe path: plans/active/TOOLING-VIS-001/bin/compare_stage_a_mapping_parity.py (HKL/calibration plumbing); tests/dbex/test_stage_a_smoke_parity.py::stage_a_smoke_result (artifact logging and metrics).

Next Up (optional)
- If mapping forward succeeds but metrics still off, add a focused callchain trace to locate where HKL metadata is lost between dataload and simulate_forward_once.

Doc Sync Plan (Conditional)
- If DB-AT-028/029 status changes, update docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md with selector status and artifact paths after tests pass.

Mapped Tests Guardrail
- Ensure both selectors collect (>0) via the collect-only command before closing the loop; keep logs in the artifacts directory.

Hard Gate
- Do not declare done unless parity_metrics.json plus DBAT028/029 metrics exist under `plans/active/TOOLING-VIS-001/reports/2025-11-25T042456Z/` with `mapping_forward_success=true` and finite mapping ROI CC/scale values (or captured failure signatures noted in summary.md).

Normative Math/Physics
- Use docs/spec-db-conformance.md:280-366 and docs/spec-db-core.md:84-90 directly for chi²/variance definitions; do not paraphrase or relax tolerances.
