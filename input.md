**Summary**: Restore canonical DB-AT-001 tensors inside this checkout and harden the generator so manifest emission fails when payload files are missing.
**Mode**: Parity
**Focus**: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
**Branch**: integration
**Mapped tests**: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke
**Artifacts**: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T191906Z/

**Do Now (hard validity contract)**
- Focus Item: NANOBRAG-GOLDEN-001
- Implement: scripts/generate_simple_cubic_golden.py::generate_simple_cubic_golden — add co-located tensor existence checks before manifest/copy steps and rerun capture so implementation.md A3/B1/B3/C1 stay satisfied in this workspace.
- Validate: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke
- Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T191906Z/

**Priorities & Rationale**
- docs/spec-db-core.md:20-41 — Canonical fixtures must persist `[panel, slow, fast]` tensors/masks locally to honor the core data contract.
- docs/spec-db-conformance.md:22-26 — DB_AT_001 acceptance requires provenance-rich manifests and canonical tensors to enforce correlation/localization thresholds.
- docs/forward_equivalence.md:46-52 — Parity loops must hit correlation ≥0.2 and ≥90% localization once real tensors are wired in, so we need reliable payloads before tightening thresholds.
- docs/nanobrag_api.md:22-45 — Regeneration must keep the detector/beam conventions aligned when re-running the capture after code safeguards.
- docs/spec-db-tracing.md:15-24 — First-divergence workflow depends on reproducible tensor artifacts; missing `.npy` files block tracing.
- docs/findings.md (MANIFEST-001, SCALE-002) — Generator changes must enforce co-resident payloads and maintain post-sim √scale so regenerated tensors remain comparable to DiffBragg.

**How-To Map**
1. export LOOP_TS=2025-10-29T191906Z
2. export REPORT_DIR=plans/active/NANOBRAG-GOLDEN-001/reports/$LOOP_TS
3. export PYTHONPATH="../nanoBragg/src:$PYTHONPATH"
4. KMP_DUPLICATE_LIB_OK=TRUE python scripts/generate_simple_cubic_golden.py --canonical-out "$REPORT_DIR/golden_dataset" --emit-manifest --fixtures tests/fixtures/golden_data/simple_cubic --hkldebug "$REPORT_DIR/torch_hkl_debug.json" | tee "$REPORT_DIR/canonical_capture.log"
5. ls tests/fixtures/golden_data/simple_cubic/*.npy > "$REPORT_DIR/fixture_files.txt" and record sha256sum outputs into "$REPORT_DIR/tensor_checksums.txt"
6. KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke | tee "$REPORT_DIR/pytest_db_at_001.log"
7. Copy parity artifacts (`parity_harness/*`, metrics, first_divergence) into "$REPORT_DIR/parity_harness/"

**Pitfalls To Avoid**
- Do not run the generator from a sibling checkout; stay in this repo so manifest paths and payloads align (MANIFEST-001).
- Keep environment frozen — no package installs or rebuilds.
- Ensure `np.save` writes succeed and verify `.npy` files exist before emitting manifest/metadata.
- Preserve SCALE-001/SCALE-002 guarantees: structure factors remain unscaled, apply √(spot_scale_override) post simulation only.
- Maintain HKL orientation (sample→source beam vector) when regenerating configs to avoid zero hit rates.
- Always set `KMP_DUPLICATE_LIB_OK=TRUE` for DB_AT_001 parity runs per CONFORMANCE-001.
- Archive torch_hkl_debug.json and parity metrics under the loop timestamp for tracing (PARITY-001).
- Fail fast if fixtures lack `.npy` payloads after generation; do not let pytest proceed with synthetic fallbacks.
- Keep loss mask dtype bool and confirm shapes before copying to fixtures.
- Watch for leftover artifacts in older timestamp directories; ensure new evidence lives under `$REPORT_DIR`.

**If Blocked**
- Capture the failing command and stderr into $REPORT_DIR/blocker.log, add the signature to docs/fix_plan.md Attempts History (Metrics/Artifacts placeholders), set focus status to `blocked`, and log the condition plus return criteria in galph_memory before pivoting.

**Findings Applied (Mandatory)**
- MANIFEST-001 — Co-locate tensor payloads with manifest; abort if `.npy` files are missing before checksum.
- SCALE-002 — Reapply √(spot_scale_override) after simulation when regenerating tensors to match DiffBragg scale.
- SCALE-001 — Leave structure factors unscaled so generator avoids double application of DiffBragg scale.
- PARITY-001 — Emit parity metrics/first-divergence artifacts for reproducible tracing under the loop timestamp.
- CONFORMANCE-001 — Use the documented DB_AT_001 selector with `KMP_DUPLICATE_LIB_OK=TRUE` and enforce provenance expectations.
- TESTING-003 — Keep DB_AT_001 selector Active by archiving the new pytest log under $REPORT_DIR.
