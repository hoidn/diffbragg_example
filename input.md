Summary: Hoist Stage B stack dependencies (json/os/logging/StageBTelemetryCollector) to module scope, clean up the parity guard, and prove the lazy-import removal keeps the Stage B guard + smoke selectors green.
Mode: none
InitiativeType: architecture
Focus: ARCH-LAZY-IMPORTS-001 — Lazy imports / process-noise hygiene
Branch: integration
Mapped tests:
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload | tee plans/active/ARCH-LAZY-IMPORTS-001/reports/2025-12-03T171500Z/pytest_stage_b_guard.log
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/ARCH-LAZY-IMPORTS-001/reports/2025-12-03T171500Z/pytest_stage_b_smoke.log
Artifacts: plans/active/ARCH-LAZY-IMPORTS-001/reports/2025-12-03T171500Z/
Do Now:
- Implement:
  * `dbex/refinement/stage_b_impl.py::{_check_stage_b_baseline_parity,_run_stage_b_lbfgs,_compute_loss_stage_b}` — move the current inline `import json`, `import os`, `import logging`, and `from pathlib import Path` statements to module scope; add `logger = logging.getLogger(__name__)`; keep a single module-scope import of `StageBTelemetryCollector` and have the guard reference it directly so there are no per-call imports.
  * `dbex/refinement/stage_b.py::StageB.run` — ensure the parity guard and telemetry plumbing rely on the eager imports (no nested `import logging` or `StageBTelemetryCollector` calls) and that JSON diff writing still happens via the shared `logger` + `Path` helpers.
- Validate: rerun the mapped selectors with canonical env flags, saving the `tee` logs shown above inside the artifact directory; stop immediately if either selector fails and leave the failing log in place for supervisor review.
How-To Map:
1. At the top of `dbex/refinement/stage_b_impl.py`, add `import json`, `import logging`, `import os`, `from pathlib import Path`, and `from dbex.refinement.telemetry_collectors import StageBTelemetryCollector`, then define `logger = logging.getLogger(__name__)`. Remove every nested import in `_check_stage_b_baseline_parity`, `_run_stage_b_lbfgs`, and helper functions; replace `logging.warning(...)` with `logger.warning(...)`.
2. Update `_check_stage_b_baseline_parity` to use the module-scope `StageBTelemetryCollector` identity check, keep the JSON diff writer logic intact with the new `Path` helper, and route warnings through `logger`. Double-check that environment lookups (`DBEX_SMOKE_TELEMETRY_PATH`) still behave the same way.
3. Scan `_run_stage_b_lbfgs` and `_compute_loss_stage_b` for inline `import logging` statements (there are multiple `import logging` blocks tied to fallback log messages) and remove them in favor of the shared `logger`. Do the same for any other Stage B helper that was calling `import logging` mid-function.
4. Run the mapped tests with the commands listed under “Mapped tests”, ensuring `AUTHORITATIVE_CMDS_DOC`, `KMP_DUPLICATE_LIB_OK`, and `NANOBRAGG_DISABLE_COMPILE=1` are exported per docs/TESTING_GUIDE.md §1 and that each command tees its output into the artifact directory.
Pitfalls To Avoid:
- Do not introduce new lazy imports elsewhere while cleaning these up; keep scope to Stage B stack.
- Preserve warning text and JSON payload schema in `_check_stage_b_baseline_parity` so REFINE-FLOW-001 comparisons remain actionable.
- Keep the module logger local (no global logging.basicConfig calls) to avoid mutating other modules’ logging state.
- Stage B helper functions run inside LBFGS closures — avoid adding heavy imports or slow logging paths inside tight loops.
- Respect Environment Freeze: no pip/conda installs; treat missing dependencies as blockers and log them per docs/fix_plan.md guidance.
- Capture pytest logs even on failure (per docs/TESTING_GUIDE.md), then stop and report; do not rerun tests blindly.
- Verify `AUTHORITATIVE_CMDS_DOC` remains set to `./docs/TESTING_GUIDE.md` before executing pytest so command provenance stays recorded.
If Blocked:
- If either mapped selector fails due to Stage B behavior changes, archive the full log + any generated JSON diff into the artifact directory, add a note to docs/fix_plan.md Attempts History, and stop for supervisor triage instead of attempting speculative telemetry tweaks.
Findings Applied:
- ARCH-ENGINE-002 — Stage wrappers must import dependencies eagerly with documented guards (dbex/refinement/stage_b.py/stage_b_impl.py).
- GEOMETRY-001 / GEOMETRY-003 — Mapping-dependent helpers cannot hide tensor dependencies; Stage B imports must stay explicit so detector/crystal plumbing remains auditable.
- RUNTIME-001 — No torch.compile/dtype surprises from lazy imports; device neutrality depends on predictable import order.
Pointers:
- plans/active/ARCH-LAZY-IMPORTS-001/implementation.md:61 (Phase B checklist + Stage B cleanup scope).
- docs/fix_plan.md:139 (ARCH-LAZY-IMPORTS-001 ledger entry & attempts history).
- docs/spec-db-workflow.md:76 (Stage B normative contract and runtime guardrails).
- docs/TESTING_GUIDE.md:102 (Stage smoke env knobs and telemetry logging expectations).
Next Up: Once Stage B imports are clean, repeat the pattern for Stage C and Stage A helper modules (Phase B.3 completion) before adding an import-hygiene selector in Phase C.
Doc Sync Plan: none (no new selectors or renamed tests).
Mapped Tests Guardrail: selectors already collect >0 tests; no authoring needed.
Hard Gate: treat any new Stage B parity deltas or smoke regressions as blockers — do not merge import changes without both selectors passing.
Normative Math/Physics: See docs/spec-db-core.md §Objective Function & Variance Model for the variance-weighted χ² telemetry Stage B must continue to report.
