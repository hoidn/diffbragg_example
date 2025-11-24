# ARCH-REFACTOR-001 Phase D D2.3+D2.4 Planning Analysis

**Date:** 2025-11-24T080106Z
**Phase:** D2.3+D2.4 — Test Suite + Documentation
**Status:** Planning

## Objective

Complete Phase D D2 by adding unit/integration tests for the extracted `dbex/tools/stage_a_adam.py` module and creating minimal documentation. Validate that the module can be imported and used programmatically, not just via the CLI.

## Context

**Phase D D2.1+D2.2 ✓ COMPLETE** (2025-11-24T095000Z, commit 7264817):
- Extracted 1849-line CLI into `dbex/tools/stage_a_adam.py` module (1898 lines with docstrings)
- 15 functions extracted (renamed public: `build_dataload`, `setup_environment`, etc.)
- 3 classes: `StageAComponents`, `ForwardModelProbeSummary`, `StageADebugConfig`
- CLI refactored to thin 340-line argparse shim (-1509 lines, -81.6%)
- **CLI smoke test ✅ PASSED** (Phase 1, cpu, seed=42, exit code 0, 92 ROIs)

**Remaining Work:**
- D2.3: Test suite (`tests/dbex/test_stage_a_adam_tooling.py`)
- D2.4: Documentation (README + validation)

## Phase D D2.3: Test Suite Specification

### File: `tests/dbex/test_stage_a_adam_tooling.py`

#### Scope
Create **10 test cases** covering:
1. **Unit tests (4)** — Fast, no fixtures, test dataclasses and utilities
2. **Integration tests (4)** — With mock fixtures, test core workflows
3. **CLI smoke tests (2)** — Validate CLI backward compatibility

#### Test Design Principles
- **Fast execution:** Target <30s total runtime (per D2 planning, avoid golden_data dependency)
- **Mock fixtures:** Use synthetic/tiny data, no real refinement runs
- **Focus on APIs:** Test public interfaces, not internal implementation
- **No regression risk:** Tests should NOT break existing workflows

### Test Cases (10 total)

#### Unit Tests (4)

**1. `test_stage_a_components_dataclass`**
- **Purpose:** Validate `StageAComponents` dataclass instantiation and field access
- **Assertions:**
  - Can create instance with all fields
  - Required fields raise TypeError if omitted
  - Optional fields default correctly
- **Runtime:** <0.1s

**2. `test_stage_a_debug_config_dataclass`**
- **Purpose:** Validate `StageADebugConfig` CLI argument dataclass
- **Assertions:**
  - Can create instance with default values
  - All CLI flags represented as fields
  - Type annotations correct (device: str, seed: int, phases: List[int])
- **Runtime:** <0.1s

**3. `test_create_debug_run_dir`**
- **Purpose:** Validate debug run directory creation with tmpdir fixture
- **Setup:** Use pytest `tmp_path` fixture
- **Assertions:**
  - Directory created with expected timestamp format
  - Returns (timestamp_str, Path) tuple
  - Subdirectories don't exist yet (lazy creation)
- **Runtime:** <0.5s

**4. `test_write_commands_txt`**
- **Purpose:** Validate command log generation
- **Setup:** Use pytest `tmp_path` fixture
- **Assertions:**
  - Creates `commands.txt` with expected content
  - Contains seed, argv, timestamp
  - File readable and parseable
- **Runtime:** <0.5s

#### Integration Tests (4)

**5. `test_build_dataload_real_assets`**
- **Purpose:** Validate `build_dataload()` can construct DataLoad with actual golden data
- **Setup:** Use canonical fixture path (golden_data/exp00000/1_0.pkl)
- **Assertions:**
  - Returns DataLoad instance
  - DataLoad has required attrs (experiment, reflections, mtz_object, etc.)
  - No crashes or import errors
- **Runtime:** <5s (loads real data)

**6. `test_setup_environment_determinism`**
- **Purpose:** Validate `setup_environment()` sets seeds and returns device
- **Setup:** Call with seed=42, device="cpu"
- **Assertions:**
  - Returns device ("cpu" or "cuda")
  - numpy.random.get_state() reproducible after re-seeding
  - torch.manual_seed effective (if torch available)
- **Runtime:** <1s

