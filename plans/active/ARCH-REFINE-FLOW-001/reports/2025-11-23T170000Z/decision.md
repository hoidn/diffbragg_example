# Phase E Telemetry Validation — Decision

**Initiative:** ARCH-REFINE-FLOW-001 Phase E  
**Date:** 2025-11-23  
**Loop:** i=234 (ralph)

## Problem

Phase E requires engine delegation telemetry enrichment: `engine_protocol` and `stage_modes` fields must be present in all telemetry returned by `run_nanobrag_refinement(..., use_engine_delegation=True)`.

Commit 42975bf (prior loop) fixed RefinementTelemetry schema but enrichment logic was misplaced in unreachable code branch.

## Root Cause Analysis

1. **Schema bugfix (commit 42975bf):** Added `engine_protocol` and `stage_modes` fields to RefinementTelemetry dataclass — CORRECT.

2. **Enrichment placement bug:**  
   - Enrichment code at lines 4371-4378 was placed inside a dormant branch (never executed).
   - Actual engine delegation for Stage-A-only mode occurs at lines 3800-3819 (Phase B2 code path).
   - Stage-A-only mode check (`stage_a_only_mode`) triggers Phase B2 path, bypassing Phase E enrichment.

## Solution

**Inject enrichment into Phase B2 engine delegation path (lines 3809-3814):**

```python
# Phase E: Enrich telemetry with engine protocol and stage modes
from dataclasses import asdict
telemetry_a_dict = asdict(telemetry_a)
telemetry_a_dict["engine_protocol"] = "stage_a"  # Stage-A-only mode
telemetry_a_dict["stage_modes"] = {}  # No Stage B/C enabled
telemetry_a_enriched = RefinementTelemetry(**telemetry_a_dict)
```

**Return enriched telemetry:** `return bragg_full, {"A": telemetry_a_enriched}`

## Validation

**Test:** `test_stage_a_engine_delegation_telemetry`  
- Validates `engine_protocol="stage_a"` and `stage_modes={}` for Stage-A-only mode.
- **Result:** PASSED (12.5s)

**Regression guard:** `test_stage_a_expansion`  
- Ensures existing engine delegation still works with enrichment.
- **Result:** PASSED

## Acceptance Criteria Met

- ✅ `engine_protocol` field present and correct ("stage_a" for Stage-A-only)
- ✅ `stage_modes` field present and correct ({} for Stage-A-only)
- ✅ Backward compatibility maintained (telemetry dict key "A" preserved)
- ✅ Phase A4 fields still present (`stage_type`, `mode`)
- ✅ Core telemetry intact (`canonical_chi_squared`, `masked_mse_trace_full`, `param_deltas`)

## Artifacts

- Test log: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T170000Z/pytest_engine_telemetry_validation.log`
- Test: `tests/dbex/test_torch_refine_smoke.py:789-888` (`test_stage_a_engine_delegation_telemetry`)
- Enrichment code: `dbex/nanobrag_refinement.py:3809-3814`

## Next Steps

1. Add ARCH-ENGINE-003 finding documenting enrichment placement pattern
2. Update TESTING_GUIDE.md with new selector
3. Mark Phase E checklist items complete in implementation.md
4. Commit and push

