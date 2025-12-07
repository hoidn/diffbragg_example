# MAP-SCALE-003 Phase B — CLI Telemetry Verification & Test Assertions

## Summary
Verify CLI plumbing correctly populates structure-factor telemetry (`hkl_source`, `hkl_path`) and extend test assertions to validate HDF5 serialization (test_torch_diagnostics_metadata) and diagnostics dict persistence (test_db_at_024_mapping_smoke).

## Metadata
- **Mode**: none
- **ActionType**: implementation_ready
- **DecisionStatus**: patch_ready
- **InitiativeType**: feature
- **Focus**: MAP-SCALE-SYNC-001 — Calibration Ladder Synchronization (member plan: MAP-SCALE-003)
- **Branch**: integration
- **Mapped tests**:
  - `tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata`
  - `tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke`
- **Artifacts**: `plans/active/MAP-SCALE-003/reports/2025-12-07T180000Z/`

## Findings Applied (Mandatory)
- **SCALE-003**: Zero-iteration helper must ingest refined |F| amplitudes — ✓ Planning traced MTZ loading path; Phase B verifies CLI threading
- **SCALE-004**: CLI plumbing must propagate refined MTZ path — ✓ Planning identified --refined-mtz arg; Phase B validates hkl_path population
- **SCALE-006**: Telemetry must capture calibration metadata provenance — ✓ Schema defined (hkl_source, hkl_n_reflections, hkl_mean_amplitude); Phase B adds test assertions
- **SCALE-007**: Silent fallback from refined to raw violates spec — ✓ Deferred enforcement to MAP-SCALE-005; Phase B asserts hkl_source="refined" in DB-AT-024
- **TESTING-003**: Selector status transitions require pytest --collect-only confirmation — ✓ Phase B includes collect-only logs in artifacts

## ARCH Contracts (mandatory)
### ARCH-CONTRACT-WRITER-001 (Torch Diagnostics Persistence)
- **Owner module**: `dbex/io/writer.py::write_torch_outputs` (lines 41-54, 196-200)
- **Pointer**: `docs/architecture/dbex/io/writer.idl.md:55-85`
- **Failure classification**: Implementation bug (verifying HDF5 attrs match schema)
- **Contract**: Writer SHALL serialize hkl_telemetry dict to /torch_diagnostics HDF5 group attrs (hkl_source, hkl_n_reflections, hkl_mean_amplitude, hkl_path); backward compatibility required (additive-only extension)

### ARCH-CONTRACT-STRUCTURE-FACTORS-001 (Refined MTZ Ingestion)
- **Owner module**: `dbex/nanobrag_bridge.py::simulate_forward_once` (line 1230)
- **Pointer**: `docs/config_crosswalk.md:15-72`, `docs/spec-db-workflow.md:125-158`
- **Failure classification**: Implementation bug (verifying telemetry dict construction)
- **Contract**: Bridge SHALL construct hkl_telemetry dict from function params (hkl_source, hkl_path) + computed stats (len(hkl_indices), np.mean(hkl_amplitudes)) and include it in diagnostics dict returned to CLI

### ARCH-CONTRACT-CALIBRATION-001 (Calibration Metadata Threading)
- **Owner module**: `dbex/refine_one.py::run_nanobrag_backend` (lines 162-248)
- **Pointer**: `docs/architecture/calibration_scaling.md:45-78`
- **Failure classification**: Implementation bug (verifying hkl_source/hkl_path propagation from CLI args)
- **Contract**: CLI backend SHALL populate hkl_source based on --refined-mtz vs --mtzFile precedence and forward hkl_path (absolute MTZ path) to bridge/writer

## Do Now (hard validity contract)

**Objective**: Implement MAP-SCALE-003 Phase B (CLI plumbing verification + test assertions)

### Task 1: Verify CLI Plumbing (Read + Document)
**File**: `dbex/refine_one.py`
1. **Implement**: Read `dbex/refine_one.py` (focus: run_nanobrag_backend function, lines 162-300)
2. Locate where `--refined-mtz` argument is consumed and how `hkl_source`/`hkl_path` are set
3. Trace data flow: CLI args → `simulate_forward_once` → `write_torch_outputs`
4. Document file:line anchors in `plans/active/MAP-SCALE-003/reports/2025-12-07T180000Z/cli_plumbing_verification.md`:
   - Where `hkl_source` is set (expected: "refined" if --refined-mtz provided, else "raw")
   - Where `hkl_path` is set (expected: absolute path from --refined-mtz or --mtzFile)
   - Where telemetry dict is passed to writer
5. Validation: Confirm CLI correctly threads telemetry to writer OR identify gap requiring code fix

