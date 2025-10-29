**Summary**: Reapply the canonical torch scale, regenerate the golden tensors, and repoint DB_AT_001 parity artifacts under the new loop timestamp.
**Mode**: Parity
**Focus**: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
**Branch**: integration
**Mapped tests**: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001
**Artifacts**: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T190533Z/{golden_dataset/, parity_harness/, canonical_capture.log, torch_hkl_debug.json, pytest_db_at_001.log}

**Do Now (hard validity contract)**
- Focus Item: NANOBRAG-GOLDEN-001
- Implement: scripts/generate_simple_cubic_golden.py::generate_simple_cubic_golden; tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity.test_db_at_001_parity_smoke (checklist A3/B1/B3/C1)
- Validate: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity.test_db_at_001_parity_smoke
- Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T190533Z/

**Priorities & Rationale**
- plans/active/NANOBRAG-GOLDEN-001/implementation.md:8-17 — Target checklist A3/B1/B3/C1 to finish canonical tensor emission, manifest wiring, and parity harness swap in one loop.
- docs/spec-db-core.md:20-33 — Regenerated fixtures must supply `[panel, slow, fast]` tensors and masks that align with the spec contract.
- docs/spec-db-conformance.md:22-26 — DB_AT_001 parity smoke requires manifest provenance and correlation/localization thresholds once canonical data exists.
- docs/forward_equivalence.md:46-52 — Enforce median correlation ≥0.2 and ≥90% localization after scaling fix to regain parity confidence.
- docs/findings.md:13-19 — Honor SCALE-001/SCALE-002 and HKL-ORIENT-001 guardrails so intensity scaling and beam orientation stay compliant during regeneration.

**How-To Map**
1. export LOOP_TS=2025-10-29T190533Z
2. export REPORT_DIR=plans/active/NANOBRAG-GOLDEN-001/reports/$LOOP_TS
3. mkdir -p "$REPORT_DIR/golden_dataset" "$REPORT_DIR/parity_harness"
4. export PYTHONPATH=../nanoBragg/src:$PYTHONPATH
5. KMP_DUPLICATE_LIB_OK=TRUE python scripts/generate_simple_cubic_golden.py --canonical-out "$REPORT_DIR/golden_dataset" --emit-manifest --fixtures tests/fixtures/golden_data/simple_cubic --hkldebug "$REPORT_DIR/torch_hkl_debug.json" | tee "$REPORT_DIR/canonical_capture.log"
6. find tests/fixtures/golden_data/simple_cubic -maxdepth 1 -name '*.npy' -print | sort > "$REPORT_DIR/fixture_files.txt"
7. KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity.test_db_at_001_parity_smoke | tee "$REPORT_DIR/pytest_db_at_001.log"

**Pitfalls To Avoid**
- No package installs or rebuilds; environment freeze holds.
- Do not re-scale structure factors (SCALE-001); only apply post-sim √scale.
- Ensure torch outputs are bool-masked and saved as float32/uint8 → bool before writing fixtures.
- Update parity harness output paths to $LOOP_TS to avoid writing into 2025-10-29T181603Z artifacts.
- Capture first_divergence/metrics artifacts under the new report dir to satisfy PARITY-001.
- Treat nanobrag_torch zero/NaN output as a blocker; log ratios before exiting.
- Keep HKL incident direction sample→source (HKL-ORIENT-001) when touching generator configs.
- Confirm torch HKL hit rate (~>95%) in torch_hkl_debug.json before trusting metrics.
- Guard file globbing so fixture `.npy` absence fails fast rather than silently.
- Preserve manifest SHA256 calculations; do not regress checksum coverage.

**If Blocked**
- Archive failing command stderr into $REPORT_DIR/error.log, add the signature to docs/fix_plan.md Attempts History (Metrics/Artifacts placeholders), mark NANOBRAG-GOLDEN-001 `blocked`, and log the condition plus return criteria in galph_memory with next_action=switch_focus.

**Findings Applied (Mandatory)**
- SCALE-001 — Keep structure factors unscaled; only adjust torch outputs per the generator fix.
- SCALE-002 — Reapply √(spot_scale_override) after simulation before persisting tensors.
- HKL-ORIENT-001 — Maintain sample→source beam vector when regenerating configs to preserve HKL coverage.
- PARITY-001 — Continue emitting parity diagnostics (metrics + first_divergence) in the refreshed report directory.
- DIAGNOSTICS-001 — Store canonical capture logs and parity artifacts for traceability.
- TESTING-003 — Use the documented DB_AT_001 selector and keep its artifact log under the loop timestamp.
