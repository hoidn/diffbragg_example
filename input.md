# Phase C2 Chi² Offset Diagnostic Investigation (Loop i=209)

## Summary
Diagnose 9.3% chi-squared offset between Stage A final and Stage B initial in engine delegation path through focused parameter state capture.

## Mode
Docs

## Focus
ARCH-REFINE-FLOW-001 — Phase C2 bugfix (chi² offset root cause investigation)

## Branch
integration

## Mapped Tests
none — evidence-only loop (diagnostic script creation + execution)

## Artifacts
`plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T081911Z/`

## Do Now

### Context from Prior Loops

**Loop i=206 (commit a82893e):** Fixed asdict() conversion bug + verified StageB.name - chi² offset persisted (9.3%)

**Loop i=207-208 (commit dea42cd):** Added `baseline_crystal` parameter to `_build_final_bragg_from_stage_b_telemetry` helper - chi² offset STILL persisted (9.3%)

**Root Cause Analysis (Galph Loop i=209):**

After deep code review, I've identified that Ralph's fix in i=207-208 targeted the WRONG code path. The `_build_final_bragg_from_stage_b_telemetry` helper (lines 2713-2916) is used for the **final** Bragg regeneration AFTER Stage B optimization completes. It is NOT involved in computing the **initial** chi² that causes the test to fail.

The initial chi² comes from `_run_stage_b_lbfgs` line 2635 calling `compute_loss_stage_b` at iteration 0. Both the closure (lines 2414-2416, 2496-2498) AND StageB.run() (lines 163-199) already correctly handle baseline_misset, so the bug must be elsewhere.

**Hypothesis:** A subtle parameter mismatch exists where Stage B's initial reconstruction uses slightly different values than Stage A's final validation. Candidates:
1. Cell parameters using perturbed crystal instead of baseline
2. Scale parameter (log_scale) value divergence
3. Device/dtype mismatch (CPU vs CUDA)
4. HKL grid corruption

### Step 1: Revert Erroneous Signature Changes

Ralph accidentally added `=None` defaults to 7 REQUIRED parameters in loop i=208. Revert this error.

**File:** `dbex/nanobrag_refinement.py`
**Lines:** 2720-2726

**Before (INCORRECT from i=208):**
```python
def _build_final_bragg_from_stage_b_telemetry(
    telemetry_a,
    telemetry_b,
    detector,
    beam,
    crystal,
    baseline_crystal=None,
    inputs=None,          # ← WRONG
    hkl_grid=None,        # ← WRONG
    hkl_metadata=None,    # ← WRONG
    config=None,          # ← WRONG
    device=None,          # ← WRONG
    dtype=None,           # ← WRONG
    stage_a_ctx=None,
):
```

**After (CORRECT):**
```python
def _build_final_bragg_from_stage_b_telemetry(
    telemetry_a,
    telemetry_b,
    detector,
    beam,
    crystal,
    baseline_crystal,
    inputs,
    hkl_grid,
    hkl_metadata,
    config,
    device,
    dtype,
    stage_a_ctx=None,
):
```

### Step 2: Write Diagnostic Analysis to artifacts

**File:** `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T081911Z/analysis.md`

This file already exists (created by Galph). Read it to understand the hypothesis framework.

### Step 3: Write summary.md with Turn Summary

Document Ralph's i=208 attempt and why it didn't work. Explain that the helper targets the wrong code path.

**File:** `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T081911Z/summary.md`

**Template:**
```markdown
### Turn Summary
Fixed signature error from loop i=208 (removed erroneous `=None` defaults from 7 required parameters in `_build_final_bragg_from_stage_b_telemetry` helper).
Analyzed why loop i=208's baseline_crystal fix didn't resolve the chi² offset: the helper is used for final Bragg regeneration AFTER Stage B optimization, not for the initial chi² computation that fails the test.
Next: Create focused diagnostic script to capture parameter state at Stage A→B boundary and identify true divergence source (cell/misset/scale/device).
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T081911Z/ (analysis.md, summary.md)
```

### Step 4: Update galph_memory.md

Append new entry documenting this loop's action (signature revert + analysis + next diagnostic plan).

**File:** `galph_memory.md`

**Entry template:**
```markdown
## 2025-11-23T081911Z — ARCH-REFINE-FLOW-001 Phase C2 root cause analysis

- Focus: ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase C2 bugfix)
- Action Type: planning
- Key Observations: Reviewed Ralph's loop i=208 baseline_crystal fix attempt (commit dea42cd). Fix was structurally correct but targeted wrong code path (_build_final_bragg_from_stage_b_telemetry helper used for final Bragg regeneration AFTER Stage B optimization, not for initial chi² computation). Initial chi² computed by _run_stage_b_lbfgs calling compute_loss_stage_b at iteration 0 (line 2635). Both closure (lines 2414-2416, 2496-2498) and StageB.run() (lines 163-199) correctly handle baseline_misset, so bug must be parameter reconstruction mismatch. Reverted erroneous signature changes from i=208 (removed `=None` from 7 required params). Authored comprehensive analysis.md documenting 4 hypotheses: H1 cell params using perturbed crystal, H2 log_scale divergence, H3 device/dtype mismatch, H4 HKL grid corruption. Recommended diagnostic script approach to capture exact parameter state at Stage A→B boundary.
- Artifact Path: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T081911Z/
- Next Actions: Ralph creates diagnostic script to capture parameter comparison, identifies divergent parameter(s), fixes bug, reruns test.
- <Action State>: [planning]

2025-11-23T081911Z focus=ARCH-REFINE-FLOW-001 state=planning dwell=1 artifacts=plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T081911Z/ next_action=prepare_diagnostic_do_now_for_next_loop
```

