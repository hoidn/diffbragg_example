# Ralph Input — Loop i=241

## Summary
Test Stage A smoke with `pixel_batch_size=128` on 24GB GPU to validate OOM fix.

## Focus
PERF-GPU-MEM-001 — GPU Memory Usage Analysis and Optimization (Phase C)

## Branch
`integration`

## Mapped Tests
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (with `--smoke-detector-size=small`)
- `tests/architecture/test_nanobrag_partiality.py` (parity validation)

## Artifacts
`plans/active/PERF-GPU-MEM-001/reports/2025-12-09T000000Z/`

---

## Do Now (Implementation)

**Focus Item:** PERF-GPU-MEM-001 — Phase C (Optimization Verification)

**Action Type:** Implementation + Verification

### Background

The upstream `pixel_batch_size` feature is now fully functional (see `inbox/pixel-batching-implementation-response-2025-12-08.md`). Key points:
- Orchestration-level batching in `Simulator.run()` via `_run_chunked()`
- CLI: `-pixel_batch_size N` or API: `simulator.run(pixel_batch_size=N)`
- Recommended chunk sizes: 32-64 rows (8GB), 64-128 rows (12GB), **128-256 rows (24GB)**
- 13 upstream tests pass (parity + gradcheck verified)
- 10-30% slowdown expected vs full vectorization (acceptable trade-off for OOM avoidance)

### Tasks

**C.1 — Verify pixel_batch_size feature is available:**

```bash
# Check nanobrag_torch has the pixel batching feature
grep -n "pixel_batch_size" ~/Documents/nanoBragg/src/nanobrag_torch/simulator.py | head -5
grep -n "_run_chunked" ~/Documents/nanoBragg/src/nanobrag_torch/simulator.py | head -3
```

**C.2 — Thread pixel_batch_size through DBEX:**

Check if DBEX needs modification to pass `pixel_batch_size` to the simulator. The parameter should flow from:
- CLI: Add `--pixel-batch-size` flag to `refine_one.py` if not present
- API: Thread through `Simulator.run()` calls in `nanobrag_bridge.py` and/or `nanobrag_refinement.py`

Key files to check:
- `dbex/refine_one.py` — CLI argument parsing
- `dbex/nanobrag_bridge.py` — `simulate_forward_torch()` and related helpers
- `dbex/refinement/stage_a.py` — Stage A closure creation
- `dbex/refinement/reconstruction.py` — Reconstruction path (OOM site)

**C.3 — Run Stage A smoke test with pixel batching:**

```bash
cd /home/ollie/Documents/diffbragg_example
mkdir -p plans/active/PERF-GPU-MEM-001/reports/2025-12-09T000000Z

# Run Stage A smoke with pixel_batch_size (if CLI flag exists)
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
  pytest tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
  --smoke-detector-size=small -v \
  2>&1 | tee plans/active/PERF-GPU-MEM-001/reports/2025-12-09T000000Z/stage_a_pixel_batch.log
```

If CLI threading is needed, implement it first, then rerun.

**C.4 — Validate physics unchanged:**

```bash
# Run partiality tests to confirm physics unchanged
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
  pytest tests/architecture/test_nanobrag_partiality.py -v \
  2>&1 | tee plans/active/PERF-GPU-MEM-001/reports/2025-12-09T000000Z/partiality_parity.log
```

**C.5 — Document results:**

Create `plans/active/PERF-GPU-MEM-001/reports/2025-12-09T000000Z/summary.md` with:
1. Memory usage before/after (if measurable)
2. Test pass/fail status
3. Any code changes made (with file:line references)
4. Any blockers encountered

---

## Environment

- nanobrag_torch source: `/home/ollie/Documents/nanoBragg/src/nanobrag_torch`
- DBEX source: `/home/ollie/Documents/diffbragg_example`
- Required flags: `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1`
- GPU: 24GB (target for OOM fix validation)
- Recommended chunk size: 128 rows

---

## Pitfalls To Avoid

1. **DO NOT** modify nanobrag_torch source — the feature is already implemented upstream
2. **DO** use `KMP_DUPLICATE_LIB_OK=TRUE` to avoid Intel MKL conflicts
3. **DO NOT** change any physics code — only wire the existing `pixel_batch_size` parameter
4. **DO** preserve backward compatibility — make `pixel_batch_size` optional with `None` default
5. **DO** check if threading is needed at multiple levels (CLI, refinement, reconstruction)
6. **DO NOT** introduce new environment variables — use existing parameter threading
7. **DO** archive all pytest logs to the artifacts directory
8. **DO** ensure the feature is opt-in (full vectorization remains default)

---

## If Blocked

If pixel_batch_size threading requires significant API changes:

1. Document the required changes (which files, which functions)
2. Scope a minimal implementation (just enough to validate the OOM fix)
3. If OOM still occurs even with chunking, capture memory profile and document
4. Update `galph_memory.md` with block rationale

---

## Findings Applied (Mandatory)

- **RUNTIME-001**: NANOBRAGG_DISABLE_COMPILE=1 required for stable GPU execution
  - Adherence: Included in test commands
- **TESTING-003**: TEST_SUITE_INDEX.md update if new selectors added
  - Adherence: Will update if Phase C adds new test infrastructure

---

## Pointers

- `inbox/pixel-batching-implementation-response-2025-12-08.md` — Upstream feature details
- `plans/active/PERF-GPU-MEM-001/implementation.md:126-143` — Phase C checklist
- `plans/active/PERF-GPU-MEM-001/reports/2025-12-08T224000Z/memory_profile.md` — Phase A memory analysis
- `docs/fix_plan.md:97-108` — PERF-GPU-MEM-001 ledger entry

---

## Next Up (optional)

If Phase C succeeds:
- **C.6** — Run full detector smoke (if memory allows)
- **D.1-D.5** — Phase D validation tasks (full parity suite, docs update)

If Phase C blocked:
- Document blockers and return to supervisor for replanning
