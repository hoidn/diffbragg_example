### Turn Summary
Refactored `_build_stage_a_params` from 13 positional parameters to single typed `StageAInputContext` parameter per ARCH-STAGE-CONTEXT-CONSOLIDATION Phase C.1.
Call site now constructs `StageAInputContext` dataclass before invoking the helper; function body unpacks context fields for backwards compatibility with existing logic.
Tests: 6/6 context module tests PASS, Stage A expansion test collects successfully.
Next: Phase C.2 — refactor `_build_stage_b_params` signature to use `StageBInputContext`.
Artifacts: plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/reports/2025-12-09T010000Z/ (pytest_context.log, pytest_smoke_collect.log)

---

## Implementation Details

### Changes Made

1. **Signature update** (stage_a.py:100-104)
   - FROM: 13 positional parameters (crystal, detector, inputs, config, device, dtype, hkl_grid, hkl_metadata, sigma_floor_sq_cache, baseline_crystal, baseline_detector, beam)
   - TO: `_build_stage_a_params(self, config: 'RefinementConfig', input_ctx: 'StageAInputContext')`

2. **Unpacking code** (stage_a.py:132-144)
   - Added import: `from dbex.refinement.context import StageAInputContext`
   - Added unpacking of all 11 fields from `input_ctx` for backwards compatibility

3. **Call site update** (stage_a.py:1819-1837)
   - Constructs `StageAInputContext` with all fields
   - Calls `_build_stage_a_params(config=self._config, input_ctx=input_ctx)`

### Test Results

- **Context module tests**: 6/6 PASSED
  - test_build_refinement_context_copies_job_context_metadata
  - test_build_refinement_context_explicit_metadata_overrides_job_context
  - test_build_job_context_rejects_invalid_sigma_reference
  - test_build_job_context_rejects_empty_sigma_provenance
  - test_build_job_context_validates_hkl_metadata_has_halo
  - test_build_job_context_accepts_valid_inputs

- **Stage A smoke collection**: 1 test collected (test_stage_a_expansion)

### SPEC/ADR Alignment

Per `docs/findings.md::ARCH-STAGE-CTX-001`:
> Context dataclasses must be located in `dbex/refinement/context.py`

The `StageAInputContext` dataclass at context.py:1033-1071 is now used as specified.
