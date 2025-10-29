Summary: Unblock NANOBRAG-GOLDEN-001 by restoring the simforge/simtbx environment, acquiring nanobrag_torch, and recapturing the DiffBragg baseline evidence.
Mode: Parity
Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
Branch: integration
Mapped tests: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001
Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T024902Z/{golden_dataset/env_bootstrap.log,golden_dataset/legacy/diffbragg_forward.log,collect_db_at_001.log}
Do Now:
  1. NANOBRAG-GOLDEN-001 A1 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Bootstrap or reactivate the simforge/simtbx environment per README.md:50-140, then source setup_env.sh to capture `dbex_status` output and python import checks in plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T024902Z/golden_dataset/env_bootstrap.log. tests: none — environment provisioning.
  2. NANOBRAG-GOLDEN-001 A1 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Install or vendor nanobrag_torch into the simtbx environment (clone/build nanoBragg2 per plans/nanobrag_integration_plan.md:23-54 or use an available wheel), verify `python -c "import nanobrag_torch, torch"` succeeds, and append version/device details to env_bootstrap.log. tests: none — dependency acquisition.
  3. NANOBRAG-GOLDEN-001 A2 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — With the environment active, run `python -m dbex.refine_one --backend diffbragg ...` to export the legacy bragg tensor and configs into golden_dataset/legacy/, logging stdout/stderr to diffbragg_forward.log to confirm the CUDA runtime mismatch is resolved. tests: none — baseline capture.
  4. NANOBRAG-GOLDEN-001 C3 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Re-collect DB_AT_001 evidence via `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001` and store the log at plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T024902Z/collect_db_at_001.log to keep selector docs synchronized (doc edits deferred until canonical tensors land). tests: KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001.
Priorities & Rationale:
- README.md:50-140 — Step 1 describes the required simforge/simtbx bootstrap that A1 must complete before canonical tensor capture.
- setup_env.sh:40-108 — Activation script expects the simforge env; capturing dbex_status output documents readiness and failures.
- plans/nanobrag_integration_plan.md:23-54 — Implementation roadmap requires nanobrag_torch install prior to bridge/tensor generation.
- docs/spec-db-conformance.md:23-26 — DB_AT_001 thresholds necessitate a trustworthy DiffBragg baseline before swapping golden data.
- docs/spec-db-core.md:20-41 — `[panel, slow, fast]` contracts demand validated simulator outputs, driving the DiffBragg rerun.
- docs/TESTING_GUIDE.md:74-85 — Selector remains Active; collect-only evidence must stay current alongside environment changes.
How-To Map:
- Detect platform and install Miniforge: `wget https://github.com/conda-forge/miniforge/releases/latest/download/$INSTALLER; bash $INSTALLER -b -u -p "$PWD/simforge"`.
- Create simtbx env: `./simforge/bin/mamba create -n simtbx -c conda-forge cctbx-base libboost-devel libboost-python-devel dxtbx python=3.9 cmake -y`.
- Build easyBragg + simtbx: `git clone --recurse-submodules https://github.com/pixel-modelers/easyBragg.git; cd easyBragg; export PATH=$PWD/../simforge/envs/simtbx/bin:$PATH; cmake -B build_ext -DCMAKE_POLICY_VERSION_MINIMUM=3.5 .; make -C build_ext -j4 install; python -m build; pip install dist/simtbx-0.1.tar.gz`.
- Activate environment: `source ./setup_env.sh; dbex_status | tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T024902Z/golden_dataset/env_bootstrap.log`.
- Install nanobrag_torch: `git clone https://github.com/pixel-modelers/nanoBragg2.git; cd nanoBragg2; pip install -e .`; verify with `python -c "import nanobrag_torch, torch; print(torch.__version__)" | tee -a .../env_bootstrap.log`.
- Capture DiffBragg baseline: `python -m dbex.refine_one --backend diffbragg -e refGeom.expt -r refGeom.refl -i 0 -o plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T024902Z/golden_dataset/legacy/dbex_diffbragg.h5 -m 747_mask.pkl -z scaled.mtz |& tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T024902Z/golden_dataset/legacy/diffbragg_forward.log`.
- Re-run collect-only: `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001 | tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T024902Z/collect_db_at_001.log`.
Pitfalls To Avoid:
- Do not execute `setup_env.sh` with `bash`; it must be sourced to export PATH/CONDA_PREFIX.
- Avoid running python commands before the simforge path precedes system python (`which python` should point into simforge/envs/simtbx/bin).
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
