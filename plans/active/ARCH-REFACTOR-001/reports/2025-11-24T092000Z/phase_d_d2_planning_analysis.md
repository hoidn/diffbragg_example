# ARCH-REFACTOR-001 Phase D D2 Planning Analysis

**Date:** 2025-11-24T092000Z
**Phase:** D2 — Stage A Debug Tooling Modularization
**Status:** Planning

## Objective

Extract reusable utilities from `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py` (1849 lines) into `dbex/tools/stage_a_adam.py` module. The CLI script becomes a thin argparse shim. Add unit/integration tests.

## Current Script Analysis

**File:** `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py`
**Size:** 1849 lines
**Purpose:** Stage A mapping/orientation debug instrumentation with 5 phases:
- Phase 0: Environment lockdown + debug run directory
- Phase 1: Forward-model equality probe (mapping vs Stage-A simulator)
- Phase 2: Loss-definition alignment (mapping diagnostics vs variance-weighted chi²)
- Phase 3: Zero-point alignment probe (Adam core reproduces bragg_zero_iter at zero params)
- Phase 4: Single-step Adam experiment (full params)
- Phase 5: Block-wise DoF sweeps (scale-only, scale+cell, scale+orientation, full)

### Functions (17 total)
1. `_build_dataload()` — Construct DataLoad for canonical assets
2. `_setup_environment()` — Seed, device, determinism lockdown
3. `_create_debug_run_dir()` — Timestamped output directory creation
4. `_write_commands_txt()` — Repro command log
5. `_import_stage_a_dependencies()` — Lazy torch imports
6. `_build_stage_a_components()` — Create detector/crystal/beam configs, HKL grid, simulator
7. `_stage_a_forward()` — Stage A forward model execution
8. `_build_stage_a_bragg_noop()` — No-op simulator (mapping zero point)
9. `_run_forward_model_probe()` — Phase 1: Forward parity probe
10. `_run_loss_alignment_probe()` — Phase 2: Loss function alignment
11. `_stage_a_adam_core()` — Core Adam optimization loop
12. `_run_single_step_adam()` — Phase 4: Single-step experiment
13. `_run_zero_point_check()` — Phase 3: Zero-point validation
14. `_run_blockwise_dof_experiments()` — Phase 5: DoF sweeps
15. `_run_gradient_probe()` — Gradient analysis (optional phase)
16. `_parse_args()` — Argparse CLI
17. `main()` — Entry point

### Classes (2 total)
1. `_StageAComponents` — Dataclass holding detector/crystal/beam configs, HKL grid, etc.
2. `ForwardModelProbeSummary` — Dataclass for Phase 1 results

### Dependencies
- External: `dbex.data_load`, `dbex.nanobrag_bridge`, `dbex.nanobrag_refinement`, `dbex.vis`, `tests.fixtures.parity_loader`
- Stdlib: `argparse`, `json`, `os`, `random`, `sys`, `dataclasses`, `datetime`, `pathlib`, `statistics`, `typing`
- Third-party: `numpy`, torch (lazy import)

### Current Issues
- **sys.path hacking:** Line 51-52 adds REPO_ROOT to sys.path (brittle)
- **Monolithic structure:** 1849 lines, hard to test in isolation
- **CLI-only invocation:** No programmatic API for reuse

## Extraction Strategy

### Phase D D2.1: Module Creation
**File:** `dbex/tools/stage_a_adam.py`
**Scope:** Extract reusable components

#### Core Classes (Move to Module)
- `StageAComponents` (rename from `_StageAComponents`, make public)
- `ForwardModelProbeSummary`
- NEW: `StageADebugConfig` (dataclass for all CLI args)

#### Core Functions (Move to Module)
1. **Setup & Environment:**
   - `build_dataload(repo_root: Path) -> DataLoad`
   - `setup_environment(seed: int, device_str: str) -> int`
   - `create_debug_run_dir(base_dir: Path = ...) -> Tuple[str, Path]`

2. **Stage A Components:**
   - `build_stage_a_components(...) -> StageAComponents`
   - `build_stage_a_bragg_noop(...) -> Tuple[...]`

3. **Simulation:**
   - `stage_a_forward(...) -> Tuple[...]`

4. **Probes & Experiments:**
   - `run_forward_model_probe(...) -> ForwardModelProbeSummary`
   - `run_loss_alignment_probe(...) -> Dict`
   - `run_zero_point_check(...) -> Dict`
   - `run_single_step_adam(...) -> Dict`
   - `run_blockwise_dof_experiments(...) -> Dict`
   - `run_gradient_probe(...) -> Dict` (optional)

5. **Core Optimization:**
   - `stage_a_adam_core(...) -> Tuple[...]`

#### Utilities (Module-Level)
- `write_commands_txt(out_dir: Path, seed: int, argv: List[str]) -> None`
- `import_stage_a_dependencies() -> None` (lazy torch import helper)

#### Total Extracted: ~15 functions, 3 classes

### Phase D D2.2: CLI Refactoring
**File:** `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py` (refactored)
**Scope:** Thin argparse shim (~150-200 lines)

