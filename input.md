# Input for Ralph: ARCH-REFACTOR-001 Phase D D2.1 + D2.2 — Stage A Debug Tooling Module + CLI Refactor

## Summary
Extract reusable utilities from `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py` (1849 lines) into `dbex/tools/stage_a_adam.py` module (~800-1000 lines). Refactor CLI to thin argparse shim (~150-200 lines). Validate with manual CLI smoke test.

## Mode
none

## Focus
ARCH-REFACTOR-001 — Refinement Engine Modularization & Physics Separation (Phase D D2: Stage A Debug Tooling Modularization, Sub-phases D2.1 + D2.2)

## Branch
integration

## Mapped Tests
none — tooling-only refactor (CLI smoke test manual validation)

## Artifacts
`plans/active/ARCH-REFACTOR-001/reports/2025-11-24T095000Z/`
- `extraction_mapping.md` (function/class mapping: source → target lines)
- `cli_smoke_test.log` (manual backward compat validation)
- `phase_d_d2_decision.md` (decision synthesis with Path A/B/C/D template)
- `summary.md` (Turn Summary as specified in galph_prompt end_of_loop_hygiene)

## Do Now

**IMPORTANT:** This is Phase D D2.1 + D2.2 (module creation + CLI refactor). Tests (D2.3) will follow in next loop.

### Phase D D2.1: Module Creation (~4-5 hours)

**Target:** `dbex/tools/stage_a_adam.py` (~800-1000 lines)

**Checklist:**
1. Create `dbex/tools/__init__.py` (empty or minimal)
2. Create `dbex/tools/stage_a_adam.py` with header:
   ```python
   """
   Stage A Debug Tooling — Reusable Utilities

   Extracted from plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py
   Initiative: ARCH-REFACTOR-001 Phase D D2.1
   Owner: galph

   Core utilities for Stage A mapping/orientation debug instrumentation.
   See `plans/active/ARCH-REFACTOR-001/reports/2025-11-24T092000Z/phase_d_d2_planning_analysis.md` for extraction strategy.
   """
   ```
3. Move classes (rename from private to public):
   - `_StageAComponents` → `StageAComponents` (dataclass)
   - `ForwardModelProbeSummary` (already public, keep as-is)
   - NEW: `StageADebugConfig` (dataclass for all CLI args, consolidate argparse logic)
4. Move functions (15 total, extract verbatim without logic changes):
   - Setup & Environment: `build_dataload`, `setup_environment`, `create_debug_run_dir`, `write_commands_txt`
   - Stage A Components: `build_stage_a_components`, `build_stage_a_bragg_noop`
   - Simulation: `stage_a_forward`
   - Probes & Experiments: `run_forward_model_probe`, `run_loss_alignment_probe`, `run_zero_point_check`, `run_single_step_adam`, `run_blockwise_dof_experiments`, `run_gradient_probe`
   - Core Optimization: `stage_a_adam_core`
   - Utilities: `import_stage_a_dependencies` (preserve lazy torch imports)
5. For each function/class:
   - Copy verbatim from original script (NO logic changes)
   - Remove leading underscore from function names (make public: `_build_dataload` → `build_dataload`)
   - Add comprehensive docstrings (Parameters, Returns, Raises, Notes, Findings)
   - Update internal imports: Use `from dbex.tools.stage_a_adam import ...` patterns
6. Preserve lazy torch imports: Keep `import_stage_a_dependencies()` pattern intact
7. Update imports at module level: No `sys.path` hacking, use direct imports from `dbex.*`

**Expected Result:** `dbex/tools/stage_a_adam.py` with ~800-1000 lines, all classes/functions extracted with docstrings.

### Phase D D2.2: CLI Refactoring (~1-2 hours)

**Target:** `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py` (refactored to ~150-200 lines)

