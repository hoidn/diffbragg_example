# MAP-SCALE-005 — CLI refined telemetry enforcement

## Purpose
Ensure the nanobrag CLI refuses to proceed when refined structure factors are requested but not actually consumed, eliminating silent fallbacks to raw MTZ amplitudes and aligning runtime behavior with SCALE-007 telemetry guardrails.

## References
- `dbex/refine_one.py` — CLI entry point (`run_nanobrag_backend`, `_write_torch_outputs`)
- `docs/spec-db-workflow.md` §4 — calibration + refined structure-factor workflow requirements
- `docs/spec-db-tracing.md` §2 — telemetry expectations for refined assets
- `docs/findings.md` — SCALE-003, SCALE-004, SCALE-007 guardrails
- `tests/dbex/test_refine_one_cli.py` — existing CLI regression coverage for refined MTZ usage
- `plans/active/MAP-SCALE-002/implementation.md` — calibration plumbing context
- `plans/active/MAP-SCALE-004/implementation.md` — zero-iteration telemetry contract

## Exit Criteria (from fix_plan)
1. Harden `run_nanobrag_backend` so CLI runs fail fast when `--refined-mtz` is provided but refined structure factors are not consumed (load failure, telemetry downgrade, or missing MTZ) instead of silently falling back to raw amplitudes.
2. Add regression coverage in `tests/dbex/test_refine_one_cli.py` exercising the failure path (expect raised `RuntimeError`/`SystemExit` with actionable message) and verifying telemetry remains `refined` when refined assets succeed; archive targeted pytest and collect-only logs under `plans/active/MAP-SCALE-005/reports/<timestamp>/`.
3. Update documentation ledgers (`docs/TESTING_GUIDE.md`, `docs/development/TEST_SUITE_INDEX.md`) and knowledge base (`docs/findings.md` if new guardrail) to reflect the CLI telemetry enforcement behavior, referencing SCALE-007 and new artifact paths.

## Phase Breakdown

- **Phase A — Reality check & guard design**
  - [ ] A1: Reproduce current CLI fallback behavior when `--refined-mtz` points to a missing file; capture stdout/stderr and confirm telemetry reports `raw`.
  - [ ] A2: Gather spec and findings citations (SCALE-003/004/007, docs/spec-db-workflow.md §4, docs/spec-db-tracing.md §2) supporting failure-on-fallback policy; summarize guard requirements in `reports/<timestamp>/summary.md`.
  - [ ] A3: Define precise failure surfaces (refined MTZ missing, load error, telemetry downgrade) and desired user-facing error messaging.

- **Phase B — Implementation & tests**
  - [ ] B1: Update `dbex/refine_one.py::run_nanobrag_backend` to raise a clear error when refined MTZ ingestion fails or telemetry reports `raw` after a refined request; ensure exit respects Environment Freeze (no sys.exit without message).
  - [ ] B2: Extend `_write_torch_outputs` or surrounding call sites if needed to enforce telemetry validation post-simulation and propagate guardrails to diagnostics logging.
  - [ ] B3: Add/extend regression tests in `tests/dbex/test_refine_one_cli.py` covering both the success path (still refined) and the new failure path; capture targeted pytest + collect-only logs under `plans/active/MAP-SCALE-005/reports/<timestamp>/`.

- **Phase C — Documentation & ledger sync**
  - [ ] C1: Update `docs/TESTING_GUIDE.md` and `docs/development/TEST_SUITE_INDEX.md` to document the failure-mode behavior, command snippets, and artifact expectations for the new test.
  - [ ] C2: Append fix_plan Attempts History entry with metrics, commands, and artifact paths; update `docs/findings.md` if a new telemetry enforcement guardrail is warranted or adjust SCALE-007 status notes.
  - [ ] C3: Archive logs and summaries in `plans/active/MAP-SCALE-005/reports/<timestamp>/` (include stderr captures for the failure case).

## Artifacts Index
- Working directory: `plans/active/MAP-SCALE-005/`
- Reports: `plans/active/MAP-SCALE-005/reports/<timestamp>/`
- Scripts (if promoted): `plans/active/MAP-SCALE-005/bin/`