**7. `test_stage_a_forward_smoke`**
- **Purpose:** Validate `stage_a_forward()` executes without crashes
- **Setup:**
  - Use `build_dataload()` for real fixture
  - Create minimal `StageAComponents` via `build_stage_a_components()`
  - Run forward model with zero params
- **Assertions:**
  - Returns (bragg_tensor, roi_indices, loss_tensor, param_values_dict)
  - bragg_tensor has expected shape
  - loss_tensor is scalar
- **Runtime:** <10s (includes HKL grid build + simulation)
- **Note:** This is the CRITICAL test that validates the module's core functionality

**8. `test_zero_point_check_integration`**
- **Purpose:** Validate `run_zero_point_check()` workflow
- **Setup:**
  - Use real fixture + minimal components
  - Run zero-point check with tolerance=1e-3 (relaxed for test speed)
- **Assertions:**
  - Returns dict with keys: `zero_point_ok`, `mean_abs_diff`, `chi2_rel_diff`
  - `zero_point_ok` is boolean
  - Diffs are numeric and finite
- **Runtime:** <10s

#### CLI Smoke Tests (2)

**9. `test_cli_help_succeeds`**
- **Purpose:** Validate `--help` flag works without crashes
- **Setup:** Use `subprocess.run()` to invoke CLI script
- **Command:** `python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py --help`
- **Assertions:**
  - Exit code 0
  - stdout contains "usage:"
  - No import errors in stderr
- **Runtime:** <2s

**10. `test_cli_phase_1_backward_compat`**
- **Purpose:** Validate CLI Phase 1 still produces expected artifacts (regression from D2.1+D2.2)
- **Setup:** Use subprocess with same command from D2.1 smoke test
- **Command:** `python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py --phases 1 --device cpu --seed 42 --out-dir <tmp>`
- **Assertions:**
  - Exit code 0
  - `forward_model_probe.json` exists
  - JSON has keys: `n_rois`, `max_abs_diff`, `correlation_stats`
  - `n_rois` >= 90 (smoke check, not exact 92)
- **Runtime:** <10s (reuses D2.1 smoke test validation)

### Total Estimated Test Runtime
- Unit tests (4): ~1.2s
- Integration tests (4): ~26s
- CLI smoke tests (2): ~12s
- **Total:** ~40s (slightly over 30s target, acceptable for comprehensive coverage)

## Phase D D2.4: Documentation Specification

### File: `dbex/tools/README.md`

#### Scope
Create minimal README documenting:
1. **Module Purpose:** Stage A debug tooling library extracted from CLI
2. **Public APIs:** List of functions and classes with one-line descriptions
3. **Usage Example:** Programmatic API example (Python code)
4. **CLI Reference:** Brief mention of CLI shim with pointer to `--help`

#### Content Outline

```markdown
# dbex.tools — Internal Tooling Library

## Overview
Reusable utilities for DBEX development and debugging, extracted from plan-specific scripts for easier testing and maintenance.

## Modules

### `stage_a_adam.py`
Stage A mapping and orientation debug instrumentation.

**Public Classes:**
- `StageAComponents` — Dataclass holding detector/crystal/beam configs, HKL grid, simulator
- `ForwardModelProbeSummary` — Results from forward model parity probe
- `StageADebugConfig` — CLI configuration dataclass

**Public Functions:**
- `build_dataload(repo_root: Path) -> DataLoad` — Construct DataLoad for canonical assets
- `setup_environment(seed: int, device_str: str) -> str` — Seed RNGs, return device
- `create_debug_run_dir(base_dir: Path) -> Tuple[str, Path]` — Timestamped output dir
- `build_stage_a_components(dataload, config) -> StageAComponents` — Create simulation components
- `stage_a_forward(components, param_values_dict) -> Tuple[...]` — Execute forward model
- `run_forward_model_probe(dataload, config, out_dir) -> ForwardModelProbeSummary` — Phase 1
- `run_loss_alignment_probe(dataload, config, out_dir) -> Dict` — Phase 2
- `run_zero_point_check(dataload, config, out_dir) -> Dict` — Phase 3
- `run_single_step_adam(dataload, config, out_dir) -> Dict` — Phase 4
- `run_blockwise_dof_experiments(dataload, config, out_dir) -> Dict` — Phase 5

**Usage Example (Programmatic API):**
```python
from pathlib import Path
from dbex.tools.stage_a_adam import (
    StageADebugConfig,
    build_dataload,
    run_forward_model_probe,
)

