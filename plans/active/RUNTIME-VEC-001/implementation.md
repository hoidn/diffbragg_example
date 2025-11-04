# RUNTIME-VEC-001 — Source Weight Runtime Guard

## Phase A — Evidence & Scope Definition
- [ ] A1: Confirm `nanobrag_torch` CLI is accessible from the DBEX environment (baseline command, version banner) and capture spec references for source-weight handling (`docs/architecture/pytorch_design.md` §1.1.5, `docs/pytorch_runtime_checklist.md` item #4).
- [ ] A2: Inventory the existing `nanoBragg/tests/test_cli_scaling.py::TestSourceWeights*` cases, identify which assertions map directly to DBEX needs (equal weighting, divergence parity), and note required fixtures/artifacts to port.
- [ ] A3: Define artifact policy for the ported tests (e.g., write metrics JSON into `$RUNTIME_VEC_ARTIFACT_DIR` on failure) and document planned pytest selectors + environment flags.

## Phase B — Implementation & Tests
- [ ] B1: Port the equal-weight enforcement test (`TestSourceWeights::test_source_weights_ignored_per_spec`) into `tests/dbex/test_runtime_vectorization.py`, reusing DBEX-friendly helpers and temporary sourcefiles.
- [ ] B2: Ensure the new test runs via the mapped selector (`pytest -v tests/dbex/test_runtime_vectorization.py::TestRuntimeVectorization::test_source_weights_ignored_per_spec`) with GPU-neutral guardrails; capture targeted pytest log and collect-only output under `plans/active/RUNTIME-VEC-001/reports/<timestamp>/`.
- [ ] B3: Refine remaining `TestSourceWeights*` coverage (divergence correlation checks, CLI parity metrics) or document deferral with TODO and thresholds if scope-limited this loop.

## Phase C — Validation & Documentation
- [ ] C1: Update `docs/TESTING_GUIDE.md` and `docs/development/TEST_SUITE_INDEX.md` to promote the runtime vectorization row from Planned to Active with command, env flags, artifact paths, and metrics overview.
- [ ] C2: Append fix_plan Attempts History detailing commands, artifacts, and findings references (RUNTIME-001, source weighting tolerances); create/update `docs/findings.md` if new runtime guardrails surface.
- [ ] C3: Archive pytest/collect logs with environment context under `plans/active/RUNTIME-VEC-001/reports/<timestamp>/commands/` or equivalent, ensuring rerun reproducibility.
