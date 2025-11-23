# Phase C2.2 HKL Hit-Rate Diagnostic Investigation

## Summary
Investigate why CPU fallback path has 0% HKL hit rate (all 224M lookups out of bounds), identify crystal parameter/configuration mismatch between CUDA and CPU StageAContext construction, and apply targeted fix.

## Mode
none — evidence-only (diagnostic instrumentation + analysis)

## Focus
ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase C2.2 HKL hit-rate parameter diagnostic)

## Branch
integration

## Mapped Tests
- `pytest -xvs tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers -k "not small_detector"` (full detector, CPU fallback path) — evidence gathering, expected to FAIL but with diagnostic output
- none — pure diagnostic loop, no validation tests

## Artifacts
plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T120000Z/{root_cause_analysis_v3.md, crystal_config_comparison.md, hkl_diagnostics.log, decision.md, summary.md}

## Do Now

### Context Review
1. Read `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T120000Z/root_cause_analysis_v3.md` (comprehensive HKL hit-rate analysis with 4 ranked hypotheses)
2. Read Ralph's loop i=218 blocker: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T111500Z/blocker_hypothesis_b.md`
3. Review prior RCA: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T111500Z/root_cause_analysis_v2.md` (Hypothesis A — in-place HKL, now confirmed working on CUDA)

### Diagnostic Instrumentation (Phase 1-2)
4. **Add Crystal Config Diagnostics** to CPU path:
   - Location: `dbex/nanobrag_refinement.py` after line 2209 (where `stage_b_eval_stage_a_ctx` is built for CPU)
   - Insert temporary diagnostic print BEFORE `_build_stage_a_context` call:
     ```python
     # DIAGNOSTIC: CPU crystal config comparison (temp)
     print(f"[CRYSTAL_CPU_PRE] cell={crystal.get_unit_cell().parameters()}")
     print(f"[CRYSTAL_CPU_PRE] A_matrix={np.array(crystal.get_A()).reshape(3,3).tolist()}")
     print(f"[CRYSTAL_CPU_PRE] U_matrix={np.array(crystal.get_U()).reshape(3,3).tolist()}")
     print(f"[CRYSTAL_CPU_PRE] B_matrix={np.array(crystal.get_B()).reshape(3,3).tolist()}")
     ```
   - Inside `_build_stage_a_context` after line 548 (`crystal_config, _ = create_crystal_config(...)`):
     ```python
     # DIAGNOSTIC: CPU crystal config post-bridge (temp)
     print(f"[CRYSTAL_CPU_POST] cell_a={crystal_config.cell_a}, cell_b={crystal_config.cell_b}, cell_c={crystal_config.cell_c}")
     print(f"[CRYSTAL_CPU_POST] cell_alpha={crystal_config.cell_alpha}, cell_beta={crystal_config.cell_beta}, cell_gamma={crystal_config.cell_gamma}")
     print(f"[CRYSTAL_CPU_POST] mosflm_a_star={getattr(crystal_config, 'mosflm_a_star', None)}")
     print(f"[CRYSTAL_CPU_POST] mosflm_b_star={getattr(crystal_config, 'mosflm_b_star', None)}")
     print(f"[CRYSTAL_CPU_POST] mosflm_c_star={getattr(crystal_config, 'mosflm_c_star', None)}")
     print(f"[CRYSTAL_CPU_POST] misset_deg={getattr(crystal_config, 'misset_deg', None)}")
     print(f"[CRYSTAL_CPU_POST] device={device}")
     ```

5. **Add CUDA Crystal Config Diagnostics** for comparison:
   - Location: Before line 924 (where original `stage_a_ctx = _build_stage_a_context` is called for CUDA)
   - Insert same `[CRYSTAL_CUDA_PRE]` and `[CRYSTAL_CUDA_POST]` diagnostics as above

6. **Add HKL Index Diagnostics** to simulator:
   - **CRITICAL**: Do NOT edit `/home/ollie/Documents/nanoBragg/src/nanobrag_torch/simulator.py` (external package, requires patch workflow)
   - Instead, add diagnostic AFTER simulator.run() call in closure at line ~2503 or ~2559:
     ```python
     # DIAGNOSTIC: Extract first HKL indices after run (temp)
     if eval_device.type == "cpu":
         print(f"[BRAGG_CPU] bragg_patch.shape={bragg_patch.shape}, bragg_patch.min={bragg_patch.min().item()}, bragg_patch.max={bragg_patch.max().item()}, bragg_patch.mean={bragg_patch.mean().item()}")
     ```

### Test Execution
7. **Run full detector test with diagnostics**:
   ```bash
   DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_SIGMA_SOURCE=cli_override KMP_DUPLICATE_LIB_OK=TRUE \
   pytest -xvs tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers 2>&1 | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T120000Z/pytest_stage_b_full_diagnostic.log
   ```
   - Expected outcome: FAIL (same gradient error), but with crystal config comparison output

### Analysis & Decision
8. **Extract and Compare Crystal Configs**:
   ```bash
   grep "CRYSTAL_CPU_PRE\|CRYSTAL_CPU_POST\|CRYSTAL_CUDA_PRE\|CRYSTAL_CUDA_POST" plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T120000Z/pytest_stage_b_full_diagnostic.log > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T120000Z/crystal_config_comparison.txt
   ```
   - Identify differences between CUDA and CPU crystal parameters
   - Check cell parameters (a,b,c,alpha,beta,gamma)
   - Check MOSFLM A* vectors (mosflm_a/b/c_star)
   - Check misset angles

9. **Synthesize Root Cause and Decision Path**:
   - Write `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T120000Z/decision.md` with findings
   - If parameter mismatch identified → **DO NOT APPLY FIX THIS LOOP** (evidence-only per Mode)
   - Document specific parameter discrepancy and proposed one-line fix location
   - Rank decision paths A-D per root_cause_analysis_v3.md §Decision Paths

10. **Document Findings**:
    - Write `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T120000Z/summary.md` with:
      - Parameter comparison table (CUDA vs CPU)
      - Identified mismatch (if any)
      - Proposed fix (file:line:change)
      - Decision path recommendation (A/B/C/D)
      - Next loop actions (apply fix, validate, clean up)

## How-To Map

**Test command** (already provided in step 7):
```bash
DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_SIGMA_SOURCE=cli_override KMP_DUPLICATE_LIB_OK=TRUE \
pytest -xvs tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers
```

**Crystal config extraction**:
```bash
grep "CRYSTAL_" <pytest_log> | sort | uniq > crystal_comparison.txt
```

**HKL stats extraction**:
```bash
grep "HKL stats" <pytest_log>
```

**Bragg tensor diagnostics**:
```bash
grep "BRAGG_CPU" <pytest_log>
```

## Pitfalls To Avoid

1. **Do NOT edit nanobrag_torch source** (`/home/ollie/Documents/nanoBragg/src/nanobrag_torch/*.py`) — that requires patch workflow per POLICY-001; add diagnostics around simulator calls instead
2. **Do NOT apply fixes this loop** — Mode: none means evidence gathering only; next loop will be ready_for_implementation with the identified fix
3. **Do NOT remove existing diagnostics yet** — Keep HKL_GRAD_CHECK and CPU_FALLBACK_DIAGNOSTICS blocks for comparison
4. **Ensure crystal diagnostics print BEFORE and AFTER bridge transformation** — need both dxtbx crystal state AND nanobrag_torch CrystalConfig state
5. **Use consistent print prefixes** — `[CRYSTAL_CPU_PRE]`, `[CRYSTAL_CPU_POST]`, `[CRYSTAL_CUDA_PRE]`, `[CRYSTAL_CUDA_POST]` for easy grepping
6. **Extract actual numeric values, not object repr** — Use `.tolist()` for numpy arrays, `.item()` for tensors
7. **Compare apples-to-apples** — Both CUDA and CPU paths should show the SAME diagnostic outputs in the SAME format
8. **Environment Freeze** — No package installs; diagnostics are temporary print statements only
9. **Remember this is evidence gathering** — Expect test to FAIL; success criteria is diagnostic output quality, not test passage
10. **Document the proposed fix but don't apply it** — Next loop (ready_for_implementation per dwell guard) will apply the fix after Galph reviews this evidence

## Findings Applied

- **GRADIENT-002** (In-Place HKL Modification): Out-of-place torch.where fix WORKS on CUDA (small detector PASSED), proves gradient preservation technique is correct
- **PERF-WARM-011/012** (CPU Fallback Context): CPU StageAContext construction at line 2209 is suspected parameter mismatch source
- **POLICY-001** (Environment Freeze): Diagnostics are temporary prints, no external package edits; nanobrag_torch changes require patch workflow
- **RUNTIME-001/CONFORMANCE-001**: Test environment flags preserved (DBEX_SMOKE_DETECTOR_SIZE, DBEX_SMOKE_SIGMA_SOURCE, KMP_DUPLICATE_LIB_OK)

## Pointers

- Root Cause Analysis v3: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T120000Z/root_cause_analysis_v3.md`
- Loop i=218 Blocker: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T111500Z/blocker_hypothesis_b.md`
- Loop i=217 RCA v2: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T111500Z/root_cause_analysis_v2.md`
- CPU Context Builder: `dbex/nanobrag_refinement.py:2206-2221`
- Crystal Config Bridge: `dbex/nanobrag_bridge.py:445-506` (per GRADIENT-001)
- Stage A Context Builder: `dbex/nanobrag_refinement.py:490-652`
- HKL Hit-Rate Stats: Emitted by `nanobrag_torch/simulator.py` (read-only, external package)

## If Blocked

If diagnostics don't reveal obvious parameter mismatch:
1. Capture full diagnostic logs in `hkl_diagnostics.log`
2. Write `decision.md` documenting ambiguity
3. Propose next steps: either (a) add reciprocal lattice vector diagnostics to nanobrag_torch (requires patch), or (b) minimal reproducer with known HKL grid, or (c) escalate to defer CPU fallback support
4. Document block in `summary.md` and commit diagnostic artifacts
5. Next loop: Galph reviews and decides escalation path (Path B/C from RCA v3)

## Next Up

If parameter mismatch found this loop:
- **Next Loop (ready_for_implementation)**: Apply targeted one-line parameter fix, validate both small+full detector tests, remove diagnostics if both PASS, mark Phase C2.2 COMPLETE

If no mismatch found:
- **Next Loop (gathering_evidence)**: Add reciprocal lattice vector diagnostics per Phase 2, or build minimal reproducer per Phase 4

## Doc Sync Plan

None — diagnostic loop, no tests modified.

## Normative References

- See `docs/spec-db-core.md` for HKL grid semantics and structure factor lookup requirements
- See `docs/spec-db-runtime.md` for device neutrality requirements
- See `docs/config_crosswalk.md` for crystal parameter mapping conventions
