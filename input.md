**Summary**: Capture per-ROI peak offsets, regenerate canonical tensors inside this checkout, and rerun DB_AT_001 parity smoke to localize the torch vs DiffBragg misalignment.
**Mode**: Parity
**Focus**: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
**Branch**: integration
**Mapped tests**: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke
**Artifacts**: plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T000201Z/

**Do Now (hard validity contract)**
- Focus Item: NANOBRAG-GOLDEN-001
- Implement: scripts/generate_simple_cubic_golden.py::compute_roi_metrics — log per-ROI torch/diff peak coordinates, offsets, and emitted `roi_XXXX.npz` filenames so parity gaps can be traced without ad-hoc probes.
- Validate: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke
- Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T000201Z/

**Priorities & Rationale**
- docs/spec-db-tracing.md:12 — First-divergence workflow expects peak metadata to accompany triptych dumps before tightening thresholds.
- docs/findings.md:13 — MANIFEST-001 requires canonical generators to emit artifacts within the active workspace; regeneration must stay local.
- docs/findings.md:15 — SCALE-002 mandates consistent post-sim scaling; logging offsets ensures we don’t regress while re-running the capture.
- docs/spec-db-conformance.md:23 — DB_AT_001 metrics must trend upward; parity smoke remains the acceptance checkpoint.

**How-To Map**
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. export LOOP_TS=2025-11-04T000201Z; export REPORT_DIR=plans/active/NANOBRAG-GOLDEN-001/reports/$LOOP_TS; mkdir -p "$REPORT_DIR" "$REPORT_DIR/golden_dataset" "$REPORT_DIR/roi_triptychs"
3. Update `compute_roi_metrics` to capture torch/diff peak coordinates, compute `(dy, dx)` offsets, and include the corresponding `roi_XXXX.npz` filename in both the returned records and `index.json`; ensure existing sampling/seed logic stays deterministic.
4. Re-run `scripts/generate_simple_cubic_golden.py` with local paths: `PYTHONPATH=../nanoBragg/src:$PYTHONPATH KMP_DUPLICATE_LIB_OK=TRUE python scripts/generate_simple_cubic_golden.py --canonical-out "$REPORT_DIR/golden_dataset" --hkldebug "$REPORT_DIR/torch_hkl_debug.json" --emit-manifest --fixtures tests/fixtures/golden_data/simple_cubic --roi-dump "$REPORT_DIR/roi_triptychs" | tee "$REPORT_DIR/canonical_capture.log"`
5. python - <<'PY' > "$REPORT_DIR/roi_offsets.json"
import json, math, os, pathlib
report = pathlib.Path(os.environ["REPORT_DIR"])
index_path = report/"roi_triptychs"/"index.json"
index = json.loads(index_path.read_text()) if index_path.exists() else {}
logs = {"n_dumps": index.get("n_dumps"), "max_abs_offset": 0.0, "median_abs_offset": 0.0, "samples": []}
offsets = []
for sample in index.get('samples', []):
    torch_peak = sample.get('torch_peak')
    diff_peak = sample.get('diff_peak')
    if torch_peak and diff_peak:
        dy = torch_peak[0] - diff_peak[0]
        dx = torch_peak[1] - diff_peak[1]
        offsets.append(math.hypot(dy, dx))
        logs['samples'].append({
            'roi_idx': sample.get('roi_idx'),
            'panel_id': sample.get('panel_id'),
            'dy': dy,
            'dx': dx,
            'filename': sample.get('filename')
        })
if offsets:
    offsets.sort()
    logs['max_abs_offset'] = max(offsets)
    logs['median_abs_offset'] = offsets[len(offsets)//2]
print(json.dumps(logs, indent=2))
PY
find "$REPORT_DIR/roi_triptychs" -maxdepth 1 -name 'roi_*.npz' -print > "$REPORT_DIR/roi_npz_listing.txt"
6. KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke | tee "$REPORT_DIR/pytest_db_at_001.log"
7. Append metrics + artifact pointers to docs/fix_plan.md Attempts History and stash parity notes under "$REPORT_DIR/"

**Pitfalls To Avoid**
- No package installs (Environment Freeze)
- Keep roi_dump payloads inside this repo; do not reference `_2` checkout paths
- Preserve float32/bool dtypes when writing `.npz`
- Respect deterministic RNG seed for ROI sampling
- Avoid mutating manifest schema beyond adding offset metadata references
- Don’t drop existing metrics fields from `index.json`
- Preserve `[panel, slow, fast]` ordering when slicing
- Keep torch post-sim scaling (√scale) unchanged while adding logging
- Capture command outputs if failures occur (redirect to blocker log)

**If Blocked**
- Save failing command output to "$REPORT_DIR/blocker.log", update docs/fix_plan.md Attempts History with Metrics:/Artifacts: placeholders and unblock criteria, mark the focus blocked, and record the block & return conditions in galph_memory.md.

**Findings Applied (Mandatory)**
- MANIFEST-001 — Regenerate tensors and manifests within this checkout, error if payloads missing.
- SCALE-002 — Retain √(spot_scale_override) scaling before logging offsets.
- PARITY-001 — Enrich first-divergence artifacts with localized metadata for ROI inspection.
- CONFIG-001 — Ensure mask/axis contracts remain `[panel, slow, fast]` when writing offsets.
- TESTING-003 — Parity selector stays Active; capture pytest log in artifacts.

**Pointers**
- docs/spec-db-tracing.md:12
- docs/findings.md:13
- docs/spec-db-conformance.md:23
- plans/active/NANOBRAG-GOLDEN-001/implementation.md:1

**Next Up (optional)**: Investigate torch detector geometry (beam center / basis vectors) once peak offsets are logged.
