# Phase C2 Bugfix — Missing baseline_crystal Parameter

## Summary
Fix 9.3% chi-squared offset between Stage A final and Stage B initial values in engine delegation path by adding `baseline_crystal` parameter to `_build_final_bragg_from_stage_b_telemetry` helper.

## Mode
none

## Focus
ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase C2 bugfix: baseline_crystal missing)

## Branch
integration

## Mapped Tests
- `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` (regression guard, small detector)
- Selector: `NANOBRAGG_DISABLE_COMPILE=1 KMP_DUPLICATE_LIB_OK=TRUE pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers -k small --tb=short -v`

## Artifacts
plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T081500Z/

## Do Now

**Context:** Ralph's Phase C2 loop i=206 (commit a82893e, 2025-11-23T075320Z) identified a 9.3% chi-squared offset between Stage A final (7.053e+08) and Stage B initial (7.709e+08) values when using RefinementEngine delegation path. Ralph fixed 3 AttributeErrors (asdict conversion bugs + enable_warm_cache typo), but the chi-squared offset persists. Root cause: `_build_final_bragg_from_stage_b_telemetry` helper (dbex/nanobrag_refinement.py:2713-2910) is missing the `baseline_crystal` parameter, so `baseline_misset_deg_tensor` is always `None` (lines 2812-2814), causing incorrect misset computation in final Bragg regeneration.

**Evidence:**
- Line 3035-3036: Engine inputs include `baseline_crystal` and `baseline_detector`
- Line 3071-3084: Helper call does NOT pass `baseline_crystal`
- Lines 2812-2814: `baseline_misset_deg_tensor = None` with comment "Note: baseline_crystal would need to be passed"
- Lines 3115-3120: Inline path correctly computes `baseline_misset_deg_tensor` before Stage A
- Lines 2414-2416 (compute_loss_stage_b): Adds `baseline_misset + misset_delta` when baseline is available
- Lines 2846-2850 (helper): Same add logic, but baseline is always None → wrong misset → wrong chi²

**Fix Strategy:**
1. Add `baseline_crystal=None` parameter to helper signature (after `crystal`, line 2718)
2. Import `compute_baseline_misset_deg` if not already present (check line 2758)
3. Replace `baseline_misset_deg_tensor = None` comment (line 2812-2814) with actual computation
4. Pass `baseline_crystal=baseline_crystal` in engine delegation call (line 3077, after `crystal` arg)
5. Rerun regression guard to verify chi-squared offset ≤ 0.1%

**Implement:**
- dbex/nanobrag_refinement.py::_build_final_bragg_from_stage_b_telemetry (add baseline_crystal parameter + compute baseline_misset)
- dbex/nanobrag_refinement.py (line ~3077, engine delegation: pass baseline_crystal to helper)

**Validate:**
- Rerun `test_stage_b_shell_modifiers` with small detector
- Verify Stage B initial chi² ≈ Stage A final chi² (relative tolerance ≤ 0.1%)
- Capture test log + chi² comparison in artifacts

## How-To Map

1. **Add baseline_crystal parameter to helper signature** (dbex/nanobrag_refinement.py:2713-2726):
   - Line 2718: Change `crystal,` to `crystal, baseline_crystal=None,`
   - Lines 2734-2746 (docstring Args): Add after `crystal:` entry:
     ```
     baseline_crystal: Optional baseline dxtbx Crystal object for extracting deterministic
                       misset when `crystal` is perturbed. When provided, computes
                       U_delta = U_perturbed @ U_baseline^{-1} and adds it to the orientation
                       path as a tensor to preserve differentiability. Defaults to None.
     ```

2. **Verify compute_baseline_misset_deg import** (should be at line 2758):
   ```bash
   grep -n "compute_baseline_misset_deg" dbex/nanobrag_refinement.py | grep "from dbex.nanobrag_bridge import" | head -1
   ```
   - If missing, add to imports at line 2754-2758:
     ```python
     from dbex.nanobrag_bridge import (
         create_detector_config,
         create_crystal_config,
         compute_baseline_misset_deg,  # ADD THIS LINE if missing
     )
     ```

3. **Replace baseline_misset placeholder with computation** (dbex/nanobrag_refinement.py:2810-2814):
   - Find lines 2810-2814:
     ```python
     # Compute baseline misset if available
     baseline_misset_deg_tensor = None
     # Note: baseline_crystal would need to be passed to this helper to compute baseline misset
     # For now, we'll skip baseline misset support in engine path (matches inline path logic)
     ```
   - Replace with:
     ```python
     # Compute baseline misset if baseline_crystal provided (matches inline path lines 3115-3120)
     baseline_misset_deg_tensor = compute_baseline_misset_deg(
         crystal,
         baseline_crystal,
         device=device,
         dtype=dtype,
     )
     ```

