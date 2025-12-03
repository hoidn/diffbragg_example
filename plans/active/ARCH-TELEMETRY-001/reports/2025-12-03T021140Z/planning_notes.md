# ARCH-TELEMETRY-001 Phase C.3.2 Planning Notes

## Goal
Remove legacy_telemetry_dict plumbing in Stage A/B/C and RefinementEngine now that writer consumes StageResult dataclasses directly (Phase C.3.1 complete).

## Current State (Phase C.3.1 Complete)

### Writer Path (dbex/io/writer.py)
- ✅ `_extract_stage_payload()` helper extracts telemetry + perf counters from typed StageResult dataclasses (lines 216-252)
- ✅ Per-stage serialization loop prefers `stage_results[stage_label]` when present (lines 263-273)
- ✅ Stage B baseline attrs use three-tier priority: stage_artifacts → StageResult → RefinementTelemetry (lines 347-375)
- ✅ Tests PASSED: CLI metadata (2/2), Stage B guard, Stage B shell smoke, Stage C detector microslip

### Remaining Legacy Dict Usage

#### 1. Stage B (dbex/refinement/stage_b.py:1490-1508)
```python
legacy_telemetry_dict = stage_result.to_legacy_dict()

# Extract fields from legacy dict (collector owns traces and perf counters)
loss_trace_sample_b = legacy_telemetry_dict['loss_trace_sample']
loss_trace_full_b = legacy_telemetry_dict['loss_trace_full']
# ... 9 more fields ...
stage_b_baseline_rel_diff = legacy_telemetry_dict.get('stage_b_baseline_rel_diff', None)
```

**Issue:** Stage B still calls `to_legacy_dict()` and extracts 12 fields via dict subscripting instead of accessing `stage_result.telemetry.*` and `stage_result.perf_counters.*` directly.

#### 2. Stage C (dbex/refinement/stage_c.py:1125-1139)
```python
legacy_telemetry_dict = stage_result.to_legacy_dict()

# Refresh telemetry fields from finalized collector
loss_trace_sample_c = legacy_telemetry_dict['loss_trace_sample']
# ... 9 more fields ...
```

**Issue:** Stage C still calls `to_legacy_dict()` and extracts 10 fields via dict subscripting.

#### 3. RefinementEngine (dbex/refinement/engine.py:203-215)
```python
legacy_telemetry_dict = {}
for stage_name, telem in self._telemetry.items():
    if stage_name == "stage_a":
        legacy_telemetry_dict["A"] = telem
    # ... map stage_b→B, stage_c→C ...
return legacy_telemetry_dict
```

**Issue:** Engine still maps internal stage names ("stage_a") to legacy labels ("A") for backward compatibility with tests. This was needed when tests expected dict keys, but **Phase C.3.1 writer changes** now consume StageResult directly, so this mapping may no longer be needed.

**Note:** Engine key mapping (lines 203-215) was added in ARCH-REFACTOR-001 Phase D.3 telemetry bugfix (commit a6f39bac) to fix test assertions like `assert 'A' in telemetry_dict`. Need to verify if tests still rely on this or if they've been updated to use stage_result directly.

## Phase C.3.2 Implementation Strategy

### Step 1: Stage A Cleanup (if applicable)
**Check:** Does Stage A have `to_legacy_dict()` usage?
- Grep shows no `legacy_telemetry_dict` usage in stage_a.py
- ✅ Stage A already clean (likely cleaned up in earlier phase)

### Step 2: Stage B Direct Field Access (dbex/refinement/stage_b.py:1490-1524)
**Current pattern (lines 1490-1508):**
```python
stage_result = collector.finalize()
legacy_telemetry_dict = stage_result.to_legacy_dict()
loss_trace_sample_b = legacy_telemetry_dict['loss_trace_sample']
# ... 11 more fields ...
```

