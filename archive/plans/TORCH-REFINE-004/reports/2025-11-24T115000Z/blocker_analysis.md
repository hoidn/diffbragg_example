# Phase 8 Blocker Analysis — KeyError 'shell_indices'

**Initiative:** TORCH-REFINE-004 (Stage B Per-Reflection Mode Migration)

**Date:** 2025-11-24T115000Z

**Blocker:** KeyError 'shell_indices' at `dbex/refinement/stage_b.py:343` (old line numbering, corresponds to line 245 in current wrapper code)

---

## Symptom

Ralph's Phase 8 attempt (commit 8e8ea55, loop i=263) executed:
1. ✓ Test fixture fix (crystal_symmetry injection, HKL indices grid build)
2. ✓ Default enforcement (RefinementConfig.stage_b_mode = "per_reflection")
3. ✓ UnboundLocalError fixes (config_stage_b_mode_override initialization)
4. ✓ TypeError fix (initialize_asu_modifiers parameter name)

**Result:** All compilation + unit tests PASSED, but E2E per-reflection smoke test FAILED with:
```
KeyError: 'shell_indices'
  File "dbex/refinement/stage_b.py", line 245, in run
    shell_indices = param_values['shell_indices']
```

**Evidence:**
- ASU mapping succeeded (n_asu ~34K unique reflections per stdout)
- Friedel folding working correctly
- No fallback warnings → per-reflection mode executed
- Error occurs AFTER Stage A completes, during Stage B wrapper initialization

---

## Root Cause Analysis

### 1. Mode Branching in _build_stage_b_params (dbex/nanobrag_refinement.py)

**Lines 2662-2673:**
```python
# Add mode-specific fields
if config_stage_b_mode_override == "per_reflection":
    param_dict.update({
        'asu_indices': asu_indices_t,
        'n_asu_unique': n_asu_unique,
        'log_modifiers': log_modifiers,
    })
else:  # shell mode
    param_dict.update({
        'shell_indices': shell_indices,
        'shell_edges': shell_edges,
        'shell_modifier_raw': shell_modifier_raw,
    })
```

**Observation:** `_build_stage_b_params` creates **mode-specific keys** in the returned param_dict:
- Per-reflection mode: `asu_indices`, `n_asu_unique`, `log_modifiers`
- Shell mode: `shell_indices`, `shell_edges`, `shell_modifier_raw`

### 2. Stage B Wrapper Param Extraction (dbex/refinement/stage_b.py)

**Lines ~340-350 (after param_values dict from _build_stage_b_params):**
```python
# Extract variables needed for helper 2/3 calls and telemetry assembly
shell_indices = param_values['shell_indices']  # LINE 343 — UNCONDITIONAL ACCESS
shell_edges = param_values['shell_edges']
# ... (more shell-mode extractions)
```

**Bug:** Wrapper **unconditionally extracts `shell_indices`** without checking `param_values['stage_b_mode']` first.

**Consequence:** When `stage_b_mode == "per_reflection"`, param_values dict does NOT contain `shell_indices` key → KeyError.

---

## Fix Specification

### Change Location
`dbex/refinement/stage_b.py` lines ~342-360

### Implementation
```python
# Extract mode from param_values
stage_b_mode = param_values['stage_b_mode']

# Mode-aware parameter extraction
if stage_b_mode == "per_reflection":
    # Per-reflection mode: extract ASU parameters
    asu_indices = param_values['asu_indices']
    log_modifiers = param_values['log_modifiers']
    n_asu_unique = param_values['n_asu_unique']
    # Shell-mode keys are None in per-reflection mode
    shell_indices = None
    shell_edges = None
else:  # shell mode
    # Shell mode: extract shell parameters
    shell_indices = param_values['shell_indices']
    shell_edges = param_values['shell_edges']
    shell_modifier_raw = param_values['shell_modifier_raw']
    # ASU-mode keys are None in shell mode
    asu_indices = None
    n_asu_unique = 0
```

### Additional Checks
1. **Helper function calls (line ~290):** Verify `_build_stage_b_lbfgs_closure` can handle both modes (may extract from param_values internally OR require explicit parameters)
2. **Telemetry assembly (lines ~340-422):** Verify wrapper telemetry logic handles per-reflection mode fields (n_asu_unique, optimizer_type, asu_modifier_stats)

---

## Validation Protocol

### 1. Compilation Check
```bash
python -c "from dbex.refinement.stage_b import StageB"
```
Expected: No import errors

