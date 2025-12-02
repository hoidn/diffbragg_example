Summary: Bring Stage A/B smoke tests up to date with the StageArtifacts contract by asserting that StageAArtifacts/StageBArtifacts populate `bragg_full` when downstream stages are disabled, then rerun the canonical Stage A and Stage B shell smokes plus the CLI writer selector to lock in Phase D evidence for ARCH-STAGE-CONTEXT-001.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-STAGE-CONTEXT-001 — Stage Context + Engine Artifact Boundary
Branch: integration
Mapped tests:
- tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion
- tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers
- tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata
Artifacts: plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T150500Z/

Do Now:
- FocusItem: ARCH-STAGE-CONTEXT-001 Phase D — Final Bragg Artifact Propagation
- Implement: tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion — destructure the third return value (`engine_artifacts`), assert it only contains `stage_a` for this Stage-A-only flow, and verify `StageAArtifacts.bragg_full` is a CPU numpy array whose shape and values (`np.allclose`) match `bragg_refined`. This makes the Stage A terminal invariant executable instead of a comment.
- Implement: tests/dbex/test_torch_refine_smoke.py::{test_stage_b_shell_modifiers,test_stage_b_per_reflection_smoke} — capture `engine_artifacts`, assert Stage A artifacts keep `bragg_full=None` whenever Stage B runs, and verify Stage B artifacts populate `bragg_full` (shape/value match `bragg_refined`) with the correct `stage_b_mode` (`shell_modifiers` vs `per_reflection`). The per-reflection test continues to xfail its gradient gate; just insert the artifact assertions before that failure path.
- Validate: `pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=small` with `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1` and tee to `plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T150500Z/pytest_stage_a_small.log`.
- Validate: `pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small` with the same env vars and tee to `.../pytest_stage_b_shell.log`.
- Validate: `pytest -vv tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata` (KMP_DUPLICATE_LIB_OK=TRUE, AUTHORITATIVE_CMDS_DOC set) and tee to `.../pytest_cli_writer.log` to prove the writer’s artifact plumbing remains aligned with the new assertions.

How-To Map:
- `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=small | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T150500Z/pytest_stage_a_small.log`
- `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T150500Z/pytest_stage_b_shell.log`
- `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T150500Z/pytest_cli_writer.log`

Pitfalls To Avoid:
- Do not loosen the REFINE-008 gates or downgrade the known TORCH-REFINE-004 failure; the new assertions should run before the per-reflection test’s failure path but must not mask it.
- Keep artifact checks on CPU numpy tensors; writer/HDF5 plumbing expects CPU-resident buffers, so avoid `tensor.to("cuda")` within the tests.
- Leave the Stage B full-detector skip (GRADIENT-003) intact and continue using the small-detector fixture with CLI sigma overrides documented in docs/TESTING_GUIDE.md.
- Ensure `AUTHORITATIVE_CMDS_DOC` and the smoke env vars are exported for every pytest invocation so fixtures stay deterministic.

If Blocked: If the artifact assertions show `bragg_full=None`, capture the failing pytest output plus a short note in `plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T150500Z/blocked.md`, then update docs/fix_plan.md with the blocker instead of weakening the assertions.

Findings Applied (Mandatory):
- ARCH-STAGE-CTX-001 — Stage wrappers must honor typed StageArtifacts; tests now enforce it.
- REFINE-FLOW-001 — Stage B shell flows still need canonical Stage A telemetry parity when generating final Bragg tensors.
- PHYSICS-LOSS-001 — Parity smokes must continue to use the canonical sigma/variance configuration.

Pointers:
- plans/active/ARCH-STAGE-CONTEXT-001/implementation.md#phase-d — authoritative checklist for Phase D work.
- tests/dbex/test_torch_refine_smoke.py — Stage A/B smoke tests gaining the new assertions (see Stage A expansion around line ~373 and Stage B shell/per-reflection around lines ~1330/1687).
- docs/TESTING_GUIDE.md §2 — canonical commands/env vars for the Stage smokes and CLI writer selector.

Next Up (optional): After these assertions are in place, we can run a parity-only loop on the per-reflection smoketest to log the existing gradient failure signature for PERF-WARM-SIM-001 before closing ARCH-STAGE-CONTEXT-001.
