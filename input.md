**Summary**: Apply SCALE-002 by fixing post-simulation scaling diagnostics and regenerating the canonical DB-AT-001 tensors inside this repo so parity evidence reflects local payloads.
**Mode**: Parity
**Focus**: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
**Branch**: integration
**Mapped tests**: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke
**Artifacts**: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T193557Z/

**Do Now (hard validity contract)**
- Focus Item: NANOBRAG-GOLDEN-001
- Implement: scripts/generate_simple_cubic_golden.py::generate_simple_cubic_golden — instrument √(spot_scale_override) diagnostics, ensure torch panels are scaled and copied into this checkout, and satisfy implementation.md checklists A3/B1/B3/C1.
- Validate: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke
- Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T193557Z/

**Priorities & Rationale**
- docs/spec-db-core.md:16-33 — Canonical fixtures must surface `[panel, slow, fast]` photon-intensity tensors locally, so scaling fixes and tensor copies are mandatory.
- docs/spec-db-conformance.md:23-26 — DB_AT_001 parity requires provenance-rich manifolds plus canonical tensors before thresholds can pass.
- docs/forward_equivalence.md:46-52 — Correlation ≥0.2 and ≥90% localization depend on torch intensities matching DiffBragg after √scale is applied.
- docs/nanobrag_api.md:22-68 — Regeneration must align with torch beam/detector conventions when post-sim scaling is injected.
- docs/findings.md:48-71 — MANIFEST-001 and SCALE-002 findings enforce local payload presence and √scale post-processing during capture.

**How-To Map**
1. export LOOP_TS=2025-10-29T193557Z; export REPORT_DIR=plans/active/NANOBRAG-GOLDEN-001/reports/$LOOP_TS
2. mkdir -p "$REPORT_DIR" "$REPORT_DIR/golden_dataset" "$REPORT_DIR/logs"
3. export PYTHONPATH="../nanoBragg/src:$PYTHONPATH"
4. KMP_DUPLICATE_LIB_OK=TRUE python scripts/generate_simple_cubic_golden.py --canonical-out "$REPORT_DIR/golden_dataset" --hkldebug "$REPORT_DIR/torch_hkl_debug.json" --emit-manifest --fixtures tests/fixtures/golden_data/simple_cubic | tee "$REPORT_DIR/canonical_capture.log"
5. python - <<'PY' | tee "$REPORT_DIR/scale_diagnostics.txt"
import numpy as np, json
from pathlib import Path
report = Path("$REPORT_DIR")
diff = np.load(report/"golden_dataset"/"legacy"/"bragg_diffbragg.npy")
torch = np.load(report/"golden_dataset"/"torch"/"bragg_torch.npy")
ratio = float(torch.max() / diff.max()) if diff.max() else float('nan')
print(f"torch_max={torch.max():.6e}")
print(f"diff_max={diff.max():.6e}")
print(f"max_ratio={ratio:.6e}")
with open(report/"golden_dataset"/"torch"/"panel_metrics.json") as fh:
    metrics = json.load(fh)
print(f"panel_metrics[0]: torch_max={metrics[0]['torch_max']:.6e}, loss_mask_coverage={metrics[0]['loss_mask_coverage']:.6e}")
PY
6. ls tests/fixtures/golden_data/simple_cubic/*.npy > "$REPORT_DIR/fixture_files.txt" && sha256sum tests/fixtures/golden_data/simple_cubic/*.npy > "$REPORT_DIR/tensor_checksums.txt"
7. KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke | tee "$REPORT_DIR/pytest_db_at_001.log"
8. tar -C tests/fixtures/parity_harness -cf "$REPORT_DIR/parity_harness_artifacts.tar" . && ls "$REPORT_DIR"

**Pitfalls To Avoid**
- Environment: treat missing deps as blockers; log the error and mark the focus blocked (no installs).
- Ensure generator runs from this checkout so manifest paths and tensors align (MANIFEST-001).
- Keep structure factors unscaled and apply √(spot_scale_override) only after simulation (SCALE-001/002).
- Confirm torch panels remain float32 and preserve `[panel, slow, fast]` ordering when stacking.
- Verify loss masks stay boolean before copying; do not regress CONFIG-001 guard.
- Capture scaling diagnostics before running pytest to avoid chasing parity noise without evidence.
- Avoid overwriting previous artifacts; use the LOOP_TS path for all outputs.
- Fail fast if torch/diff max ratio is off by >5% and record the mismatch in docs/fix_plan.md Attempts History.

**If Blocked**
- Save failing command output to "$REPORT_DIR/blocker.log", append the signature plus return criteria to docs/fix_plan.md Attempts History (Metrics/Artifacts placeholders), set focus status to `blocked`, and log the block with next steps in galph_memory.md before pivoting.

**Findings Applied (Mandatory)**
- MANIFEST-001 — Generator must abort if fixtures lack co-resident tensors before manifest emission.
- SCALE-001 — Prevent duplicate √scale application by leaving structure factors untouched.
- SCALE-002 — Reapply √(spot_scale_override) post simulation so torch intensities match DiffBragg scale.
- CONFIG-001 — Maintain detector/beam/mask conventions when regenerating canonical tensors.
- PARITY-001 — Archive parity metrics and diagnostics for reproducible first-divergence tracing.
- CONFORMANCE-001 — Use the documented DB_AT_001 selector with `KMP_DUPLICATE_LIB_OK=TRUE` when validating the regeneration.
