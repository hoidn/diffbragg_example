**Summary**: Promote the regenerated nanoBragg canonical tensors into the fixtures and reconcile the parity loader so DB_AT_001 runs against real bool-masked data.

**Mode**: Parity

**Focus**: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset

**Branch**: integration

**Mapped tests**: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001

**Artifacts**: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T104500Z/

**Do Now (hard validity contract)**
- Focus Item: NANOBRAG-GOLDEN-001 (A2, A3, B1, B2)
- Implement: tests/fixtures/parity_loader.py::load_golden_data — align canonical filenames, coerce loss_mask to bool, and log manifest provenance so fixtures stay spec-compliant.
- Prep: PYTHONPATH=../nanoBragg/src:$PYTHONPATH KMP_DUPLICATE_LIB_OK=TRUE python scripts/generate_simple_cubic_golden.py --canonical-out plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T104500Z/golden_dataset --hkldebug plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T104500Z/torch_hkl_debug.json (covers A2/A3) and copy tensors into tests/fixtures/golden_data/simple_cubic/ with sha256 recompute (B1).
- Validate: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001
- Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T104500Z/

**Priorities & Rationale**
- docs/spec-db-core.md:20-44 — Fixtures must expose `[panel, slow, fast]` tensors with square-pixel metadata; regenerating and copying canonical arrays enforces the normative contract.
- docs/spec-db-conformance.md:23-26 — DB_AT_001 requires canonical baselines with real metrics before parity thresholds can be trusted; updating fixture data plus manifest is prerequisite to resume acceptance evidence.
- docs/forward_equivalence.md:21-53 — Regenerating paired DiffBragg/torch stacks and parity metrics satisfies Phase A before we enforce thresholds.
- docs/TESTING_GUIDE.md:63-88 — Selector `KMP_DUPLICATE_LIB_OK=TRUE pytest -v ... -k DB_AT_001` is marked Active; the loop keeps it passing with new tensors and manifest checks.
- docs/config_crosswalk.md:15-72 — Copying configs/metadata from capture ensures detector/beam/crystal mapping remains faithful when the loader casts bool masks.

**How-To Map**
1. `mkdir -p plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T104500Z/golden_dataset`
2. `PYTHONPATH=../nanoBragg/src:$PYTHONPATH KMP_DUPLICATE_LIB_OK=TRUE python scripts/generate_simple_cubic_golden.py --canonical-out plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T104500Z/golden_dataset --hkldebug plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T104500Z/torch_hkl_debug.json | tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T104500Z/canonical_capture.log`
3. `python - <<'PY'
from pathlib import Path
import numpy as np
root = Path('plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T104500Z/golden_dataset')
fixture = Path('tests/fixtures/golden_data/simple_cubic')
fixture.mkdir(parents=True, exist_ok=True)
legacy = root/'legacy'
torch_dir = root/'torch'
np.save(fixture/'bragg_diffbragg.npy', np.load(legacy/'bragg_diffbragg.npy').astype('float32'))
torch_stack = np.load(torch_dir/'bragg_torch.npy')
np.save(fixture/'bragg_panel_0.npy', torch_stack[0].astype('float32'))
np.save(fixture/'target_panel_0.npy', np.load(torch_dir/'target_panel_0.npy').astype('float32'))
loss_mask = np.load(torch_dir/'loss_mask_panel_0.npy').astype(bool)
np.save(fixture/'loss_mask_panel_0.npy', loss_mask)
PY`
4. `python - <<'PY'
import json, hashlib
from pathlib import Path
import numpy as np
fixture = Path('tests/fixtures/golden_data/simple_cubic')
files = {}
for name in ['bragg_diffbragg.npy','bragg_panel_0.npy','target_panel_0.npy','loss_mask_panel_0.npy']:
    path = fixture/name
    arr = np.load(path)
    files[name.split('.')[0]] = {
        'dtype': 'bool' if 'loss_mask' in name else 'float32',
        'filename': name,
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'shape': list(arr.shape)
    }
manifest = {
    'dataset_name': 'DB_AT_001_canonical',
    'files': {
        'bragg_diffbragg': files['bragg_diffbragg'],
        'bragg': files['bragg_panel_0'],
        'target': files['target_panel_0'],
        'loss_mask': files['loss_mask_panel_0']
    },
    'generation_date': __import__('datetime').datetime.utcnow().isoformat()+'Z',
    'provenance': 'Canonical nanoBragg capture — see plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T104500Z/',
    'spec_reference': 'docs/spec-db-core.md:20-41',
    'version': '1.2.0'
}
fixture.joinpath('manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
PY`
5. `python - <<'PY'
import json
from pathlib import Path
manifest = json.loads(Path('tests/fixtures/golden_data/simple_cubic/manifest.json').read_text())
meta_path = Path('tests/fixtures/golden_data/simple_cubic/metadata.json')
meta = json.loads(meta_path.read_text())
meta.update({
    'provenance': 'Canonical DiffBragg + nanobrag_torch capture (plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T104500Z/)',
    'generation_date': manifest['generation_date'],
    'notes': [
        'DiffBragg baseline captured with scripts/generate_simple_cubic_golden.py',
        'Torch baseline matches HKL-ORIENT-001 fix; loss_mask stored as bool',
        'Metrics logged under plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T104500Z/metrics.json'
    ]
})
meta_path.write_text(json.dumps(meta, indent=2)+'\n')
PY`
6. `apply_patch <<'PATCH'
*** Update File: .gitignore
@@
-*.npy
+*.npy
+!tests/fixtures/golden_data/simple_cubic/*.npy
*** End Patch
PATCH`
7. `pytest --version` (sanity) then `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001 | tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T104500Z/pytest_db_at_001.log`
8. Capture updated manifest/metadata into the artifact README and record checksums in docs/fix_plan.md Attempts History.

