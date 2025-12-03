# Input for Ralph (Loop 2025-12-02T214000Z)

## Summary
Investigate beam flux defaults and validate DIAG-NANOBRAGG-OVERSAMPLE-001 fix with clean test run.

## Mode
none (evidence collection + validation)

## InitiativeType
diagnostics

## Focus
DIAG-NANOBRAGG-OVERSAMPLE-001 — nanobrag_torch Oversample Parameter Investigation (Phase C.7-C.8: Clean Validation)

## Branch
integration

## Mapped tests
- `tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity` (validates non-zero simulator output, chi²/pixel initial ≤ 1e2)
- `tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity` (validates ROI correlation before ≥ 0.2)

## Artifacts
`plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-02T214000Z/`
- `pytest_db_at_028_029_clean.log` (test results without debug instrumentation)
- `beam_flux_investigation.md` (beam config source code analysis)
- `summary.md` (loop summary and findings)

## Do Now

**Context**: Ralph's Phase D diagnostic probe (ARCH-SIM-CONSTRUCTION-001) found beam flux=0.0 as likely cause of zero simulator output. DIAG-NANOBRAGG-OVERSAMPLE-001 Phase C successfully threaded oversample=3 through all 292 DetectorConfig instances, but the tests were SKIPPED due to missing fixture data. Need to:
1. Complete DIAG Phase C validation (C.7: remove debug instrumentation, C.8: clean test run)
2. Investigate beam flux defaults if tests still fail

### Task C.7: Remove nanobrag_torch debug instrumentation

**Command**:
```bash
cd /home/ollie/Documents/diffbragg_example/src/nanobrag-torch

# Revert the debug patch
git checkout src/nanobrag_torch/simulator.py

# Rebuild
pip install -e . --no-deps > ../../plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-02T214000Z/nanobragg_rebuild_clean.log 2>&1
```

**Expected**: Clean nanobrag_torch without debug prints

### Task C.8: Run clean validation tests

**Command**:
```bash
cd /home/ollie/Documents/diffbragg_example

mkdir -p plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-02T214000Z

AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=metadata \
DBEX_SMOKE_DETECTOR_SIZE=full \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv \
  tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity \
  tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity \
  > plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-02T214000Z/pytest_db_at_028_029_clean.log 2>&1

echo "Exit code: $?" >> plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-02T214000Z/pytest_db_at_028_029_clean.log
```

**Expected outcomes**:

**Scenario A (DIAG fix successful)**: Tests PASS
- chi²/pixel initial ≤ 1e2
- ROI correlation before ≥ 0.2
- bragg_after magnitude ~0.24 (matches bragg_before)
→ Mark DIAG-NANOBRAGG-OVERSAMPLE-001 **done**, unblock ARCH-SIM-CONSTRUCTION-001

**Scenario B (Tests still fail with zero output)**: Tests FAIL
- bragg_after still 1.025e-05 or 0.0
- Ralph's hypothesis confirmed: beam flux=0.0 causes zero output
→ Proceed to Task C.9 (beam flux investigation)

**Scenario C (Tests SKIPPED)**: Missing fixture data
- Document the skip reason
- Attempt to locate or generate missing data, or adjust test strategy

### Task C.9: Beam flux investigation (Conditional - only if Scenario B)

**Only execute if tests FAIL in Task C.8 due to zero/low simulator output.**

**Read source code**:
```bash
grep -n "flux" /home/ollie/Documents/diffbragg_example/dbex/refinement/config_factories.py | head -20
```

**Analysis questions**:
1. Where is beam flux sourced from in `create_beam_config()`?
2. What is the default value when `beam_flux=None`?
3. Should flux default to 1.0 (dimensionless scale) or to a physical value from beam metadata?

**Create analysis document**:

File: `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-02T214000Z/beam_flux_investigation.md`