### Task 2: Extend test_torch_diagnostics_metadata Assertions (Edit + Run)
**File**: `tests/dbex/test_refine_one_cli.py`
1. **Implement**: Read lines 913-1100 (test_torch_diagnostics_metadata function)
2. Locate existing HDF5 attr assertions (after line 1020)
3. Add 4 new assertions after existing diagnostics attrs (check mock hkl_telemetry dict values from lines 959-965 first to get correct expected values)
4. Run test: `pytest tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata -v`
5. Capture pytest log to `plans/active/MAP-SCALE-003/reports/2025-12-07T180000Z/pytest_diagnostics_metadata.log`

### Task 3: Extend test_db_at_024_mapping_smoke Assertions (Edit + Run)
**File**: `tests/dbex/test_mapping_consistency.py`
1. **Implement**: Read lines 188-400 (TestDB_AT_024_Mapping class + test_db_at_024_mapping_smoke function)
2. Locate diagnostics dict assertions (search for `assert "` in diagnostics context)
3. Add hkl_telemetry assertions after existing diagnostics checks
4. Run test: `pytest tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke -v`
5. Capture pytest log to `plans/active/MAP-SCALE-003/reports/2025-12-07T180000Z/pytest_db_at_024.log`

### Task 4: Regression Guard (Run)
**Objective**: Confirm no test discovery breakage from assertion additions
1. Run collect-only for both modified tests and capture logs

### Task 5: Write Summary & Update Plan
**Objective**: Document Phase B completion
1. Create summary.md with all task findings
2. Update implementation.md with Phase B completion status

## Forbidden This Loop
- **No new probes**: Phase B is test validation only; instrumentation out of scope
- **No plan-local diagnostic scripts**: All work in production test files
- **Do not modify writer/bridge code unless Task 1 reveals missing telemetry construction** (unlikely per Phase A findings)

## How-To Map
### Environment
```bash
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1
export DBEX_SMOKE_SIGMA_SOURCE=metadata
export DBEX_SMOKE_DETECTOR_SIZE=full
```

### Test Execution Commands
```bash
# Create reports directory
mkdir -p plans/active/MAP-SCALE-003/reports/2025-12-07T180000Z/

# Task 2: test_torch_diagnostics_metadata
pytest tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata -v > plans/active/MAP-SCALE-003/reports/2025-12-07T180000Z/pytest_diagnostics_metadata.log 2>&1

# Task 3: test_db_at_024_mapping_smoke
pytest tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke -v > plans/active/MAP-SCALE-003/reports/2025-12-07T180000Z/pytest_db_at_024.log 2>&1

# Task 4: Collect-only regression guard
pytest tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata --collect-only > plans/active/MAP-SCALE-003/reports/2025-12-07T180000Z/collect_diagnostics_metadata.log 2>&1
pytest tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke --collect-only > plans/active/MAP-SCALE-003/reports/2025-12-07T180000Z/collect_db_at_024.log 2>&1
```

### Artifact Destinations
All artifacts under: `plans/active/MAP-SCALE-003/reports/2025-12-07T180000Z/`
- `cli_plumbing_verification.md` (Task 1 file:line anchors)
- `pytest_diagnostics_metadata.log` (Task 2 test run)
- `pytest_db_at_024.log` (Task 3 test run)
- `collect_diagnostics_metadata.log` (Task 4 regression guard)
- `collect_db_at_024.log` (Task 4 regression guard)
- `summary.md` (Task 5 turn summary)

## Pitfalls To Avoid
1. **Type discipline**: This is a `feature` initiative (exposing telemetry schema), not `spec_change` — do not alter normative behavior, only add observability
2. **No stacking**: If Task 2/3 tests FAIL due to missing telemetry dict construction (not assertion bugs), STOP and document the gap in summary.md; next loop will fix bridge code
3. **Shadow-pipeline guard**: No plan-local scripts — all work in production test files per PROBE-FREEZE-001
4. **Evidence→Action**: Task 1 MUST end with file:line anchors OR explicit "gap identified at X" note; do not leave CLI plumbing status ambiguous
5. **Findings paydown**: All SCALE findings (003/004/006/007) addressed via schema + test assertions per Phase A planning
6. **ARCH consistency**: Writer schema already correct (Phase A audit confirmed); only validate data flow CLI → bridge → writer
7. **Environment freeze**: Do not install/upgrade packages; tests use existing fixtures

## If Blocked
- **Task 1 reveals missing CLI plumbing**: Document gap in cli_plumbing_verification.md, write summary.md noting "implementation_required", mark Phase B incomplete, next loop fixes bridge code
- **Task 2/3 tests FAIL due to assertion errors (not missing data)**: Adjust expected values based on actual fixture schema, re-run tests
- **Task 2/3 tests FAIL due to missing hkl_telemetry dict**: Document in summary.md, mark Phase B blocked, next loop adds telemetry construction to bridge
- **Task 4 collect-only errors**: Fix test syntax errors, re-run collect-only

## Doc Sync Plan (Conditional)
**Not required for Phase B** (no new test files authored; only assertion additions to existing tests)

**If tests PASS**: Phase C will update TESTING_GUIDE.md + TEST_SUITE_INDEX.md to document hkl_telemetry fields