**Pitfalls To Avoid**
- Loss mask must be saved/manifested as bool; do not regress to uint8 (see tests/fixtures/parity_loader.py expectations).
- Preserve `[panel, slow, fast]` ordering when slicing `bragg_torch.npy`; never squeeze dimensions out of order.
- Keep `.gitignore` exception narrow to the simple_cubic fixtures to avoid flooding git status with other `.npy` artifacts.
- Do not overwrite prior artifact timestamps; create the new 2025-10-29T104500Z directory before capture.
- Ensure the generator runs with `PYTHONPATH` pointing at ../nanoBragg/src so imports resolve without environment mutations.
- Run parity pytest only after manifest/metadata updates; otherwise checksum assertions will fail and mask dtype asserts won't run.
- If CUDA or nanobrag_torch init fails, stop immediately and log the import/driver error (Environment Freeze).
- Verify sha256 entries after copy; stale hashes will cause manifest validation failures.
- Stage `.gitignore` and fixture .npy files together to keep the repo consistent.
- Keep the parity loader changes minimal—no reformatting or unrelated refactors so the diff stays focused.

**If Blocked**
- If generator errors (ImportError, CUDA driver mismatch, etc.), halt, record the stderr in plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T104500Z/canonical_capture.log, mark NANOBRAG-GOLDEN-001 as `blocked` in docs/fix_plan.md with the error signature, and append a `blocked` entry to docs/findings.md attempts history before switching focus.

**Findings Applied (Mandatory)**
- HKL-ORIENT-001 — Reusing the corrected incident-beam orientation ensures the torch tensors populate non-zero HKL ranges.
- CONFIG-001 — Copying configs/metadata preserves the documented dxtbx→torch mapping contracts during fixture refresh.
- CONFORMANCE-001 — Refreshing fixtures enables DB_AT_001 parity acceptance to run with canonical data and correct thresholds.
- TESTING-003 — Selector remains Active; plan records fresh collect evidence and ensures manifest checksums stay valid.
- GEOMETRY-001 — Validates square pixel pitch and `[panel, slow, fast]` ordering when rehydrating fixtures.
