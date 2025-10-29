Summary: Prepare ROI bounding-box catalog and canonical dataset playbook to unblock NANOBRAG-GOLDEN-001 canonical capture under Environment Freeze.
Mode: Docs
Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
Branch: integration
Mapped tests: KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001; KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001
Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T075930Z/{roi_bbox_catalog.json,roi_bbox_summary.md,torch_capture_playbook.md,manifest_delta_outline.md}
Do Now:
  1. NANOBRAG-GOLDEN-001::A2 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Extract ROI bbox catalog from refGeom.refl using dxtbx, emit JSON to roi_bbox_catalog.json, and log summary stats to roi_bbox_summary.md while cross-checking the legacy HDF5 ROI groups; tests: none.
  2. NANOBRAG-GOLDEN-001::A3 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Draft torch capture playbook mapping the bbox catalog onto `[panel, slow, fast]` tensor writes with seeding/device policy, storing the outline in torch_capture_playbook.md; tests: none.
  3. NANOBRAG-GOLDEN-001::B1 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Outline manifest/metadata deltas introducing canonical dataset entries plus roi_catalog references and checksum plan inside manifest_delta_outline.md; tests: none.
  4. NANOBRAG-GOLDEN-001::D1 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Refresh DB_AT_001 collect-only evidence (parity + forward selectors) with logs under the new report directory and note doc-sync targets; tests: KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001; KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001.
