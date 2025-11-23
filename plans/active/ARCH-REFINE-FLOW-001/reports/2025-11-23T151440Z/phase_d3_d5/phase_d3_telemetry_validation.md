# Phase D3: StageC Telemetry Schema Validation

## Objective
Verify that StageC wrapper preserves canonical Stage A metadata plus Stage C-specific fields per `docs/spec-db-core.md` telemetry schema and `plans/active/ARCH-REFINE-FLOW-001/implementation.md:242`.

## Telemetry Source
- **Small detector**: `telemetry_stage_c_small.json` (29 ROIs, 1024×1024)
- **Full detector**: `telemetry_stage_c_full.json` (92 ROIs, 2527×2463)

## Canonical RefinementTelemetry Fields Checklist

### Required Base Fields (from dbex/nanobrag_refinement.py:392-440)
- [x] `optimizer` — Present (implicit via "LBFGS" stage context)
- [x] `stage` — Present as `"stage_c_detector_microslip"`
- [x] `status` — Present: `"ok"`
- [x] `message` — Present: `""`
- [x] `param_deltas` — Present: `{"panel_0_distance_offset_mm": {...}}`
- [x] `loss_trace_full` — Present (deprecated chi² trace)
- [x] `chi_squared_trace_full` — Present (PHYSICS-LOSS-001)

### PHYSICS-LOSS-001/002: Dual Loss Metrics
- [x] `chi_squared_trace_full` — Present: 9 iterations (small), 4 iterations (full)
- [x] `chi_squared_improvement` — Present: 0.000324 (small), 0.000601 (full)
- [ ] `chi_squared_initial` — **MISSING** (would be first element of trace)
- [ ] `chi_squared_final` — **MISSING** (would be last element of trace)
- [ ] `masked_mse_initial` — **MISSING** (legacy metric)
- [ ] `masked_mse_final` — **MISSING** (legacy metric)
- [x] `loss_improvement` — Present (0.000324 / 0.000601)

**Note**: The telemetry uses improvement/trace format instead of explicit initial/final scalars. This is semantically equivalent (initial = trace[0][1], final = trace[-1][1]), but differs from the format expected by input.md:39-40 which references explicit `chi_squared_initial`/`chi_squared_final` fields.

### Stage C-Specific Fields (REFINE-007)
- [x] `detector_offset_reduction_min` — Present: 0.99999994 (both)
- [x] `detector_offset_final_abs_max` — Present: 1.49e-08 mm (both)
- [x] `param_deltas_c` — Present as `param_deltas` (single panel): `{"panel_0_distance_offset_mm": {"initial": 0.25, "final": 1.49e-08, "delta": -0.25}}`

### Phase A4: Unified Stage Fields
- [ ] `stage_type` — **MISSING** (expected `"C"`)
- [ ] `mode` — **MISSING** (expected `"detector_offsets"`)

**Critical Gap**: The test harness telemetry format does NOT match the RefinementTelemetry dataclass structure. The JSON emitted by `test_stage_c_detector_microslip` is a test-specific diagnostic format, not the engine-aggregated telemetry from StageC.run().

### Perf Counters (PERF-WARM-006)
- [x] `cache_mode` — Present: `"warm"`
- [x] `roi_mode` — Present: `"roi"`
- [x] `closure_evals` — Present: 39 (small), 11 (full)
- [x] `validation_runs` — Present: 9 (small), 4 (full)
- [x] `forward_time_ms` — Present: `{mean, min, max, total}`
- [x] `roi_count_total` — Present: 29 (small), 92 (full)
- [x] `roi_count_sampled` — Present: 29 (small), 92 (full)

### PHYSICS-LOSS-003: Canonical Stage A Snapshot
- [x] `canonical_stage_label` — Present: `"A"`
- [x] `canonical_chi_squared` — Present: 658657984.0 (small), 290869088.0 (full)
- [x] `canonical_chi_squared_iteration` — Present: 29 (small), 40 (full)
- [x] `canonical_roi_count` — Present: 29 (small), 92 (full)
- [x] `canonical_detector_distances_mm` — Present: `[231.276...]`

### Variance Floor Telemetry (PHYSICS-LOSS-002)
- [ ] `variance_floor_value` — **MISSING**
- [ ] `variance_floor_clamp_fraction` — **MISSING**
- [ ] `sigma_readout_provenance` — **MISSING**
- [ ] `sigma_readout_reference_value` — **MISSING**

## Validation Result: PARTIAL PASS (Test Harness Limitation)

### Finding: Test Harness vs Engine Telemetry Mismatch

The telemetry JSON files captured via `DBEX_SMOKE_TELEMETRY_PATH` are emitted by the **test harness** (`tests/dbex/test_torch_refine_smoke.py`), NOT by the StageC wrapper class itself. This is a diagnostic format optimized for smoke test validation, not the canonical RefinementTelemetry dataclass structure.

**Evidence**:
1. Test harness telemetry includes Stage C-specific fields (`detector_offset_reduction_min`, `detector_offset_final_abs_max`) ✓
2. Test harness telemetry includes PHYSICS-LOSS-003 Stage A snapshot ✓
3. Test harness telemetry includes perf counters (cache_mode, roi_mode, forward_time_ms) ✓
4. Test harness telemetry **MISSING** Phase A4 fields (`stage_type="C"`, `mode="detector_offsets"`)
5. Test harness telemetry uses improvement/trace format instead of explicit initial/final scalars

**To validate the StageC wrapper's actual telemetry schema**, we need to:
1. Read `dbex/refinement/stage_c.py` lines ~350-408 to verify the telemetry packaging logic
2. Confirm that StageC.run() returns a dict with `stage_type="C"` and `mode="detector_offsets"` per Phase D2 commit 71d5e0d
3. Verify that the engine aggregation path preserves these fields (Phase A4 extension)

## Deferred Validation (StageC Source Code Review)

Since the test harness telemetry is not authoritative, I will validate the StageC wrapper's telemetry packaging directly from source code in the next section.

## REFINE-007 Gate Validation (From Test Harness Telemetry)

Even though the test harness format differs from RefinementTelemetry, it DOES include the REFINE-007 gate metrics. Validation result: **PASS** (both small and full)

- **Small detector**:
  - `detector_offset_reduction_min`: 0.99999994 (≥0.80 ✓)
  - `detector_offset_final_abs_max`: 1.49e-08 mm (≤0.05 mm ✓)
  - Gate: **PASS**

- **Full detector**:
  - `detector_offset_reduction_min`: 0.99999994 (≥0.80 ✓)
  - `detector_offset_final_abs_max`: 1.49e-08 mm (≤0.05 mm ✓)
  - `chi_squared_regression`: (290694208 - 290869088) / 290869088 = -0.0006012 (≤0.0005 ✗, but **improvement** not regression)
  - Gate: **PASS** (improvement is better than threshold, negative regression = good)

## Chi-Squared Regression Clarification

The full detector chi² changed from 290869088.0 (Stage A final) → 290694208.0 (Stage C final), which is a **-0.06%** change (improvement, not regression). The REFINE-007 gate `chi_squared_regression <= 0.0005` means "Stage C must not degrade chi² by more than 0.05% relative to Stage A". Since we improved chi² (negative regression), this is well within the threshold.

## Next Steps

1. Read `dbex/refinement/stage_c.py` telemetry packaging logic (lines ~350-408)
2. Confirm `stage_type="C"` and `mode="detector_offsets"` are present in StageC.run() return dict
3. Write `phase_d4_refine007_validation.json` with gate results
4. Document finding: Test harness telemetry format is diagnostic-only, not authoritative for RefinementTelemetry schema validation
