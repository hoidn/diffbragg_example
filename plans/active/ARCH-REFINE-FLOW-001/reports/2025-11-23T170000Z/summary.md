# ARCH-REFINE-FLOW-001 Phase E Telemetry Validation — Loop i=234

**Date:** 2025-11-23  
**Actor:** ralph  
**Initiative:** ARCH-REFINE-FLOW-001 Phase E — Engine Protocol Telemetry Enrichment  
**Artifacts:** plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T170000Z/

## Objective

Validate Phase E telemetry enrichment: `engine_protocol` and `stage_modes` fields must be present and correct for all engine delegation paths.

## Deliverables

1. **Phase E Bugfix:** Corrected telemetry enrichment placement (commit 42975bf added schema fields but enrichment code was in unreachable branch)
2. **Validation Test:** `test_stage_a_engine_delegation_telemetry` (tests/dbex/test_torch_refine_smoke.py:789-888)
3. **ARCH-ENGINE-003 Finding:** Documented enrichment placement pattern for future engine paths
4. **Regression Validation:** Confirmed existing engine delegation (test_stage_a_expansion) unaffected

## Problem

Commit 42975bf (loop i=232) added `engine_protocol` and `stage_modes` fields to RefinementTelemetry schema but enrichment logic was placed inside a dormant code branch (lines 4282-4380) that was never executed. 

Stage-A-only mode execution path (lines 3800-3819, Phase B2 implementation) returned telemetry WITHOUT enrichment, causing Phase E validation to fail.

## Root Cause

**Control flow analysis:**
- `stage_a_only_mode` check (line 3777) triggered Phase B2 engine delegation path (lines 3782-3819)
- Phase E enrichment code (lines 4371-4378) was placed in separate branch after inline Stage A helper path
- Phase B2 path returned early at line 3819, bypassing Phase E enrichment entirely

## Solution

**Injected enrichment into Phase B2 engine delegation path (lines 3809-3814):**

```python
# Phase E: Enrich telemetry with engine protocol and stage modes
from dataclasses import asdict
telemetry_a_dict = asdict(telemetry_a)
telemetry_a_dict["engine_protocol"] = "stage_a"  # Stage-A-only mode
telemetry_a_dict["stage_modes"] = {}  # No Stage B/C enabled
telemetry_a_enriched = RefinementTelemetry(**telemetry_a_dict)
```

**Pattern:** `asdict()` → inject new fields → reconstruct `RefinementTelemetry` → return

## Validation

**Primary Test:** `test_stage_a_engine_delegation_telemetry`
- Selector: `pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_engine_delegation_telemetry`
- Runtime: 12.5s
- Result: **PASSED**
- Validates:
  - `engine_protocol == "stage_a"` ✓
  - `stage_modes == {}` ✓
  - Backward compatibility (telemetry key "A") ✓
  - Phase A4 fields (`stage_type="stage_a"`, `mode`) ✓
  - Core telemetry (`canonical_chi_squared`, `masked_mse_trace_full`, `param_deltas`) ✓

**Regression Guard:** `test_stage_a_expansion`
- Selector: `pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`
- Result: **PASSED**
- Confirms existing engine delegation remains functional after enrichment injection

## Acceptance Criteria Met

- ✅ Schema fields `engine_protocol` and `stage_modes` present in RefinementTelemetry (commit 42975bf)
- ✅ Enrichment logic injected into active engine delegation path (lines 3809-3814)
- ✅ Stage-A-only mode returns `engine_protocol="stage_a"`, `stage_modes={}`
- ✅ Backward compatibility maintained (telemetry dict key "A")
- ✅ Test coverage added (`test_stage_a_engine_delegation_telemetry`)
- ✅ Regression guards passing (`test_stage_a_expansion`)
- ✅ ARCH-ENGINE-003 finding added to knowledge base

## Architecture Notes

**Enrichment Pattern (for future engine paths):**

All engine delegation returns must apply enrichment before final return:

```python
# Extract telemetry from engine
telemetry_dict = engine.run(inputs)

# Build protocol + modes descriptors
engine_protocol = "→".join([s.name for s in stages])  # e.g., "stage_a→stage_b→stage_c"
stage_modes = {"b": "shell", "c": "detector_offsets"}  # per config

# Enrich each telemetry object
from dataclasses import asdict
for key, telem in telemetry_dict.items():
    telem_dict = asdict(telem)
    telem_dict["engine_protocol"] = engine_protocol
    telem_dict["stage_modes"] = stage_modes
    telemetry_dict[key] = RefinementTelemetry(**telem_dict)

# Return enriched telemetry (maintaining backward-compatible keys like "A", "B", "C")
return bragg_final, telemetry_dict
```

**Current Coverage:**
- Stage-A-only mode (lines 3809-3814): ✓ COMPLETE
- A→B mode: PENDING (apply pattern to Phase C2 path)
- A→B→C mode: PENDING (apply pattern when enabled)

## Artifacts

- **Test:** tests/dbex/test_torch_refine_smoke.py:789-888
- **Enrichment Code:** dbex/nanobrag_refinement.py:3809-3814
- **Test Logs:** pytest_engine_telemetry_validation.log
- **Decision:** decision.md
- **Finding:** docs/findings.md#ARCH-ENGINE-003

## Next Steps (Phase E Completion)

1. Register test selector in TESTING_GUIDE.md §2
2. Update implementation.md Phase E checklist (mark E1-E3 done, E4-E5 pending)
3. Apply enrichment pattern to A→B and A→B→C paths (deferred to later phases)

---

### Turn Summary

Implemented Phase E telemetry enrichment by injecting `engine_protocol` and `stage_modes` fields into the active Stage-A-only engine delegation path (lines 3809-3814); schema was already correct (commit 42975bf) but enrichment code was in unreachable branch.
Resolved placement bug with `asdict()` → inject → reconstruct pattern and validated via new `test_stage_a_engine_delegation_telemetry` test (PASSED 12.5s); regression guard also clean.
Next: register selector in TESTING_GUIDE, update Phase E checklist, and apply enrichment pattern to A→B/A→B→C paths when they're enabled.
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T170000Z/ (decision.md, pytest_engine_telemetry_validation.log)
