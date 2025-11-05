Summary: Hand off orientation misset plumbing plus deterministic perturbation so Stage A reliably clears the ≥5% gate with telemetry proof.
Mode: none
Focus: TORCH-REFINE-002 — Stage A expansion — full crystal and orientation
Branch: integration
Mapped tests: pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --maxfail=1
Artifacts: plans/active/TORCH-REFINE-002/reports/2025-11-05T035905Z/

Do Now:
- TORCH-REFINE-002
  - Implement: dbex/nanobrag_bridge.py::create_crystal_config — ensure tensor `misset_deg_override` survives CrystalConfig instantiation and rotates the torch simulator without breaking autograd; dbex/nanobrag_refinement.py::run_nanobrag_refinement — surface bounded orientation misset telemetry (XYZ degrees + quaternion norm) and wire the deltas into Stage A rollback snapshots; tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion — inject a deterministic refGeom perturbation helper so the smoke asserts ≥5% improvement and non-zero orientation delta.
  - Validate: pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --maxfail=1
  - Artifacts: plans/active/TORCH-REFINE-002/reports/2025-11-05T035905Z/

How-To Map:
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion | tee plans/active/TORCH-REFINE-002/reports/2025-11-05T035905Z/collect_stage_a.log
3. KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --maxfail=1 | tee plans/active/TORCH-REFINE-002/reports/2025-11-05T035905Z/pytest_stage_a.log
4. python - <<'PY' > plans/active/TORCH-REFINE-002/reports/2025-11-05T035905Z/orientation_delta.txt
from pathlib import Path
log = Path("plans/active/TORCH-REFINE-002/reports/2025-11-05T035905Z/pytest_stage_a.log").read_text()
for line in log.splitlines():
    if "Orientation norm" in line or "Improvement" in line:
        print(line)
PY

Pitfalls To Avoid:
- Preserve gradient flow: do not call `.item()`/`.detach()` when threading orientation tensors into configs.
- Maintain quaternion normalization and clip orientation magnitude to ±3° before conversion.
- Keep deterministic perturbation test-only; never mutate canonical refGeom artifacts on disk.
- Ensure ROI sampling and validation cadence stay unchanged so telemetry comparisons remain valid.
- Capture updated telemetry keys without renaming existing fields relied on by downstream tooling.
- Archive fresh logs under the 2025-11-05T035905Z path—no overwriting earlier runs.
- Respect Environment Freeze: no installs, compiles, or torch upgrades.

If Blocked:
- Record the exact failure signature (telemetry status, traceback) in plans/active/TORCH-REFINE-002/reports/2025-11-05T035905Z/blocked.md and update docs/fix_plan.md Attempts History with the blocker summary.
- Append a galph_memory entry marking focus blocked and note prerequisites (e.g., nanobrag_torch API gaps) before switching focus.

Findings Applied (Mandatory):
- REFINE-001 — Warm-start `log_scale` and clamp before exponentiation to avoid gradient explosions.
- REFINE-002 — Recognize nucleus improvement ceiling; expanded DoFs must justify restoring the ≥5% gate.
- REFINE-003 — Orientation path must stay differentiable through quaternion→misset routing and CrystalConfig.
- REFINE-004 — Guarantee ≥5% gate via deterministic perturbation scoped to the smoke harness only.
- GRADIENT-001 — Crystal overrides remain tensors; no MOSFLM A* reinjection when overrides are active.

Pointers:
- docs/spec-db-workflow.md:30 — Stage A gate and orientation contract details.
- plans/nanobrag_integration_plan.md:176 — Stage A expansion milestones and telemetry expectations.
- dbex/nanobrag_refinement.py:333 — Current quaternion→misset mapping inside compute_loss.
- dbex/nanobrag_bridge.py:512 — CrystalConfig override plumbing for `misset_deg` and tensor overrides.
- tests/dbex/test_torch_refine_smoke.py:132 — Stage A expansion smoke assertions awaiting ≥5% improvement and orientation deltas.

Next Up (optional):
1. TORCH-REFINE-003 — Stage C detector microslip once Stage A orientation gate lands.