4. **Pass baseline_crystal in engine delegation call** (dbex/nanobrag_refinement.py:3071-3084):
   - Find line 3076-3077:
     ```python
     crystal=crystal,
     inputs=inputs,
     ```
   - Change to:
     ```python
     crystal=crystal,
     baseline_crystal=baseline_crystal,
     inputs=inputs,
     ```

5. **Compilation check**:
   ```bash
   python -c "from dbex.nanobrag_refinement import run_nanobrag_refinement; print('OK')" 2>&1 | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T081500Z/compilation_check.log
   ```

6. **Regression guard** (MANDATORY):
   ```bash
   NANOBRAGG_DISABLE_COMPILE=1 KMP_DUPLICATE_LIB_OK=TRUE \
     pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers -k small --tb=short -v \
     2>&1 | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T081500Z/pytest_stage_b_baseline_crystal_fix.log
   ```

7. **Verification** (chi-squared comparison):
   ```bash
   # Extract chi² values from test log
   grep -E "Stage (A|B) (final|initial) chi" plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T081500Z/pytest_stage_b_baseline_crystal_fix.log

   # If test PASSED, extract final chi² values for summary
   # If test FAILED, extract AssertionError with exact chi² values
   ```

8. **Write summary**:
   - File: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T081500Z/summary.md`
   - Include:
     - Problem statement (9.3% chi² offset, root cause)
     - Fix applied (4 code changes: signature + docstring + computation + call site)
     - Chi² comparison before/after (from test logs)
     - Test results (PASS/FAIL)
     - Next actions (if PASS: mark Phase C2 complete; if FAIL: escalate with blocker)

9. **Commit** (if test PASSES):
   ```bash
   git add -A
   git commit -m "$(cat <<'EOF'
   ARCH-REFINE-FLOW-001 Phase C2: Fix baseline_crystal parameter in Stage B final Bragg helper

   Problem: Engine delegation path had 9.3% chi-squared offset between Stage A final and
   Stage B initial because _build_final_bragg_from_stage_b_telemetry helper was missing
   baseline_crystal parameter, causing incorrect misset computation.

   Root Cause: Helper always set baseline_misset_deg_tensor=None (line 2812), so final misset
   calculation used only delta (misset_xyz_deg) instead of baseline+delta. This mismatched
   compute_loss_stage_b (lines 2414-2416) which correctly adds baseline when available.

   Changes:
   - Added baseline_crystal parameter to _build_final_bragg_from_stage_b_telemetry signature
   - Updated docstring to document baseline_crystal purpose (GEOMETRY-003 contract)
   - Replaced baseline_misset=None with compute_baseline_misset_deg call (matching inline path)
   - Passed baseline_crystal in engine delegation call (line ~3077)

   Tests: PASSED
   - test_stage_b_shell_modifiers (small detector): Stage B initial chi² now matches Stage A final
     within 0.1% tolerance (chi² offset resolved)

   Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T081500Z/

   🤖 Generated with [Claude Code](https://claude.com/claude-code)

   Co-Authored-By: Claude <noreply@anthropic.com>
   EOF
   )"
   git push
   ```

## Pitfalls To Avoid

1. **Parameter ordering**: Add `baseline_crystal` AFTER `crystal` parameter (line 2718) to match inline path pattern
2. **Default value**: Use `baseline_crystal=None` to preserve backward compatibility (helper can be called without baseline)
3. **Import check**: `compute_baseline_misset_deg` should already be imported at line 2758; do NOT add duplicate import
4. **Inline path unchanged**: Do NOT modify inline path (lines 3102-onward); it already computes baseline_misset correctly at lines 3115-3120
5. **Test selector**: Use `-k small` to run small-detector test only (faster, ROI mode enabled, 0.1% tolerance)
6. **Tolerance understanding**: Small detector uses 0.1% (1e-3) relative tolerance; full detector uses 5% (5e-2) due to CPU fallback
7. **Device/dtype neutrality**: `compute_baseline_misset_deg` already respects `device` and `dtype` parameters; no hardcoding needed
8. **Environment flags**: MUST set `NANOBRAGG_DISABLE_COMPILE=1` and `KMP_DUPLICATE_LIB_OK=TRUE` per RUNTIME-001/CONFORMANCE-001

**Environment:** Frozen. Do not install/upgrade packages. If import fails, mark blocked with error signature.

## If Blocked

1. **Scenario: Test still fails with chi-squared offset**
   - Extract exact chi² values from pytest log:
     ```bash
     grep "Stage B initial chi-squared.*!= Stage A final" plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T081500Z/pytest_stage_b_baseline_crystal_fix.log
     ```
   - Compute relative difference manually: `abs(stage_b_initial - stage_a_final) / stage_a_final`
   - Check if helper received non-None `baseline_crystal`:
     - Add debug print before line 2812: `print(f"DEBUG: baseline_crystal={baseline_crystal}, type={type(baseline_crystal)}")`
     - Rerun test with debug
   - Verify `baseline_misset_deg_tensor` is used at lines 2847-2850 (should add to misset_xyz_deg when not None)
   - Document findings in `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T081500Z/blocker.md`

2. **Scenario: ImportError or AttributeError on compute_baseline_misset_deg**
   - Verify function exists:
     ```bash
     grep -n "^def compute_baseline_misset_deg" dbex/nanobrag_bridge.py
     ```
   - If missing, check git history:
     ```bash
     git log --oneline --all --grep="compute_baseline_misset_deg" | head -5
     ```
   - Mark blocked in blocker.md with exact error + git context

3. **Scenario: Compilation error on helper signature change**
   - Verify syntax: `baseline_crystal=None` comes AFTER `crystal,` with comma
   - Check for duplicate parameter names
   - Capture full traceback in blocker.md

4. **Escalation Path**:
   - Update `docs/fix_plan.md` Attempts History with: timestamp, focus, status=blocked, blocker summary, artifacts path
   - Update `galph_memory.md` with blocker state + dwell count
   - Write comprehensive blocker.md explaining issue + proposed next diagnostic steps

## Findings Applied

- **GEOMETRY-003**: Crystal misset computation via `compute_baseline_misset_deg` (baseline A* matrix → XYZ Euler misset delta). Adherence: Using same function as inline path (lines 3115-3120) to maintain parity.
- **PHYSICS-LOSS-001**: Variance-weighted chi-squared dual metrics (Stage A/B both persist chi_squared_trace_full). Adherence: Fix ensures Stage B initial chi² matches Stage A final chi² so loss traces are meaningful.
- **RUNTIME-001**: `NANOBRAGG_DISABLE_COMPILE=1` required for gradient tests. Adherence: Set in regression guard command.
- **CONFORMANCE-001**: `KMP_DUPLICATE_LIB_OK=TRUE` required for acceptance tests. Adherence: Set in regression guard command.
- **POLICY-001**: Environment Freeze allows targeted bugfixes. Adherence: Changes use only existing functions (compute_baseline_misset_deg), no new dependencies.

## Pointers

- **Spec**: docs/spec-db-workflow.md:31-34 (Refinement Protocol Architecture, Stage delegation)
- **Spec**: docs/spec-db-core.md:57-68 (Variance-weighted loss definition)
- **Implementation**: dbex/nanobrag_refinement.py:2713-2910 (_build_final_bragg_from_stage_b_telemetry helper signature + body)
- **Implementation**: dbex/nanobrag_refinement.py:3071-3084 (engine delegation call site)
- **Implementation**: dbex/nanobrag_refinement.py:3115-3120 (inline path baseline_misset computation, reference pattern)
- **Implementation**: dbex/nanobrag_bridge.py:723-780 (compute_baseline_misset_deg implementation)
- **Test**: tests/dbex/test_torch_refine_smoke.py:1116-1203 (Stage B chi-squared continuity assertion, line 1116-1119)
- **Finding**: GEOMETRY-003 (baseline misset computation contract)
- **Finding**: PHYSICS-LOSS-001 (chi-squared telemetry contract)
- **Plan**: plans/active/ARCH-REFINE-FLOW-001/implementation.md (Phase C2 objectives)
- **Ralph's Blocker**: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T075320Z/summary.md (loop i=206 bugfix evidence)

## Next Up

If finished early and test PASSES:
- Update implementation.md with Phase C2 completion status
- Run full-detector Stage B smoke (`-k full`) to verify no regressions in canonical path (optional, low priority)

Do NOT proceed to Phase C3 without explicit Galph approval.

## Doc Sync Plan

Not required (no new tests added, existing test_stage_b_shell_modifiers selector unchanged).

## Mapped Tests Guardrail

Selector collects >0 tests (verified via `pytest --collect-only`):
- `test_stage_b_shell_modifiers`: 2 parametrized tests (smoke_detector_size=small/full), status=Active

No downgrade required. Small-detector test MUST PASS for Phase C2 completion.
