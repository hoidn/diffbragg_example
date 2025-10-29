Summary: Restore torch and nanobrag_torch dependencies so NANOBRAG-GOLDEN-001 Phase A capture can proceed and stage fresh evidence for canonical dataset generation.
Mode: none
Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
Branch: integration
Mapped tests: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001; KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001
Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T030352Z/{golden_dataset/env_bootstrap.log,golden_dataset/blocking_summary.md,golden_dataset/legacy/diffbragg_forward.log,golden_dataset/torch/,collect_db_at_001_parity.log,collect_db_at_001_forward.log}
Do Now:
  1. NANOBRAG-GOLDEN-001::A1 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Reproduce the libc10_cuda failure inside the simtbx env (`which python`, `python -m torch.utils.collect_env`, short torch smoke import) and append driver/library status plus any tracebacks to golden_dataset/env_bootstrap.log and golden_dataset/blocking_summary.md. tests: none — environment diagnostics.
  2. NANOBRAG-GOLDEN-001::A1 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Clone/install nanobrag_torch (`git clone https://github.com/pixel-modelers/nanoBragg2.git`, `pip install -e ./nanoBragg2`) and confirm `python -c "import nanobrag_torch; print(nanobrag_torch.__version__)"`, logging results to env_bootstrap.log. tests: none — dependency install.
  3. NANOBRAG-GOLDEN-001::A2 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Once torch imports cleanly, rerun `python -m dbex.refine_one --backend diffbragg ... --noop` to export the legacy bragg tensor into golden_dataset/legacy/, capturing stdout/stderr in diffbragg_forward.log and persisting `bragg_diffbragg.npy`. tests: none — DiffBragg baseline export.
  4. NANOBRAG-GOLDEN-001::A3 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Copy `scripts/generate_simple_cubic_golden.py` into the loop scratch dir and refactor it to call nanobrag_torch.Simulator (converting bridge stubs to real dataclasses) for panel 0, writing `bragg_panel0.npy` + metadata under golden_dataset/torch/ and teeing command output to run_log.log. tests: none — nanoBragg2 forward capture attempt.
Priorities & Rationale:
- docs/spec-db-core.md:20 — Canonical tensors must respect `[panel, slow, fast]` ordering, so simulator outputs need to be validated before manifest work.
- docs/forward_equivalence.md:21 — DiffBragg baseline evidence is mandatory before comparing against the torch capture.
- docs/spec-db-conformance.md:23 — DB_AT_001 thresholds motivate restoring torch + DiffBragg parity before swapping golden data.
- docs/nanobrag_api.md:22 — DetectorConfig/Simulator requirements drive the nanobrag_torch install and forward capture.
- docs/pytorch_runtime_checklist.md:26 — Environment commands must honor `KMP_DUPLICATE_LIB_OK=TRUE`/`NANOBRAGG_DISABLE_COMPILE=1` guardrails to keep torch stable.
- docs/config_crosswalk.md:23 — Bridge mapping (beam center swap, mask polarity) has to survive the new simulator path, so capture work must reuse those helpers.
How-To Map:
- `source ~/miniconda3/bin/activate simtbx && which python | tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T030352Z/golden_dataset/env_bootstrap.log`
- `source ~/miniconda3/bin/activate simtbx && python -m torch.utils.collect_env | tee -a plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T030352Z/golden_dataset/env_bootstrap.log`
- `source ~/miniconda3/bin/activate simtbx && python - <<'PY'
import torch
print('torch_version', torch.__version__)
print('cuda_available', torch.cuda.is_available())
PY >> plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T030352Z/golden_dataset/env_bootstrap.log`
- `source ~/miniconda3/bin/activate simtbx && git clone https://github.com/pixel-modelers/nanoBragg2.git && pip install -e nanoBragg2`
- `source ~/miniconda3/bin/activate simtbx && python -c "import nanobrag_torch; print('nanobrag_torch', nanobrag_torch.__version__)" >> plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T030352Z/golden_dataset/env_bootstrap.log`
- `source ~/miniconda3/bin/activate simtbx && python -m dbex.refine_one --backend diffbragg -e refGeom.expt -r refGeom.refl -i 0 -o plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T030352Z/golden_dataset/legacy/dbex_diffbragg.h5 -m 747_mask.pkl -z scaled.mtz --noop |& tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T030352Z/golden_dataset/legacy/diffbragg_forward.log`
- `mkdir -p plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T030352Z/scratch && cp scripts/generate_simple_cubic_golden.py plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T030352Z/scratch/canonical_panel0.py`
- `source ~/miniconda3/bin/activate simtbx && KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T030352Z/scratch/canonical_panel0.py --panel 0 --out plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T030352Z/golden_dataset/torch |& tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T030352Z/golden_dataset/torch/run_log.log`
- `KMP_DUPLICATE_LIB_OK=TRUE python -m pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001 | tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T030352Z/collect_db_at_001_parity.log`
- `KMP_DUPLICATE_LIB_OK=TRUE python -m pytest --collect-only -q tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001 | tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T030352Z/collect_db_at_001_forward.log`
Pitfalls To Avoid:
- Keep git working tree clean; stash cloned nanoBragg2 outside tracked paths or ensure it’s ignored before committing.
- Do not overwrite fallback tensors until the canonical dataset is fully captured and validated.
- Capture full CUDA traceback details in blocking_summary.md if the libc10_cuda error persists after reinstalling torch.
- Always activate the simtbx environment before running pip/pytest/torch commands to prevent dependency drift.
- Ensure `KMP_DUPLICATE_LIB_OK=TRUE` precedes every pytest invocation to avoid OpenMP crashes.
- Verify GPU readiness with `nvidia-smi` prior to DiffBragg reruns so CUDA driver issues are obvious.
- Reuse bridge helpers for detector/beam masks; do not bypass mask polarity guards when generating canonical tensors.
- Treat external trees (`dials/`, `dxtbx/`, `cctbx_project/simtbx/`) as read-only while debugging.
- Document every failure path in env_bootstrap.log or run_log.log before escalating a block.
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
