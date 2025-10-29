# NANOBRAG-GOLDEN-001 Loop Summary (2025-10-29T030352Z)

## Objectives
Phase A1-A2 environment bootstrapping and DiffBragg baseline capture for canonical golden dataset generation.

## Status: PARTIAL — 3/4 Checklist Items Completed, 1 Blocked

### Completed Items

#### A1.1 — Environment Validation ✓
- **Torch import issue:** RESOLVED (self-healed since 2025-10-29T024902Z)
- **Python:** 3.9.23 @ `/home/ollie/miniconda3/envs/simtbx/bin/python`
- **Torch:** 2.8.0+cu128
- **CUDA:** Available (GeForce RTX 3090, driver 570.195.03, runtime 12.0.140)
- **dbex module:** Imports cleanly (no cudaGetDriverEntryPointByVersion error)
- **Diagnostics captured:** `golden_dataset/env_bootstrap.log` (full torch.utils.collect_env output)

#### A1.2 — nanobrag_torch Installation ✓
- **Repository:** https://github.com/hoidn/nanoBragg.git cloned to `nanoBragg2/`
- **Version:** 0.1.0
- **Installation:** `pip install -e ./nanoBragg2` (editable mode)
- **Dependencies:** fabio, lxml, matplotlib, scipy, pytest (all satisfied)
- **Verification:** `import nanobrag_torch; print(nanobrag_torch.__version__)` → `0.1.0`

#### A3 — Selector Collection Evidence ✓
Per Doc Sync Plan (input.md:52-53), collected pytest evidence for Active selectors:
- **DB_AT_001 parity:** 14 tests collected (`test_db_at_001_parity.py`)
- **DB_AT_001 forward equivalence:** 1 test collected (`test_forward_equivalence_complete.py`)
- **Artifact paths:**
  - `collect_db_at_001_parity.log`
  - `collect_db_at_001_forward.log`
- **Compliance:** Both selectors documented as Active in `docs/TESTING_GUIDE.md` collect >0 tests (satisfies TESTING-003 finding)

### Blocked Item

#### A2 — DiffBragg Baseline Export ✗
- **Objective:** Capture `bragg_diffbragg.npy` tensor via forward-only pass for Phase B comparison
- **Attempt:** Custom script `scratch/capture_diffbragg.py` invoking `run_diffbragg(DL, devId=0)`
- **Result:** BLOCKED by CUDA error
  - Refinement **succeeded** (2101 iterations, converged to `F=678151 sigZ=12.27413`)
  - Final forward pass for Bragg tensor export **failed** with:
    ```
    GPUassert: invalid argument /home/ollie/Documents/easyBragg/simtbx_project/simtbx/diffBragg/src/diffBraggCUDA.cu 708
    ```
  - No `.npy` output files generated
- **Log:** `golden_dataset/legacy/diffbragg_forward.log` (897 KB, 2101 iterations logged)
- **Impact:** Cannot proceed with Phase A3 (nanoBragg2 forward capture for panel 0) or Phase B (canonical dataset manifest) until DiffBragg baseline is available

## Artifacts Generated

### Environment Diagnostics
- `golden_dataset/env_bootstrap.log` — torch environment, nanobrag_torch installation logs
- `golden_dataset/blocking_summary.md` — CUDA blocker documentation

### DiffBragg Baseline (Incomplete)
- `golden_dataset/legacy/diffbragg_forward.log` — Full refinement log (897 KB, 2101 iterations)
- `golden_dataset/legacy/bragg_diffbragg.npy` — NOT CREATED (CUDA error)
- `golden_dataset/legacy/metadata.txt` — NOT CREATED (CUDA error)
- `scratch/capture_diffbragg.py` — Custom capture script (DataLoad → run_diffbragg)

### Test Evidence
- `collect_db_at_001_parity.log` — 14 tests collected (0.22s, Python 3.9.23, pytest 8.4.2)
- `collect_db_at_001_forward.log` — 1 test collected (0.98s, warnings logged)