Template:
```markdown
# Beam Flux Investigation

## Scenario B Trigger
Tests failed in Task C.8 with zero/low simulator output despite oversample=3 fix.

## Source Code Analysis

### create_beam_config() Implementation
[Paste relevant code from config_factories.py]

### Default Flux Handling
**When beam_flux=None**:
- Current behavior: [describe]
- Source location: config_factories.py line [X]

### Upstream Callers
**Where is create_beam_config() called**:
1. `dbex/refinement/stage_a_utils.py` line [X]: passes `beam_flux=...`
2. `dbex/refinement/reconstruction.py` line [X]: passes `beam_flux=...`
3. [other call sites]

**What values are passed**:
- Stage A: [value/expression]
- Reconstruction: [value/expression]

## Root Cause Hypothesis

**If flux defaults to 0.0**:
- Simulator output = structure_factors × 0.0 × ... = 0.0
- Fix: Change default to 1.0 or extract from beam.get_flux() if available

**If flux is sourced incorrectly**:
- Check if calibration_metadata.beam_flux exists and is threaded correctly

## Recommended Fix

[Specific code change needed in config_factories.py]

## Next Steps

[Implementation plan or escalation path]
```

### Task C.10: Write summary

**File**: `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-02T214000Z/summary.md`

**Content**:
- Clean test outcome (PASS/FAIL/SKIP)
- If PASS: Celebrate! DIAG-NANOBRAGG-OVERSAMPLE-001 complete, oversample fix validated
- If FAIL: Beam flux investigation findings and recommended next action
- If SKIP: Document blocker and path forward

## How-To Map

### Rebuild Commands
```bash
# Navigate to nanobrag-torch source
cd /home/ollie/Documents/diffbragg_example/src/nanobrag-torch

# Revert debug patch
git checkout src/nanobrag_torch/simulator.py

# Rebuild (--no-deps to avoid environment changes)
pip install -e . --no-deps
```

### Test Execution
Per `docs/TESTING_GUIDE.md` §2.2, use the exact selectors and environment flags shown in Task C.8.

### Beam Flux Source Code Locations
- Config factory: `dbex/refinement/config_factories.py::create_beam_config` (lines ~89-125)
- Stage A caller: `dbex/refinement/stage_a_utils.py::_build_stage_a_context` (line ~267)
- Reconstruction caller: `dbex/refinement/reconstruction.py::build_final_bragg_from_stage_a_telemetry` (line ~187)

## Pitfalls To Avoid

1. **Do NOT skip the clean rebuild (Task C.7)** - debug instrumentation must be removed for clean test
2. **Do NOT modify test fixtures** - if tests SKIP, document the blocker rather than patching data
3. **Do NOT proceed to Task C.9 if tests PASS** - beam flux investigation only needed for Scenario B
4. **Do NOT install new packages** - use `pip install -e . --no-deps` to preserve environment
5. **Do NOT change acceptance criteria** - if tests fail, investigate root cause (flux issue), don't weaken gates

## If Blocked

**If rebuild fails**:
- Capture full error in rebuild log
- Document blocker in summary.md
- Do not proceed to test run

**If tests SKIP**:
- Document the exact skip reason from pytest output
- Check if fixture data can be located (look in `sp.proc/`, `refGeom_small/`)
- If data truly missing, may need to generate it or adjust test strategy

**If tests FAIL with non-zero output**:
- May indicate a different issue than beam flux
- Capture metrics and document in summary.md
- Do not proceed to Task C.9 unless output is zero/near-zero

## Findings Applied

- **DIAG-OVERSAMPLE-001**: Phase C complete (292/292 configs have oversample=3)
- **RALPH-DIAG-FLUX-001** (new, from Phase D probe): Beam flux=0.0 likely causes zero simulator output

## Pointers

- DIAG-NANOBRAGG-OVERSAMPLE-001 implementation plan: `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/implementation.md`
- Phase C planning notes: `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T050000Z/phase_c_planning.md`
- Ralph's flux finding: `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-02T224500Z/zero_output_analysis.md`
- Beam config spec: `docs/spec-db-core.md` §25-30 (beam configuration contracts)

## Next Up

**If tests PASS**: Mark DIAG-NANOBRAGG-OVERSAMPLE-001 done, update problems.md, prepare to unblock ARCH-SIM-CONSTRUCTION-001

**If tests FAIL (zero output)**: Implement beam flux fix (likely a simple default value change in config_factories.py)

**If tests SKIP**: Resolve fixture blocker or adjust test strategy (may need to generate sp.proc data)