**Checklist:**
1. Read current CLI structure (1849 lines)
2. Rewrite as thin shim:
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
       # Keep existing argparse logic (unchanged)
       # ... argparse setup ...
       args = parser.parse_args()
       return StageADebugConfig(
           repo_root=args.repo_root,
           device=args.device,
           seed=args.seed,
           phases=args.phases,
           # ... all CLI args ...
       )

   def main(argv=None) -> None:
       """Entry point - delegate to module functions."""
       config = parse_args()
       dataload = build_dataload(config.repo_root)
       setup_environment(config.seed, config.device)
       timestamp, out_dir = create_debug_run_dir(config.base_output_dir)
       write_commands_txt(out_dir, config.seed, sys.argv)

       if 1 in config.phases:
           run_forward_model_probe(dataload, config, out_dir)
       if 2 in config.phases:
           run_loss_alignment_probe(dataload, config, out_dir)
       if 3 in config.phases:
           run_zero_point_check(dataload, config, out_dir)
       if 4 in config.phases:
           run_single_step_adam(dataload, config, out_dir)
       if 5 in config.phases:
           run_blockwise_dof_experiments(dataload, config, out_dir)
       if 'gradient' in config.extra_probes:
           run_gradient_probe(dataload, config, out_dir)

   if __name__ == "__main__":
       main()
   ```
3. Remove `sys.path` hacking (lines 51-52)
4. Keep argparse logic unchanged (backward compatibility)
5. `parse_args()` returns `StageADebugConfig` dataclass (consolidates all CLI args)
6. `main()` delegates to module functions (thin orchestration)

**Expected Result:** CLI reduced from 1849 → ~150-200 lines, imports from `dbex.tools.stage_a_adam`, backward compatible.

### Validation: CLI Smoke Test (~15 minutes)

**Critical:** Backward compatibility validation BEFORE committing.

**Commands:**
```bash
# Test Phase 1 (Forward model probe) on CPU with tiny fixture
cd /home/ollie/Documents/diffbragg_example
python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --phases 1 \
  --device cpu \
  --out-dir /tmp/stage_a_debug_test_$(date +%s) \
  --seed 42

# Expected: Same Phase 1 JSON artifacts structure, no errors
```

**Validation Checks:**
- CLI runs without errors
- Output directory contains `forward_model_probe.json`
- JSON structure matches baseline (max_abs_diff, mse, correlations fields present)
- Runtime ~10-30s (tiny fixture)

**If PASS:** Record log to `plans/active/ARCH-REFACTOR-001/reports/2025-11-24T095000Z/cli_smoke_test.log`

**If FAIL:** Debug module imports, fix extraction errors, retry

### Decision Synthesis

**Path A:** CLI smoke test PASSED → Phase D D2.1 + D2.2 COMPLETE, ready for D2.3 (tests) next loop

**Path B:** CLI smoke test FAILED (import errors) → Fix module imports, retry smoke test, if pass → Path A

**Path C:** CLI smoke test FAILED (logic errors) → Extraction introduced bugs, revert to verbatim copy, retry

**Path D:** CLI smoke test TIMEOUT → Fixture issue (not extraction bug), record timeout, retry with explicit timeout flag

### Commit

**Message (if Path A):**
```
ARCH-REFACTOR-001 Phase D D2.1+D2.2: Stage A debug tooling module + CLI refactor — tests: not run

Extracted reusable utilities from stage_a_mapping_adam_debug.py (1849 lines)
into dbex/tools/stage_a_adam.py module (~800-1000 lines):
- 15 functions: setup, components, simulation, probes, optimization
- 3 classes: StageAComponents, ForwardModelProbeSummary, StageADebugConfig
- Preserved lazy torch imports, comprehensive docstrings

Refactored CLI to thin argparse shim (~150-200 lines):
- parse_args() returns StageADebugConfig dataclass
- main() delegates to module functions (no sys.path hacking)
- Backward compatible: Phase 1 smoke test PASSED (cpu, seed=42)