# Configure debug run
config = StageADebugConfig(
    repo_root=Path.cwd(),
    device="cpu",
    seed=42,
    phases=[1],  # Forward probe only
    base_output_dir=Path("./debug_output"),
)

# Execute phase
dataload = build_dataload(config.repo_root)
results = run_forward_model_probe(dataload, config, config.base_output_dir)
print(f"Max abs diff: {results.max_abs_diff:.6e}")
```

**CLI Reference:**
The original CLI script at `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py` is now a thin shim over this module. See `--help` for usage.
```

**Estimated Size:** ~80-100 lines

### Docstring Validation

**Already Complete (D2.1):**
All extracted functions in `dbex/tools/stage_a_adam.py` have comprehensive docstrings with:
- One-line summary
- Parameters section
- Returns section
- Raises section (where applicable)
- Notes section (where applicable)

**No Additional Work Required** — D2.1 already included docstring additions.

## Risk Assessment

### R1: Test fixtures too slow (MEDIUM → LOW)
**Mitigation:**
- Use `NANOBRAGG_DISABLE_COMPILE=1` env var to bypass torch.compile
- Integration tests (5-8) use real fixtures but only Phase 1 zero-point (fastest)
- No multi-step optimization loops in tests

### R2: CLI smoke test flakiness (LOW)
**Mitigation:**
- Reuse exact command from D2.1 validation (already proven to work)
- Use fixed seed (42) for determinism
- Relax assertions (n_rois >= 90, not exact 92)

### R3: Import circular dependencies (LOW)
**Mitigation:**
- `dbex/tools/stage_a_adam.py` is already a leaf node (no dbex.tools imports within dbex)
- Lazy torch imports already implemented in D2.1

### R4: Test coverage <80% (MEDIUM → LOW)
**Mitigation:**
- 10 tests cover: dataclasses (2), utils (2), core workflows (4), CLI (2)
- Focus on public APIs (15 functions, 3 classes)
- Integration test 7 (`test_stage_a_forward_smoke`) exercises most code paths
- Accept that some internal helpers may not reach 80%, prioritize critical paths

### R5: Documentation drift (LOW)
**Mitigation:**
- README points to `--help` for CLI, avoiding duplication
- Programmatic API example is minimal (6 lines of actual code)
- No version-specific details that will rot

## Implementation Plan

### Phase D D2.3: Test Suite (Main Task)

**Steps:**
1. Create `tests/dbex/test_stage_a_adam_tooling.py` with 10 test cases
2. Run tests: `NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_adam_tooling.py`
3. Validation: All 10 tests PASS, runtime <60s (relaxed from 30s)
4. Coverage check (optional): `pytest --cov=dbex.tools.stage_a_adam --cov-report=term tests/dbex/test_stage_a_adam_tooling.py`

**Estimated Effort:** ~4-5 hours
- Unit tests (1-4): 1 hour
- Integration tests (5-8): 2.5 hours (test 7 is most complex)
- CLI smoke tests (9-10): 0.5 hour
- Debugging + iteration: 1 hour buffer

### Phase D D2.4: Documentation (Secondary Task)

**Steps:**
1. Create `dbex/tools/README.md` (~80-100 lines)
2. Run CLI help validation: `python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py --help`
3. Manual smoke test: Re-run D2.1 CLI command to confirm backward compat

**Estimated Effort:** ~1 hour
- README authoring: 30 min
- CLI help validation: 10 min
- Smoke test: 10 min
- Review + polish: 10 min

### Total Estimated Effort: ~5-6 hours (single loop feasible)

## Decision Tree

### Path A: ALL TESTS PASS (Expected, HIGH confidence ~85%)
**Outcome:** Phase D D2 ✓ COMPLETE
**Actions:**
1. Update `plans/active/ARCH-REFACTOR-001/implementation.md` Phase D checklist:
   - Mark D2 status: ✓ COMPLETE with timestamp
   - Add validation note: "10 tests PASSED, runtime <60s, README created"
2. Archive artifacts (test logs, coverage report if run, README.md) to reports/2025-11-24T080106Z/
3. Commit message: "ARCH-REFACTOR-001 Phase D D2.3+D2.4: Test suite + docs (10 tests PASSED) — tests: run"
4. Update galph_memory.md with completion note
5. Return control to Galph for Phase D D3 planning OR Phase D completion assessment

