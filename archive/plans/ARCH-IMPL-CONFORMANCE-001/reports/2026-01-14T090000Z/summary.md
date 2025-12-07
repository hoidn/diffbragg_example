### Turn Summary (Loop i=114 Execution)

**Timestamp**: 2025-12-06T19:53:00Z
**Initiative**: ARCH-IMPL-CONFORMANCE-001 Phase B.5 (Evidence Collection)
**Status**: Evidence collected, root cause localized, initiative BLOCKED pending architectural scope decision

Executed Phase B.5 evidence-collection loop with diagnostic logging at 4 hops (test → config → reconstruction → apply_sqrt_spot_scale). Trace log proves calibration_metadata threading is **WORKING CORRECTLY** at all hops (spot_scale_override=4.786e17 present, sqrt_spot_scale=6.918e8 applied). Root cause is NOT threading break — it's simulator construction parity break between Stage A and reconstruction cold path. Stage A masked_mean=2.15, reconstruction cold masked_mean=75.74 (ratio 1:35). Reconstruction raw simulator output (9.90e-08) is ~2e7× smaller than Stage A's bragg_zero_iter before scaling, indicating different N_cells/beam_flux/baseline_alignment application order in simulator factories. Warm-cache regression PASSED. Initiative marked **BLOCKED** — exceeds bugfix/architecture scope; requires deep audit of Stage A vs cold-path simulator construction semantics, baseline_alignment_factor computation (C.14 warning shows telemetry_model_mean_masked=None), and legacy log_scale fallback.

**Artifacts**: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T090000Z/` (pytest_phase_b5_trace.log, pytest_warm_cache_regression.log, phase_b5_decision.md)

---

### Turn Summary (Loop i=114 Planning)

**Initiative**: ARCH-IMPL-CONFORMANCE-001 Phase B.5 (Evidence Collection)
**Focus**: Diagnose calibration_metadata threading break preventing cold-path sqrt scaling

## Problem

Loop i=113 diagnostic revealed Phase A.2 cold-path test did NOT hang (completes in 49.8s) but FAILS with 64.6% rel_error (ratio 2.83:1 scale mismatch). Evidence from pytest log shows raw simulator output (6.9e-01) ≈ scaled output (6.9e-01), proving `apply_sqrt_spot_scale` saw `calibration_metadata=None` despite Ralph's i=112 fix threading it to `RefinementConfig`.

Expected behavior: `spot_scale_override ≈ 3.2e17` → `sqrt_spot_scale ≈ 5.66e8` → scaled output should be ~5.66e8× raw output.

## Hypothesis

The `effective_calibration_metadata` defaulting logic at reconstruction.py:219 fails because either:
- (A) RefinementConfig constructor doesn't preserve `calibration_metadata` parameter
- (B) `calibration_metadata` parameter not passed to `build_final_bragg_from_stage_a_telemetry`
- (C) Test threading never actually applied

## Action Taken (Loop i=114)

Planned evidence-collection loop to add diagnostic logging at 4 critical hops:
1. test_scale_contracts.py:262 — RefinementConfig creation
2. reconstruction.py:221 — effective_calibration_metadata defaulting
3. reconstruction.py:509 — apply_sqrt_spot_scale call site
4. scaling_utils.py:88-111 — sqrt_spot_scale execution

Each hop logs calibration_metadata value (None vs dict with spot_scale_override) so we can identify where the chain breaks.

## Deliverables for i=114

Ralph will:
1. Add `[CALIBRATION TRACE]` print statements at each hop (NO production code changes)
2. Run Phase A.2 test with full output capture
3. Analyze trace log to identify which hop shows None
4. Write `phase_b5_decision.md` stating root cause (Scenario A/B/C) + exact fix path
5. Run warm-cache regression check (expect PASS)
6. Commit artifacts only (NOT logging changes)

## Expected Outcomes

After logging analysis, Phase B.6 will implement the fix:
- **If Scenario A**: Fix RefinementConfig.__init__ to preserve `calibration_metadata` parameter
- **If Scenario B**: Fix test to pass `calibration_metadata=stage_a_ctx.calibration` to `build_final_bragg_from_stage_a_telemetry`
- **If Scenario C**: Fix test to actually thread calibration (Ralph's fix didn't apply)

Once fixed, Phase A.2 test should PASS with rel_error ≈ 1e-07.

## ARCH Compliance

- **ARCH-CONTRACT-002** enforcement: Single owner API for sqrt scaling (scaling_utils.py)
- **SCALE-008** authority: Stage A warm-cache baseline (simulate_forward_once)
- **SCALE-009** parity: Reconstruction cold path must match Stage A (currently VIOLATED)

## Lifecycle Status

- **DecisionStatus**: exploring (requires trace evidence to localize break)
- **Dwell**: 0 (first evidence loop for this selector+signature)
- **Loop budget**: 4/6 total (A.0-A.2 nucleus, B.1-B.2 API, B.3-B.4 refactor, this planning)

## References

- Planning doc: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T090000Z/phase_b5_planning.md`
- Prior diagnostic: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T060000Z/summary.md`
- Evidence: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T060000Z/pytest_phase_a2_extended_timeout.log:13-15`
- Canonical API: `dbex/refinement/scaling_utils.py:35-111`
