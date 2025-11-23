# Phase C0 Baseline Blocker

## Failure Mode
**NameError: name 'canonical_roi_count' is not defined**

## Location
`dbex/nanobrag_refinement.py:2657`

```python
stage_b_total_work_items = canonical_roi_count if use_stage_b_roi_mode else n_panels
```

## Traceback
```
tests/dbex/test_torch_refine_smoke.py:1163: in test_stage_b_shell_modifiers
    bragg_refined, telemetry_dict = run_nanobrag_refinement(
dbex/nanobrag_refinement.py:2657: in run_nanobrag_refinement
    stage_b_total_work_items = canonical_roi_count if use_stage_b_roi_mode else n_panels
E   NameError: name 'canonical_roi_count' is not defined
```

## Test
`tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers`
- Detector: small
- Exit code: 1
- Test runtime: ~14.68s (failed before Stage B execution)

## Suspected Root Cause
Undefined variable reference in Stage B inline code. The variable `canonical_roi_count` is referenced but not defined in the Stage B section of `run_nanobrag_refinement`.

This appears to be a leftover reference from a prior refactor or incomplete implementation.

## Context
- Stage A completed successfully (HKL stats show successful grid generation for all ROIs)
- Failure occurs at the beginning of Stage B initialization (line 2657)
- `use_stage_b_roi_mode` flag is being evaluated, suggesting Stage B ROI-mode logic was being activated

## Minimal Repro Steps
```bash
cd /home/ollie/Documents/diffbragg_example_2/diffbragg_example
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
  -v --tb=short --smoke-detector-size=small
```

## Artifacts
- `pytest_collect_stage_b.log` — Collection verification (1 test collected ✓)
- `pytest_stage_b_small.log` — Full test output with traceback
- This blocker document

## Root Cause Analysis
The variable `canonical_roi_count` is defined at line 873 inside helper function `_build_stage_a_params`, but line 2657 attempts to use it in the main `run_nanobrag_refinement` function where it's NOT in scope.

However, at line 2241, the main function extracts `canonical_baseline = stage_a_context['canonical_baseline']`, which DOES contain `canonical_baseline["roi_count"]` (set at line 884 in the helper).

**Fix**: Replace `canonical_roi_count` with `canonical_baseline["roi_count"]` at all Stage B usage sites.

## Affected Lines
Search results for `canonical_roi_count` in `run_nanobrag_refinement` (lines 2087+):
- Line 2657: `stage_b_total_work_items = canonical_roi_count if use_stage_b_roi_mode else n_panels`
- Line 3078: `stage_b_roi_count_total = canonical_roi_count`
- Line 3079: `stage_b_roi_count_sampled = canonical_roi_count if not use_stage_b_roi_mode else len(sampled_stage_b_indices)`

All three need to be replaced with `canonical_baseline["roi_count"]`.

## Next Actions
1. Apply targeted bugfix per CLAUDE.md Environment Freeze exception policy
2. Save patch file to baseline/ directory
3. Document fix rationale in findings.md
4. Re-run baseline collection

## Status
**FIX IN PROGRESS** — Applying targeted bugfix under Environment Freeze exception (locally available source code blocking critical path).

---
Created: 2025-11-23T061726Z