### Path B: SOME TESTS FAIL (Low probability ~10%)
**Outcome:** Debug test logic or module bugs
**Actions:**
1. Capture failure signatures (which tests, exact error messages)
2. Triage: test logic bug vs module bug vs environment issue
3. If test logic bug (e.g., wrong assertion): Fix tests, re-run
4. If module bug (e.g., missing import): Fix module, re-run
5. If environment issue (e.g., golden_data missing): Document blocker, return to Galph
6. Iteration: Maximum 2 debug cycles before returning to Galph with blocker report

### Path C: IMPORT ERRORS (Very low probability ~3%)
**Outcome:** Module structure issue
**Actions:**
1. Check `dbex/tools/__init__.py` exists (should be empty or minimal)
2. Verify module can be imported: `python -c "from dbex.tools import stage_a_adam"`
3. Fix import paths or circular dependencies
4. Re-run tests after fix

### Path D: CLI SMOKE TEST REGRESSION (Low probability ~2%)
**Outcome:** CLI refactoring broke backward compatibility
**Actions:**
1. Compare CLI output with D2.1 validation artifacts
2. Check CLI argparse logic for typos or missing delegations
3. Fix CLI shim, re-run smoke test
4. If unfixable: Rollback D2.2 CLI changes, escalate to Galph

## Validation Criteria

### Phase D D2.3 Success Criteria
- [x] 10 test cases implemented in `tests/dbex/test_stage_a_adam_tooling.py`
- [ ] All tests PASS when run with `NANOBRAGG_DISABLE_COMPILE=1`
- [ ] Total runtime <60s (relaxed from 30s planning target)
- [ ] No import errors or crashes
- [ ] Integration test 7 (`test_stage_a_forward_smoke`) validates core workflow

### Phase D D2.4 Success Criteria
- [ ] `dbex/tools/README.md` created with usage example
- [ ] CLI `--help` succeeds (exit code 0)
- [ ] CLI Phase 1 smoke test matches D2.1 validation (backward compatibility)

### Overall Phase D D2 Completion Criteria
- [x] D2.1: Module extraction complete (2025-11-24T095000Z)
- [x] D2.2: CLI refactoring complete (2025-11-24T095000Z)
- [ ] D2.3: Test suite complete
- [ ] D2.4: Documentation complete
- [ ] `implementation.md` Phase D D2 marked ✓ COMPLETE

## Findings Applied

- **POLICY-001** (Environment Freeze): Tests use existing deps (pytest, no new packages)
- **ARCH-ENGINE-002** (Lazy Imports): Module already implements lazy torch imports per D2.1
- **TESTING-003** (Registry Sync): NOT required for internal tooling tests (not user-facing selectors)
- **CLAUDE.md** (Incremental Progress): D2 split into 2 loops (D2.1+D2.2 extraction, D2.3+D2.4 tests+docs)
- **galph_prompt** (Implementation Floor): This is ready_for_implementation loop (production test code ~300-400 lines)

## Next Actions (For Ralph)

Execute Phase D D2.3+D2.4 implementation with 11-step protocol:

1. **Read planning analysis** — This document
2. **Create test file** — `tests/dbex/test_stage_a_adam_tooling.py` (~300-400 lines)
3. **Implement unit tests (4)** — Tests 1-4, dataclasses + utils
4. **Implement integration tests (4)** — Tests 5-8, core workflows
5. **Implement CLI smoke tests (2)** — Tests 9-10, backward compat
6. **Run test suite** — `NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_adam_tooling.py`
7. **Create README** — `dbex/tools/README.md` (~80-100 lines)
8. **Validate CLI help** — `python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py --help`
9. **Decision synthesis** — Write decision.md with Path A/B/C/D outcome
10. **Update implementation.md** — Mark Phase D D2 ✓ COMPLETE if Path A
11. **Write summary.md** — Turn Summary with metrics
12. **Commit and push** — Message: "ARCH-REFACTOR-001 Phase D D2.3+D2.4: Test suite + docs (10 tests PASSED) — tests: run"

**Expected Outcome:** Path A (all tests PASS, Phase D D2 COMPLETE)
