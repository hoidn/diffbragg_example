# Phase C1a-loop1: Extract `_build_stage_b_params` Helper ONLY

## Summary
Extract the first Stage B helper function (`_build_stage_b_params`, ~140 lines) from inline code in `run_nanobrag_refinement`, verify compilation, commit partial progress. NO regression guard required (helper not yet wired).

## Mode
none

## Focus
ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase C1a-loop1)

## Branch
integration

## Mapped tests
none — evidence-only (compilation check only, helper not yet wired)

## Artifacts
`plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T060833Z/`
- `phase_c1a_loop1_extraction_diff.patch` — Diff of extracted helper
- `compilation_check.log` — Python compilation output (exit code 0 required)
- `summary.md` — Turn Summary block

## Do Now

You are implementing **Phase C1a-loop1** of the ARCH-REFINE-FLOW-001 multi-loop Stage B extraction strategy, approved by Galph after Phase B's successful 7-loop completion.

**CRITICAL SCOPE LIMIT:** This loop extracts **ONLY** the `_build_stage_b_params` helper (~140 lines). Do NOT extract the other two helpers (`_build_stage_b_lbfgs_closure`, `_run_stage_b_lbfgs`) or refactor the main function. Those will be handled in subsequent loops (C1a-loop2, C1a-loop3).

### Context
- **Phase B Precedent:** Phase B successfully extracted Stage A in 3 sub-loops (B1a-loop1: helper1, B1a-loop2: helper2, B1a-loop3: helper3 + refactor)
- **Phase C0 Baseline:** test_stage_b_shell_modifiers PASSED after `canonical_roi_count` bugfix (commit c1a9e32)
- **Stage B Inline Code:** Lines ~2527-3137 in `dbex/nanobrag_refinement.py` (~610 lines total)
- **Helper 1 Target:** Lines ~2570-2710 (parameter initialization + telemetry state + optimizer setup)

### Step-by-Step Tasks

#### 1. Review Phase C0 Baseline Artifacts
Read the following to understand the current Stage B code structure:
- `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T061726Z/baseline/summary.md`
- `dbex/nanobrag_refinement.py` lines 2527-2750 (Stage B initialization section)

#### 2. Identify Helper 1 Extraction Boundaries
Locate the Stage B initialization code block that sets up:
- Shell modifier raw parameters (`shell_modifier_raw`)
- Optimizer (Adam for shell modifiers)
- Telemetry accumulators (chi_squared_trace, masked_mse_trace, variance floor stats, perf counters)
- CPU fallback context (`use_stage_b_cpu_fallback`, `stage_b_eval_stage_a_ctx`)
- ROI/panel mode configuration (`use_stage_b_roi_mode`, `sampled_stage_b_indices`)

**Expected boundaries:** Lines ~2570-2710 (approximately 140 lines)

**Signature to implement:**
```python
def _build_stage_b_params(
    config: RefinementConfig,
    device: torch.device,
    dtype: torch.dtype,
    stage_a_ctx: Optional[Dict[str, Any]],
    canonical_baseline: Dict[str, Any],
    n_panels: int,
    sampled_panel_ids: List[int],
    sigma_floor_sq_cache: Dict[torch.device, torch.Tensor],
    use_stage_a_roi_mode: bool,
) -> Dict[str, Any]:
    """
    Build Stage B shell modifier parameters, optimizer, and telemetry state.

    Returns:
        param_values: Dict containing:
            - params: List[torch.Tensor] — Trainable shell_modifier_raw
            - optimizer: torch.optim.Adam — Optimizer for shell modifiers
            - telemetry_state: Dict — Accumulators for chi_squared/masked_mse traces, perf counters
            - stage_b_eval_stage_a_ctx: Optional[Dict] — CPU-cloned or original Stage A context
            - use_stage_b_cpu_fallback: bool
            - stage_b_use_warm_cache: bool
            - stage_b_cache_mode: str — "warm" or "cold"
            - use_stage_b_roi_mode: bool
            - stage_b_roi_label: str — "roi" or "panel"
            - stage_b_total_work_items: int
            - sampled_stage_b_indices: List[int]
            - full_stage_b_indices: List[int]
            - default_f_fallback_count: int
    """
```

