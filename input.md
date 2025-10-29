Summary: Use the pinned simtbx environment (torch 2.4.1+cu121) to finish Phase A canonical capture and advance NANOBRAG-GOLDEN-001.
Mode: none
Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
Branch: integration
Mapped tests: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001; KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001
Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T030352Z/{golden_dataset/env_bootstrap.log,golden_dataset/blocking_summary.md,golden_dataset/legacy/dbex_diffbragg_gpu.h5,golden_dataset/legacy/diffbragg_forward_gpu.log,golden_dataset/torch/,collect_db_at_001_parity.log,collect_db_at_001_forward.log}
Mapped tests: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001; KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001
Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T030352Z/{golden_dataset/env_bootstrap.log,golden_dataset/blocking_summary.md,golden_dataset/legacy/dbex_diffbragg_gpu.h5,golden_dataset/legacy/diffbragg_forward_gpu.log,golden_dataset/torch/,collect_db_at_001_parity.log,collect_db_at_001_forward.log}
Do Now:
  1. NANOBRAG-GOLDEN-001::A3 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Use `nanobrag_torch.Simulator` to generate canonical bragg tensors for panel 0 (extendable to all panels) using the refGeom inputs, saving outputs under golden_dataset/torch/ and logging via run_log.log. tests: none — simulator capture.
  2. NANOBRAG-GOLDEN-001::B1 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Update manifest/metadata files to reference the new DiffBragg baseline (`dbex_diffbragg_gpu.h5`) and canonical torch outputs, including SHA256 checksums and provenance notes. tests: none — documentation/manifest update.
  3. NANOBRAG-GOLDEN-001::B2 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Extend pytest fixtures to validate the canonical tensors and regenerate DB_AT_001 collect-only evidence (parity + forward selectors) pointing at the new artifact paths. tests: KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001; KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001.
Priorities & Rationale:
- docs/spec-db-core.md:20 — Canonical tensors must respect `[panel, slow, fast]` ordering, so simulator outputs need to be validated before manifest work.
- docs/forward_equivalence.md:21 — DiffBragg baseline evidence is mandatory before comparing against the torch capture.
- docs/spec-db-conformance.md:23 — DB_AT_001 thresholds motivate restoring torch + DiffBragg parity before swapping golden data.
- docs/nanobrag_api.md:22 — DetectorConfig/Simulator requirements drive the nanobrag_torch install and forward capture.
- docs/pytorch_runtime_checklist.md:26 — Environment commands must honor `KMP_DUPLICATE_LIB_OK=TRUE`/`NANOBRAGG_DISABLE_COMPILE=1` guardrails to keep torch stable.
- docs/config_crosswalk.md:23 — Bridge mapping (beam center swap, mask polarity) has to survive the new simulator path, so capture work must reuse those helpers.
How-To Map:
- `source ~/miniconda3/bin/activate simtbx && python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"`
- `python plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T030352Z/scratch/canonical_panel0.py --panel 0 --out plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T030352Z/golden_dataset/torch |& tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T030352Z/golden_dataset/torch/run_log.log`
- `python tools/update_manifest.py --golden-dir plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T030352Z/golden_dataset --target tests/fixtures/golden_data/simple_cubic --log plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T030352Z/golden_dataset/manifest_update.log`
- `shasum -a 256 plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T030352Z/golden_dataset/legacy/dbex_diffbragg_gpu.h5 plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T030352Z/golden_dataset/torch/*.npy >> plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T030352Z/golden_dataset/manifest_checksums.txt`
- `KMP_DUPLICATE_LIB_OK=TRUE python -m pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001 | tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T030352Z/collect_db_at_001_parity.log`
- `KMP_DUPLICATE_LIB_OK=TRUE python -m pytest --collect-only -q tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001 | tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T030352Z/collect_db_at_001_forward.log`
Pitfalls To Avoid:
- Do not upgrade torch/torchvision—stay on 2.4.1+cu121 unless the plan explicitly changes it.
- Keep git working tree clean; stash cloned nanoBragg outside tracked paths or ensure it’s ignored before committing.
- Avoid overwriting fallback tensors until canonical outputs and manifests are validated and checksummed.
- Always activate the simtbx environment before running pip/pytest/torch commands to prevent dependency drift.
- Ensure `KMP_DUPLICATE_LIB_OK=TRUE` precedes every pytest invocation to avoid OpenMP crashes.
- Reuse bridge helpers for detector/beam masks; do not bypass mask polarity guards when generating canonical tensors.
- Capture SHA256 checksums immediately after generating new tensors and append them to manifest_checksums.txt.
- Treat external trees (`dials/`, `dxtbx/`, `cctbx_project/simtbx/`) as read-only while debugging.
If Blocked:
- Record the failing command, exit code, and stderr in the matching artifact file, update docs/fix_plan.md Attempts History with `Status: blocked`, note the block in galph_memory, and hand back to supervisor for rerouting.
Findings Applied (Mandatory):
- CONFORMANCE-001 — Keeps DB_AT_001 acceptance thresholds credible by refreshing DiffBragg evidence alongside the new torch path.
- CONFIG-001 — Ensures detector/beam/crystal mappings stay aligned while adapting bridge outputs to nanobrag_torch.
- DIAGNOSTICS-001 — Restores torch diagnostics readiness so `/torch_diagnostics` parity artifacts can be emitted once the simulator runs.
- PARITY-001 — Maintains first-divergence workflow readiness by logging canonical capture attempts under parity artifacts.
- TESTING-003 — Collect-only refresh keeps Active selectors documented with up-to-date evidence.
Doc Sync Plan (Mandatory):
- Update docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md with refreshed artifact paths after canonical tensors land; gather evidence via `KMP_DUPLICATE_LIB_OK=TRUE python -m pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001 > plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T030352Z/collect_db_at_001_parity.log` and `KMP_DUPLICATE_LIB_OK=TRUE python -m pytest --collect-only -q tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001 > plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T030352Z/collect_db_at_001_forward.log` for citation.