#### New Structure
```python
#!/usr/bin/env python3
"""Stage A Mapping Adam Debug CLI - thin shim over dbex.tools.stage_a_adam."""

import argparse
import sys
from pathlib import Path

from dbex.tools.stage_a_adam import (
    StageADebugConfig,
    build_dataload,
    setup_environment,
    create_debug_run_dir,
    write_commands_txt,
    run_forward_model_probe,
    run_loss_alignment_probe,
    run_zero_point_check,
    run_single_step_adam,
    run_blockwise_dof_experiments,
    run_gradient_probe,
)

def parse_args() -> StageADebugConfig:
    """Parse CLI arguments into config dataclass."""
    # argparse logic (unchanged)
    ...
    return StageADebugConfig(...)

def main(argv=None) -> None:
    """Entry point."""
    config = parse_args()
    dataload = build_dataload(config.repo_root)
    setup_environment(config.seed, config.device)
    timestamp, out_dir = create_debug_run_dir(config.base_output_dir)
    write_commands_txt(out_dir, config.seed, sys.argv)

    # Phase execution (thin delegation)
    if 1 in config.phases:
        run_forward_model_probe(dataload, config, out_dir)
    if 2 in config.phases:
        run_loss_alignment_probe(dataload, config, out_dir)
    # ... etc for phases 3, 4, 5
```

**Estimated CLI Size:** ~150-200 lines (down from 1849)

### Phase D D2.3: Test Suite Creation
**File:** `tests/dbex/test_stage_a_adam_tooling.py`
**Scope:** Unit and integration tests (~300-400 lines)

#### Test Cases
1. **Unit Tests (Fast, No Fixtures)**
   - `test_stage_a_components_dataclass` — Dataclass instantiation
   - `test_create_debug_run_dir` — Directory creation + cleanup
   - `test_write_commands_txt` — Command log generation

2. **Integration Tests (With Fixtures)**
   - `test_build_stage_a_components` — Config creation (mock DataLoad)
   - `test_stage_a_forward_smoke` — Forward model execution (tiny fixture)
   - `test_zero_point_check_smoke` — Zero-point validation (mock components)
   - `test_adam_core_single_step` — Single Adam step (mock closures)

3. **CLI Smoke Test**
   - `test_cli_phase_1_only` — Run Phase 1 with mock fixtures
   - `test_cli_help` — `--help` succeeds
   - `test_cli_dry_run` — Dry-run mode (no actual simulation)

**Validation Strategy:**
- Fast tests: <5s total runtime
- Fixtures: Use mock/tiny synthetic data (no golden_data dependency)
- Coverage target: ≥80% for extracted functions

### Phase D D2.4: Documentation
**Files:**
- `dbex/tools/README.md` — Module index + usage examples
- `dbex/tools/stage_a_adam.py` — Comprehensive docstrings

**Example Usage (Programmatic API):**
```python
from dbex.tools.stage_a_adam import (
    StageADebugConfig,
    build_dataload,
    run_forward_model_probe,
)

config = StageADebugConfig(
    repo_root=Path.cwd(),
    device="cpu",
    seed=42,
    phases=[1],  # Forward probe only
)
dataload = build_dataload(config.repo_root)
results = run_forward_model_probe(dataload, config, out_dir=Path("./debug_output"))
print(f"Max abs diff: {results.max_abs_diff}")
```

## Dependencies & Risks

### Dependencies
- **POLICY-001** (Environment Freeze): All code uses existing deps (no new installs)
- **ARCH-ENGINE-002** (Lazy imports): Preserve torch lazy import pattern
- **Existing APIs**: No changes to `dbex.nanobrag_bridge`, `dbex.nanobrag_refinement` surfaces

### Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **R1: Circular imports** | LOW | `dbex.tools` is leaf-node (imports FROM dbex.*, not vice versa) |
| **R2: Test fixtures too heavy** | MEDIUM | Use mock/tiny synthetic data, avoid golden_data |
| **R3: CLI backward compatibility** | LOW | Keep CLI interface unchanged (same args, same behavior) |
| **R4: Module load time** | LOW | Preserve lazy torch imports, defer heavy imports |
| **R5: Extraction introduces bugs** | LOW | Move code verbatim (no logic changes), validate with CLI smoke test |

### Mitigation: Regression Guard
- Existing workflows using `stage_a_mapping_adam_debug.py` must work unchanged
- CLI smoke test: `python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py --phases 1 --device cpu --out-dir /tmp/test_run`
- Expected: Same output structure, same JSON artifacts, same Phase 1 results

## Implementation Checklist

### D2.1: Module Creation (~4-5 hours)
- [ ] Create `dbex/tools/__init__.py` (empty or minimal exports)
- [ ] Create `dbex/tools/stage_a_adam.py`
- [ ] Move classes: `StageAComponents`, `ForwardModelProbeSummary`, add `StageADebugConfig`
- [ ] Move functions: 15 functions (setup, components, simulation, probes, optimization)
- [ ] Update imports: Replace `sys.path` hack with direct `from dbex.tools.stage_a_adam import ...`
- [ ] Preserve lazy imports: `import_stage_a_dependencies()` remains in module
- [ ] Add comprehensive docstrings: All public functions + classes

