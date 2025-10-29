**Summary**: Remove double-scaling in canonical capture so DB_AT_001 parity can use real tensors and refresh fixtures in-repo.
**Mode**: Parity
**Focus**: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
**Branch**: integration
**Mapped tests**: tests/dbex/test_db_at_001_parity.py -k DB_AT_001
**Artifacts**: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T212500Z/{golden_dataset/, parity_harness/, canonical_capture.log, pytest_db_at_001.log}

**Do Now (hard validity contract)**
- Implement: scripts/generate_simple_cubic_golden.py::build_structure_factor_grid (checklists A2/A3; drop sqrt(scale_override) multiplier, ensure canonical `.npy` emission & manifest refresh feeding B1/B2).
- Checklist: A2, A3, B1, B2 (plans/active/NANOBRAG-GOLDEN-001/implementation.md).
- Validate: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001
- Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T212500Z/{golden_dataset/, parity_harness/, canonical_capture.log, pytest_db_at_001.log}

**Priorities & Rationale**
- docs/spec-db-conformance.md:23-26 — DB_AT_001 mandates ≥0.2 correlation/≥90% localization, so we must realign torch intensity before rerunning the selector.
- docs/forward_equivalence.md:60-82 — Canonical artifacts (bragg_torch.npy, metrics.json) belong under a dated report directory; regenerating the dataset keeps evidence spec-compliant.
- docs/config_crosswalk.md:24-44 — Crosswalk forbids ad-hoc scaling beyond documented parameters; removing the sqrt(scale_override) path respects the mapping.
- docs/TESTING_GUIDE.md:64-87 — DB_AT_001 parity selector is Active; rerunning with canonical tensors maintains registry truth and captures fresh logs.
- docs/spec-db-core.md:20-41 — Golden tensors must persist `[panel, slow, fast]` float32/boolean payloads; copying the regenerated `.npy` files into fixtures satisfies the contract.

**How-To Map**
- export KMP_DUPLICATE_LIB_OK=TRUE
- export PYTHONPATH=../nanoBragg/src:$PYTHONPATH
- python scripts/generate_simple_cubic_golden.py --canonical-out plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T212500Z/golden_dataset --hkldebug plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T212500Z/torch_hkl_debug.json --emit-manifest --fixtures tests/fixtures/golden_data/simple_cubic | tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T212500Z/canonical_capture.log
- ls tests/fixtures/golden_data/simple_cubic/*.npy > plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T212500Z/fixture_files.log
- KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001 | tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T212500Z/pytest_db_at_001.log

**Pitfalls To Avoid**
- Environment freeze: no pip/conda installs or rebuilds beyond documented source patches.
- Do not reintroduce sqrt(scale_override) scaling; DiffBragg already applies the spot scale (SCALE-001).
- Ensure `--fixtures` uses this repo path; avoid writing to stale clones (manifest generator records absolute paths).
- Keep PYTHONPATH targeting ../nanoBragg/src so the local nanobrag_torch sources resolve.
- Capture artifacts in the new timestamp directory; avoid overwriting 2025-10-29T181603Z evidence.
- Confirm `.npy` files are float32 (bragg, target) and bool (loss_mask) before committing; reject unintended dtype changes.
- Monitor canonical_capture.log for HKL stats; unexpected 0% hit rate indicates HKL-ORIENT-001 regression.
- Abort immediately if CUDA device selection fails; log the error instead of downgrading to CPU silently.

**If Blocked**
- If nanobrag_torch import/Simulator crashes or canonical capture fails, stop, log stderr to plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T212500Z/error.log, update docs/fix_plan.md Attempts History, mark focus `blocked`, and await guidance.

**Findings Applied (Mandatory)**
- CONFIG-001 — Enforce documented detector/beam/crystal mappings while adjusting scaling logic.
- HKL-ORIENT-001 — Keep incident beam negation intact when regenerating HKL grids.
- PARITY-001 — Ensure regenerated run preserves first-divergence artifacts and deterministic scan order.
- CONFORMANCE-001 — Use mandated env flag and selector to validate DB_AT_001 parity.
- SCALE-001 — Remove duplicate sqrt(scale_override) application so torch intensities match DiffBragg scale.