**Target pattern:**
```python
stage_result = collector.finalize()
# Access typed fields directly
loss_trace_sample_b = stage_result.telemetry.loss_trace_sample
loss_trace_full_b = stage_result.telemetry.loss_trace_full
chi_squared_trace_sample_b = stage_result.telemetry.chi_squared_trace_sample
chi_squared_trace_full_b = stage_result.telemetry.chi_squared_trace_full
masked_mse_trace_sample_b = stage_result.telemetry.masked_mse_trace_sample
masked_mse_trace_full_b = stage_result.telemetry.masked_mse_trace_full
perf_closure_evals_b = stage_result.perf_counters.perf_closure_evals
perf_validation_runs_b = stage_result.perf_counters.perf_validation_runs
perf_forward_times_ms_b = stage_result.perf_counters.perf_forward_times_ms
variance_floor_clamped_pixels_b = stage_result.perf_counters.variance_floor_clamped_pixels
variance_floor_masked_pixels_b = stage_result.perf_counters.variance_floor_masked_pixels

# REFINE-FLOW-001: Extract baseline parity diagnostics from typed telemetry
stage_b_baseline_rel_diff = stage_result.telemetry.stage_b_baseline_rel_diff
stage_b_baseline_abs_diff = stage_result.telemetry.stage_b_baseline_abs_diff
stage_b_baseline_diff_path = stage_result.telemetry.stage_b_baseline_diff_path
```

**Changes:**
- Remove line 1490: `legacy_telemetry_dict = stage_result.to_legacy_dict()`
- Replace dict subscripting (lines 1493-1503) with direct field access via `stage_result.telemetry.*` and `stage_result.perf_counters.*`
- Replace `.get()` calls (lines 1506-1508) with direct field access (baseline fields are always present in StageBTelemetry)

### Step 3: Stage C Direct Field Access (dbex/refinement/stage_c.py:1125-1139)
**Current pattern (lines 1125-1139):**
```python
stage_result = collector.finalize()
legacy_telemetry_dict = stage_result.to_legacy_dict()
loss_trace_sample_c = legacy_telemetry_dict['loss_trace_sample']
# ... 9 more fields ...
```

**Target pattern:**
```python
stage_result = collector.finalize()
# Access typed fields directly
loss_trace_sample_c = stage_result.telemetry.loss_trace_sample
loss_trace_full_c = stage_result.telemetry.loss_trace_full
chi_squared_trace_sample_c = stage_result.telemetry.chi_squared_trace_sample
chi_squared_trace_full_c = stage_result.telemetry.chi_squared_trace_full
masked_mse_trace_sample_c = stage_result.telemetry.masked_mse_trace_sample
masked_mse_trace_full_c = stage_result.telemetry.masked_mse_trace_full
iteration_count_c = stage_result.telemetry.iteration_count
perf_closure_evals_c = stage_result.perf_counters.perf_closure_evals[0]
perf_validation_runs_c = stage_result.perf_counters.perf_validation_runs[0]
perf_forward_times_ms_c = stage_result.perf_counters.perf_forward_times_ms
variance_floor_clamped_pixels_c = stage_result.perf_counters.variance_floor_clamped_pixels[0]
variance_floor_masked_pixels_c = stage_result.perf_counters.variance_floor_masked_pixels[0]
```

**Changes:**
- Remove line 1125: `legacy_telemetry_dict = stage_result.to_legacy_dict()`
- Replace dict subscripting (lines 1128-1139) with direct field access
- **Note:** Perf counters are single-element lists in StageCPerfCounters, so keep `[0]` indexing

### Step 4: RefinementEngine Key Mapping Removal (CONDITIONAL)
**Decision point:** Can we remove engine.py:203-215?

**Analysis:**
- Writer (Phase C.3.1) now accesses `stage_results[stage_label]` directly (line 266-271), not via `telemetry_dict["A"]`
- CLI code (dbex/refine_one.py) may still expect legacy keys when extracting stage_results
- Tests (test_torch_refine_smoke.py) may still assert on `telemetry_dict["A"]` keys

**Strategy:** Keep engine key mapping for now (defer to Phase C.4 or later) to avoid breaking tests. Focus Phase C.3.2 on Stage B/C cleanup only.

