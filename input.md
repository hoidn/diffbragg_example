# ARCH-TELEMETRY-001 Phase C.3.2 — Remove Legacy Telemetry Dict Plumbing

## Summary
Remove `to_legacy_dict()` calls and dict subscripting in Stage B/C; access telemetry and perf counter fields directly from `StageResult` typed dataclasses.

## Mode
**Parity**

## InitiativeType
**architecture**

## Focus
[ARCH-TELEMETRY-001] — Telemetry Observer Refactor (Phase C.3.2: legacy_telemetry_dict retirement)

## Branch
`integration`

## Mapped Tests
```bash
# Stage B baseline parity guard (validates baseline_* field extraction)
tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload

# Stage B shell smoke (validates loss/chi²/variance floor telemetry)
tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers

# Stage C detector microslip (validates Stage C telemetry with [0] indexing)
tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip
```

## Artifacts
`plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T021140Z/`

## Do Now

### Background
Phase C.3.1 (complete) taught `dbex/io/writer.py` to consume typed `StageResult` dataclasses when available, with fallback to legacy dict path for mocks. Now remove the **production code** usage of `to_legacy_dict()` in Stage B/C so they access telemetry and perf counter fields directly via `stage_result.telemetry.*` and `stage_result.perf_counters.*`.

**DO NOT** modify `RefinementEngine` (engine.py) this loop—key mapping removal is deferred to Phase C.4.

### Task 1: Stage B Direct Field Access (dbex/refinement/stage_b.py:1490-1508)

**Target:** Replace `to_legacy_dict()` with direct field access.

**Current code (lines 1490-1508):**
```python
stage_result = collector.finalize()
legacy_telemetry_dict = stage_result.to_legacy_dict()

# Extract fields from legacy dict (collector owns traces and perf counters)
loss_trace_sample_b = legacy_telemetry_dict['loss_trace_sample']
loss_trace_full_b = legacy_telemetry_dict['loss_trace_full']
chi_squared_trace_sample_b = legacy_telemetry_dict['chi_squared_trace_sample']
chi_squared_trace_full_b = legacy_telemetry_dict['chi_squared_trace_full']
masked_mse_trace_sample_b = legacy_telemetry_dict['masked_mse_trace_sample']
masked_mse_trace_full_b = legacy_telemetry_dict['masked_mse_trace_full']
perf_closure_evals_b = legacy_telemetry_dict['perf_closure_evals']
perf_validation_runs_b = legacy_telemetry_dict['perf_validation_runs']
perf_forward_times_ms_b = legacy_telemetry_dict['perf_forward_times_ms']
variance_floor_clamped_pixels_b = legacy_telemetry_dict['variance_floor_clamped_pixels']
variance_floor_masked_pixels_b = legacy_telemetry_dict['variance_floor_masked_pixels']

# REFINE-FLOW-001: Extract baseline parity diagnostics from typed telemetry
stage_b_baseline_rel_diff = legacy_telemetry_dict.get('stage_b_baseline_rel_diff', None)
stage_b_baseline_abs_diff = legacy_telemetry_dict.get('stage_b_baseline_abs_diff', None)
stage_b_baseline_diff_path = legacy_telemetry_dict.get('stage_b_baseline_diff_path', None)
```

**Changes:**
1. **DELETE line 1490:** `legacy_telemetry_dict = stage_result.to_legacy_dict()`
2. **REPLACE lines 1493-1503** (dict subscripting) with direct field access:
   ```python
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
   ```

3. **REPLACE lines 1506-1508** (`.get()` calls) with direct field access:
   ```python
   stage_b_baseline_rel_diff = stage_result.telemetry.stage_b_baseline_rel_diff
   stage_b_baseline_abs_diff = stage_result.telemetry.stage_b_baseline_abs_diff
   stage_b_baseline_diff_path = stage_result.telemetry.stage_b_baseline_diff_path
   ```

**Rationale:** `StageBTelemetry` dataclass always includes baseline parity fields (not Optional), so `.get(key, None)` is unnecessary; use direct field access for type safety.

### Task 2: Stage C Direct Field Access (dbex/refinement/stage_c.py:1125-1139)

**Target:** Replace `to_legacy_dict()` with direct field access.

**Current code (lines 1125-1139):**
```python
stage_result = collector.finalize()
legacy_telemetry_dict = stage_result.to_legacy_dict()

# Refresh telemetry fields from finalized collector
loss_trace_sample_c = legacy_telemetry_dict['loss_trace_sample']
loss_trace_full_c = legacy_telemetry_dict['loss_trace_full']
chi_squared_trace_sample_c = legacy_telemetry_dict['chi_squared_trace_sample']
chi_squared_trace_full_c = legacy_telemetry_dict['chi_squared_trace_full']
masked_mse_trace_sample_c = legacy_telemetry_dict['masked_mse_trace_sample']
masked_mse_trace_full_c = legacy_telemetry_dict['masked_mse_trace_full']
iteration_count_c = legacy_telemetry_dict['iteration_count']
perf_closure_evals_c = legacy_telemetry_dict['perf_closure_evals'][0]
perf_validation_runs_c = legacy_telemetry_dict['perf_validation_runs'][0]
perf_forward_times_ms_c = legacy_telemetry_dict['perf_forward_times_ms']
variance_floor_clamped_pixels_c = legacy_telemetry_dict['variance_floor_clamped_pixels'][0]
variance_floor_masked_pixels_c = legacy_telemetry_dict['variance_floor_masked_pixels'][0]
```

