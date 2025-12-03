# DIAG-NANOBRAGG-OVERSAMPLE-001 Phase C.7-C.8 Validation Summary

## Loop Timestamp
2025-12-02T214000Z

## Focus
DIAG-NANOBRAGG-OVERSAMPLE-001 Phase C.7-C.8: Clean Validation & Beam Flux Investigation

## Initiative Type
diagnostics

## Problem & Alignment

### Task
Execute Phase C.7-C.8 of DIAG-NANOBRAGG-OVERSAMPLE-001 per input.md:
- C.7: Revert nanobrag_torch debug instrumentation
- C.8: Run clean validation tests (DB-AT-028/029)
- C.9 (conditional): Investigate beam flux if tests fail with zero output

### SPEC Alignment
- **DB-AT-028** (docs/spec-db-conformance.md:276-318): Loss scale sanity — chi²/pixel initial ≤ 1e2
- **DB-AT-029** (docs/spec-db-conformance.md:319-366): ROI structure parity — median ROI correlation before ≥ 0.2

### ARCH Alignment
No architecture changes in this loop; pure evidence collection and root cause analysis per diagnostics initiative type.

## Search & Existing Implementation

**Debug instrumentation status**: Already reverted (no debug code found in simulator.py via grep)

**Beam flux tracing**:
- Searched `create_beam_config` in config_factories.py:234-284
- Traced call sites in stage_a_utils.py:276,525,619
- Located BeamConfig dataclass default in src/nanobrag-torch/src/nanobrag_torch/config.py:33

## Changes Made

### Phase C.7: Revert Debug Instrumentation
**Status**: No changes needed (debug code already clean)
- Verified no DIAG-NANOBRAGG-OVERSAMPLE-001 markers in simulator.py
- nanobrag_torch working tree clean

### Phase C.8: Rebuild & Test
**Rebuild**: Executed per input.md Task C.7
```bash
cd src/nanobrag-torch
pip install -e . --no-deps
```
- Exit code: 0
- Log: plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-02T214000Z/nanobragg_rebuild_clean.log

**Test execution**: Ran DB-AT-028/029 per input.md Task C.8

**Test results**: **Scenario B** (tests FAILED with zero simulator output)
- DB-AT-028: SKIPPED (fixture issue)
- DB-AT-029: FAILED — "No valid ROI correlations computed for bragg_before"
- Debug output shows zero simulator output

### Phase C.9: Beam Flux Investigation (Triggered by Scenario B)

**Root cause identified**: BeamConfig defaults to flux=0.0 when not explicitly set

**Call chain analysis**:
1. BeamConfig dataclass (src/nanobrag-torch/src/nanobrag_torch/config.py:33): flux: float = 0.0
2. create_beam_config() (dbex/refinement/config_factories.py:234-284): When flux=None, field NOT added to beam_kwargs
3. Call sites in stage_a_utils.py: Line 276 (warm), Lines 525/619 (cold paths)

**Why this causes zero output**: simulator_output = structure_factors × flux × ... = structure_factors × 0.0 = 0.0

**Comprehensive investigation**: Documented in beam_flux_investigation.md

## Tests and Static Checks

### Tests Executed
- DB-AT-028: SKIPPED
- DB-AT-029: FAILED (zero output)
- Runtime: 28.13s

Zero simulator output confirmed: bragg_panel[0] mean = 0.0, bragg_full mean = 0.0

## Docs & Ledgers Updates

### fix_plan.md
- Added 2025-12-02T214000Z entry to DIAG-NANOBRAGG-OVERSAMPLE-001 Attempts History
- Status: blocked_beam_flux_default
- Next actions: Apply BeamConfig flux=1.0 fix

### findings.md
- Added DIAG-FLUX-001 entry with full root cause analysis
- Fix recommendation: Change BeamConfig default from flux=0.0 to flux=1.0

### Artifacts Created
1. pytest_db_at_028_029_clean.log
2. beam_flux_investigation.md
3. nanobragg_rebuild_clean.log
4. summary.md

## Next Steps

### Recommended Next Action
Apply 1-line fix to BeamConfig default: flux: float = 1.0

**Implementation plan**:
1. Apply fix to BeamConfig dataclass
2. Rebuild nanobrag_torch with --no-deps
3. Rerun DB-AT-028/029 validation tests
4. If tests PASS → mark DIAG-NANOBRAGG-OVERSAMPLE-001 done
5. Unblock ARCH-SIM-CONSTRUCTION-001

### Root Cause Notes for Supervisor
**Double root cause discovered**:
1. Oversample=3 fix (Phase C.1-C.6): Already implemented
2. Beam flux=0.0 default (Phase C.7-C.8): NEW root cause discovered this loop

Both fixes required for DIAG-NANOBRAGG-OVERSAMPLE-001 completion.

---

### Turn Summary
Validated DIAG-NANOBRAGG-OVERSAMPLE-001 Phase C.7-C.8 with clean nanobrag_torch rebuild and DB-AT-028/029 test run; tests FAILED with zero simulator output (Scenario B).
Root cause identified: BeamConfig defaults to flux=0.0 when not explicitly set, causing simulator output = structure_factors × 0.0 = 0.0; comprehensive investigation traced call chain and documented fix options (preferred: change BeamConfig default to flux=1.0), updated fix_plan.md + findings.md with DIAG-FLUX-001.
Next: Apply 1-line BeamConfig flux=1.0 fix, rebuild, rerun tests → expect PASS and mark DIAG-NANOBRAGG-OVERSAMPLE-001 done.
Artifacts: plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-02T214000Z/ (pytest_db_at_028_029_clean.log, beam_flux_investigation.md, nanobragg_rebuild_clean.log, summary.md)
