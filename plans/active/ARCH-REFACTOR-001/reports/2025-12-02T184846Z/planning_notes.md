# ARCH-REFACTOR-001 Phase C.5 Planning
## Loop: 2025-12-02T184846Z
## Focus: Stage B LBFGS Inline Execution + Utility Relocation

### Context
**Problems ledger directive serviced**: "PRIORITIZE ARCH-REFACTOR-001 ASAP" from problems.md. This planning loop incorporates the ledger requirement by advancing ARCH-REFACTOR-001 toward completion.

Ralph successfully completed Phase C.4 (Stage B context strictness + parameter builder inlining) in commit `cd855064`. Stage B now:
- Requires strict `RefinementContext` input (removed legacy dict fallback)
- Owns its parameter building logic via inlined `_build_stage_b_params()` private method (322 lines from stage_b_impl.py)
- Both acceptance gates passed: Stage B baseline parity guard + Stage B shell modifier smoke test

### Remaining Work in stage_b_impl.py
Current file: 1025 lines

Functions still to address:
1. `_check_stage_b_baseline_parity` (lines 44-183) - baseline parity guard, ~140 lines
2. `compute_hkl_shell_lookup` (lines 185-278) - shell mode utility, ~94 lines
3. `compute_hkl_asu_map` (lines 280-395) - ASU mapping utility, ~116 lines
4. `initialize_asu_modifiers` (lines 397-445) - ASU initialization, ~49 lines
5. `apply_asu_modifiers` (lines 447-487) - ASU application helper, ~41 lines
6. `_build_stage_b_params` - ALREADY INLINED in Phase C.4 (but definition still in file)
7. `_run_stage_b_lbfgs` (lines 819-1025) - LBFGS execution loop, ~207 lines

### Phase C.5 Scope
Per implementation plan checklist:
- **C5.A**: Port `_run_stage_b_lbfgs` into `StageB._run_lbfgs()`, mirroring Stage C pattern
- **C5.B**: Expose shared utilities by relocating to a dedicated module or StageB class methods
- **C5.C**: Validation via Stage B guard + shell smoke selectors

### Implementation Strategy

#### Option 1: All utilities as StageB static methods
Pros: Single location, clear ownership
Cons: StageB class becomes large, utilities not easily reused outside refinement

#### Option 2: Create dbex/refinement/stage_b_utils.py
Pros: Clean separation, utilities can be imported by tests/tools
Cons: Adds another module to the stack

#### Option 3 (RECOMMENDED): Hybrid approach
- Move `_run_stage_b_lbfgs` → `StageB._run_lbfgs()` (private method)
- Move `_check_stage_b_baseline_parity` → `StageB._check_baseline_parity()` (private method)
- Create `dbex/refinement/hkl_utils.py` for the ASU/shell utilities (public API)
  - `compute_hkl_shell_lookup`
  - `compute_hkl_asu_map`
  - `initialize_asu_modifiers`
  - `apply_asu_modifiers`

Rationale:
- LBFGS and parity guard are Stage B-specific, should live with the stage
- ASU/shell utilities are general HKL operations, useful for other stages/tools
- Clean module boundary: hkl_utils has no StageB/refinement dependencies

### Dependencies & Call Sites

Need to check:
1. Where are the ASU/shell utilities currently imported?
2. Does Stage C or any tools use these helpers?
3. Are there tests that import directly from stage_b_impl?

### Acceptance Criteria
1. `dbex/refinement/stage_b.py` contains `_run_lbfgs()` and `_check_baseline_parity()` methods
2. `dbex/refinement/hkl_utils.py` contains the ASU/shell utilities with docstrings
3. All imports updated (StageB, Stage C if applicable, tests, tools)
4. Stage B guard test PASSES: `test_stage_b_baseline_guard_diff_payload`
5. Stage B shell smoke PASSES: `test_stage_b_shell_modifiers`
6. No references to `_run_stage_b_lbfgs` outside of legacy compatibility shims

### Mapped Tests
- `tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload`
- `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers`
- (Optional) Stage C smoke to ensure no ASU import breakage

### Next Actions
1. Scan for current usage of ASU/shell utilities
2. Update implementation.md with detailed C5 checklist
3. Write input.md with concrete Do Now for Ralph
4. Update problems.md to note this loop serviced the ARCH-REFACTOR-001 directive
