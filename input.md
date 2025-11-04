Summary: Surface zero-iteration scale diagnostics so we can reconcile simulator vs canonical mapping.
Mode: none
Focus: MAP-SCALE-001 — Zero-iteration mapping scale alignment
Branch: integration
Mapped tests: tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke
Artifacts: plans/active/MAP-SCALE-001/reports/2025-11-04T090000Z/

Do Now:
- Implement: dbex/nanobrag_bridge.py::simulate_forward_once — extend diagnostics to record raw Bragg statistics (pre-scale mean/max), target mean over the loss mask, and derived target/bragg ratios; plumb the new fields through to `tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke` so `mapping_metrics.json` captures them for post-run analysis while keeping the selector xfail reason up to date.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-001/reports/2025-11-04T090000Z pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke
- Artifacts: Capture `mapping_metrics.json`, updated `mapping_metrics.csv` (if emitted), and the pytest log under plans/active/MAP-SCALE-001/reports/2025-11-04T090000Z/

How-To Map:
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. export KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-001/reports/2025-11-04T090000Z
3. pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke

Pitfalls To Avoid:
- Do not remove the existing xfail; update its reason with new metric values if they change.
- Respect Environment Freeze; no package installs or CUDA/toolchain tweaks.
- Preserve SCALE-001/002 behavior (no pre-scaling structure factors; keep sqrt(spot_scale_override) semantics).
- Keep diagnostics device/dtype neutral (CPU expected); avoid GPU-only code paths.
- Ensure new diagnostics serialize cleanly to JSON (float casts, no numpy types).
- Do not regress artifact policy: write metrics only when DBAT024_ARTIFACT_DIR is set.
- Maintain loss-mask usage when computing target means/ratios (exclude sentinel pixels).
- Leave canonical fixtures untouched (tests/fixtures/golden_data/simple_cubic/*).
- Keep pytest selector duration reasonable (no additional heavy loops).
- Capture artifacts in the specified reports directory (no temp paths).

If Blocked:
- Record failure details (stack trace, missing dependency) in plans/active/MAP-SCALE-001/reports/2025-11-04T090000Z/blockers.md and flag the focus as blocked in docs/fix_plan.md Attempts History.
- If `nanobrag_torch` import fails, cite the ImportError signature verbatim and halt; do not attempt installs.
- If canonical assets are missing, log the missing filenames and stop rather than stubbing data.

Findings Applied (Mandatory):
- SCALE-001 — No structure-factor pre-scaling; post-simulation adjustments only.
- SCALE-002 — Maintain sqrt(spot_scale_override) post-sim scaling semantics.
- CONFORMANCE-001 — Keep DB_AT_024 selector discoverable with actionable diagnostics.
- TESTING-003 — Uphold artifact + pytest collection policy for Active selectors.
- PARITY-001 — Diagnostics must support first-divergence workflows (JSON-safe, deterministic ordering).
- CONFIG-001 — Trusted mask polarity and ROI slicing rules must remain intact when computing ratios.

Pointers:
- docs/spec-db-workflow.md:33 — Global scale initialization requirements in ADU mode.
- docs/architecture.md:88 — Stage A expectations for global scale parameters.
- docs/spec-db-conformance.md:43 — DB_AT_024 acceptance thresholds and artifact expectations.
- plans/active/MAP-SCALE-001/reports/2025-11-04T082000Z/summary.md — Latest diagnostics and strategy evaluation.
- tests/dbex/test_mapping_consistency.py:1 — Current DB_AT_024 selector structure and artifact writers.
- docs/TESTING_GUIDE.md:70 — Runtime flags and artifact policy for DB_AT_024.

Next Up (optional):
1. Compare simulator output to canonical `bragg_torch.npy` per ROI to isolate missing DiffBragg scale metadata.