Priorities & Rationale:
- docs/spec-db-core.md:20-33 — Bounding-box semantics and `[panel, slow, fast]` ordering demand a vetted ROI catalog before canonical tensors are regenerated.
- docs/spec-db-conformance.md:23-26 — Manifest provenance/checksum rules require pre-planned metadata updates aligned with canonical files.
- docs/forward_equivalence.md:21-52 — DiffBragg vs torch comparison workflow drives the torch capture playbook requirements.
- docs/TESTING_GUIDE.md:63-66 — Selector taxonomy mandates fresh collect-only logs whenever DB_AT_001 evidence is updated.
- docs/findings.md (DIFFBRAGG-001, TESTING-003) — Documentation-first handling of the diffBragg bug and selector activation guardrails shape the plan.
How-To Map:
- `python - <<'PY' > plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T075930Z/roi_bbox_catalog.json
import json
import sys
from pathlib import Path
from dials.array_family import flex

table = flex.reflection_table.from_file('refGeom.refl')
records = []
for idx, (panel, bbox) in enumerate(zip(table['panel'], table['bbox'])):
    records.append({
        "roi_id": f"roi{idx}",
        "panel": int(panel),
        "bbox": {
            "fast0": int(bbox[0]),
            "fast1": int(bbox[1]),
            "slow0": int(bbox[2]),
            "slow1": int(bbox[3])
        }
    })
json.dump({"source": "refGeom.refl", "roi_count": len(records), "entries": records}, sys.stdout, indent=2, sort_keys=True)
PY`
- `python - <<'PY' > plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T075930Z/roi_bbox_summary.md
import json
from pathlib import Path
import h5py

catalog_path = Path('plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T075930Z/roi_bbox_catalog.json')
h5_path = Path('plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T063817Z/golden_dataset/legacy/dbex_diffbragg_gpu.h5')

lines = ["# ROI Bounding Box Summary", ""]
if catalog_path.exists():
    data = json.loads(catalog_path.read_text())
    lines.append(f"- Catalog entries: {data['roi_count']}")
    if data['entries']:
        lines.append(f"- First ROI bbox: {data['entries'][0]['bbox']}")
else:
    lines.append(f"- Missing catalog at {catalog_path}")

if h5_path.exists():
    with h5py.File(h5_path, 'r') as handle:
        roi_keys = sorted(k for k in handle['/bragg'].keys() if k.startswith('roi'))
        lines.append(f"- Legacy HDF5 ROI groups: {len(roi_keys)}")
        bbox_attrs = sum(1 for k in roi_keys if handle['/bragg'][k].attrs.get('bbox') is not None)
        lines.append(f"- Stored bbox attributes in HDF5: {bbox_attrs} (expected 0)")
else:
    lines.append(f"- Missing legacy HDF5 at {h5_path}")

lines.append("")
lines.append("Source artifacts: refGeom.refl, plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T063817Z/golden_dataset/legacy/dbex_diffbragg_gpu.h5")
print('\\n'.join(lines))
PY`
- `python - <<'PY' > plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T075930Z/torch_capture_playbook.md
from pathlib import Path

lines = [
    "# Torch Capture Playbook",
    "",
    "## Overview",
    "Leverage the ROI bbox catalog to drive canonical `[panel, slow, fast]` tensor exports via `nanobrag_torch`, aligning with docs/forward_equivalence.md:21-52.",
    "",
    "## Steps",
    "1. Activate Environment Freeze-compliant simtbx env (`which python`) and verify `import nanobrag_torch` succeeds.",
    "2. Load detector/beam/crystal configs via `dbex.prepare_refinement_inputs` and honor mapping rules from docs/config_crosswalk.md:15-72.",
    "3. Run per-panel forward pass with deterministic seed + device (`CUDA_VISIBLE_DEVICES=0`, `torch.manual_seed(1337)`) and write tensors to `golden_dataset/torch/bragg_panel_{panel:02d}.npy`.",
    "4. Slice ROI tensors using bbox entries from `roi_bbox_catalog.json`, persisting ROI extracts and documenting ordering.",
    "5. Capture metrics (`metrics.json`) and config snapshots for parity harness ingestion.",
    "",
    "## Preconditions",
    "- DIFFBRAGG-001 still blocks legacy fallback; avoid rerunning broken diffBragg capture.",
    "- Confirm ROI catalog covers exactly the legacy ROI groups (92 entries).",
    "",
    "## Artifacts",
    "- Tensor dumps under `plans/active/NANOBRAG-GOLDEN-001/reports/<loop>/golden_dataset/torch/`.",
    "- Logs: `torch_capture.log`, `metrics.json`, ROI overlay placeholders.",
]

print('\\n'.join(lines))
PY`
- `python - <<'PY' > plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T075930Z/manifest_delta_outline.md
import json
from pathlib import Path

manifest_path = Path('tests/fixtures/golden_data/simple_cubic/manifest.json')
dataset_name = None
if manifest_path.exists():
    dataset_name = json.loads(manifest_path.read_text()).get('dataset_name')

lines = [
    "# Manifest Delta Outline",
    "",
    f"- Current dataset_name: {dataset_name or 'missing'}",
    "",
    "## Planned Changes",
    "- Replace fallback dataset name with canonical identifier (e.g., `nanoBragg_canonical_v1`).",
    "- Introduce `datasets` array entries for `panel` and `roi` payloads with SHA256 placeholders.",
    "- Add `roi_catalog` reference pointing to roi_bbox_catalog.json (docs/spec-db-core.md:20-33 alignment).",
    "- Expand `provenance` with DiffBragg/torch command logs, git SHAs, and environment tags per POLICY-001.",
    "",
    "## Verification Hooks",
    "- Update parity_loader to validate checksums and ROI ordering.",
    "- Ensure docs/spec-db-conformance.md:23-26 thresholds are testable via pytest fixtures.",
    "",
    "## Follow-up",
    "- After canonical tensors exist, compute SHA256 hashes and refresh metadata.json accordingly.",
]

print('\\n'.join(lines))
PY`
- `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001 |& tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T075930Z/collect_db_at_001_parity.log`
- `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001 |& tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T075930Z/collect_db_at_001_forward.log`
Pitfalls To Avoid:
- Do not mutate `tests/fixtures/golden_data/simple_cubic/` assets until canonical tensors are validated.
- Preserve ROI ordering from reflection table indices to maintain first-divergence determinism (PARITY-001).
- Avoid rerunning DiffBragg capture while DIFFBRAGG-001 remains unresolved; rely on existing artifacts.
- Keep catalog JSON stable (sorted keys, integers) to ease future checksum comparisons.
- Document any dxtbx import failures immediately and treat them as Environment Freeze blockers.
- Maintain artifact isolation per loop; never append to prior timestamp directories.
- Capture commands verbatim for provenance to satisfy docs/spec-db-conformance.md:23-26.
If Blocked: Record the blocker in docs/fix_plan.md Attempts History with Metrics/Artifacts placeholders, stash partial outputs under the report directory, and set `next_action=switch_focus` in galph_memory.md.
Findings Applied (Mandatory):
- DIFFBRAGG-001 — Plan avoids executing the broken DiffBragg forward path and focuses on documentation until a sanctioned patch is available.
- TESTING-003 — Fresh collect-only commands/log destinations ensure selector status stays truthful.
- PARITY-001 — ROI catalog + playbook steps retain deterministic ROI ordering required for first-divergence tracing.
- CONFIG-001 — Torch playbook explicitly references config_crosswalk mappings to prevent hydration regressions.
Doc Sync Plan (Mandatory):
- DB_AT_001 parity (`tests/dbex/test_db_at_001_parity.py`) — `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001 |& tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T075930Z/collect_db_at_001_parity.log`
- DB_AT_001 forward equivalence (`tests/dbex/test_forward_equivalence_complete.py`) — `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001 |& tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T075930Z/collect_db_at_001_forward.log`
- After collection, update docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md to cite the new 2025-10-29T075930Z artifact paths.
