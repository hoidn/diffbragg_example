Summary: Rebuild the simforge torch stack (2.4.1+cu121) and capture a clean DiffBragg baseline so NANOBRAG-GOLDEN-001 can leave fallback data.
Mode: Parity
Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
Branch: integration
Mapped tests: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001; KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001
Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T040641Z/{golden_dataset/env_reset.log,golden_dataset/nanobrag_install.log,golden_dataset/legacy/diffbragg_forward_gpu.log,golden_dataset/legacy/diffbragg_forward_cpu.log,golden_dataset/legacy/bragg_diffbragg.npy,collect_db_at_001_parity.log,collect_db_at_001_forward.log,blocking_notes.md}
Do Now:
  1. NANOBRAG-GOLDEN-001::A1 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Recreate simforge/envs/simtbx per README Step 1, install torch==2.4.1+cu121 & torchvision==0.19.1+cu121, reinstall nanobrag_torch editable, and log torch.utils.collect_env to env_reset.log. tests: none — environment reset.
  2. NANOBRAG-GOLDEN-001::A2 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Run scratch/capture_diffbragg.py with DIFFBRAGG_USE_CUDA=1 inside the restored env, saving bragg_diffbragg.npy and teeing diffbragg_forward_gpu.log; if CUDA still asserts at diffBraggCUDA.cu:708, rerun a CPU fallback (devId=-1) via an inline script and archive diffbragg_forward_cpu.log plus blocking_notes.md. tests: none — DiffBragg baseline capture.
  3. NANOBRAG-GOLDEN-001::A2 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Re-collect DB_AT_001 selectors after the baseline export and store fresh --collect-only logs under the 2025-10-29T040641Z report directory to keep TESTING-003 satisfied. tests: KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001; KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001.
Priorities & Rationale:
- docs/spec-db-core.md:19-41 — Canonical tensors must honor `[panel, slow, fast]` ordering, so the DiffBragg baseline must exist before replacing fallback fixtures.
- docs/spec-db-conformance.md:10-26 — DB_AT_001 acceptance requires a trustworthy DiffBragg forward tensor and artifacts before enforcing thresholds.
- docs/forward_equivalence.md:21-55 — Forward-equivalence workflow mandates capturing DiffBragg and torch outputs with metrics and logs in the same report set.
- docs/pytorch_runtime_checklist.md:39-48 — Environment guardrails pin torch/torchvision and require `KMP_DUPLICATE_LIB_OK=TRUE` prior to parity selectors.
- plans/nanobrag_integration_plan.md:23-28 — Phase 0 directs editable nanobrag_torch install plus DiffBragg baselines ahead of canonical capture.
- README.md:76-104 — README Step 1 defines the simforge/envs/simtbx layout that setup_env.sh expects; rebuilding it restores reproducible tooling.
How-To Map:
- `wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh -O miniforge.sh && bash miniforge.sh -b -u -p "$PWD/simforge"`
- `./simforge/bin/mamba create -n simtbx -c conda-forge cctbx-base libboost-devel libboost-python-devel dxtbx python=3.9 cmake -y`
- `source setup_env.sh && pip install torch==2.4.1+cu121 torchvision==0.19.1+cu121 --extra-index-url https://download.pytorch.org/whl/cu121`
- `pip install -e .`
- `pip install -e git+https://github.com/hoidn/nanoBragg.git#egg=nanobrag_torch |& tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T040641Z/golden_dataset/nanobrag_install.log`
- `python -m torch.utils.collect_env > plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T040641Z/golden_dataset/env_reset.log`
- `DIFFBRAGG_USE_CUDA=1 python plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T030352Z/scratch/capture_diffbragg.py |& tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T040641Z/golden_dataset/legacy/diffbragg_forward_gpu.log`
- `python - <<'PY' |& tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T040641Z/golden_dataset/legacy/diffbragg_forward_cpu.log`
from dbex.data_load import DataLoad
from dbex.run_diffbragg import run_diffbragg
DL = DataLoad(type('Args', (), {
    'exptName': 'refGeom.expt',
    'reflName': 'refGeom.refl',
    'mtzFile': 'scaled.mtz',
    'maskFile': '747_mask.pkl',
    'exptIdx': 0,
    'mtzCol': 'F,SIGF',
})())
import numpy as np
Bragg = run_diffbragg(DL, devId=-1)
np.save('plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T040641Z/golden_dataset/legacy/bragg_diffbragg.npy', Bragg)
PY
- `KMP_DUPLICATE_LIB_OK=TRUE python -m pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001 | tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T040641Z/collect_db_at_001_parity.log`
- `KMP_DUPLICATE_LIB_OK=TRUE python -m pytest --collect-only -q tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001 | tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T040641Z/collect_db_at_001_forward.log`
Pitfalls To Avoid:
- Do not upgrade torch/torchvision beyond 2.4.1+cu121/0.19.1+cu121 unless a new plan authorizes it.
- Keep cloned upstream mirrors (`easyBragg`, `nanoBragg`) outside tracked paths or ensure .gitignore covers them before building.
- Confirm setup_env.sh succeeds (simforge present) before running pip, DiffBragg, or pytest; otherwise commands hit system python.
- Always export KMP_DUPLICATE_LIB_OK=TRUE (and DIFFBRAGG_USE_CUDA=1 for GPU runs) to avoid runtime crashes or silent CPU fallback.
- Capture GPU and CPU logs even on failure so blockers can be documented without rerunning heavy jobs.
- Preserve fallback tensors until canonical artifacts, manifests, and checksums are validated and referenced in docs.
- Treat dials/, dxtbx/, and cctbx_project/simtbx/ as read-only unless a plan explicitly targets them.
- Record SHA256 checksums immediately after generating new tensors to prevent provenance gaps.
If Blocked:
- Append the failing command, exit code, and stderr to blocking_notes.md, update docs/fix_plan.md Attempts History with `Status: blocked`, `Metrics: pending`, and `Artifacts: <report-path>`, log the block plus return condition in galph_memory, then pause for supervisor direction.
Findings Applied (Mandatory):
- CONFORMANCE-001 — Re-collect DB_AT_001 logs after the baseline run to keep acceptance thresholds tied to current artifacts.
- CONFIG-001 — Restoring the vetted bridge environment keeps detector/beam/crystal mapping spec-compliant while producing the DiffBragg baseline.
- DIAGNOSTICS-001 — Capture DiffBragg execution logs so parity diagnostics remain traceable under plans/active/.../golden_dataset/.
- PARITY-001 — Archive failure traces (GPU assert, CPU fallback) to preserve first-divergence analysis inputs if DiffBragg still misbehaves.
- TESTING-003 — Refresh --collect-only evidence for Active selectors so docs and artifacts stay aligned post-env rebuild.
Doc Sync Plan (Mandatory):
- After logs land, update docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md to cite `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T040641Z/collect_db_at_001_parity.log` and `.../collect_db_at_001_forward.log`; gather the evidence via `KMP_DUPLICATE_LIB_OK=TRUE python -m pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001 > .../collect_db_at_001_parity.log` and `KMP_DUPLICATE_LIB_OK=TRUE python -m pytest --collect-only -q tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001 > .../collect_db_at_001_forward.log` for citation.
