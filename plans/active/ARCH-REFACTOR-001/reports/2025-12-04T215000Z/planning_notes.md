# ARCH-REFACTOR-001 Phase C.8 Planning Notes

## Loop: 2025-12-04T215000Z
## Focus: Phase C.8 — Stage A Helper Inlining

### Context

Phase C.7 completed successfully (commit f6d964f0): 7 cross-stage helpers extracted to `stage_a_utils.py` (637 lines), imports updated across 5 files, all 4/4 validation tests passed.

Remaining in `dbex/refinement/stage_a_impl.py` (1524 lines total):
- 3 Stage-A-private helpers (~1025 lines):
  1. `_sync_stage_a_crystal` (lines 238-247, ~10 lines, trivial)
  2. `_build_stage_a_params` (lines 510-1226, ~717 lines, complex)
  3. `_run_stage_a_lbfgs` (lines 1227-end, ~298 lines, medium)

### Objective

Inline the 3 remaining Stage-A-private helpers into the `StageA` class (dbex/refinement/stage_a.py, currently 1275 lines), mirroring the pattern used for Stage C (Phase C.2) and Stage B (Phase C.5).

### Analysis

**Current StageA usage:**
- Line 442: `warm_crystal_model = _sync_stage_a_crystal(stage_a_ctx, warm_crystal_model)`
- Line 924: `helper1_result = _build_stage_a_params(...)`
- Line 1033: `status, message, ... = _run_stage_a_lbfgs(...)`

**Target pattern (from Stage C/B):**
- Convert to private methods: `StageA._sync_crystal()`, `StageA._build_stage_a_params()`, `StageA._run_lbfgs()`
- Update call sites to use `self._*` instead of module-level helpers
- Keep all logic, type hints, docstrings, telemetry collector wiring unchanged

**Scope:**
- Inline all 3 functions into StageA class
- Remove imports from stage_a_impl
- Update call sites (3 locations in StageA.run)
- DO NOT delete stage_a_impl.py yet (Phase C.9)

**Risks:**
- Large diff (~1025 lines moving)
- _build_stage_a_params is 717 lines — needs careful indentation
- Must preserve ARCH-TELEMETRY-001 observer wiring
- Must preserve device/dtype neutrality (GRADIENT-004)
- Must preserve warm-cache logic (PERF-WARM-016)

**Validation tests:**
- test_stage_a_expansion (Stage A smoke)
- test_stage_a_engine_delegation_telemetry (engine telemetry validation)
- test_stage_b_baseline_guard_diff_payload (Stage B guard, uses Stage A artifacts)
- test_stage_b_shell_modifiers (Stage B shell smoke)

### Implementation Plan

**Step 1: Inline _sync_stage_a_crystal** (trivial, 10 lines)
- Add as `StageA._sync_crystal()` private method
- Update call site at line 442

**Step 2: Inline _build_stage_a_params** (complex, 717 lines)
- Add as `StageA._build_stage_a_params()` private method
- Update call site at line 924
- Preserve all telemetry collector wiring
- Keep all CPU fallback logic (GRADIENT-003)

**Step 3: Inline _run_stage_a_lbfgs** (medium, 298 lines)
- Add as `StageA._run_lbfgs()` private method
- Update call site at line 1033
- Preserve observer-only telemetry path (ARCH-TELEMETRY-001)

**Step 4: Update imports**
- Remove `_sync_stage_a_crystal`, `_build_stage_a_params`, `_run_stage_a_lbfgs` from imports
- stage_a_impl will retain 8 extracted functions (now in stage_a_utils) until Phase C.9 deletion

**Step 5: Validation**
- Run 4 mapped tests with canonical env flags
- All must PASS with no behavioral regression

### Constraints

- Environment Freeze: no package changes
- Device/dtype neutrality (GRADIENT-004): preserve tensor device/dtype handling
- Collector-only telemetry (ARCH-TELEMETRY-001): keep observer callbacks intact
- Warm cache (PERF-WARM-016): preserve simulator reuse logic
- ARCH-STAGE-CTX-001: use typed contexts only

### Expected Metrics

- Files touched: 2 (stage_a.py, stage_a_impl.py imports only)
- LOC: ~+1025 lines in stage_a.py (inlined methods), -3 imports
- stage_a.py will grow from 1275 to ~2300 lines
- stage_a_impl.py will remain at 1524 lines (functions stay for C.9 deletion)
- No behavior change: all tests must produce identical telemetry

### Artifacts

- pytest_stage_a_expansion.log
- pytest_stage_a_telemetry.log
- pytest_stage_b_guard.log
- pytest_stage_b_shell.log
- summary.md

### Next Actions

After C.8 completes:
- Phase C.9: Delete stage_a_impl.py entirely
- Update any remaining imports
- Final validation with full selector suite
