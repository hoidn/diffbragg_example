### Turn Summary (Loop i=113)

Loop i=112 misdiagnosed hang as environment issue. Diagnostic revealed no hang - Phase A.2 cold-path test completes in <50s but FAILS with test metadata threading issue. Test was missing calibration_metadata + HKL alignment from stage_a_ctx. Fixed test but cold path still produces ~35× too-high output, indicating fundamental simulator construction mismatch between simulate_forward_once (used by Stage A) and reconstruction cold path. Blocked: requires deeper parity investigation between forward model paths. Next: escalate to supervisor for architecture review.

Artifacts: plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T060000Z/pytest_phase_a2_extended_timeout.log

### Analysis

**Problem discovered**: Loop i=112 concluded Phase A.2 hung at ~2.5min timeout. Extended timeout to 10min reveals test completes in 49.8s but FAILS with rel_error=0.646 (64.6%, ratio ~2.83).

**Root cause investigation**:
1. Phase A.2 test created minimal `RefinementConfig()` without `calibration_metadata`
2. Cold path failed to receive `spot_scale_override` from config, producing wrong scaling
3. Fixed: threaded `stage_a_ctx.calibration` and `stage_a_ctx.hkl_indices/amplitudes` to test

**Post-fix status**: Cold path now receives calibration_metadata but produces WORSE output:
- Stage A: `masked_mean=2.112`
- Cold path: `masked_mean=75.74` (35× too high!)
- Raw simulator output: `9.90e-08` (microscopic), then scaled to 68.5 by sqrt(spot_scale)

**Hypothesis**: Fundamental mismatch between `simulate_forward_once` (nanobrag_bridge.py:1230+) and reconstruction cold path (reconstruction.py:242-325). The factory correctly returns sqrt_scale for post-application, but the raw simulator outputs differ by many orders of magnitude between the two paths.

**Evidence**:
- Cold path applies `apply_sqrt_spot_scale` at reconstruction.py:505-509 (correct per SCALE-002)
- Factory computes but doesn't apply sqrt_scale (helpers.py:190-194, returns at line 228)
- But raw simulator outputs are ~10^7 different between Stage A and cold path

**Decision**: Blocked. This exceeds scope of "debug hang" and reveals architectural issue requiring:
1. Comparative analysis of `simulate_forward_once` vs reconstruction cold path simulator construction
2. Verification of N_cells/beam_config/spot_scale application order
3. Possible DMI investigation with Ledger evidence at simulator boundaries

**Commits**: Test calibration_metadata + HKL threading fixes applied (not pushed - awaiting resolution)
