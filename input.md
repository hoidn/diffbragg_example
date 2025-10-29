Summary: Frame an Environment Freeze–compliant recovery plan for NANOBRAG-GOLDEN-001 by diagnosing the diffBragg CUDA free() failure and staging a CPU fallback capture for the canonical dataset.
Mode: Docs
Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
Branch: integration
Mapped tests: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001; KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001
Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T055449Z/{planning_notes.md}
Do Now:
  1. NANOBRAG-GOLDEN-001::A2 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Capture annotated snippet of ../easyBragg/simtbx_project/simtbx/diffBragg/src/diffBraggCUDA.cu around line 708 and document pointer lifetime hypotheses in planning_notes.md. tests: none — analysis only.
  2. NANOBRAG-GOLDEN-001::A2 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Run setup_env.sh under Environment Freeze to log the missing simforge bootstrap (no installs) and archive stdout/stderr for ledger evidence. tests: none — diagnostics only.
  3. NANOBRAG-GOLDEN-001::A2 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Attempt a CPU (`devId=-1`) DiffBragg export via inline Python using existing DataLoad harness, teeing output to plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T055449Z/golden_dataset/legacy/diffbragg_cpu_attempt.log; record success/failure and resulting artifacts. tests: none — forward-model capture.
Priorities & Rationale:
- docs/spec-db-core.md:20-41 — Canonical tensors must match `[panel, slow, fast]` contracts, so we need a trustworthy DiffBragg baseline before swapping the fallback dataset.
- docs/spec-db-conformance.md:23-26 — DB_AT_001 acceptance criteria hinge on having baseline DiffBragg metrics; documenting the blocker keeps conformance work auditable.
- docs/forward_equivalence.md:21-55 — Phase 1 mandates paired DiffBragg/torch artifacts with metrics, guiding the CPU fallback capture plan.
- docs/nanobrag_api.md:21-83 — Simulator inputs expect consistent detector/beam/crystal configs; baseline analysis must preserve these mappings when exporting tensors.
- docs/findings.md#CONFIG-001 — Prior pitfall notes enforce detector/beam/crystal normalization, informing the hypothesis review.
How-To Map:
- `nl -ba ../easyBragg/simtbx_project/simtbx/diffBragg/src/diffBraggCUDA.cu | sed -n '680,725p' > plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T055449Z/diffBraggCUDA_free_segment.log`
- `source setup_env.sh |& tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T055449Z/env_status.log`
- `mkdir -p plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T055449Z/golden_dataset/legacy && source setup_env.sh && python - <<'PY'
from dbex.data_load import DataLoad
from dbex.run_diffbragg import run_diffbragg
import numpy as np
class Args:
    exptName = "refGeom.expt"
    reflName = "refGeom.refl"
    mtzFile = "scaled.mtz"
    maskFile = "747_mask.pkl"
    exptIdx = 0
    mtzCol = "F,SIGF"
DL = DataLoad(Args())
Bragg = run_diffbragg(DL, devId=-1)
np.save("plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T055449Z/golden_dataset/legacy/bragg_diffbragg_cpu.npy", Bragg)
PY |& tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T055449Z/golden_dataset/legacy/diffbragg_cpu_attempt.log`
Pitfalls To Avoid:
- Do not install or upgrade packages; Environment Freeze forbids torch/conda changes.
- Avoid editing capture_diffbragg.py until hypotheses confirm required adjustments.
- Keep new artifacts under the 2025-10-29T055449Z report tree to preserve traceability.
- Preserve the existing fallback tensors until canonical replacements and manifests are validated.
- Guard against stale environment variables; always log setup_env.sh output before running capture scripts.
- Ensure CPU fallback run does not overwrite the prior GPU HDF5 artifacts.
- Capture failures verbatim instead of summarizing to retain diagnostics for future loops.
- Maintain `[panel, slow, fast]` ordering when saving any tensor exports.
- Do not delete nanoBragg/easyBragg mirrors that prior attempts rely on.
- Avoid running more than the mapped pytest selectors unless instructed; stick to evidence-only activity.
If Blocked: Log command, exit code, and stderr in diffbragg_cpu_attempt.log; append blocker summary to planning_notes.md, update docs/fix_plan.md Attempts History with Metrics/Artifacts placeholders, and record the block + return condition in galph_memory before switching focus.
Findings Applied (Mandatory):
- CONFIG-001 — Hypothesis review protects detector/beam/crystal mappings while tracing the CUDA free() failure.
- CONFORMANCE-001 — Planning keeps DB_AT_001 acceptance artifacts (collect-only logs) in mind while staging new captures.
- DIAGNOSTICS-001 — Logging env_status and cpu_attempt outputs preserves diagnostic trails per tracing spec.
- PARITY-001 — Capturing first-divergence-ready artifacts (even on failure) supports downstream parity analysis.
- TESTING-003 — Plan includes refreshing collect-only logs after a successful capture so documentation stays accurate.
Doc Sync Plan (Mandatory):
- `KMP_DUPLICATE_LIB_OK=TRUE python -m pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001 > plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T055449Z/collect_db_at_001_parity.log`
- `KMP_DUPLICATE_LIB_OK=TRUE python -m pytest --collect-only -q tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001 > plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T055449Z/collect_db_at_001_forward.log`
- Update docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md with the new artifact paths once the above logs exist.
