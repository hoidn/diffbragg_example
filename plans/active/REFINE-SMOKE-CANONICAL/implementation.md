# REFINE-SMOKE-CANONICAL — Restore canonical Stage B/C smoke convergence

## Initiative
- ID: REFINE-SMOKE-CANONICAL
- Title: Restore canonical Stage B/C smoke convergence
- Owner: Ralph
- Spec Owner: docs/spec-db-workflow.md
- Status: pending

## Goals
- Diagnose and fix the canonical (full-detector) Stage B LBFGS failure so shell modifiers actually execute an optimization step and chi-squared deltas stay within the spec-calibrated tolerances.
- Ensure Stage C detector-distance refinement produces real detector-offset shrinkage and non-regressing chi-squared traces by aligning telemetry with the injected perturbations instead of hard-coded zeros.

## Phases Overview
- Phase A — Telemetry Validation: Capture authoritative Stage B/C telemetry + failure signatures on the canonical detector.
- Phase B — Stage B Optimizer Repair: Fix the LBFGS scope/telemetry bugs and re-validate chi-squared deltas + shell modifiers.
- Phase C — Stage C Detector Physics: Correct offset tracking and chi-squared guards so the microslip smoke enforces real motion.

## Exit Criteria
1. `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=full` passes on GPU with Stage B telemetry showing (a) no LBFGS runtime errors, (b) a recorded chi-squared improvement ≥ 0 or ≥ −1 × 10⁻⁶ (per REFINE-008), and (c) shell modifiers within ±1 % of identity.
2. `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full` passes with Stage C telemetry proving ≥ 80 % detector-offset shrinkage (or ≤ ±0.05 mm final) and chi-squared traces that do not regress more than 0.05 % relative to Stage A; the reduction calculation must reference the actual injected offsets.
3. Telemetry artifacts (JSON + pytest logs) capturing the repaired Stage B and Stage C runs live under `plans/active/REFINE-SMOKE-CANONICAL/reports/<timestamp>/` and are summarized in `docs/fix_plan.md` Attempts History.
4. Test registry synchronized: `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` reflect any test/gate updates; `pytest --collect-only` logs for the Stage B and Stage C selectors are saved under `plans/active/REFINE-SMOKE-CANONICAL/reports/<timestamp>/`. Do not close the initiative if either selector marked "Active" collects 0 tests.

## Compliance Matrix (Mandatory)
- [ ] **Spec Constraint:** docs/spec-db-workflow.md §§Stage B/C definitions + Stage Smoke Dataset Policy (lines 36‑95).
- [ ] **Fix-Plan Link:** docs/fix_plan.md — Row [REFINE-SMOKE-CANONICAL].
- [ ] **Finding/Policy ID:** REFINE-007 (Stage C detector microslip gate), REFINE-008 (Stage B shell modifier telemetry), PHYSICS-LOSS-001 (chi-squared telemetry fidelity).

## Spec Alignment
- **Normative Spec:** docs/spec-db-workflow.md
- **Key Clauses:** Stage B must use differentiable tricubic HKL interpolation with halo support; Stage C must perform per-panel detector translations and prove non-regressing chi-squared; Stage Smoke Dataset Policy requires canonical detector gates to remain strict when `--smoke-detector-size=full`.

## Context Priming (read before edits)
- docs/spec-db-workflow.md §§Stage B/C + Stage Smoke Dataset Policy.
- docs/TESTING_GUIDE.md Stage smoke selectors table.
- docs/findings.md entries REFINE-007, REFINE-008, PHYSICS-LOSS-001.
- plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T031620Z/pytest_stage_smokes_full.log (failure signatures).
- dbex/nanobrag_refinement.py Stage B/C implementations.

## Phase A — Telemetry Validation
### Checklist
- [ ] A0: **Nucleus — Canonical reproduction:** Rerun the Stage B and Stage C selectors with `DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH` set, saving logs + telemetry JSON under this plan’s reports directory; annotate the observed Stage B exception (`chi_squared_best_b` scope) and Stage C zero-improvement traces.
- [ ] A1: Summarize telemetry deltas (chi-squared traces, shell modifiers, detector offsets) from the failing runs and link to specific spec clauses they violate in `docs/fix_plan.md`.
- [ ] A2: Draft debugging hypotheses (e.g., LBFGS closure scoping, detector offset baseline mismatch) and capture them in `plans/active/REFINE-SMOKE-CANONICAL/reports/<timestamp>/analysis.md` for traceability.

### Dependency Analysis (Required for Refactors)
- **Touched Modules:** `dbex/nanobrag_refinement.py` (Stage B/C closures + telemetry), `tests/dbex/test_torch_refine_smoke.py` (gate assertions), potential updates to `docs/TESTING_GUIDE.md`.
- **Circular Import Risks:** Low — changes stay inside `dbex.nanobrag_refinement` and test modules already importing it.
- **State Migration:** None; Stage contexts are per-run objects. Ensure telemetry schema changes remain backward-compatible for downstream consumers (`dbex/refine_one`, CLI diagnostics).

### Notes & Risks
- Capturing telemetry on the canonical detector requires GPU RAM; honor `NANOBRAG_DISABLE_COMPILE=1` and `KMP_DUPLICATE_LIB_OK=TRUE` per runtime policy.

## Phase B — Stage B Optimizer Repair
### Checklist
- [ ] B1: Fix the LBFGS closure variables (add `nonlocal` declarations, remove stray debug prints, ensure best-parameter snapshots copy tensors before device moves) so Stage B completes without `UnboundLocalError`.
- [ ] B2: Validate that Stage B chi-squared deltas, shell modifiers, and telemetry traces propagate through `telemetry_dict["B"]`; add unit tests or smoke-level assertions that fail if Stage B never records an improvement or deviates beyond ±1 % modifiers.
- [ ] B3: Update docs/test guidance (if thresholds change) and capture full-detector logs demonstrating the repaired behavior.

### Notes & Risks
- LBFGS snapshots must remain on CPU when `stage_b_full_eval_on_cpu=True`; careless `.to(device)` calls can thrash memory or change semantics.

## Phase C — Stage C Detector Physics
### Checklist
- [ ] C1: Thread the actual detector perturbation baseline into Stage C telemetry (e.g., stash `create_perturbed_geometry` offsets or compute differences against `perturbed_detector`) so reduction calculations reference real initial offsets.
- [ ] C2: Ensure Stage C chi-squared traces respond to detector motion by verifying gradients propagate (check `compute_loss_stage_c` ROI sampler + warm cache) and adjust the smoke test to flag zero-improvement scenarios.
- [ ] C3: Re-run Stage C smokes, archive telemetry/logs, and update docs/TESTING_GUIDE.md tolerances only if the physics-driven gates need slight rewording (not wholesale relaxation).

### Notes & Risks
- Detector geometry updates must respect CUSTOM convention and distance pivots; regressions here could break DB-AT selectors beyond the smoke suite.

## Artifacts Index
- Reports root: `plans/active/REFINE-SMOKE-CANONICAL/reports/`
- Latest run: `<YYYY-MM-DDTHHMMSSZ>/`