Code reduction: -1649 lines (1849 → 200 CLI, +800 module)
Validation: CLI smoke test (Phase 1 forward probe, /tmp output, JSON artifacts match baseline)
Next: Phase D D2.3 (test suite: unit/integration/CLI smoke tests)
```

## How-To Map

### 1. Read Phase D D2 Planning Analysis
```bash
cat plans/active/ARCH-REFACTOR-001/reports/2025-11-24T092000Z/phase_d_d2_planning_analysis.md
```
**Why:** Comprehensive extraction strategy (17 functions, 2 classes, risks, validation)

### 2. Create Module `dbex/tools/stage_a_adam.py`
- Create `dbex/tools/__init__.py` (empty)
- Create `dbex/tools/stage_a_adam.py` with header docstring
- Extract classes: `StageAComponents` (rename from `_StageAComponents`), `ForwardModelProbeSummary`, NEW `StageADebugConfig`
- Extract functions: 15 functions verbatim (remove leading `_`, add docstrings)
- Preserve lazy imports: `import_stage_a_dependencies()` intact
- Update imports: No `sys.path`, use `from dbex.*`

### 3. Refactor CLI `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py`
- Rewrite to thin shim (~150-200 lines)
- Import from `dbex.tools.stage_a_adam`
- `parse_args()` → `StageADebugConfig`
- `main()` delegates to module functions
- Remove `sys.path` hacking

### 4. CLI Smoke Test (Manual Validation)
```bash
python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --phases 1 --device cpu --out-dir /tmp/stage_a_debug_test_$(date +%s) --seed 42
```
- Expected: Phase 1 forward_model_probe.json in output dir, no errors
- Save log: `plans/active/ARCH-REFACTOR-001/reports/2025-11-24T095000Z/cli_smoke_test.log`

### 5. Decision Synthesis
- Read smoke test log
- Path A (PASS) / Path B (import fail) / Path C (logic fail) / Path D (timeout)
- Write `phase_d_d2_decision.md` with verdict

### 6. Write Extraction Mapping
- Document which source lines → target lines (function-by-function)
- Save: `plans/active/ARCH-REFACTOR-001/reports/2025-11-24T095000Z/extraction_mapping.md`

### 7. Update implementation.md Checklist
```python
# Mark D2 items:
# - [ ] D2 → partially complete (D2.1+D2.2 done, D2.3+D2.4 remain)
```

### 8. Write Turn Summary
- See galph_prompt end_of_loop_hygiene for format
- 3-5 short sentences: what shipped, main problem, next step
- Artifacts line pointing to this loop's reports directory
- Write to `plans/active/ARCH-REFACTOR-001/reports/2025-11-24T095000Z/summary.md`

### 9. Commit (if Path A)
- `git add dbex/tools/ plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py plans/active/ARCH-REFACTOR-001/`
- Message template above (tests: not run)
- `git push`

## Pitfalls To Avoid

1. **DO NOT change logic** during extraction — copy verbatim, only rename/add docstrings
2. **DO NOT break lazy imports** — `import_stage_a_dependencies()` must remain for torch deferral
3. **DO NOT add sys.path hacking** to module — use direct `from dbex.*` imports
4. **DO NOT skip CLI smoke test** — backward compat validation is CRITICAL before commit
5. **DO NOT bundle test suite** (D2.3) into this loop — tests are next loop (D2.3 + D2.4)
6. **Preserve argparse structure** — CLI args unchanged (backward compatibility)
7. **Module location** — `dbex/tools/` not `dbex/tooling/` or other paths
8. **Dataclass NEW** — `StageADebugConfig` is NEW class (consolidate all CLI args from argparse)
9. **Docstrings** — Add Parameters/Returns/Raises/Notes sections for all public functions
10. **Findings references** — Cite POLICY-001 (Environment Freeze), ARCH-ENGINE-002 (lazy imports) in module docstring

## If Blocked

**Blocker:** Circular imports detected during module load
- **Action:** Verify `dbex/tools/stage_a_adam.py` imports FROM `dbex.*` (leaf-node constraint)
- **Capture:** `python -c "from dbex.tools.stage_a_adam import StageAComponents"` error message
- **Log:** `plans/active/ARCH-REFACTOR-001/reports/2025-11-24T095000Z/blocked_circular_imports.log`

**Blocker:** CLI smoke test fails with import errors
- **Action:** Check `import from dbex.tools.stage_a_adam ...` syntax in CLI
- **Capture:** Full traceback
- **Log:** `cli_smoke_test.log` with error details

**Blocker:** Extraction > 8 hours (exceeds single loop time budget)
- **Action:** Split Phase D D2.1 (module only) and D2.2 (CLI only) into separate loops
- **Capture:** Current progress (module complete? CLI complete?)
- **Log:** Write partial progress + return to supervisor for re-scoping

## Findings Applied

- **POLICY-001** (Environment Freeze): Use existing deps only, no new installs ✓
- **ARCH-ENGINE-002** (Lazy Imports): Preserve `import_stage_a_dependencies()` torch deferral ✓
- **CLAUDE.md Incremental**: Extract verbatim (no logic changes), validate with smoke test ✓

## Pointers

### Specs & Architecture
- `plans/active/ARCH-REFACTOR-001/implementation.md:191-209` (Phase D checklist)
- `plans/active/ARCH-REFACTOR-001/reports/2025-11-24T092000Z/phase_d_d2_planning_analysis.md` (extraction strategy)

### Source File
- `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py:1-1849` (extraction target)

### Testing
- Manual CLI smoke test (Phase 1, cpu, seed=42) — backward compat validation

## Next Up

**Next Loop (i=257):** Phase D D2.3 + D2.4 (test suite + docs)
- Create `tests/dbex/test_stage_a_adam_tooling.py` (~300 lines, 10 tests)
- Unit tests: dataclasses, dir creation, command log
- Integration tests: zero-point/adam/DoF flows with mock fixtures
- CLI smoke tests: Phase 1, help, dry-run
- Documentation: `dbex/tools/README.md` with usage examples

## Doc Sync Plan

Not applicable (no test collection changes this loop, tooling-only refactor)

## Mapped Tests Guardrail

Not applicable (tooling-only refactor, no pytest selectors involved)
