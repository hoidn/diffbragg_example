# Phase C2 Bugfix Summary (Loop i=206)

## Problem Statement

**SPEC Lines Implemented:**
- spec-db-workflow.md:31-34 (Refinement Protocol Architecture, Stage delegation)
- spec-db-core.md (RefinementTelemetry dataclass structure)

## Changes

### Bug 1: RefinementTelemetry dict conversion (dbex/nanobrag_refinement.py:3089-3097)

**Root Cause:** Code attempted to call `.items()` on `RefinementTelemetry` dataclass instances (`telemetry_a_raw`, `telemetry_b_raw`) without first converting them to dicts.

**Fix Applied:**
```python
# Before (BROKEN):
telemetry_b = RefinementTelemetry(**{k: v for k, v in telemetry_b_raw.items() if k not in [...]})

# After (FIXED):
from dataclasses import asdict
telemetry_a_dict = asdict(telemetry_a_raw)
telemetry_b_dict = asdict(telemetry_b_raw)
telemetry_b = RefinementTelemetry(**{k: v for k, v in telemetry_b_dict.items() if k not in [...]})
```

### Bug 2: StageB.name property verification

**Status:** ALREADY CORRECT. The `StageB.name` property correctly returns `"stage_b"` (dbex/refinement/stage_b.py:39-42).

### Bug 3: enable_warm_cache typo (dbex/nanobrag_refinement.py:2853)

**Root Cause:** Code referenced `config.enable_warm_cache`, but the correct attribute is `config.enable_stage_a_warm_cache` per RefinementConfig definition (line 294).

**Fix Applied:**
```python
# Before (BROKEN):
stage_b_use_warm_cache = config.enable_warm_cache and stage_a_ctx is not None

# After (FIXED):
stage_b_use_warm_cache = config.enable_stage_a_warm_cache and stage_a_ctx is not None
```

## Test Results

**Targeted test:** `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers`

**Progress:**
1. ✅ Compilation check passed
2. ✅ Original Bug 1 (line 3089-3090) fixed - no AttributeError on `.items()`
3. ✅ Bug 2 verified - StageB.name returns "stage_b"
4. ✅ Bug 3 (line 2853) fixed - no AttributeError on `enable_warm_cache`
5. ✅ Engine delegation path executes successfully (StageA → StageB)
6. ❌ **NEW ISSUE DISCOVERED:** Chi-squared discrepancy between Stage A final (7.053e+08) and Stage B initial (7.709e+08) — **9.3% systematic offset**

## Findings

### REFINE-FLOW-001: Engine Delegation Chi-Squared Offset

**Symptom:** When using RefinementEngine([StageA(), StageB()]) delegation path, Stage B initial chi² differs from Stage A final chi² by ~9.3% (tolerance: 0.1%).

**First Observed:** 2025-11-23T075320Z (ARCH-REFINE-FLOW-001 Phase C2 bugfix loop i=206)

**Signature:**
```
Stage A final chi²: 7.053e+08
Stage B initial chi²: 7.709e+08
Relative difference: 9.3% (tolerance: 0.1%)
```

**Context:**
- Detector: small (ROI mode enabled)
- Device: CUDA
- Config: enable_stage_b=True, enable_stage_c=False, enable_stage_a_roi_mode=True

**Hypothesis:** The `_build_final_bragg_from_stage_b_telemetry` helper (dbex/nanobrag_refinement.py:2747-2916) may reconstruct Stage A parameters differently than the inline path, similar to the CONVERGENCE-001 "code path divergence" pattern.

**Recommended Next Steps:**
1. Add telemetry logging to compare parameter reconstruction between inline and engine delegation paths
2. Check if Stage A final parameters (log_scale, cell deltas, misset) are correctly extracted from telemetry at StageB.run() line 144-156
3. Verify crystal_overrides dictionary construction matches inline path (dbex/nanobrag_refinement.py:3102-3104 vs helper line 2839-2846)
4. If systematic offset is <20% and convergence is stable (per CONVERGENCE-001 acceptance criteria), document and adjust tolerance
5. Otherwise, fix parameter reconstruction bug in helper

**Related Findings:**
- CONVERGENCE-001 (zero-delta bypass, systematic offset <20% acceptable when convergence stable)
- GEOMETRY-003 (crystal_overrides vs detector_config.misset_deg propagation)

## Artifacts

- `compilation_check.log` - ✅ PASSED
- `pytest_stage_b_after_bugfix.log` - PyTorch CUDA graph assertion failure (torch.compile issue, resolved by NANOBRAGG_DISABLE_COMPILE=1)
- `pytest_stage_b_with_disable_compile.log` - AttributeError on enable_warm_cache (Bug 3 discovered)
- `pytest_stage_b_final.log` - Chi-squared discrepancy AssertionError (new systematic offset issue)

## Next Actions

1. **Mark ARCH-REFINE-FLOW-001 Phase C2 as "blocked — suspected implementation defect (chi² offset)"** per repeat-failure guard
2. Commit the 3 bugfixes (asdict conversion + enable_warm_cache typo + verification)
3. Create NEW fix-plan item: **ARCH-REFINE-FLOW-002: Diagnose Engine Delegation Chi² Offset** or add Phase C3 to ARCH-REFINE-FLOW-001 for systematic offset investigation
4. Capture failure evidence path: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T075320Z/pytest_stage_b_final.log`
5. Notify supervisor via output

## Files Changed

- `dbex/nanobrag_refinement.py:3088-3097` (Bug 1 fix: asdict conversion)
- `dbex/nanobrag_refinement.py:2853` (Bug 3 fix: enable_warm_cache → enable_stage_a_warm_cache)
- `dbex/refinement/stage_b.py` (Bug 2: VERIFIED, no changes needed)

## Static Analysis

Not run (bugs were runtime AttributeErrors, not lint/type issues).

## Collection Verification

Not applicable (no new tests added, only fixing existing engine delegation path).