### Step 5: Commit Changes

```bash
git add -A
git commit -m "$(cat <<'EOF'
ARCH-REFINE-FLOW-001 Phase C2 (Galph analysis): Revert signature error, identify wrong-path fix

**Problem:** Loop i=208's baseline_crystal fix didn't resolve 9.3% chi² offset despite being structurally correct.

**Root Cause Analysis:** The `_build_final_bragg_from_stage_b_telemetry` helper (lines 2713-2916) is used for FINAL Bragg regeneration AFTER Stage B optimization completes. It is NOT involved in computing the INITIAL chi² that causes test_stage_b_shell_modifiers to fail.

The initial chi² comes from `_run_stage_b_lbfgs` line 2635 calling `compute_loss_stage_b` at iteration 0. Both the closure (lines 2414-2416, 2496-2498) AND StageB.run() (lines 163-199) already correctly handle baseline_misset, so the bug must be a subtle parameter reconstruction mismatch.

**Changes:**
- Reverted erroneous signature from i=208: removed `=None` defaults from 7 required parameters (inputs, hkl_grid, hkl_metadata, config, device, dtype) in `_build_final_bragg_from_stage_b_telemetry`
- Authored analysis.md documenting 4 hypotheses for parameter divergence (cell/scale/device/HKL)
- Updated galph_memory.md with planning state + next diagnostic approach

**Next Actions:** Create diagnostic script to capture exact parameter state at Stage A→B boundary, identify divergent parameter, fix bug.

**Artifacts:** plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T081911Z/

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
git push
```

## How-To Map

1. **Signature revert:** Edit `dbex/nanobrag_refinement.py` lines 2720-2726
   - Remove `=None` from lines 2720-2726 for: `inputs`, `hkl_grid`, `hkl_metadata`, `config`, `device`, `dtype`
   - Keep `=None` ONLY for `baseline_crystal` (line 2719) and `stage_a_ctx` (line 2726)

2. **Read existing analysis.md:** `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T081911Z/analysis.md` (created by Galph)

3. **Write summary.md:** Document signature revert + wrong-path analysis + next diagnostic plan (see template in Step 3)

4. **Update galph_memory.md:** Append entry documenting this loop's planning action (see template in Step 4)

5. **Compilation check:**
   ```bash
   python -c "from dbex.nanobrag_refinement import run_nanobrag_refinement; print('OK')" 2>&1 | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T081911Z/compilation_check.log
   ```

6. **Commit:** Signature revert + analysis docs + galph_memory update

## Pitfalls To Avoid

1. **Do NOT run tests** - this is a docs-only planning loop
2. **Do NOT attempt code fixes yet** - next loop will create diagnostic script first
3. **Do NOT modify the baseline_crystal logic added in i=208** - that part was correct (just targeted wrong helper)
4. **Respect Environment Freeze** - no package installs
5. **Keep summary.md concise** - 3-5 sentences per Turn Summary guidelines

## If Blocked

1. **Signature revert unclear:** Check git diff for i=208 commit dea42cd to see what was changed
2. **Compilation fails:** Verify removed `=None` from exactly 7 params, kept for baseline_crystal + stage_a_ctx
3. **Can't understand analysis:** Focus on summary.md only, skip detailed hypothesis review

## Findings Applied

- **CONVERGENCE-001:** Zero-delta bypass (not applicable - Stage B has non-zero modifiers)
- **GEOMETRY-003:** baseline_misset computation (verified correct in closure)
- **POLICY-001:** Environment Freeze allows targeted source bugfixes (permitting signature revert)

## Pointers

- Analysis: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T081911Z/analysis.md` (Galph's hypothesis framework)
- Loop i=206 artifacts: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T075320Z/summary.md` (asdict fix)
- Loop i=208 commit: dea42cd (baseline_crystal attempt that didn't work)
- Code: `dbex/nanobrag_refinement.py:2713-2916` (_build_final_bragg_from_stage_b_telemetry helper)
- Code: `dbex/nanobrag_refinement.py:2635-2642` (_run_stage_b_lbfgs initial chi² computation - the REAL code path)
- Code: `dbex/refinement/stage_b.py:163-173` (cell parameter reconstruction - likely divergence location)

## Next Up

Next loop (i=210): Create diagnostic script per analysis.md recommendations, execute to identify divergent parameter, then fix the actual bug.
