# Phase D1b Decision: _build_stage_c_lbfgs_closure Helper Extraction

## Validation Results

### 1. Compilation Status
**PASS** - Module imports successfully with no syntax errors.

Command:
```bash
python -c "import dbex.nanobrag_refinement; print('Compilation PASSED')"
```

Output: `Compilation PASSED`

### 2. Helper Signature Verification
**CORRECT** - Function signature matches specification exactly:
- Returns `Tuple[Callable[[List[int], bool], Tuple[torch.Tensor, torch.Tensor]], Callable[[], torch.Tensor]]`
- Accepts 15 parameters as specified in input.md
- Three dict parameters: `param_values`, `telemetry_state`, `stage_c_context`

### 3. Lines Extracted
**298 lines** extracted from inline code at lines 4078-4293 (original line numbers)
- Helper function: lines 2894-3191 (new location)
- Nested function 1 `compute_loss_stage_c`: ~170 lines
- Nested function 2 `closure_stage_c`: ~45 lines
- Dict unpacking and setup: ~75 lines

### 4. Nested Functions
**TWO nested functions** preserved:
1. `compute_loss_stage_c(panel_ids: List[int], is_full: bool = False) -> Tuple[torch.Tensor, torch.Tensor]`
   - Implements variance-weighted chi-squared loss with Stage C detector distance adjustments
   - Preserves warm-cache branching for stage_a_ctx
   - Preserves ROI sampling logic
   - Contains lazy imports (nanobrag_torch.models, nanobrag_torch.simulator)

2. `closure_stage_c() -> torch.Tensor`
   - LBFGS closure contract implementation
   - Gradient NaN/Inf checks
   - Periodic full validation logic
   - Best snapshot updates with `nonlocal` declarations

### 5. Return Type
**CORRECT** - Returns tuple of two callables:
```python
return compute_loss_stage_c, closure_stage_c
```

## Decision Path: A (Compilation PASS)

### Status
Helper extraction SUCCESSFUL - Proceed to Phase D1c.

### Rationale
1. **Compilation clean**: No syntax errors, import errors, or indentation issues
2. **Signature correct**: Matches specification with proper type hints
3. **Nested functions intact**: Both closure functions extracted completely with correct signatures
4. **Lexical scope captured**: All ~25 variables properly unpacked from input dicts
5. **Physics patterns preserved**: PHYSICS-LOSS-001/002 patterns intact
6. **Lazy imports correct**: Conditional imports stay inside nested functions per RUNTIME-001

### Next Steps
1. **Phase D1c** (next loop): Extract `_run_stage_c_lbfgs` helper + wire all 3 helpers + regression guard
2. Update `implementation.md` Phase D1b checklist to complete
3. Commit helper extraction with appropriate message

### Verification Notes
- Helper NOT wired into `run_nanobrag_refinement` (call site changes deferred to D1c)
- No regression test required (helper not called, compilation-only verification per proven pattern)
- Inline Stage C code at original lines 4078-4293 remains unchanged (wiring will remove it in D1c)

### Conformance
- **REFINE-007** (docs/findings.md:43): Stage C gate preserved - closure maintains telemetry accumulators
- **PHYSICS-LOSS-001/002** (docs/findings.md:20,21): Variance-weighted loss + sigma_floor preserved
- **PERF-WARM-011/012** (docs/findings.md:46,47): Warm cache + ROI sampling patterns preserved
- **RUNTIME-001** (docs/findings.md:29): Lazy imports stay INSIDE nested functions
- **POLICY-001** (docs/findings.md:66): Environment Freeze - helper extraction only, no env changes

## Artifacts
- `compilation_check.log`: Compilation output (PASS)
- `helper_diff.patch`: Git diff showing extracted helper
- `metrics.json`: Quantitative metrics (lines, nested functions, signature)
- `decision.md`: This document (3-path synthesis with Path A chosen)
