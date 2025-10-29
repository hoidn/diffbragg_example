**Summary**: Calibrate nanoBragg torch intensity scale, regenerate canonical tensors, and refresh DB_AT_001 parity evidence under a new report timestamp.
**Mode**: Parity
**Focus**: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
**Branch**: integration
**Mapped tests**: tests/dbex/test_db_at_001_parity.py -k DB_AT_001
**Artifacts**: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T185313Z/{golden_dataset/, parity_harness/, canonical_capture.log, pytest_db_at_001.log}

**Do Now (hard validity contract)**
- Implement: scripts/generate_simple_cubic_golden.py::generate_simple_cubic_golden — apply √(mdl_parm["scale"]) post-simulation scaling, recreate canonical `.npy` tensors/manifest under 2025-10-29T185313Z, and repoint tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity.test_db_at_001_parity_smoke to the new artifact directory (checklists A3, B1, C1, C2).
- Validate: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001
- Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T185313Z/{golden_dataset/, parity_harness/, canonical_capture.log, pytest_db_at_001.log}

**Priorities & Rationale**
- SCALE-002 + docs/config_crosswalk.md:67-71 — Honor the global scale contract by reapplying the legacy spot scale after torch forward passes so canonical tensors stay parity-comparable.
- SCALE-001 + docs/nanobrag_api.md:22-44 — Keep structure factors unscaled and adjust output units (photons) via fluence/global scale to prevent the 6×10^8 swing observed in prior loops.
- PARITY-001 + docs/spec-db-conformance.md:23-26 & docs/forward_equivalence.md:46-52 — Regenerating data and rerunning DB_AT_001 ensures correlation/localization thresholds are validated with real artifacts.
- CONFIG-001 + docs/spec-db-core.md:20-41 — Refresh fixtures/manifest with `[panel, slow, fast]` tensors and bool masks so loader invariants remain satisfied.
- DIAGNOSTICS-001 + docs/spec-db-tracing.md:15-24 — Preserve first-divergence and metrics artifacts to keep parity debugging workflow intact after the scale fix.

**How-To Map**
1. export LOOP_TS=2025-10-29T185313Z
2. export REPORT_DIR=plans/active/NANOBRAG-GOLDEN-001/reports/$LOOP_TS
3. mkdir -p "$REPORT_DIR/golden_dataset" "$REPORT_DIR/parity_harness"
4. export PYTHONPATH=../nanoBragg/src:$PYTHONPATH
5. KMP_DUPLICATE_LIB_OK=TRUE python scripts/generate_simple_cubic_golden.py --canonical-out "$REPORT_DIR/golden_dataset" --hkldebug "$REPORT_DIR/torch_hkl_debug.json" --emit-manifest --fixtures tests/fixtures/golden_data/simple_cubic | tee "$REPORT_DIR/canonical_capture.log"
6. ls tests/fixtures/golden_data/simple_cubic/*.npy > "$REPORT_DIR/fixture_files.log"
7. KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001 | tee "$REPORT_DIR/pytest_db_at_001.log"

**Pitfalls To Avoid**
- Environment freeze: no package installs or rebuilds.
- Do not reintroduce structure-factor scaling; apply only the post-sim √scale factor.
- Ensure `.npy` tensors persist in both report dir and fixtures before exiting.
- Update parity harness artifact path to `$LOOP_TS`; avoid writing into 2025-10-29T181603Z again.
- Keep loss masks bool and bragg/target float32 when saving fixtures.
- Capture first_divergence.json and metrics so tracing workflow stays valid.
- Abort and log if nanobrag_torch returns NaNs/zeros after scaling; treat as blocker.
- Confirm HKL debug JSON regenerates (98%+ hit rate) to catch geometry regressions.
- Avoid overwriting previous canonical_capture.log; always tee into new timestamp.
- Guard against shell glob failures when fixture `.npy` files are missing (treat as failure).

**If Blocked**
- If torch outputs remain mis-scaled or simulator errors, archive stderr to $REPORT_DIR/error.log, note ratio diagnostics, mark NANOBRAG-GOLDEN-001 `blocked` in docs/fix_plan.md Attempts History, and log the condition in galph_memory with next_action=switch_focus.

**Findings Applied (Mandatory)**
- SCALE-002 — Apply √(spot_scale_override) after the torch run to align intensities.
- SCALE-001 — Keep structure factors unscaled to avoid double-applying the scale.
- CONFIG-001 — Maintain documented detector/beam/crystal mappings while refreshing fixtures.
- PARITY-001 — Emit parity artifacts (metrics + first divergence) for debugging continuity.
- DIAGNOSTICS-001 — Capture parity logs under the new report directory for traceability.
- TESTING-003 — Preserve Active DB_AT_001 selector status with collected pytest evidence.
