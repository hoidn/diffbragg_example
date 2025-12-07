# Input for Ralph (Loop i=125)

## Summary
Validate PHYSICS-LOSS-001 initiative closure: all phases A-I are checked complete; verify exit criteria, run mapped acceptance tests, and prepare closure summary or identify blocking work.

## Mode
none

## ActionType
review_or_housekeeping

## DecisionStatus
validated

## InitiativeType
bugfix

## Focus
[PHYSICS-LOSS-001] — Variance-Weighted Loss Parity and Telemetry

## Branch
integration

## Mapped tests
```bash
# Core acceptance tests from implementation.md exit criteria
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip
pytest -vv tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke
pytest -vv tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata
pytest -vv tests/sp_proc/test_sigma_metadata_fixture.py
```

## Artifacts
plans/active/PHYSICS-LOSS-001/reports/2025-12-07T060000Z/

## Findings Applied (Mandatory)
- **PHYSICS-LOSS-001** (variance-weighted loss spec): All phases A-I delivered per implementation.md checklist.
- **PHYSICS-LOSS-002** (sigma-floor enforcement): Implemented in Phase D/E; telemetry provenance tracked.
- **PHYSICS-LOSS-003** (sigma-map ingestion): Phases E-I cover CLI/metadata/external_lookup paths.
- **PHYSICS-LOSS-004** (DIALS external_lookup harvest): Phases F-I deliver metadata integration.
- **PHYSICS-LOSS-005** (telemetry chi-squared/masked_mse dual reporting): Phase D canonical alignment complete.
- **SCALE-001** (calibration precedence): Phases align with spot-scale/N_cells/beam-flux requirements.
- **SCALE-002** (spot-scale override threading): Metadata propagation validated Phases G-I.

## Pointers
- Spec: `docs/spec-db-core.md:57-68` (variance-weighted loss function)
- Architecture: `docs/architecture/calibration_scaling.md` (sigma/scale/MTZ threading)
- Testing: `docs/TESTING_GUIDE.md:§1.4` (sigma-map workflow), `docs/development/TEST_SUITE_INDEX.md`
- Implementation: `plans/active/PHYSICS-LOSS-001/implementation.md` (all phases A-I complete)
- Findings: `docs/findings.md` (PHYSICS-LOSS-001—005, SCALE-001/002)

## ARCH Contracts (mandatory)
**Relevant Contracts:**
1. **ARCH-CONTRACT-LOSS-001** (Variance-weighted loss API)
   - Owner: `dbex/physics/loss.py::_compute_variance_weighted_loss` (delivered Phase D)
   - Classification: **implementation bug** (was missing pre-Phase A, now complete)

2. **ARCH-CONTRACT-CALIBRATION-001** (Sigma provenance threading)
   - Owner: `dbex/data_load.py::_load_external_lookup_sigma_map`, `dbex/refinement/config.py::RefinementConfig.sigma_readout_provenance`
   - Classification: **implementation complete** (Phases E-I delivered metadata integration)

3. **ARCH-CONTRACT-TELEMETRY-001** (Chi-squared + masked_mse dual reporting)
   - Owner: `dbex/refinement/telemetry.py::RefinementTelemetry`, `dbex/io/writer.py::_write_torch_outputs`
   - Classification: **implementation complete** (Phase D/I telemetry enforcement validated)

## Do Now (hard validity contract)

**Task:** Validate PHYSICS-LOSS-001 initiative closure readiness

**Closure verification steps:**
1. **Exit Criteria Check:**
   - ✅ Verify all 4 exit criteria from fix_plan.md:378-393 satisfied
   - Review implementation.md Phases A-I completion notes
   - Check for outstanding TODOs/risks in implementation.md or latest reports

2. **Test Validation:**
   - Run mapped acceptance tests (Stage A/B/C smoke + DB-AT-024 + CLI metadata + sigma-metadata fixture)
   - Confirm all tests PASS with no regressions
   - Capture pytest logs + exit codes in artifacts directory

3. **Documentation Sweep:**
   - Verify `docs/TESTING_GUIDE.md` + `docs/development/TEST_SUITE_INDEX.md` reflect Phase I updates
   - Confirm `docs/findings.md` PHYSICS-LOSS-001—005 findings cite implementation artifacts
   - Check `docs/architecture/calibration_scaling.md` documents sigma-map threading

4. **Closure Decision:**
   - If ALL exit criteria met + tests PASS + docs current: prepare initiative_closure_summary.md
   - If blocking issues found: document them in this loop's summary.md and mark PHYSICS-LOSS-001 as `in_progress` with next action

**Artifacts to produce:**
- `plans/active/PHYSICS-LOSS-001/reports/2025-12-07T060000Z/summary.md` (this loop's analysis)
- `plans/active/PHYSICS-LOSS-001/reports/2025-12-07T060000Z/pytest_validation.log` (mapped test run)
- `plans/active/PHYSICS-LOSS-001/reports/2025-12-07T060000Z/closure_checklist.md` (exit criteria verification)
- If ready: `plans/active/PHYSICS-LOSS-001/reports/2025-12-07T060000Z/initiative_closure_summary.md`

**Pytest selectors:**
```bash
# Set env vars per TESTING_GUIDE.md
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
export DBEX_SMOKE_SIGMA_SOURCE=metadata  # Test metadata path per Phase I
export DBEX_SMOKE_DETECTOR_SIZE=full
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1

# Run acceptance battery
pytest -vv \
  tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
  tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
  tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip \
  tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke \
  tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata \
  tests/sp_proc/test_sigma_metadata_fixture.py \
  --tb=short \
  2>&1 | tee plans/active/PHYSICS-LOSS-001/reports/2025-12-07T060000Z/pytest_validation.log
```

## Forbidden This Loop
- No production code changes (review-only loop)
- No new probes or diagnostic scripts
- Do not extend implementation.md phases

## How-To Map
1. Create artifacts directory: `mkdir -p plans/active/PHYSICS-LOSS-001/reports/2025-12-07T060000Z/`
2. Run exit criteria checklist review (compare fix_plan.md:385-393 vs implementation.md)
3. Execute pytest battery with env vars as specified above
4. Review latest implementation.md reports (2025-11-21T083500Z was last timestamp)
5. Prepare closure summary or blocking issues report
6. Update galph_memory.md with closure decision

## Pitfalls To Avoid
- Do not assume closure without running mapped tests
- Verify Phase I doc updates are in place (TESTING_GUIDE/TEST_SUITE_INDEX)
- Check for uncommitted changes or stale fixtures
- Ensure metadata sigma fixture (sp.proc/) is tracked and manifest valid
- Do not mark complete if any exit criterion unmet
- Respect implementation floor: next loop after this review must be implementation OR switch focus

## If Blocked
- If tests fail: document failure signature, mark PHYSICS-LOSS-001 `in_progress`, identify next production fix
- If exit criteria unmet: list missing items explicitly, plan remediation as new phase or separate initiative
- If documentation gaps found: schedule doc-sync loop with specific targets
- If blocked: switch focus to MAP-SCALE-SYNC-001 (next priority Tier 1 roll-up)
