# Phase D0 Baseline Decision

## Verdict
**Path A** — Both tests PASS → Phase D1 ready (Stage C helper extraction)

## Test Results
- **Collection:** 1 test collected (parametrized via environment variable: small + full detectors)
- **Small detector:** PASS (16.0s, exit code 0)
- **Full detector:** PASS (40.83s, exit code 0)

## Key Observations
- **Stage C detector offset refinement behavior:** STABLE (both small and full detectors passed acceptance criteria)
- **Telemetry captured:** YES (pytest logs contain full test output with telemetry structure validation)
- **Blocker details:** Two blocking bugs discovered and fixed (see `bugfix_notes.md`)

## Bugfix Summary
1. **UnboundLocalError for RefinementTelemetry** (line 3170): Removed redundant local import that shadowed module-level class
2. **NameError for baseline_detector_distances** (lines 3830-3834): Added variable initialization in Stage C inline block

Both fixes are minimal, targeted, and preserve existing behavior. Patches saved for reproducibility (`unbound_local_error_fix.patch`, `stage_c_bugfix.patch`).

## Telemetry Details
- **Stage A + Stage C run completed:** Both tests exercised full Stage A → Stage C refinement pipeline
- **Per-panel distance_offset parameters:** Present in Stage C telemetry (validated via test acceptance criteria)
- **Chi² non-regression:** Confirmed (tests validate Stage C does not increase chi² relative to Stage A)
- **Detector offset convergence:** Validated (tests check ≥80% reduction toward zero or ≤0.05mm absolute distance per REFINE-007)
- **Loss trace non-increasing:** Validated (last 3 validations non-increasing per acceptance criteria)

## Next Actions
**Path A (both PASS):** Galph plans Phase D1 (Stage C helper extraction) following proven Phase B/C multi-loop pattern:
- Extract Stage C parameter builder helper (~150-200 lines estimated)
- Extract Stage C closure helper (~250-300 lines estimated)
- Extract Stage C LBFGS runner helper (~100-120 lines estimated)
- Wire helpers into inline path with regression guard
- Expected timeline: 2-3 loops (mirroring Phase B/C extraction: Phase B 3 loops C1a/C1b/C1c, Phase C 1 loop complete)

## Confidence Assessment
- **Baseline accuracy:** VERY HIGH (95%+)
  - Both detector sizes passed
  - Full telemetry structure validated
  - Bugfixes targeted and minimal (no refactoring, no API changes)
  - Test runtime consistent with expectations (small ~16s, full ~40s)
- **Stage C extraction readiness:** READY
  - Inline Stage C code location confirmed (dbex/nanobrag_refinement.py:3824-4328)
  - Helper extraction targets identified via Phase B/C pattern
  - Acceptance tests stable and reproducible
  - No environment/dependencies changes (Environment Freeze maintained)

## Risk Assessment
- **Extraction complexity:** MEDIUM (Stage C simpler than Stage B — no shell modes, no per-reflection variants, single distance offset per panel)
- **Regression risk:** LOW (Phase B/C extraction established proven pattern: extract helpers → wire inline → regression guard → iterate)
- **Technical debt:** Bugfixes applied directly to inline code (will be carried forward into helpers during extraction)

## Artifacts Inventory
- `pytest_collect_stage_c.log` (1 test collected)
- `pytest_stage_c_small_final.log` (PASS, 16.0s)
- `pytest_stage_c_full.log` (PASS, 40.83s)
- `metrics_stage_c_small.json`
- `metrics_stage_c_full.json`
- `unbound_local_error_fix.patch`
- `stage_c_bugfix.patch`
- `bugfix_notes.md`
- `decision.md` (this file)

## SPEC/ADR Alignment
- **REFINE-007 (docs/findings.md:43):** Stage C gate is "stable detector offset" NOT "chi² improvement" — both tests validated detector offsets do not diverge, chi² non-regressing ≤+0.05% vs Stage A
- **SPEC-DB-WORKFLOW.md §7:** Stage C refines per-panel translations along detector normal (distance offset) with rotations fixed — validated via acceptance criteria
- **TORCH-REFINE-003:** Stage C detector distance refinement acceptance criteria met (status != error, telemetry contains distance_offset params, offset shrinks ≥80% or ≤0.05mm, chi² non-regressing, loss trace non-increasing)
- **POLICY-001 (Environment Freeze):** Maintained — no package installs, no environment changes, bugfixes scoped to local source only

## Inline Stage C Code Location
- **File:** `dbex/nanobrag_refinement.py`
- **Lines:** 3824-4328 (estimated, full Stage C section from "Stage C:" comment to telemetry_c construction)
- **Helper extraction targets (Phase D1):**
  1. `_build_stage_c_params`: Parameter initialization, baseline detector distances, ROI/panel mode setup (~150-200 lines)
  2. `_build_stage_c_lbfgs_closure`: Nested compute_loss_stage_c + closure_stage_c functions (~250-300 lines)
  3. `_run_stage_c_lbfgs`: LBFGS execution, convergence checks, telemetry assembly (~100-120 lines)