**Rationale:**
- Stage B/C cleanup is self-contained and low-risk (just field access changes)
- Engine key mapping removal requires test updates across multiple files
- Incremental approach: prove Stage B/C cleanup works, then tackle engine+tests separately

**Phase C.3.2 Scope:**
- ✅ Stage B: Remove `to_legacy_dict()`, use direct field access
- ✅ Stage C: Remove `to_legacy_dict()`, use direct field access
- ⏸️ RefinementEngine: Defer key mapping removal to Phase C.4 (requires test updates)

## Validation Plan

### Mapped Tests
1. **Stage B guard:** `tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload`
   - Validates baseline parity metrics extraction
   - Exercises Stage B `stage_result.telemetry.stage_b_baseline_*` fields

2. **Stage B shell smoke:** `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers`
   - Validates Stage B telemetry/perf counters
   - Exercises loss traces, chi² traces, variance floor counters

3. **Stage C detector microslip:** `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip`
   - Validates Stage C telemetry/perf counters
   - Exercises loss traces, iteration count, perf counters with `[0]` indexing

### Expected Outcomes
- ✅ All 3 tests PASS with no behavioral changes
- ✅ `to_legacy_dict()` calls removed from Stage B/C
- ✅ Direct field access via `stage_result.telemetry.*` and `stage_result.perf_counters.*`
- ✅ No changes to RefinementEngine (deferred to Phase C.4)

## Risks & Mitigations

### Risk 1: Field Name Mismatches
**Concern:** Typed dataclass field names might not match legacy dict keys exactly.
**Mitigation:** Cross-reference `StageBTelemetry`/`StageCTelemetry` dataclass definitions (dbex/refinement/interfaces.py) with current dict key usage.

### Risk 2: None vs Missing Field Handling
**Concern:** Legacy dict used `.get(key, None)` for optional fields; typed fields may raise AttributeError if missing.
**Mitigation:** Verify all baseline parity fields (`stage_b_baseline_rel_diff`, etc.) are always present in StageBTelemetry dataclass (not Optional unless intentional).

### Risk 3: List Indexing for Stage C Perf Counters
**Concern:** Stage C perf counters are single-element lists; direct access needs `[0]` indexing.
**Mitigation:** Preserve `[0]` indexing for Stage C perf fields (lines 1135-1136, 1138-1139) as shown in target pattern above.

## File Changes Summary

### Stage B (dbex/refinement/stage_b.py)
- **Lines 1490:** DELETE `legacy_telemetry_dict = stage_result.to_legacy_dict()`
- **Lines 1493-1503:** REPLACE dict subscripting with `stage_result.telemetry.*` / `stage_result.perf_counters.*`
- **Lines 1506-1508:** REPLACE `.get()` calls with direct field access
- **Net change:** -1 line (remove to_legacy_dict call), 0 net lines (dict[key] → obj.field same length)

### Stage C (dbex/refinement/stage_c.py)
- **Lines 1125:** DELETE `legacy_telemetry_dict = stage_result.to_legacy_dict()`
- **Lines 1128-1139:** REPLACE dict subscripting with direct field access (keep `[0]` for perf counters)
- **Net change:** -1 line

### RefinementEngine (dbex/refinement/engine.py)
- **No changes this phase** (deferred to C.4)

## Artifacts

### Implementation Artifacts
- `plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T021140Z/pytest_stage_b_guard.log`
- `plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T021140Z/pytest_stage_b_smoke.log`
- `plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T021140Z/pytest_stage_c_smoke.log`

### Planning Artifacts
- This `planning_notes.md`
- `input.md` (Do Now for Ralph)
- `summary.md` (loop outcome)

## Success Criteria

1. ✅ Stage B `to_legacy_dict()` call removed
2. ✅ Stage C `to_legacy_dict()` call removed
3. ✅ All field accesses via `stage_result.telemetry.*` and `stage_result.perf_counters.*`
4. ✅ 3/3 mapped tests PASSED
5. ✅ No behavioral changes (telemetry values identical pre/post change)
6. ✅ No changes to RefinementEngine (explicitly deferred)
