Summary: Map ROI-level evidence tasks to re-scope the DB-AT-001 canonical dataset plan under the Environment Freeze.
Mode: Docs
Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
Branch: integration
Mapped tests: KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001; KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001
Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T071728Z/{planning_notes.md,roi_hdf5_scout.md,torch_roi_plan.md,manifest_update_outline.md}
Do Now:
  1. NANOBRAG-GOLDEN-001::A2 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Inspect dbex_diffbragg_gpu.h5 ROIs to catalog bounding boxes, per-ROI stats, and confirm the absence of full-panel datasets; log findings to roi_hdf5_scout.md. tests: none.
  2. NANOBRAG-GOLDEN-001::A3 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Outline torch replay steps to regenerate full-panel tensors and slice them to match ROI footprints, documenting commands and expected artifacts in torch_roi_plan.md. tests: none.
  3. NANOBRAG-GOLDEN-001::B1 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Draft manifest/metadata adjustments for a hybrid ROI/full-panel dataset, including checksum strategy and provenance notes, in manifest_update_outline.md. tests: none.
  4. NANOBRAG-GOLDEN-001::D1 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Define the test/doc sync approach for refreshed DB_AT_001 selectors, specifying the collect-only commands and log destinations for this report. tests: KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001; KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001.
Priorities & Rationale:
- docs/spec-db-core.md:20-41 — Canonical tensors demand `[panel, slow, fast]` contracts; ROI inventory must prove how we satisfy or amend this requirement.
- docs/spec-db-tracing.md:15-60 — ROI diagnostics governance drives the need to log bounding boxes and stats before proposing spec changes.
- docs/forward_equivalence.md:21-52 — Exit criteria tie DiffBragg and torch baselines together, so plans for torch replay and manifest updates must stay aligned.
- docs/findings.md:15 — DIFFBRAGG-001 enforces documentation-first handling of diffBraggCUDA.cu:708 until a sanctioned patch exists.
- docs/TESTING_GUIDE.md:74-86 — Selector evidence must remain synchronized with collect-only logs whenever dataset contracts change.
How-To Map:
- `python - <<'PY' > plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T071728Z/roi_hdf5_scout.md
import h5py
import json
from pathlib import Path
h5_path = Path('plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T063817Z/golden_dataset/legacy/dbex_diffbragg_gpu.h5')
report = ["# DiffBragg ROI Inventory", ""]
if not h5_path.exists():
    report.append(f"Missing legacy HDF5 at {h5_path}")
else:
    with h5py.File(h5_path, 'r') as handle:
        rois = sorted([k for k in handle['/bragg'].keys() if k.startswith('roi')])
        report.append(f"Total ROI groups: {len(rois)}")
        report.append("\n## ROI Bounds and Stats")
        for key in rois:
            ds = handle['/bragg'][key]
            bbox = handle['/bragg'][key].attrs.get('bbox', None)
            peak = float(ds[()].max()) if ds.size else float('nan')
            report.append(f"- {key}: shape={ds.shape}, bbox={bbox}, max_intensity={peak:.3f}")
        report.append("\n## Full-panel datasets present?")
        full_panel = [name for name in handle.keys() if name in {'bragg_full', 'target_full', 'loss_mask_full'}]
        report.append(f"Found full-panel groups: {full_panel}")
report.append("\nSource: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T063817Z/golden_dataset/legacy/dbex_diffbragg_gpu.h5")
print('\n'.join(report))
PY`
- `python - <<'PY' > plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T071728Z/torch_roi_plan.md
from pathlib import Path
report = ["# Torch ROI Replay Plan", ""]
script = Path('plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T063817Z/capture_torch_only.py')
report.append(f"Existing torch capture script present: {script.exists()} at {script}")
report.append("\n## Proposed Steps")
report.extend([
    "1. Reuse capture_torch_only.py to emit per-panel `[panel, slow, fast]` tensors under a new golden_dataset/torch/ directory.",
    "2. Emit ROI slices by reading roi_hdf5_scout.md bbox definitions and slicing torch tensors before serialization.",
    "3. Save numpy outputs with deterministic filenames (`bragg_panel_{idx:02d}.npy`) and matching loss masks.",
    "4. Record torch command invocations, device selection, and seed values in capture logs for reproducibility.",
])
report.append("\n## Preconditions")
report.append("- Confirm `nanobrag_torch` import availability inside the frozen environment before scheduling execution.")
report.append("- Ensure `KMP_DUPLICATE_LIB_OK=TRUE` and `CUDA_VISIBLE_DEVICES` policy alignment to avoid runtime divergence.")
report.append("\nArtifacts will be staged under plans/active/NANOBRAG-GOLDEN-001/reports/<loop>/golden_dataset/torch/ once capture is authorized.")
print('\n'.join(report))
PY`
- `python - <<'PY' > plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T071728Z/manifest_update_outline.md
from pathlib import Path
import json
manifest_path = Path('tests/fixtures/golden_data/simple_cubic/manifest.json')
outline = ["# Manifest Update Outline", ""]
outline.append(f"Current manifest dataset_name: {json.loads(manifest_path.read_text())['dataset_name'] if manifest_path.exists() else 'missing'}")
outline.append("\n## Proposed Fields")
outline.extend([
    "- `datasets`: expand to list Diptych entries with `kind` (ROI|panel), `panel_index`, `filename`, `sha256_placeholder`.",
    "- `provenance`: add `diffbragg_capture` and `torch_capture` sub-sections with command logs and git SHAs.",
    "- `roi_catalog`: document bbox coordinates and ROI id ordering for parity harness alignment.",
    "- `spec_version`: bump to indicate hybrid ROI/full-panel compliance requirements.",
])
outline.append("\n## Verification Hooks")
outline.extend([
    "- Update parity_loader fixtures to validate ROI-to-panel mapping and bbox integrity.",
    "- Embed checksum verification for both ROI and panel files using existing loader utilities.",
])
outline.append("\nAll new text will cite docs/spec-db-conformance.md:23-26 and docs/spec-db-tracing.md:15-60 when implemented.")
print('\n'.join(outline))
PY`
- `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001 |& tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T071728Z/collect_db_at_001_parity.log`
- `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001 |& tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T071728Z/collect_db_at_001_forward.log`
Pitfalls To Avoid:
- Do not modify simtbx or install packages; Environment Freeze still applies.
- Avoid overwriting prior report artifacts; write new evidence under 2025-10-29T071728Z/.
- Keep ROI indices ordered to preserve deterministic first-divergence analysis.
- Validate HDF5 reads without extracting large tensors into memory to prevent OOM.
- Document any gaps immediately in docs/fix_plan.md before considering scope changes.
- Ensure planned torch replay commands respect `KMP_DUPLICATE_LIB_OK=TRUE` and device selection requirements.
- Leave Metrics/Artifacts placeholders intact when appending ledger attempts.
- Coordinate manifest changes with parity_loader expectations to avoid breaking existing tests.
- Do not downgrade selectors without collecting evidence; use doc sync instead.
- Capture hash strategies without computing new SHA256 values until artifacts exist.
If Blocked: Record the blocking condition in docs/fix_plan.md Attempts History, stash partial notes under the report directory, and update galph_memory with `next_action=switch_focus`.
Findings Applied (Mandatory):
- DIFFBRAGG-001 — Plan prioritizes evidence/documentation for the diffBragg cleanup bug before any patch proposal.
- CONFORMANCE-001 — Maintains focus on selector compliance while reshaping dataset plans.
- TESTING-003 — Ensures collect-only commands/log paths are defined for selector synchronization.
- PARITY-001 — Preserves ROI ordering and first-divergence metadata obligations in the planning steps.
Doc Sync Plan (Mandatory):
- `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001 |& tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T071728Z/collect_db_at_001_parity.log`
- `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001 |& tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T071728Z/collect_db_at_001_forward.log`
- Update docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md entries for DB_AT_001 to reference the new 2025-10-29T071728Z logs after collection.
