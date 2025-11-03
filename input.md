**Summary**: Instrument canonical capture with ROI triptych dumps and re-run inside this checkout so we can localize the torch vs DiffBragg mismatch that keeps DB_AT_001 parity below spec.
**Mode**: Parity
**Focus**: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
**Branch**: integration
**Mapped tests**: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke
**Artifacts**: plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-03T233556Z/

**Do Now (hard validity contract)**
- Focus Item: NANOBRAG-GOLDEN-001
- Implement: scripts/generate_simple_cubic_golden.py::compute_roi_metrics — emit sampled ROI triptychs (DiffBragg, torch, target, mask) plus metric JSON so parity gaps can be inspected without rerunning refinement.
- Validate: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke
- Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-03T233556Z/

**Priorities & Rationale**
- docs/spec-db-tracing.md:12 — First-divergence workflow demands localized artifacts (triptychs, metrics) before tightening thresholds.
- docs/spec-db-core.md:20 — Canonical tensors must stay in `[panel, slow, fast]` order; ROI exports guard against silent axis swaps.
- docs/spec-db-conformance.md:23 — DB_AT_001 correlation/localization thresholds remain unmet; we need richer diagnostics before enforcing C2.
- docs/nanobrag_api.md:34 — Detector mask semantics must be verified; ROI dumps confirm whether torch respects trusted-mask polarity.
- docs/findings.md:14 — SCALE-001/002 + MANIFEST-001 remain active, so regeneration must stay within this repo and preserve scale provenance.

**How-To Map**
1. export LOOP_TS=2025-11-03T233556Z; export REPORT_DIR=plans/active/NANOBRAG-GOLDEN-001/reports/$LOOP_TS; mkdir -p "$REPORT_DIR" "$REPORT_DIR/golden_dataset" "$REPORT_DIR/logs" "$REPORT_DIR/roi_triptychs"
2. Modify `compute_roi_metrics` to collect deterministic ROI samples (seed 42) and, when a new `roi_dump_dir` parameter is provided, write per-ROI `.npz` bundles (`diff`, `torch`, `target`, `mask`) plus a companion JSON index summarizing correlation/RMSE/localization.
3. Wire the new optional argument through `generate_simple_cubic_golden` (env-controlled or auto) so CLI invocations can point at `$REPORT_DIR/roi_triptychs`.
4. export PYTHONPATH="../nanoBragg/src:$PYTHONPATH"
5. KMP_DUPLICATE_LIB_OK=TRUE python scripts/generate_simple_cubic_golden.py --canonical-out "$REPORT_DIR/golden_dataset" --hkldebug "$REPORT_DIR/torch_hkl_debug.json" --emit-manifest --fixtures tests/fixtures/golden_data/simple_cubic --roi-dump "$REPORT_DIR/roi_triptychs" | tee "$REPORT_DIR/canonical_capture.log"
6. python - <<'PY' | tee "$REPORT_DIR/roi_summary.txt"
import json, numpy as np, pathlib
report = pathlib.Path("$REPORT_DIR")
with open(report/"roi_triptychs"/"index.json") as fh:
    idx = json.load(fh)
print(f"roi_samples={len(idx['samples'])}")
vals = [s['correlation'] for s in idx['samples']]
if vals:
    print(f"median_corr={np.median(vals):.4f}")
torch = np.load(report/"golden_dataset"/"torch"/"bragg_torch.npy")
diff = np.load(report/"golden_dataset"/"legacy"/"bragg_diffbragg.npy")
mask = np.load(report/"golden_dataset"/"torch"/"loss_mask_panel_0.npy").astype(bool)
print(f"global_corr={np.corrcoef(torch[mask], diff[mask])[0,1]:.4f}")
PY
7. KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke | tee "$REPORT_DIR/pytest_db_at_001.log"
8. Append run details + metrics + artifact pointers to docs/fix_plan.md Attempts History and stash summary notes alongside roi index in `$REPORT_DIR`.

**Pitfalls To Avoid**
- Respect environment freeze; do not pip-install nanobrag_torch or friends.
- Ensure ROI dumps only reference local paths (no `_2` checkout leakage).
- Keep RNG seeding deterministic so subsequent loops diff cleanly.
- Persist `.npz` files under artifact dir, not under tests/fixtures.
- Avoid loading entire ROI set into memory twice; stream or slice.
- Do not change manifest layout; additional artifacts belong outside fixtures.
- Preserve torch tensor dtype/shape when writing `.npz` to avoid float64 drift.
- Guard CLI option parsing so existing users without `--roi-dump` remain unaffected.
- Capture failures to `$REPORT_DIR/blocker.log` before aborting.

**If Blocked**
- Save failing command output to "$REPORT_DIR/blocker.log", update docs/fix_plan.md Attempts History with Metrics:/Artifacts: placeholders and unblock criteria, mark focus `blocked`, and log the block + return conditions in galph_memory.md before pivoting.

**Findings Applied (Mandatory)**
- MANIFEST-001 — Keep manifest emission gated on local tensor files; ROI dumps must not bypass checks.
- SCALE-001 — Leave structure factors untouched when exporting diagnostics.
- SCALE-002 — Maintain √(spot_scale_override) post-sim scaling before ROI serialization.
- CONFIG-001 — Detector/mask mapping stays per helper contracts; ROI dumps validate compliance.
- PARITY-001 — Archive diagnostics so first-divergence workflow has evidence.
- CONFORMANCE-001 — Use the documented DB_AT_001 parity selector to validate instrumentation.

**Pointers**
- `docs/spec-db-core.md:20`
- `docs/spec-db-tracing.md:12`
- `docs/findings.md:13`
- `plans/active/NANOBRAG-GOLDEN-001/implementation.md:1`

**Next Up (optional)**: Author targeted ROI unit tests in `tests/dbex/test_db_at_001_parity.py` once triptychs confirm root cause.