**Estimated:** ~800-1000 lines in `dbex/tools/stage_a_adam.py`

### D2.2: CLI Refactoring (~1-2 hours)
- [ ] Refactor `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py`
- [ ] Reduce to thin argparse shim (~150-200 lines)
- [ ] Import from `dbex.tools.stage_a_adam`
- [ ] `parse_args()` returns `StageADebugConfig` dataclass
- [ ] `main()` delegates to module functions
- [ ] Remove `sys.path` hacking

**Estimated:** -1649 lines (1849 → 200)

### D2.3: Test Suite (~3-4 hours)
- [ ] Create `tests/dbex/test_stage_a_adam_tooling.py`
- [ ] Unit tests: dataclass, dir creation, command log (3 tests, ~50 lines)
- [ ] Integration tests: components, forward, zero-point, adam (4 tests, ~150 lines)
- [ ] CLI smoke tests: phase 1, help, dry-run (3 tests, ~100 lines)
- [ ] Run full suite: `pytest tests/dbex/test_stage_a_adam_tooling.py`

**Estimated:** ~300 lines, 10 tests total

### D2.4: Documentation + Validation (~1-2 hours)
- [ ] Add `dbex/tools/README.md` with usage examples
- [ ] CLI regression smoke test: `--phases 1 --device cpu` produces same artifacts
- [ ] Update `implementation.md`: Mark D2 complete
- [ ] Commit with message: "ARCH-REFACTOR-001 Phase D D2: Stage A debug tooling modularization — tests: pass"

## Validation Strategy

### Unit Tests
- **Fast:** <5s total runtime
- **No fixtures:** Mock DataLoad, synthetic configs
- **Coverage:** ≥80% for extracted functions

### Integration Tests
- **Medium speed:** <30s total runtime
- **Tiny fixtures:** Mock detector (10×10 pixels), 5 HKL points
- **Validates:** End-to-end Phase 1-5 flows without real data

### CLI Smoke Test
- **Backward compatibility:** Existing workflows unchanged
- **Artifacts:** Same JSON structure, same Phase 1 results
- **Command:** `python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py --phases 1 --device cpu --out-dir /tmp/test_run`

### Regression Guards
- **None required:** No production code changes, pure tooling refactor
- **Optional:** Run existing Stage A smoke test to confirm no side effects

## Estimated Effort

| Phase | Tasks | Time | Complexity |
|-------|-------|------|------------|
| D2.1 | Module creation | 4-5 hours | MEDIUM |
| D2.2 | CLI refactor | 1-2 hours | LOW |
| D2.3 | Test suite | 3-4 hours | MEDIUM |
| D2.4 | Docs + validation | 1-2 hours | LOW |
| **Total** | **4 sub-phases** | **9-13 hours** | **MEDIUM** |

**Loop Estimate:** 2-3 loops (if bundled efficiently, could be 2 loops)

### Loop 1: D2.1 + D2.2 (~6-7 hours)
- Create `dbex/tools/stage_a_adam.py` module
- Refactor CLI to thin shim
- Validate: CLI still works (manual smoke test)

### Loop 2: D2.3 + D2.4 (~5-6 hours)
- Create `tests/dbex/test_stage_a_adam_tooling.py`
- Run full test suite (10 tests)
- Documentation + final commit

**Decision:** 2-loop implementation (feasible if both loops execute within ~6-8 hours each)

## Findings Applied

- **POLICY-001** (Environment Freeze): No new dependencies, existing APIs only ✓
- **ARCH-ENGINE-002** (Lazy imports): Preserve torch lazy import pattern ✓
- **CLAUDE.md Incremental**: Break into 2 loops (module + tests) ✓

## Decision: Approve Phase D D2 for Implementation

**Verdict:** Phase D D2 (Stage A debug tooling modularization) is **APPROVED** for implementation.

**Confidence:** HIGH (~85%)
- Well-scoped: Clear extraction target (1849-line script → module + thin CLI)
- Moderate complexity: 2-3 loops estimated, feasible in ~9-13 hours
- Low risk: Isolated tooling changes, no production impact, backward compatible
- High ROI: Enables programmatic API reuse, improves testability, removes sys.path hack

**Next Actions:**
1. Ralph executes Phase D D2.1 + D2.2 (module creation + CLI refactor)
2. Supervisor reviews Phase D D2.1/D2.2 completion
3. Ralph executes Phase D D2.3 + D2.4 (tests + docs)
4. Mark Phase D D2 complete in `implementation.md`

**Estimated Timeline:** 2 loops (i=257, i=258)

## Artifacts

- `plans/active/ARCH-REFACTOR-001/reports/2025-11-24T092000Z/phase_d_d2_planning_analysis.md` (this file)
- `plans/active/ARCH-REFACTOR-001/reports/2025-11-24T092000Z/focus_selection_decision.md`
