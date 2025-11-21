# REFINE-SMOKE-CANONICAL — Restore canonical Stage B/C smoke convergence

## Initiative
- ID: REFINE-SMOKE-CANONICAL
- Title: Restore canonical Stage B/C smoke convergence
- Owner: Ralph
- Spec Owner: docs/spec-db-workflow.md
- Status: done (2025-11-21)

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
- [x] **Spec Constraint:** docs/spec-db-workflow.md §§Stage B/C definitions + Stage Smoke Dataset Policy (lines 36‑95).
- [x] **Fix-Plan Link:** docs/fix_plan.md — Row [REFINE-SMOKE-CANONICAL] (closed 2025-11-21).
- [x] **Finding/Policy ID:** REFINE-007 (Stage C detector microslip gate), REFINE-008 (Stage B shell modifier telemetry), PHYSICS-LOSS-001 (chi-squared telemetry fidelity).

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
- [x] A0: **Nucleus — Canonical reproduction:** Reran the Stage B/C selectors with `DBEX_SMOKE_DETECTOR_SIZE=full` and captured logs + telemetry under `plans/active/REFINE-SMOKE-CANONICAL/reports/2025-11-21T042222Z/` to document the `chi_squared_best_b` exception and Stage C’s bogus 100% shrinkage.
- [x] A1: Summarized the failing telemetry deltas (chi-squared traces, shell modifiers, detector offsets) and cited the violated clauses in `docs/fix_plan.md` and the report summary.
- [x] A2: Recorded debugging hypotheses (LBFGS scope bug, missing baseline detector) inside the same report directory before implementation.

### Dependency Analysis (Required for Refactors)
- **Touched Modules:** `dbex/nanobrag_refinement.py` (Stage B/C closures + telemetry), `tests/dbex/test_torch_refine_smoke.py` (gate assertions), potential updates to `docs/TESTING_GUIDE.md`.
- **Circular Import Risks:** Low — changes stay inside `dbex.nanobrag_refinement` and test modules already importing it.
- **State Migration:** None; Stage contexts are per-run objects. Ensure telemetry schema changes remain backward-compatible for downstream consumers (`dbex/refine_one`, CLI diagnostics).

### Notes & Risks
- Capturing telemetry on the canonical detector requires GPU RAM; honor `NANOBRAG_DISABLE_COMPILE=1` and `KMP_DUPLICATE_LIB_OK=TRUE` per runtime policy.

## Phase B — Stage B Optimizer Repair
### Checklist
- [x] B1: Added the missing `nonlocal` declarations + snapshot fixes inside the Stage B LBFGS closure so canonical runs complete without `UnboundLocalError`. (See `dbex/nanobrag_refinement.py` + artifacts under `plans/active/REFINE-SMOKE-CANONICAL/reports/2025-11-21T042222Z/`.)
- [x] B2: Verified Stage B chi-squared/loss traces and shell modifiers propagate through telemetry (telemetry JSON + pytest logs) and tightened the smoke assertions to guard ±1 % modifiers with non-regression gates.
- [x] B3: Synced the test guidance/registry via PHYSICS-LOSS-001 and archived the full-detector Stage B logs showing the repaired behavior.

### Notes & Risks
- LBFGS snapshots must remain on CPU when `stage_b_full_eval_on_cpu=True`; careless `.to(device)` calls can thrash memory or change semantics.

## Phase C — Stage C Detector Physics
### Checklist
- [x] C1: Threaded baseline detector distances through Stage C telemetry (baseline cache + `_apply_baseline_detector_prior`) so reduction metrics reference the true perturbations.
- [x] C2: Verified Stage C chi-squared/loss traces respond to detector motion (telemetry JSON shows ≥0.001 improvement) and kept the smoke assertions strict to flag zero-improvement cases.
- [x] C3: Replayed Stage C smokes on the full detector, archived logs/telemetry in the report directory, and confirmed no tolerance changes beyond the documented REFINE-007 gates were needed.

### Notes & Risks
- Detector geometry updates must respect CUSTOM convention and distance pivots; regressions here could break DB-AT selectors beyond the smoke suite.

## Artifacts Index
- Reports root: `plans/active/REFINE-SMOKE-CANONICAL/reports/`
- Latest run: `2025-11-21T042222Z/`
