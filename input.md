# Input for Ralph — Loop 2025-12-02T230000Z

## Summary
Apply BeamConfig flux=1.0 default fix to resolve zero simulator output, completing DIAG-NANOBRAGG-OVERSAMPLE-001.

## Mode
none (environment patch only, no production code changes)

## InitiativeType
diagnostics

## Focus
DIAG-NANOBRAGG-OVERSAMPLE-001 — nanobrag_torch Oversample Parameter Investigation (Phase C.9: Beam Flux Fix)

## Branch
integration

## Mapped tests
- tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity
- tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity

## Artifacts
`plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-02T230000Z/`

## Do Now

**Context**: Phase C.7-C.8 validation revealed second root cause: BeamConfig defaults to `flux=0.0`, causing all simulator output to be zero (bragg_panel mean=0.0, bragg_full mean=0.0). Ralph's investigation identified Option A (change BeamConfig default to 1.0) as simplest fix aligning with physics convention.

**Implement: Phase C.9 — Apply BeamConfig flux=1.0 default fix**

### Task C.9.1: Apply 1-line fix to BeamConfig dataclass
- File: `src/nanobrag-torch/src/nanobrag_torch/config.py`
- Line: ~33 (in BeamConfig dataclass)
- Change:
  ```python
  # OLD:
  flux: float = 0.0  # Photons per second

  # NEW:
  flux: float = 1.0  # Photons per second (1.0 = neutral dimensionless scale when unknown)
  ```
- Rationale: When flux is not explicitly set (no calibration metadata or cold paths), default to neutral scale factor 1.0 instead of 0.0 which zeros all output

### Task C.9.2: Create patch file
- Save the change as a git diff:
  ```bash
  cd src/nanobrag-torch
  git diff src/nanobrag_torch/config.py > ../../plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/patches/beam_flux_default_fix.patch
  ```
- Document the patch in artifacts

### Task C.9.3: Rebuild nanobrag_torch
- Execute clean rebuild:
  ```bash
  cd src/nanobrag-torch
  pip install -e . --no-deps
  ```
- Capture output to `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-02T230000Z/nanobragg_rebuild_flux_fix.log`
- Verify exit code 0

### Task C.9.4: Run validation tests
- Execute DB-AT-028/029 with clean build:
  ```bash
  AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
  DBEX_SMOKE_SIGMA_SOURCE=metadata \
  DBEX_SMOKE_DETECTOR_SIZE=full \
  KMP_DUPLICATE_LIB_OK=TRUE \
  NANOBRAGG_DISABLE_COMPILE=1 \
  pytest -vv tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity 2>&1 | tee plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-02T230000Z/pytest_db_at_028_029_flux_fix.log
  ```
- **Expected outcome**: Both tests PASS
  - bragg_before mean > 0 (non-zero simulator output)
  - bragg_after mean > 0 (non-zero refined output)
  - DB-AT-028: chi²/pixel initial ≤ 1e2
  - DB-AT-029: median ROI correlation before ≥ 0.2

### Task C.9.5: Update docs/findings.md
- Add entry for DIAG-FLUX-001:
  ```markdown
  - **DIAG-FLUX-001** (BeamConfig Flux Default): BeamConfig dataclass in nanobrag_torch defaulted to `flux=0.0`, causing zero simulator output when flux not explicitly set. Changed default to `flux=1.0` (neutral dimensionless scale) per physics convention. Affects warm path (no calibration metadata) and cold paths (stage_a_utils.py:525,619). Fix: 1-line change in `src/nanobrag-torch/src/nanobrag_torch/config.py:33`. Validation: DB-AT-028/029 PASS. Related: DIAG-NANOBRAGG-OVERSAMPLE-001 Phase C.9.
  ```

### Task C.9.6: Update docs/fix_plan.md
- Add attempt to DIAG-NANOBRAGG-OVERSAMPLE-001 Attempts History:
  ```markdown
  * 2025-12-02T230000Z (Phase C.9 complete) — Applied BeamConfig flux=1.0 default fix per beam_flux_investigation.md Option A recommendation. Changed `src/nanobrag-torch/src/nanobrag_torch/config.py:33` from `flux: float = 0.0` to `flux: float = 1.0` (neutral dimensionless scale when flux not explicitly set). Created patch file at `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/patches/beam_flux_default_fix.patch`. Rebuilt nanobrag_torch with clean build. Tests: DB-AT-028 PASSED (chi²/pixel initial ≤ 1e2), DB-AT-029 PASSED (median ROI correlation before ≥ 0.2). Simulator now produces non-zero output in all code paths. Double root cause resolution complete: (1) Oversample=3 threading (Phase C.1-C.6), (2) Beam flux=1.0 default (Phase C.9). All DIAG-NANOBRAGG-OVERSAMPLE-001 exit criteria satisfied. Artifacts: `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-02T230000Z/` (patch file, rebuild log, pytest log, summary.md). Status: done. ARCH-SIM-CONSTRUCTION-001 unblocked.
  ```