## Metrics Summary
- **Environment checks:** 3/3 passed (torch, nanobrag_torch, dbex)
- **Dependencies installed:** 2 new packages (fabio, lxml)
- **DiffBragg refinement:** 2101 iterations, converged
- **DiffBragg baseline export:** 0/1 succeeded (CUDA error)
- **nanoBragg2 forward capture:** Not attempted (depends on blocked A2)
- **Selectors validated:** 2/2 Active selectors collect >0 tests (15 total tests)
- **Artifacts captured:** 6 files (env, logs, blocking summary, collect evidence)

## Root Cause Analysis: DiffBragg CUDA Error

### Error Details
- **Location:** `diffBraggCUDA.cu:708` (simtbx/diffBragg compiled extension)
- **CUDA assertion:** "invalid argument"
- **Timing:** Post-refinement, during final Bragg tensor forward pass
- **Hypothesis:**
  1. Possible mismatch between CUDA runtime (12.0.140) and compiled extension expectations
  2. GPU memory fragmentation after 2101 refinement iterations
  3. Invalid buffer/pointer passed to CUDA kernel at line 708

### Attempted Remediation (Prior Loops)
- **2025-10-29T024902Z:** Reinstalled torch 2.8.0+cu128 (did not resolve DiffBragg CUDA error, but resolved import issue)
- **Current loop:** Custom capture script with explicit DataLoad API invocation (still hit CUDA error)

### Recommended Next Steps
1. **Investigate CUDA line 708:** Inspect diffBraggCUDA.cu to identify kernel call and argument validation
2. **Try CPU fallback:** Modify `run_diffbragg(DL, devId=-1)` to force CPU execution (if supported)
3. **Memory cleanup:** Add explicit `torch.cuda.empty_cache()` before final forward pass
4. **Alternative capture path:** Extract Bragg tensor from intermediate HDF5 outputs (if available)
5. **Skip DiffBragg baseline:** Proceed with Phase A3 using nanobrag_torch only, defer comparison to Phase B

## Next Actions for Supervisor
1. **Escalate blocker:** DiffBragg CUDA error blocking Phase A2; requires external expertise or workaround strategy
2. **Consider alternative path:** Authorize Phase A3 (nanobrag_torch forward capture) independently of DiffBragg baseline
3. **Update plan:** Revise Phase B manifest expectations to handle missing DiffBragg tensor (mark as TODO or FALLBACK)
4. **Documentation:** Ensure blocking_summary.md is cited in next `input.md` for visibility

## Compliance Checkpoints
- ✓ KMP_DUPLICATE_LIB_OK=TRUE honored for all pytest invocations
- ✓ Artifact directory `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T030352Z/` structure maintained
- ✓ Selector compliance (TESTING-003): Both Active selectors collect >0 tests
- ✓ Findings applied: CONFORMANCE-001, CONFIG-001, DIAGNOSTICS-001, TESTING-003 (referenced in blocking summary)
- ✗ Phase A2 exit criteria NOT MET: `bragg_diffbragg.npy` not captured due to CUDA error

## Files Modified/Created
```
plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T030352Z/
├── golden_dataset/
│   ├── env_bootstrap.log (torch + nanobrag_torch diagnostics)
│   ├── blocking_summary.md (CUDA blocker documentation)
│   ├── legacy/
│   │   └── diffbragg_forward.log (897 KB, 2101 iterations, CUDA error)
│   └── torch/ (empty, awaiting Phase A3)
├── scratch/
│   └── capture_diffbragg.py (DiffBragg forward capture script)
├── collect_db_at_001_parity.log (14 tests)
├── collect_db_at_001_forward.log (1 test)
└── loop_summary.md (this file)
```

## Git Status
- **nanoBragg2/ cloned** (not tracked, .gitignore expected)
- **No commits made** (per process: document block before escalating)