**Changes:**
1. **DELETE line 1125:** `legacy_telemetry_dict = stage_result.to_legacy_dict()`
2. **REPLACE lines 1128-1139** with direct field access:
   ```python
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

**Important:** Stage C perf counters are single-element lists in `StageCPerfCounters`, so keep `[0]` indexing for:
- `perf_closure_evals_c`
- `perf_validation_runs_c`
- `variance_floor_clamped_pixels_c`
- `variance_floor_masked_pixels_c`

### Task 3: Validation

Run all three mapped tests with environment variables as specified in `docs/TESTING_GUIDE.md`:

```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=metadata \
DBEX_SMOKE_DETECTOR_SIZE=full \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv \
  tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload \
  tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
  tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip \
  > plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T021140Z/pytest_phase_c32.log 2>&1
```

**Expected:** All 3/3 tests PASS with no behavioral changes.

## How-To Map

### 1. Edit Stage B (dbex/refinement/stage_b.py)
- Delete line 1490 (`to_legacy_dict()` call)
- Replace lines 1493-1508 with direct field access per Task 1

### 2. Edit Stage C (dbex/refinement/stage_c.py)
- Delete line 1125 (`to_legacy_dict()` call)
- Replace lines 1128-1139 with direct field access per Task 2 (preserve `[0]` indexing)

### 3. Validation
- Run pytest command from Task 3
- Capture logs to `plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T021140Z/pytest_phase_c32.log`

### 4. Metrics
- File changes: 2 (stage_b.py, stage_c.py)
- Net lines: -2 (delete 2× `to_legacy_dict()` calls)
- Tests: 3 mapped selectors

## Pitfalls To Avoid

1. **DO NOT** modify `dbex/refinement/engine.py` this loop—RefinementEngine key mapping removal is deferred to Phase C.4.
2. **DO NOT** remove `to_legacy_dict()` method definitions from `StageResult` dataclasses—they may still be used by tests/mocks.
3. **KEEP `[0]` indexing** for Stage C perf counter fields (lines 1135-1136, 1138-1139) as shown in Task 2.
4. **Verify field names** match dataclass definitions exactly:
   - Telemetry fields live in `stage_result.telemetry.*` (StageBTelemetry/StageCTelemetry)
   - Perf counter fields live in `stage_result.perf_counters.*` (StageBPerfCounters/StageCPerfCounters)
5. **Preserve comment context**: Lines 1493 and 1127 have inline comments ("Extract fields from legacy dict..." / "Refresh telemetry fields..."); update or remove them as needed to reflect direct field access.
6. **No behavior changes**: Field values must be identical pre/post change; tests validate this via assertions on telemetry/perf values.

## If Blocked

If tests FAIL with:
- **AttributeError on `stage_result.telemetry.<field>`**: Field name mismatch between dict key and dataclass attribute. Cross-reference `dbex/refinement/interfaces.py` dataclass definitions.
- **IndexError on `[0]`**: Perf counter is not a list in dataclass. Check `StageCPerfCounters` definition for list vs scalar types.
- **Behavioral drift** (telemetry values changed): Implementation bug; revert changes and capture `pytest -s` logs showing field values pre/post change for supervisor analysis.

Capture failure details under `plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T021140Z/ralph_findings.md` and mark loop blocked.

## Findings Applied (Mandatory)
- **ARCH-STAGE-CTX-001:** Ban telemetry dict mutation; ensure typed contexts own telemetry (completed in Phase C.1, now removing legacy compat layers)
- **ARCH-STAGE-CTX-002:** Typed contexts must own telemetry state (StageResult dataclasses now authoritative)
- **PHYSICS-LOSS-001:** Telemetry χ² must be spec-compliant (unchanged; field access preserves values)

## Pointers
- Spec: `docs/spec-db-workflow.md` (§Pipeline telemetry), `docs/spec-db-core.md` (§Objective Function)
- Architecture: `docs/architecture/data_telemetry_flow.md` (observer pattern)
- Plan: `plans/active/ARCH-TELEMETRY-001/implementation.md` (Phase C.3.2 checklist)
- Dataclass definitions: `dbex/refinement/interfaces.py` (StageBTelemetry, StageCTelemetry, StageBPerfCounters, StageCPerfCounters)
- Fix plan: `docs/fix_plan.md` — Row [ARCH-TELEMETRY-001] (Phase C.3.2 planning this loop)

## Next Up (optional)
- Phase C.4: Remove RefinementEngine key mapping (engine.py:203-215) and update tests to use StageResult directly
- Phase D: Doc Sync Plan (update `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` if selectors changed)

## Doc Sync Plan (Conditional)
Not applicable this loop (no tests added/renamed; existing selectors unchanged).
