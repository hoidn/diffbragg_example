# Ralph Do Now — ARCH-REFINE-FLOW-001 Phase C2 Chi² Offset Bugfix (Loop i=210)

## Summary
Fix cell parameter reconstruction bug in StageB.run() that causes 9.3% chi² offset between Stage A final and Stage B initial.

## Mode
none

## Focus
ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase C2 bugfix)

## Branch
integration

## Mapped tests
- `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` — Stage B regression guard (small detector)

## Artifacts
`plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T083100Z/`
- `planning_summary.md` (Galph's analysis)
- `pytest_stage_b_c2.log` (test output, you generate)
- `summary.md` (your summary, you generate)

## Do Now

**Implement:** Fix cell parameter base reconstruction in `dbex/refinement/stage_b.py::run` (line 163)

**Validating pytest selector:** `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers`

**Checklist:**

1. **Read the planning summary** (`plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T083100Z/planning_summary.md`) to understand the root cause

2. **Implement the fix** in `dbex/refinement/stage_b.py`:
   - Locate line 163: `cell_params = crystal.get_unit_cell().parameters()`
   - Replace with baseline crystal extraction:
     ```python
     # Use baseline crystal params as the base for delta reconstruction
     # (log_cell_*_delta are relative to BASELINE, not current crystal)
     if baseline_crystal is None:
         raise ValueError(
             "Stage B requires baseline_crystal to reconstruct cell parameters. "
             "The cell deltas in Stage A telemetry are relative to the baseline crystal."
         )
     cell_params = baseline_crystal.get_unit_cell().parameters()
     ```

3. **Compilation check:**
   ```bash
   python -c "import dbex.refinement.stage_b; print('Compilation: OK')"
   ```
   Exit code must be 0.

4. **Run regression guard:**
   ```bash
   KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest \
     tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
     -v -s --tb=short \
     > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T083100Z/pytest_stage_b_c2.log 2>&1
   echo "Exit code: $?" | tee -a plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T083100Z/pytest_stage_b_c2.log
   ```

5. **Extract chi² values from test log:**
   ```bash
   grep -E "Stage [AB] (initial|final) chi" plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T083100Z/pytest_stage_b_c2.log | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T083100Z/chi2_values.txt
   ```

6. **Decision synthesis:**
   - If test PASSED and chi² offset ≤0.1%: Mark Phase C2 COMPLETE in summary
   - If test PASSED but offset >0.1%: Document offset in summary, mark as partial success
   - If test FAILED: Document failure signature in summary, keep Phase C2 in_progress

7. **Update implementation.md** Phase C2 status:
   - Add completion timestamp and artifacts path to implementation.md Phase C2 section
   - Mark checklist item complete if test passed

8. **Write summary** to `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T083100Z/summary.md`:
   - Describe the fix (baseline_crystal usage at line 163)
   - Report test outcome (PASS/FAIL, chi² offset %)
   - Include Turn Summary block (see End-of-Loop Hygiene in prompt)

9. **Commit:**
   ```bash
   git add -A && git commit -m "ARCH-REFINE-FLOW-001 Phase C2: Fix cell param base (baseline_crystal) — tests: $(grep -q PASSED plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T083100Z/pytest_stage_b_c2.log && echo passed || echo failed)"
   git push
   ```

## How-To Map

### Test Execution
```bash
# Regression guard (small detector)
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest \
  tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
  -v -s --tb=short \
  > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T083100Z/pytest_stage_b_c2.log 2>&1
```

### Chi² Offset Calculation
Extract Stage A final and Stage B initial chi² values from test log:
```bash
grep -E "Stage [AB] (initial|final) chi" plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T083100Z/pytest_stage_b_c2.log
```

Expected pattern (if fixed):
- Stage A final chi²: ~7.05e+08
- Stage B initial chi²: ~7.05e+08 (within 0.1%)

## Pitfalls To Avoid

1. **Do NOT use `crystal.get_unit_cell().parameters()`** — this is the bug! Use `baseline_crystal.get_unit_cell().parameters()` instead
2. **Do NOT skip the baseline_crystal validation guard** — if baseline_crystal is None, the fix cannot work
3. **Do NOT modify any other lines** — this is a one-location bugfix (line 163 only)
4. **Do NOT change telemetry extraction logic** (lines 144-151) — that code is correct
5. **Do NOT modify closure baseline_misset handling** (lines 2414-2416, 2496-2498) — already correct
6. **Device/dtype neutrality:** No changes to device/dtype handling needed for this fix
7. **Protected Assets:** No changes to specs, findings, or test registry needed (pure bugfix)

## If Blocked

1. **Document blocker** in `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T083100Z/blocker.md`:
   - Exact error message
   - File path and line number
   - What you tried

2. **Capture artifacts:**
   - Test log (even if incomplete)
   - Compilation error (if any)

3. **Mark attempt in Attempts History:**
   - Update `docs/fix_plan.md` ARCH-REFINE-FLOW-001 Attempts History with blocker details

4. **Do NOT retry more than once** — if blocked after 1 attempt, document and exit

## Findings Applied (Mandatory)

- **REFINE-FLOW-001:** Chi² offset between Stage A final and Stage B initial in engine delegation path. Root cause: cell parameter reconstruction using current crystal instead of baseline crystal. Fix: use `baseline_crystal.get_unit_cell().parameters()` at line 163.
- **GEOMETRY-003:** Baseline misset derivation (already handled correctly in closure)
- **PERF-WARM-012:** CPU fallback for canonical runs (not relevant for small detector bugfix)
- **REFINE-008:** Stage B shell modifier gates (will be validated by regression guard)

## Pointers

- **Root cause analysis:** `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T081911Z/analysis.md` (Hypothesis H1)
- **Implementation plan:** `plans/active/ARCH-REFINE-FLOW-001/implementation.md` (Phase C2)
- **Test file:** `tests/dbex/test_torch_refine_smoke.py:660-900` (test_stage_b_shell_modifiers)
- **Stage B code:** `dbex/refinement/stage_b.py:54-300` (run method)
- **Helper extraction:** `dbex/nanobrag_refinement.py:2087-2916` (Stage B helpers, completed in Phase C1a)

## Doc Sync Plan

Not applicable — no tests added/renamed this loop.

## Mapped Tests Guardrail

`test_stage_b_shell_modifiers` is Active and collects 1 test. No collection validation needed.