#### 3. Extract Helper Function Code
**Copy** lines ~2570-2710 from `run_nanobrag_refinement` into a new function `_build_stage_b_params` placed **immediately before** the `run_nanobrag_refinement` function definition (around line 2087).

**Preserve:**
- All variable initializations (shell_modifier_raw, optimizer, telemetry lists)
- All comments (especially PHYSICS-LOSS-002, PERF-WARM-011/012 references)
- Exact indentation and logic flow

**Convert local variables to function parameters or return dict entries:**
- Input parameters: config, device, dtype, stage_a_ctx, canonical_baseline, n_panels, sampled_panel_ids, sigma_floor_sq_cache, use_stage_a_roi_mode
- Return dict `param_values` with ALL initialized variables that Stage B LBFGS closure will need

#### 4. Verify Compilation (NO Runtime Calls)
**Run Python syntax check:**
```bash
cd /home/ollie/Documents/diffbragg_example
python -c "import dbex.nanobrag_refinement" 2>&1 | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T060833Z/compilation_check.log
echo "Exit code: $?" >> plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T060833Z/compilation_check.log
```

**Expected:** Exit code 0 (no SyntaxError, ImportError)

**If compilation FAILS:** Fix the error, document the fix, retry. Do NOT proceed to commit if compilation fails.

#### 5. Generate Diff Patch
Save the extraction diff for review:
```bash
git diff dbex/nanobrag_refinement.py > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T060833Z/phase_c1a_loop1_extraction_diff.patch
```

#### 6. Update Implementation Plan Checklist
Mark Phase C1a-loop1 as COMPLETE in `plans/active/ARCH-REFINE-FLOW-001/implementation.md` (add a sub-bullet under Phase C checklist noting extraction date and helper signature).

#### 7. Write Turn Summary
Create `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T060833Z/summary.md` with the Turn Summary block (3-5 sentences: what was extracted, compilation status, next step).

#### 8. Commit Partial Progress
**Commit message:**
```
ARCH-REFINE-FLOW-001 Phase C1a-loop1: Extract _build_stage_b_params helper (~140 lines) — tests: not run
```

**Commands:**
```bash
git add -A
git commit -m "ARCH-REFINE-FLOW-001 Phase C1a-loop1: Extract _build_stage_b_params helper (~140 lines) — tests: not run"
git push
```

## How-To Map

### 1. Locate Stage B Initialization Block
```bash
cd /home/ollie/Documents/diffbragg_example
# Find shell_modifier_raw initialization (start of helper 1 scope)
grep -n "shell_modifier_raw = " dbex/nanobrag_refinement.py | head -1

# Find sampled_stage_b_indices initialization (end of helper 1 scope)
grep -n "sampled_stage_b_indices = " dbex/nanobrag_refinement.py | grep -A 5 "full_stage_b_indices"
```

### 2. Extract Helper Function
**File:** `dbex/nanobrag_refinement.py`

**Insertion point:** Line ~2086 (immediately before `def run_nanobrag_refinement`)

**Extraction pattern (from Phase B):**
1. Copy target lines into new function definition
2. Replace hardcoded values with function parameters
3. Collect all initialized variables into return dict
4. Add comprehensive docstring with Returns section

### 3. Compilation Check
```bash
python -c "import dbex.nanobrag_refinement" 2>&1 | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T060833Z/compilation_check.log
echo "Exit code: $?" >> plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T060833Z/compilation_check.log
```

### 4. Artifact Generation
```bash
# Generate diff patch
git diff dbex/nanobrag_refinement.py > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T060833Z/phase_c1a_loop1_extraction_diff.patch

# Line count verification
wc -l dbex/nanobrag_refinement.py
```

