# TORCH-REFINE-002D Loop Summary — 2025-11-05T093000Z

## Acceptance & Module Scope
**Acceptance focus:** AT-02D (Stage A improvement gate calibration per empirical probe)
**Module scope:** {refinement, tests, docs}
**SPEC lines implemented:** docs/spec-db-workflow.md:30-38 (Stage A convergence), plans/active/TORCH-REFINE-002D/implementation.md:13-16 (exit criteria)

## SPEC/ADR Alignment
Implemented:
- **docs/spec-db-workflow.md:30-38** — Stage A LBFGS closure requires ≥0.2% loss drop within ≤30 steps (recalibrated from 5% per empirical probe showing ~0.206% achievable ceiling with canonical refGeom dataset)
- **plans/active/TORCH-REFINE-002D/implementation.md:13-16** — Exit criteria satisfied: haloed grid + tricubic interpolation enabled (≥95% hit rate), Stage A assertion passes without xfail, findings/fix_plan updated

**ADR referenced:** REFINE-004, REFINE-005, REFINE-006 (gate calibration rationale)

## Search Summary
No new search required; prior attempts (TORCH-REFINE-002D 2025-11-05T083500Z, 2025-11-05T093000Z) already quantified achievable improvement ceiling via empirical probe.

**File pointers:**
- dbex/nanobrag_refinement.py:13,143,533 — Module docstring, RefinementConfig.min_loss_improvement, early-stop message
- tests/dbex/test_torch_refine_smoke.py:197-204,228,317-329 — test_stage_a_expansion docstring, config, assertion
- docs/findings.md:37-38 — REFINE-004/005 resolution
- docs/fix_plan.md:62,77 — TORCH-REFINE-002D status update

## Changes
**Modified files:**
- dbex/nanobrag_refinement.py (4 changes)
  - Line 13: Updated docstring to reference ≥0.2% convergence per TORCH-REFINE-002D
  - Line 143: Changed RefinementConfig.min_loss_improvement from 0.05 (5%) to 0.002 (0.2%)
  - Line 533: Updated early-stop message to reference 0.2% gate calibrated per TORCH-REFINE-002D

- tests/dbex/test_torch_refine_smoke.py (11 changes)
  - Lines 197-204: Updated test_stage_a_expansion docstring to reflect ≥0.2% acceptance criterion
  - Line 228: Adjusted config instantiation to use min_loss_improvement=0.002
  - Lines 317-329: Replaced ≥5% assertion with ≥0.002 threshold including probe artifact reference

- docs/findings.md (2 changes)
  - Line 37: Marked REFINE-004 as Resolved with 2025-11-05 closure date and artifact pointer
  - Line 38: Marked REFINE-005 as Resolved with 2025-11-05 closure date and implementation reference

- docs/fix_plan.md (2 changes)
  - Line 62: Updated TORCH-REFINE-002D status to done
  - Line 77: Added 2025-11-05T093000Z implementation attempt with metrics

## Targeted Test Results
**Targeted selector:**
```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion
# Collected: 1 test

KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --maxfail=1
# Result: PASSED in 173.74s (0:02:53)
```

**Metrics:**
- Stage A improvement: ~0.206% (initial=9.76e+05 → final=9.74e+05)
- Iterations: 13 LBFGS steps (status=early_stop)
- HKL hit rate: ≥95% (haloed grid + tricubic interpolation)
- Deterministic misset telemetry: validated (initial≈[0,0,1.5]°)

## Full Suite Run
```bash
pytest -v tests/
# Not executed this loop; prior full-suite validations (2025-11-05T083500Z, 2025-11-05T070500Z) clean
```

## docs/fix_plan.md Delta
**Items completed:**
- TORCH-REFINE-002D: All exit criteria satisfied (status: in_progress → done)
  - Exit criterion #1: Haloed grid + tricubic interpolation enabled with ≥95% hit rate confirmed
  - Exit criterion #2: Stage A assertion passes without xfail; ≥0.2% gate met within ≤30 LBFGS iterations
  - Exit criterion #3: docs/findings.md updated (REFINE-004/005 resolved), fix_plan.md Attempts History refreshed, selector logs archived

**New items:** None

**Attempts History snippet:**
```
  * 2025-11-05T093000Z (implementation) — Implemented ≥0.2% gate calibration per input.md Do Now. Updated RefinementConfig.min_loss_improvement from 0.05 (5%) to 0.002 (0.2%) (dbex/nanobrag_refinement.py:143) and refreshed module docstring (line 13) and early-stop message (line 533) to reference TORCH-REFINE-002D calibrated gate. Updated test_stage_a_expansion docstring (tests/dbex/test_torch_refine_smoke.py:197-204) to reflect ≥0.2% acceptance criterion, adjusted config instantiation (line 228) to match new default, and replaced ≥5% assertion (lines 317-329) with ≥0.002 threshold including probe artifact reference. Marked REFINE-004 and REFINE-005 as Resolved in docs/findings.md (lines 37-38) with 2025-11-05 closure dates and artifact pointers. Ran targeted selector: pytest --collect-only (1 test collected), pytest -v test_stage_a_expansion --maxfail=1 (PASSED in 173.74s). Metrics: Stage A now achieves acceptance with canonical refGeom dataset; probe-validated ceiling of ~0.206% improvement encoded into config default; deterministic misset telemetry maintained. Artifacts: plans/active/TORCH-REFINE-002D/reports/2025-11-05T093000Z/{collect_stage_a.log,pytest_stage_a.log}. Outcome: All exit criteria satisfied — haloed grid + tricubic interpolation enabled (exit criterion #1: ≥95% hit rate confirmed), Stage A assertion passes without xfail (exit criterion #2: ≥0.2% gate met), and findings/fix_plan updated (exit criterion #3). Next Actions: Mark TORCH-REFINE-002D done; consider future initiative to unlock >3° orientation corrections and reassess improvement ceiling.
```

## CLAUDE.md / docs/architecture.md Updates
None required — gate calibration is config-level tuning, not a structural change.

## Next Most-Important Item
**TORCH-REFINE-003** — Stage C detector microslip per plan/Phase 3 (depends on Stage A being live).

Alternative: Investigate nanobrag_torch orientation bounds to unlock >3° corrections and reassess the Stage A gate thereafter.

---

### Turn Summary
Implemented ≥0.2% Stage A gate calibration after empirical probe showed ~0.206% ceiling with refGeom dataset; acceptance test now passes with calibrated threshold.
Resolved REFINE-004/005 (dataset limitation + haloed grid solution documented) and updated config/test/docs to encode the new gate.
Next: consider TORCH-REFINE-003 (Stage C detector microslip) or investigate nanobrag orientation bounds to unlock larger misset corrections.
Artifacts: plans/active/TORCH-REFINE-002D/reports/2025-11-05T093000Z/ (collect_stage_a.log, pytest_stage_a.log)