- Update initiative status line to: `Status: done (2025-12-02T230000Z: Phase C.9 beam flux fix complete, both tests PASS)`

## How-To Map

### Environment Freeze Exception Compliance
This fix complies with CLAUDE.md Environment Freeze exception clause:
- **Scope**: Patch to locally available source (`src/nanobrag-torch/`)
- **Requirement 1**: Patch file saved to `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/patches/beam_flux_default_fix.patch`
- **Requirement 2**: Rebuild commands documented in artifacts/nanobragg_rebuild_flux_fix.log
- **Requirement 3**: Tests validate fix resolves blocking issue (DB-AT-028/029 PASS)
- **Requirement 4**: Update docs/findings.md with DIAG-FLUX-001
- **Requirement 5**: Environment state tagged "nanobragg-flux-fix-2025-12-02"

### File Operations
1. Edit `src/nanobrag-torch/src/nanobrag_torch/config.py` line ~33
2. Create patch: `cd src/nanobrag-torch && git diff src/nanobrag_torch/config.py > ../../plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/patches/beam_flux_default_fix.patch`
3. Rebuild: `cd src/nanobrag-torch && pip install -e . --no-deps | tee ../../plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-02T230000Z/nanobragg_rebuild_flux_fix.log`
4. Test: Run pytest with environment flags as specified above

### Expected Metrics
- **Before**: bragg_before mean=0.0, bragg_after mean=0.0, chi²=1.084e+05
- **After**: bragg_before mean>0, bragg_after mean>0, chi²/pixel ≤ 1e2

## Pitfalls To Avoid

1. **Do not modify production dbex code** — This is an environment patch only (nanobrag_torch source)
2. **Do not skip patch file creation** — Required per Environment Freeze exception clause
3. **Do not skip rebuild** — The change must be rebuilt into the installed package
4. **Use `--no-deps`** — Avoid triggering environment changes during rebuild
5. **Capture all logs** — Rebuild and test logs must be saved to artifacts directory
6. **Verify test PASS** — Both DB-AT-028 and DB-AT-029 must pass, not just run
7. **Non-zero output validation** — Confirm bragg_before/bragg_after are non-zero in test output
8. **Update both ledgers** — docs/findings.md AND docs/fix_plan.md must be updated

## If Blocked

**Scenario A: Rebuild fails**
- Check pip install output for dependency conflicts
- Verify src/nanobrag-torch directory has no uncommitted breaking changes
- Escalate to supervisor with rebuild log

**Scenario B: Tests still fail**
- Capture metrics from test output (bragg_before/after means, chi²)
- Check if fix was actually applied (verify config.py has flux=1.0)
- Escalate to supervisor with test log and metrics analysis

**Scenario C: Tests pass but outputs still zero**
- Verify flux value in test diagnostics (should be 1.0, not 0.0)
- Check if old installed package is still being used
- Escalate to supervisor with diagnostic evidence

## Findings Applied

**Mandatory**:
- **DIAG-FLUX-001** (this loop creates it): BeamConfig flux default causes zero output
- **SCALE-004**: Post-run scaling patterns (reference for understanding flux behavior)
- **ARCH-BRIDGE-RESP-001 Phase C.6**: Config factory locations (understand create_beam_config behavior)

## Pointers

**Specs**:
- docs/spec-db-core.md §§20-40: Detector/beam configuration contracts
- docs/spec-db-conformance.md:276-318: DB-AT-028 acceptance test
- docs/spec-db-conformance.md:319-366: DB-AT-029 acceptance test

**Implementation**:
- src/nanobrag-torch/src/nanobrag_torch/config.py:33: BeamConfig dataclass (TARGET FILE)
- dbex/refinement/config_factories.py:234-284: create_beam_config() function (context)
- dbex/refinement/stage_a_utils.py:276,525,619: Call sites (context)

**Plans**:
- plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/implementation.md: Initiative plan
- plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-02T214000Z/beam_flux_investigation.md: Root cause analysis
- plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-02T214000Z/summary.md: Phase C.7-C.8 findings

**Tests**:
- docs/TESTING_GUIDE.md §2.4: Stage A Smoke Parity selectors
- tests/dbex/test_stage_a_smoke_parity.py: Fixture and tests

## Next Up

After this loop completes successfully:
1. Mark DIAG-NANOBRAGG-OVERSAMPLE-001 as **done**
2. Unblock ARCH-SIM-CONSTRUCTION-001 (remove blocked_environment_dependency status)
3. Resume ARCH-REFACTOR-001 Phase D.3 (reconstruction baseline logic migration)

## Doc Sync Plan

Not applicable (no test additions/renames this loop).
