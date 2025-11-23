# Phase C Validation Decision (Loop i=211, Ralph)

## Decision Path: **B — Debug Stage B Execution**

## Timestamp
2025-11-23T084458Z

## Test Results Summary

### Stage B Smoke Tests
- **Small detector** (`DBEX_SMOKE_DETECTOR_SIZE=small`): **PASSED** (13.45s, exit code 0)
- **Full detector** (`DBEX_SMOKE_DETECTOR_SIZE=full`): **FAILED** - CUDA OOM (111.95s, exit code 1)

### DB-AT-024 Mapping Parity
- **Collection check**: **PASSED** (1 test collected)
- **Test execution**: NOT RUN (blocked by Stage B full detector failure)

## Root Cause Analysis

### Problem Statement
Stage B smoke test on full detector fails with CUDA OutOfMemoryError:
```
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 1.67 GiB.
GPU 0 has a total capacity of 23.56 GiB of which 49.62 MiB is free.
Including non-PyTorch memory, this process has 23.44 GiB memory in use.
```

Error location: `nanoBragg/src/nanobrag_torch/models/crystal.py:356`

### Root Cause (HIGH Confidence ~95%)
The **engine delegation path** (lines 3029-3108 in `dbex/nanobrag_refinement.py`) **is missing the CPU fallback initialization logic** required by PERF-WARM-011.

**Evidence:**
1. CPU fallback logic exists in the **inline path** (lines 2174-2184):
   ```python
   use_stage_b_cpu_fallback = (
       config.stage_b_full_eval_on_cpu
       and str(device).startswith("cuda")
       and not use_stage_a_roi_mode  # ROI mode is disabled (panel mode)
   )
   ```

2. Engine delegation path (lines 3029-3108) does NOT compute `use_stage_b_cpu_fallback` or clone Stage A context to CPU before instantiating the engine

3. `config.stage_b_full_eval_on_cpu` defaults to `True` (line 307), so the feature is enabled but not wired in the new code path

4. StageB.run() correctly consumes `use_stage_b_cpu_fallback` from `param_values` (line 249), but the engine delegation path never provides it

### Expected Behavior (per PERF-WARM-011 + PERF-WARM-012)
When `config.stage_b_full_eval_on_cpu=True` AND `device=cuda` AND ROI mode is disabled (panel mode):
1. Compute `use_stage_b_cpu_fallback = True`
2. Clone Stage A context to CPU (PERF-WARM-012) to reuse warm cache
3. Pass `use_stage_b_cpu_fallback` through to Stage B helpers
4. Stage B closures/validations run on CPU, avoiding GPU OOM

### Actual Behavior
- Engine delegation path skips CPU fallback logic entirely
- Stage B tries to allocate 1.67 GiB on GPU that has only 49.62 MiB free
- Test fails with CUDA OOM instead of falling back to CPU

## Impact Assessment

### Blocking Scope
- **Phase C validation**: BLOCKED (cannot verify Stage B full detector smoke)
- **Exit criteria C4**: NOT MET (Stage B full detector test required)
- **Exit criteria C5**: NOT RUN (DB-AT-024 deferred until Stage B fixed)

### Non-blocking Results
- ✓ Stage B small detector: PASSED (engine delegation works for small workloads)
- ✓ DB-AT-024 collection: PASSED (1 test available)
- ✓ Phase C extraction complete: C0/C1a/C1b verified via code review

## Fix Requirements

### Implementation Fix (Targeted)
**Location**: `dbex/nanobrag_refinement.py` lines 3029-3048 (engine delegation path, before engine instantiation)

**Required changes:**
1. Compute `use_stage_a_roi_mode` from Stage A context OR config
2. Compute `use_stage_b_cpu_fallback` following inline path pattern (lines 2174-2182)
3. If `use_stage_b_cpu_fallback=True`: clone Stage A context to CPU per PERF-WARM-012
4. Pass CPU-cloned context (if applicable) to engine or Stage B inputs

**Reference implementation**: Lines 2174-2203 (inline path CPU fallback + context cloning)

### Validation Requirements
After fix applied:
1. Stage B smoke full detector must PASS
2. Telemetry must show `stage_b_full_eval_on_cpu=True` and `cache_mode="warm"`
3. Stage B improvement must meet ≥3% gate (REFINE-008)
4. Run DB-AT-024 mapping parity test
5. Update `docs/fix_plan.md` Attempts History with fix details

## Next Actions

### Immediate (Next Loop)
1. **Ralph (or Galph)**: Implement CPU fallback logic in engine delegation path
   - Add 4-10 lines before line 3048 (engine instantiation)
   - Follow inline path pattern (lines 2174-2203)
   - Test on full detector smoke

2. **Validation**: Rerun Phase C validation suite:
   - Stage B smoke (small + full detectors)
   - Extract telemetry metrics (verify CPU fallback active)
   - DB-AT-024 mapping parity

### Deferred
- Phase C documentation updates (deferred until validation passes)
- Phase C3/C4/C5 marking complete in implementation.md

## Confidence Assessment
**HIGH (95%)**

**Rationale:**
- Root cause identified with exact line numbers and code comparison
- Fix pattern already proven in inline path (PERF-WARM-011/012)
- Small detector test PASSED (validates engine delegation core logic works)
- Error signature matches known PERF-WARM-011 finding

**Risk:**
- Minimal: CPU fallback logic is well-tested in inline path
- Fix is localized (4-10 lines) with clear reference implementation
- No new abstractions or helpers needed

## Artifacts
- `pytest_stage_b_small.log`: Stage B small detector PASSED (13.45s)
- `pytest_stage_b_full.log`: Stage B full detector FAILED - CUDA OOM (111.95s)
- `collect_db_at_024.log`: DB-AT-024 collection PASSED (1 test)
- `phase_c_smoke_metrics.json`: Test results summary
- `phase_c_decision.md`: This decision document

## References
- **Finding**: PERF-WARM-011 (docs/findings.md:26) — Stage B CPU fallback requirement
- **Finding**: PERF-WARM-012 — Stage B reuses Stage A warm cache on CPU
- **Spec**: docs/spec-db-workflow.md §7 — Refinement Protocol Architecture
- **Implementation**: dbex/nanobrag_refinement.py:2174-2203 (inline path reference)
- **Implementation**: dbex/nanobrag_refinement.py:3029-3108 (engine delegation path, missing CPU fallback)
- **Test**: tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers
