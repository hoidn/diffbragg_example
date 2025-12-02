Summary:
- Tighten RefinementContext/RefinementSharedContext so they import `RefinementInputs` from `dbex.refinement.inputs`, then rerun the context unit tests to prove typed plumbing still works before we close the writer/bridge initiative.

Mode: none

InitiativeType: architecture

Focus: ARCH-BRIDGE-RESP-001 — Writer / bridge responsibility split

Branch: integration

Mapped tests:
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/dbex/test_refinement_context.py

Artifacts: plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-03T093500Z/

Do Now:
- Implement: `dbex/refinement/context.py::{RefinementContext,RefinementSharedContext,build_refinement_context}` so the dataclasses and builder import the real `RefinementInputs` type from `dbex.refinement.inputs`, drop the stale `Any` placeholders that still cite `dbex.nanobrag_bridge`, and refresh the surrounding docstrings/comments to match the new module boundaries.
- Validate: Run `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/dbex/test_refinement_context.py | tee plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-03T093500Z/pytest_refinement_context.log` to confirm the type-hint tightening leaves the builders working as expected.

How-To Map:
1. `mkdir -p plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-03T093500Z`
2. In `dbex/refinement/context.py`, import `RefinementInputs` from `dbex.refinement.inputs` (module load is safe because inputs.py has no context dependency), update the `refinement_inputs` and `inputs` annotations on both dataclasses, and set the `build_refinement_context` parameter annotation accordingly; keep other fields typed as today to avoid scope creep.
3. Replace the inline comments that say "RefinementInputs from dbex.nanobrag_bridge" with "from dbex.refinement.inputs" so the docs and code agree, and double-check no new circular imports creep in (run `python -m compileall dbex/refinement/context.py` if unsure).
4. Run `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/dbex/test_refinement_context.py | tee plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-03T093500Z/pytest_refinement_context.log` to exercise the builder helpers; stash the log in the artifacts directory.
5. After tests pass, copy the plan/fix-plan/problem updates queued in Phase D (mark the fix-plan row done and note the resolved problems.md entry) in a follow-up PR if time permits; leave breadcrumbs in the artifacts directory if you defer this to the next loop.

Pitfalls To Avoid:
- Do not reintroduce TYPE_CHECKING-only imports—the contexts need concrete types so mypy and downstream editors see the right hints.
- Avoid importing `RefinementInputs` inside functions; keep it at module scope to match the rest of the context module and to prevent repeated import cost.
- Leave other `Any` annotations alone for now; this loop only targets the lingering bridge references so scope stays tight.
- Keep Environment Freeze in mind—no new dependencies or tooling changes are allowed.
- Ensure the pytest command runs under `KMP_DUPLICATE_LIB_OK=TRUE`; missing the env var often causes MKL duplicate errors.
- Do not rename dataclass fields; that would ripple through the stages and require a much broader validation pass.
- Capture logs under the requested artifact directory so the ledger audit trail stays intact.
- If you tweak docstrings, keep the normative spec citations intact (spec-db-workflow §7, context IDL, etc.).

If Blocked:
- If importing `RefinementInputs` triggers a circular import, wrap the import in a `typing.TYPE_CHECKING` block plus a runtime import inside `if TYPE_CHECKING` and leave a note in `plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-03T093500Z/blocker.md`; do not hack around it by reintroducing `Any`.
- If the context tests fail because mocks need updating, patch the local mock class inside the test (e.g., add missing fields) and capture the failing log in the artifacts directory before pausing for guidance.

Findings Applied (Mandatory):
- DIAGNOSTICS-001 — Writer/telemetry schema remains aligned after bridge split.
- PHYSICS-LOSS-001/002/003 — Sigma provenance and variance-weighted loss data must keep flowing through contexts.
- ARCH-STAGE-CTX-001/002 — Stage helpers must rely on typed contexts and the Stage B baseline guard dataclasses.

Pointers:
- dbex/refinement/context.py:72 — `RefinementContext` dataclass.
- dbex/refinement/context.py:420 — `RefinementSharedContext` definitions.
- docs/architecture/dbex/refinement/context.idl.md — authoritative contract for context fields.

Next Up (optional):
- Once the context types are updated and tested, mark `[ARCH-BRIDGE-RESP-001]` as done in docs/fix_plan.md and resolve the problems.md ledger entry so the backlog guard clears.
