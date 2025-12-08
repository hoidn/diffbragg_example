# input.md — Loop i=210

## Summary
Profile GPU memory allocation during Stage A/reconstruction to identify optimization targets for OOM fix.

## Focus
**PERF-GPU-MEM-001** — GPU Memory Usage Analysis and Optimization (Phase A)

## Branch
`integration`

## Mapped Tests
None — evidence-only profiling loop (no code changes).

## Artifacts
`plans/active/PERF-GPU-MEM-001/reports/2025-12-08T224000Z/`

---

## Do Now (Implementation Delegation)

**Focus Item:** PERF-GPU-MEM-001 Phase A (Memory Profiling)

**Implement:** Memory profiling probe + instrumentation (evidence collection only, no production edits)

**Tasks:**
1. **A0 — Create profiling probe** (`plans/active/PERF-GPU-MEM-001/bin/profile_gpu_memory.py`):
   - Script to track `torch.cuda.memory_allocated()` and `torch.cuda.max_memory_allocated()` at key points
   - Capture: before/after Crystal creation, before/after Simulator.run(), before/after reconstruction
   - Output JSON metrics to artifacts directory
   - Must be <400 LOC per PROBE-FREEZE-001

2. **A1-A2 — Profile Stage A closure execution**:
   - Run profiling against `test_stage_a_expansion` fixture path
   - Capture memory at: HKL grid allocation, mosaic domain setup, tricubic interpolation entry/exit
   - Use small detector (512x512) to avoid actual OOM during profiling

3. **A3-A4 — Profile reconstruction path**:
   - Profile `build_final_bragg_from_stage_a_telemetry` if accessible
   - Focus on tricubic interpolation memory footprint (`Crystal._tricubic_interpolation`)
   - Document which call creates the ~4GB intermediates

4. **A5 — Document findings**:
   - Create `reports/2025-12-08T224000Z/memory_profile.md` with:
     - Memory breakdown by component (table)
     - Peak allocation location (file:line)
     - Scaling observations (memory vs detector size)
   - Create `reports/2025-12-08T224000Z/summary.md`

**Validating Test:** None (evidence-only loop). Validation is completion of profiling artifacts.

---

## How-To Map

### Environment
```bash
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1
export CUDA_VISIBLE_DEVICES=0  # Single GPU profiling
```

### Memory profiling snippet pattern
```python
import torch

def log_gpu_memory(label):
    if torch.cuda.is_available():
        alloc = torch.cuda.memory_allocated() / 1e9
        max_alloc = torch.cuda.max_memory_allocated() / 1e9
        print(f"[MEMORY] {label}: allocated={alloc:.2f} GB, max={max_alloc:.2f} GB")
        return {"label": label, "allocated_gb": alloc, "max_allocated_gb": max_alloc}
    return {"label": label, "allocated_gb": 0, "max_allocated_gb": 0}

# Reset peak stats at start
torch.cuda.reset_peak_memory_stats()
```

### Key instrumentation points
- `nanobrag_torch/models/crystal.py:404` — tricubic interpolation (OOM location)
- `Crystal.__init__` — HKL grid allocation
- `Simulator.run()` — forward simulation entry/exit
- Reconstruction helpers in `dbex/physics/`

### Artifact output
```bash
# Metrics JSON
plans/active/PERF-GPU-MEM-001/reports/2025-12-08T224000Z/memory_metrics.json

# Profile markdown
plans/active/PERF-GPU-MEM-001/reports/2025-12-08T224000Z/memory_profile.md
```

---

## Pitfalls To Avoid

1. **DO NOT modify production code** — Phase A is evidence collection only
2. **DO NOT run full-detector profiles** — Use small detector (512x512) to avoid OOM during profiling
3. **DO NOT install packages** — Environment Freeze policy
4. **DO reset peak memory stats** before each measurement with `torch.cuda.reset_peak_memory_stats()`
5. **DO use NANOBRAGG_DISABLE_COMPILE=1** — Avoid Dynamo compilation overhead
6. **DO keep probe <400 LOC** — Per PROBE-FREEZE-001
7. **DO use device='cuda' if available** — Profile actual GPU memory, not CPU
8. **DO document with file:line references** — Trace exact OOM source location

---

## If Blocked

1. If CUDA not available: Profile on CPU with memory_profiler; document as CPU-only evidence
2. If fixture loading fails: Use synthetic test data (simple cubic crystal)
3. If OOM during profiling: Reduce detector size further (256x256) or chunk queries
4. Document block in `galph_memory.md` and Attempts History with error signature

---

## Findings Applied (Mandatory)

- **RUNTIME-001** (Runtime execution guardrails): Use `NANOBRAGG_DISABLE_COMPILE=1` to avoid Dynamo interference with memory profiling
  - Code: `docs/TESTING_GUIDE.md:161`, `docs/pytorch_runtime_checklist.md:26`
  - Adherence: All profiling runs use canonical environment flags

- **PROBE-FREEZE-001** (Plan-local script policy): Profiling probe must stay <400 LOC, be a thin wrapper calling existing APIs
  - Code: `docs/findings.md`, `prompts/supervisor.md::diagnostic_script_policy`
  - Adherence: Phase A.0 probe is instrumentation only, no new pipelines

- **DIAGNOSTICS-001** (Artifact patterns): Use timestamped artifacts directory with JSON metrics + markdown summary
  - Adherence: Artifacts go to `plans/active/PERF-GPU-MEM-001/reports/2025-12-08T224000Z/`

---

## Pointers

### Implementation Plan
- `plans/active/PERF-GPU-MEM-001/implementation.md` — Full Phase A-D checklist

### OOM Evidence
- `plans/active/SPEC-INTERP-TRICUBIC-001/reports/2025-12-08T130000Z/pytest_stage_a.log` — Original OOM stack trace
- Root cause: `nanobrag_torch/models/crystal.py:404` — tricubic interpolation batched gather

### Key Source Files
- `nanobrag_torch/models/crystal.py:350-450` — Tricubic interpolation implementation
- `dbex/physics/forward.py::simulate_forward_torch` — Forward simulation entry
- `dbex/physics/reconstruction.py` (if exists) — Reconstruction helpers

### Spec References
- `docs/spec-db-runtime.md` Device/Dtype Neutrality — Optimization constraints
- `docs/pytorch_runtime_checklist.md` Memory hygiene — Memory management patterns

---

## Next Up (optional)

If Phase A completes early:
- **Phase B.1**: Calculate theoretical memory requirements for each component
- **Phase B.2**: Identify memory scaling laws (linear vs quadratic in detector size)

---

## Doc Sync Plan (Conditional)

N/A — No tests added this loop. Test registry sync not required for evidence-only Phase A.
