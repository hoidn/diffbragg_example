# MAP-SCALE-002 Documentation & Test Registry Sync

**Timestamp**: 2025-11-05T030000Z
**Focus**: CLI calibration parity for nanobrag backend
**Initiative**: MAP-SCALE-002

## Summary

Completed regression + doc sync for nanobrag CLI calibration metadata. Extended CLI test suite with calibration-positive test asserting `--torch-config`/`--refined-mtz` workflow compliance per SCALE-006 guardrail. Updated TESTING_GUIDE and TEST_SUITE_INDEX to document new CLI flag guidance and artifact expectations for DB_AT_024 selector.

## Changes Made

### 1. New Test Authored

**File**: `tests/dbex/test_refine_one_cli.py`
**Test**: `test_nanobrag_backend_applies_calibration`
**Lines**: 207-345
**Purpose**: Validates calibration-positive CLI path where `--torch-config` triggers:
  1. `load_calibration_metadata()` invoked with provided path
  2. `create_beam_config()` receives flux/exposure/beamsize overrides
  3. `create_crystal_config()` receives N_cells with apply_n_cells=True
  4. `Simulator` constructed with beam_config when calibration present

**Assertions**:
- `load_calibration_metadata` called once with config path
- `create_beam_config` called with flux=1e12, exposure=1.0, beamsize_mm=1.0
- `create_crystal_config` called with N_cells=[36,28,26], apply_n_cells=True
- `Simulator` constructed with beam_config kwarg

**Test Status**: PASSED (2.10s)

### 2. Documentation Updates

#### TESTING_GUIDE.md

**File**: `docs/TESTING_GUIDE.md`
**Section**: §2.1 Active Implementation Coverage
**Line**: 86
**Changes**:
- Extended CLI backend flag entry to document calibration-positive test
- Added details on `--torch-config`/`--refined-mtz` workflow per SCALE-006
- Updated collection log reference to 2025-11-05T030000Z (7 tests)
- Added SCALE-006 to finding refs

**New Content**:
```markdown
Includes calibration-positive test (test_nanobrag_backend_applies_calibration) validating
`--torch-config`/`--refined-mtz` workflow per SCALE-006: load_calibration_metadata invoked,
beam_config receives flux/exposure/beamsize overrides, crystal_config receives N_cells with
apply_n_cells=True, Simulator constructed with beam_config when calibration present.
```

#### TEST_SUITE_INDEX.md

**File**: `docs/development/TEST_SUITE_INDEX.md`
**Section**: Implementation Coverage (Active)
**Line**: 12
**Changes**: Mirrored TESTING_GUIDE updates for registry synchronization

## Test Results

### CLI Calibration Test

**Command**:
```bash
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
pytest -v tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_applies_calibration --maxfail=1 -q
```

**Result**: 1 passed in 2.10s
**Log**: `pytest_cli_calibrated.log`

### DB_AT_024 Collection

**Command**:
```bash
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1
export DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-002/reports/2025-11-05T030000Z
pytest --collect-only tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke
```

**Result**: 1 test collected
**Log**: `collect_db_at_024.log`

### DB_AT_024 Execution

**Command**:
```bash
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1
export DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-002/reports/2025-11-05T030000Z
pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke --maxfail=1
```

**Result**: 1 passed in 29.58s
**Log**: `pytest_db_at_024.log`

### Full Test Suite

**Command**:
```bash
export KMP_DUPLICATE_LIB_OK=TRUE
pytest -v tests/
```

**Results**:
- **Collected**: 70 tests
- **Passed**: 65 tests (including new calibration test)
- **Skipped**: 3 tests (DB_AT_024 skipped without artifact dir in full run)
- **Failed**: 2 tests (pre-existing gradient tests: `test_db_at_010_gradcheck_crystal_cell_a`, `test_db_at_010_gradcheck`)
- **Runtime**: 344.89s (5m44s)

**Log**: `pytest_full_suite.log`

**Note**: The 2 gradient test failures are pre-existing issues noted in `input.md` as unrelated to this change. The new `test_nanobrag_backend_applies_calibration` test passed successfully.

## Artifacts

All artifacts captured under:
```
plans/active/MAP-SCALE-002/reports/2025-11-05T030000Z/
├── pytest_cli_calibrated.log
├── collect_db_at_024.log
├── pytest_db_at_024.log
├── pytest_full_suite.log
└── doc_updates.md (this file)
```

## Finding References

- **SCALE-006**: Nanobrag CLI must forward DiffBragg calibration metadata (flux/exposure/beamsize/N_cells) to config builders and Simulator
- **SCALE-005**: Sample clipping engages only when N_cells + beam_config flow together
- **TESTING-003**: Selector status transitions require `pytest --collect-only` confirmation

## Exit Criteria Status

### MAP-SCALE-002 Exit Criteria

1. ✅ **CLI parser accepts calibration metadata** — Already implemented in prior loop (2025-11-05T000500Z)
2. ✅ **CLI backend loads and applies calibration** — Already implemented in prior loop (2025-11-05T000500Z)
3. ✅ **Regression coverage + doc sync** — **This loop**:
   - New test `test_nanobrag_backend_applies_calibration` authored and passing
   - TESTING_GUIDE.md updated with CLI calibration workflow guidance
   - TEST_SUITE_INDEX.md synchronized
   - DB_AT_024 collect-only + execution logs captured
   - Full test suite validated (no new regressions)

All exit criteria satisfied. MAP-SCALE-002 complete pending fix_plan ledger update.

## Summary Lines

- **Tests added**: 1 (`test_nanobrag_backend_applies_calibration`)
- **Tests passing**: 65/68 (2 pre-existing gradient failures)
- **Docs updated**: 2 (TESTING_GUIDE.md, TEST_SUITE_INDEX.md)
- **Collection logs**: 1 (DB_AT_024)
- **Test logs**: 3 (CLI, DB_AT_024, full suite)
- **Lines of code changed**: ~140 (new test ~138 lines, doc updates ~2 lines)
