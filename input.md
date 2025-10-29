Summary: Unblock NANOBRAG-GOLDEN-001 by documenting the ready simtbx env, installing nanobrag_torch, and recapturing the DiffBragg baseline evidence.
Mode: Parity
Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
Branch: integration
Mapped tests: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001
Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T024902Z/{golden_dataset/env_bootstrap.log,golden_dataset/legacy/diffbragg_forward.log,collect_db_at_001.log}
Do Now:
  1. NANOBRAG-GOLDEN-001 A1 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Capture evidence that the existing simtbx conda env is active (`which python`, `python -c "import simtbx"`), then install/verify `nanobrag_torch` from `https://github.com/hoidn/nanoBragg` (per plans/nanobrag_integration_plan.md:23-54) and log results in env_bootstrap.log. tests: none — dependency validation.
  2. NANOBRAG-GOLDEN-001 A2 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — With dependencies resolved, run `python -m dbex.refine_one --backend diffbragg ...` to export the legacy bragg tensor and configs into golden_dataset/legacy/, logging stdout/stderr to diffbragg_forward.log to confirm the CUDA runtime mismatch is resolved. tests: none — baseline capture.
  3. NANOBRAG-GOLDEN-001 C3 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Re-collect DB_AT_001 evidence via `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001` and store the log at plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T024902Z/collect_db_at_001.log to keep selector docs synchronized (doc edits deferred until canonical tensors land). tests: KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001.
Priorities & Rationale:
  - setup_env.sh:40-108 — Documenting the already-prepared simtbx env ensures future tensor runs inherit consistent PATH/CONDA settings.
  - plans/nanobrag_integration_plan.md:23-54 — Implementation roadmap requires nanobrag_torch install prior to bridge/tensor generation.
  - docs/spec-db-conformance.md:23-26 — DB_AT_001 thresholds necessitate a trustworthy DiffBragg baseline before swapping golden data.
  - docs/spec-db-core.md:20-41 — `[panel, slow, fast]` contracts demand validated simulator outputs, driving the DiffBragg rerun.
  - docs/TESTING_GUIDE.md:74-85 — Selector remains Active; collect-only evidence must stay current alongside environment changes.
How-To Map:
  - Record env status: `which python | tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T024902Z/golden_dataset/env_bootstrap.log` and `python -c "import simtbx; import torch; print(torch.__version__)" | tee -a .../env_bootstrap.log`.
  - Install nanobrag_torch (if missing): `git clone https://github.com/hoidn/nanoBragg.git nanoBragg`; `cd nanoBragg`; `pip install -e .`; re-run `python -c "import nanobrag_torch"` and append output to env_bootstrap.log.
  - Capture DiffBragg baseline: `python -m dbex.refine_one --backend diffbragg -e refGeom.expt -r refGeom.refl -i 0 -o plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T024902Z/golden_dataset/legacy/dbex_diffbragg.h5 -m 747_mask.pkl -z scaled.mtz |& tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T024902Z/golden_dataset/legacy/diffbragg_forward.log`.
  - Re-run collect-only: `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001 | tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T024902Z/collect_db_at_001.log`.
Pitfalls To Avoid:
  - Do not rebuild the environment; simply verify and document the existing simtbx conda setup.
  - Keep all bootstrap logs under the 2025-10-29T024902Z report directory; don’t scatter artifacts elsewhere.
  - Ensure `KMP_DUPLICATE_LIB_OK=TRUE` is set before any pytest or torch imports to avoid OpenMP crashes.
  - Capture and append full tracebacks for any missing package or CUDA errors; don’t silently retry with system python.
- Skip overwriting fallback tensors until canonical outputs exist; treat legacy data as read-only for now.
- Confirm GPU toolkit compatibility (`nvidia-smi`, libcudart) before assuming DiffBragg errors are fixed.
- Avoid mixing `pip` from the base OS with the simtbx environment to prevent dependency drift.
If Blocked:
- Record the failure (command, stderr) in env_bootstrap.log or diffbragg_forward.log, update docs/fix_plan.md Attempts History with `Status: blocked` rationale, add the block to galph_memory, and hand back to supervisor once dependency acquisition is confirmed externally.
Findings Applied (Mandatory):
- CONFORMANCE-001 — Keeps DB_AT_001 selector thresholds aligned by revalidating environment and test evidence before dataset changes.
- CONFIG-001 — Honors the dxtbx→nanobrag mapping requirements by ensuring bridge dependencies load inside the simtbx env.
- DIAGNOSTICS-001 — Restoring the torch backend and diagnostics stack enables required parity traces once tests rerun.
- PARITY-001 — DiffBragg baseline capture plus collect-only evidence preserves first-divergence readiness for upcoming parity runs.
- TESTING-003 — Collect-only log refresh maintains selector documentation fidelity alongside environment restoration.
Doc Sync Plan (Mandatory):
- DB_AT_001 parity harness — run `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001` after the environment is restored; store the log at plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T024902Z/collect_db_at_001.log and reference it when updating docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md once canonical tensors are generated.
