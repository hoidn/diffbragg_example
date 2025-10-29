**Summary**: Guard canonical capture against cross-checkout outputs and regenerate DB_AT_001 tensors inside this repo so parity smoke can validate the refreshed fixtures.
**Mode**: Parity
**Focus**: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
**Branch**: integration
**Mapped tests**: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke
**Artifacts**: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T194739Z/

**Do Now (hard validity contract)**
- Focus Item: NANOBRAG-GOLDEN-001
- Implement: scripts/generate_simple_cubic_golden.py::generate_simple_cubic_golden — add repo-root guards for `canonical_out`/`fixtures_dir`, then rerun capture in-place to satisfy implementation.md checkpoints A3/B1/B3/C1 with local tensors and provenance.
- Validate: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke
- Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T194739Z/

**Priorities & Rationale**
- docs/spec-db-core.md:16-48 — Data contract demands locally available `[panel, slow, fast]` photon tensors, so regeneration plus guardrails keep canonical payloads resident.
- docs/spec-db-conformance.md:23-33 — DB_AT_001 thresholds require canonical tensors and manifest provenance before parity enforcement proceeds.
- docs/forward_equivalence.md:34-78 — ROI correlation/localization metrics only hold when DiffBragg/torch outputs are scale-aligned, necessitating the regeneration + smoke run.
- docs/nanobrag_api.md:28-88 — Detector/beam/crystal conventions and mask semantics must be preserved when emitting tensors post √scale.
- docs/spec-db-tracing.md:10-36 — First-divergence workflow expects diagnostics for regenerated payloads, so plan captures metrics/logs before pytest.
- tests/fixtures/golden_data/simple_cubic/manifest.json:1-26 — Manifest still points to `diffbragg_example_2` and fixtures lack `.npy`, confirming rescope to local capture.

**How-To Map**
1. export LOOP_TS=2025-10-29T194739Z; export REPORT_DIR=plans/active/NANOBRAG-GOLDEN-001/reports/$LOOP_TS; mkdir -p "$REPORT_DIR" "$REPORT_DIR/golden_dataset" "$REPORT_DIR/logs"
2. export PYTHONPATH="../nanoBragg/src:$PYTHONPATH"
3. KMP_DUPLICATE_LIB_OK=TRUE python scripts/generate_simple_cubic_golden.py --canonical-out "$REPORT_DIR/golden_dataset" --hkldebug "$REPORT_DIR/torch_hkl_debug.json" --emit-manifest --fixtures tests/fixtures/golden_data/simple_cubic | tee "$REPORT_DIR/canonical_capture.log"
4. python - <<'PY' | tee "$REPORT_DIR/scale_diagnostics.txt"
import json, numpy as np
from pathlib import Path
report = Path("$REPORT_DIR")
diff = np.load(report/"golden_dataset"/"legacy"/"bragg_diffbragg.npy")
torch = np.load(report/"golden_dataset"/"torch"/"bragg_torch.npy")
ratio = float(torch.max() / diff.max()) if diff.max() else float("nan")
print(f"torch_max={torch.max():.6e}")
print(f"diff_max={diff.max():.6e}")
print(f"max_ratio={ratio:.6e}")
with open(report/"golden_dataset"/"torch"/"panel_metrics.json") as fh:
    metrics = json.load(fh)
print(json.dumps(metrics[0], indent=2))
PY
5. ls tests/fixtures/golden_data/simple_cubic/*.npy > "$REPORT_DIR/fixture_files.txt" && sha256sum tests/fixtures/golden_data/simple_cubic/*.npy > "$REPORT_DIR/tensor_checksums.txt"
6. KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke | tee "$REPORT_DIR/pytest_db_at_001.log"
7. append parity + regeneration summary to docs/fix_plan.md Attempts History (include Metrics:/Artifacts: placeholders) and refresh plans/active/NANOBRAG-GOLDEN-001/reports/$LOOP_TS/README.md if missing.

**Pitfalls To Avoid**
- Environment freeze: no package installs; treat missing imports as blockers with logged signatures.
- Guard canonical_out/fixtures under repo_root to prevent cross-checkout manifests.
- Keep structure factors unscaled and apply √(spot_scale_override) post-simulation only.
- Preserve torch tensor dtype/order; verify loss masks remain boolean before copy.
- Do not overwrite previous reports; isolate work in $REPORT_DIR.
- Capture diagnostics before pytest so parity failures have evidence.
- Ensure KMP_DUPLICATE_LIB_OK=TRUE is exported for parity smoke.
- Avoid partial fixture updates; copy all `.npy` + manifest atomically.

**If Blocked**
- Capture failing command output to "$REPORT_DIR/blocker.log", update docs/fix_plan.md Attempts History with Metrics:/Artifacts: placeholders plus unblock criteria, mark focus `blocked`, and log the block/return conditions in galph_memory.md before switching.

**Findings Applied (Mandatory)**
- MANIFEST-001 — Enforce local tensor presence before emitting/copying manifests.
- SCALE-001 — Leave structure factors unscaled so torch intensity isn't inflated.
- SCALE-002 — Reapply √(spot_scale_override) post-simulation to match DiffBragg magnitude.
- CONFIG-001 — Maintain detector/mask conventions during regeneration.
- CONFORMANCE-001 — Validate with the documented DB_AT_001 parity selector and archive evidence.
- PARITY-001 — Capture diagnostics to support first-divergence tracing workflows.