### 2. Phase 6 Unit Regression (5 tests)
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest tests/dbex/test_stage_b_asu_mapping.py -v
```
Expected: 5/5 PASSED, runtime <2s (baseline 1.04s per commit 19dd43e)

### 3. Shell Mode Regression
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers -vv
```
Expected: PASSED, runtime ~13-15s (baseline 13.66s per commit aebdddd)

### 4. Per-Reflection Smoke (currently BLOCKED by KeyError)
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke -vv
```
Expected after fix:
- Get past line 343 KeyError
- ASU telemetry fields present (n_asu_unique ~34K, optimizer_type="adam", asu_modifier_stats)
- Chi² improvement vs Stage A
- Convergence status ok/converged/early_stop

---

## Decision Tree

### Path A: All 4 Validation Tests PASS
- **Outcome:** Blocker resolved, per-reflection E2E validated
- **Next:** Galph assesses Phase 8 completion, plans Phase 9 (documentation)
- **Artifacts:** pytest logs showing PASS + telemetry validation

### Path B: Per-Reflection Test New Error (not KeyError 'shell_indices')
- **Outcome:** KeyError resolved but new issue emerged
- **Next:** Ralph documents new error type + full traceback, classifies (telemetry/optimizer/ASU/tensor), escalates to Galph
- **Max Retries:** 2 cycles before escalating to new sub-initiative

### Path C: Shell Mode Regression FAIL
- **Outcome:** Mode isolation fix broke shell path
- **Next:** Ralph rollbacks wrapper changes, verifies shell-mode code paths unchanged, debugs conditional logic
- **Root Cause:** Likely conditional extraction introduced bug in shell branch

### Path D: Compilation Error
- **Outcome:** Python syntax error or import error
- **Next:** Ralph fixes syntax, revalidates compilation check
- **Common Issues:** Indentation, missing colon, undefined variable

---

## Confidence Assessment

**Root Cause Confidence:** 95%
- Evidence: KeyError traceback points to exact line (stage_b.py:343)
- Evidence: _build_stage_b_params creates mode-specific keys (lines 2662-2673)
- Evidence: Wrapper accesses shell_indices unconditionally (no mode check before line 343)
- Evidence: ASU mapping succeeded (n_asu ~34K per stdout) → per-reflection mode executed correctly

**Fix Confidence:** 90%
- Fix is straightforward: conditional extraction based on stage_b_mode
- Pattern already established in _build_stage_b_params (lines 2662-2673)
- Risk: Helper function compatibility (may need signature updates)
- Risk: Telemetry assembly compatibility (may need mode-aware branches)

**Single-Loop Delivery Confidence:** 85%
- Estimated effort: 1-1.5 hours (wrapper fix ~30 min, validation ~45 min, decision synthesis ~15 min)
- Risks: LOW (isolated wrapper change, clear validation path, regression guards in place)

---

## Findings Applied

- **REFINE-001/002/005:** LBFGS scale warm-start, acceptance gate, halo-padded HKL grid mandatory
- **SCALE-001/002:** Unscaled structure factors, global post-simulation factor
- **PHYSICS-LOSS-001:** Variance-weighted loss function
- **POLICY-001:** Environment Freeze (no pip installs, dbex-only changes)
- **ARCH-ENGINE-002:** Lazy torch imports preserved
- **spec-db-workflow.md:59:** Per-reflection SHALL be default (Phase 8 objective)
- **spec-db-workflow.md:60:** Shell mode fallback permitted
- **spec-db-workflow.md:61:** Tricubic + halo mandatory
- **spec-db-workflow.md:107:** Optimizer flexibility (LBFGS/Adam per parameter count gate)

---

## References

- **Error Traceback:** `plans/active/TORCH-REFINE-004/reports/2025-11-24T095000Z/pytest_per_reflection_smoke_retry3.log:343-346`
- **Mode Branching Implementation:** `dbex/nanobrag_refinement.py:2662-2673`
- **Wrapper Param Extraction:** `dbex/refinement/stage_b.py:240-425`
- **Phase 7 Implementation:** Commit 936d6e0 (ASU integration + mode branching)
- **Phase 8 Assessment:** `plans/active/TORCH-REFINE-004/reports/2025-11-24T095000Z/phase_8_assessment.md`
- **Implementation Plan:** `plans/active/TORCH-REFINE-004/implementation.md:160-180`