## Pitfalls To Avoid

1. **DO NOT extract helpers 2 or 3** — This loop is ONLY for `_build_stage_b_params` (~140 lines). Helpers 2 and 3 come in C1a-loop2 and C1a-loop3.

2. **DO NOT refactor `run_nanobrag_refinement` to call the helper** — The helper is not wired yet. It's just a function definition added to the file.

3. **DO NOT run tests** — No regression guard required for partial extraction (per Phase B precedent).

4. **Preserve all imports** — If helper code uses `torch`, `time.perf_counter`, or `_build_stage_a_context`, ensure those imports remain accessible.

5. **Preserve all comments** — PHYSICS-LOSS-002, PERF-WARM-011/012 comments are critical documentation.

6. **Use correct dict access** — `canonical_baseline["roi_count"]` not `canonical_roi_count` (per REFINE-009 bugfix)

7. **Return ALL initialized variables** — The closure (helper 2) will need shell_modifier_raw, optimizer, telemetry lists, CPU fallback context, ROI indices, etc.

8. **No device/dtype changes** — Preserve exact device/dtype handling (CPU fallback logic is critical)

9. **No optimizer changes** — Keep Adam with LR=config.stage_b_lr unchanged

10. **Environment Freeze** — Do not install packages. This is a pure refactor.

## If Blocked

**Scenario A: Compilation Error**
- Read error message carefully
- Fix syntax/import error
- Re-run compilation check
- Document fix in summary.md

**Scenario B: Unclear Helper Boundaries**
- Use `grep -n "shell_modifier_raw"` to find start
- Use `grep -n "full_stage_b_indices"` to find end
- Cross-reference with Phase B helper 1 extraction pattern (lines 761-996 in Phase B1a-loop1)
- If still unclear, document ambiguity and commit what you have

**Scenario C: Git Conflicts**
- Run `git status` to identify conflicted files
- Resolve conflicts manually (keep intended content)
- Run `git add` on resolved files
- Continue with commit

## Findings Applied

- **REFINE-009** (canonical_roi_count scope fix) — Use `canonical_baseline["roi_count"]` not `canonical_roi_count`
- **PERF-WARM-011** (Stage B GPU OOM) — CPU fallback logic must be preserved exactly
- **PERF-WARM-012** (Stage B warm cache on CPU) — StageAContext cloning for CPU eval must be preserved
- **PHYSICS-LOSS-002** (variance floor) — Variance floor telemetry accumulators must be in return dict
- **REFINE-008** (Stage B acceptance gates) — Telemetry structure preserved for future validation

## Pointers

- **Spec:** docs/spec-db-workflow.md §7 (Refinement Protocol Architecture)
- **Implementation Plan:** plans/active/ARCH-REFINE-FLOW-001/implementation.md (Phase C checklist lines 179-186)
- **Fix Plan:** docs/fix_plan.md:181-200 (ARCH-REFINE-FLOW-001 entry, Phase C status)
- **Phase B Precedent:** plans/active/ARCH-REFINE-FLOW-001/implementation.md:86-109 (B1a-loop1/2/3 successful pattern)
- **Phase C0 Baseline:** plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T061726Z/baseline/summary.md
- **Findings:** docs/findings.md rows 67 (REFINE-009), 26 (PERF-WARM-011), 27 (PERF-WARM-012), 35 (PHYSICS-LOSS-002), 61 (REFINE-008)

## Next Up (if finished early)

**DO NOT start next helper.** This loop is scoped to helper 1 only. If you finish early:
1. Double-check compilation passed (exit code 0)
2. Verify diff patch generated
3. Review Turn Summary for clarity
4. Commit and push
5. End loop gracefully

Galph will plan C1a-loop2 (extract `_build_stage_b_lbfgs_closure` helper) in the next supervisor iteration.
