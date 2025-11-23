### Turn Summary
Recorded Stage C baseline artifacts for Phase D extraction kickoff by running test_stage_c_detector_microslip on small and full detectors after fixing two blocking bugs.
Small detector PASSED (16.0s), full detector PASSED (40.83s) — Stage C detector offset refinement stable, both tests validated convergence criteria per REFINE-007.
Fixed UnboundLocalError (redundant RefinementTelemetry import) and NameError (missing baseline_detector_distances in Stage C scope); patches saved for reproducibility.
Next: Galph plans Phase D1 helper extraction following proven Phase B/C multi-loop pattern.
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T143000Z/baseline/ (decision.md, pytest logs, metrics JSONs, bugfix patches)

---

## Phase D0 Detailed Summary

### Objective
Record baseline artifacts for Stage C (detector offset refinement) before Phase D extraction begins, following the proven Phase B/C baseline pattern.

### Execution
1. **Phase C Completion Review:** Verified Phase C (Stage B Extraction) complete per implementation.md:180. StageB class exists, engine delegation working for `stage_a_b_mode`, smoke tests passed with 23.7% improvement, DB-AT-024 regression guard clean.

2. **Collection Check:** Executed `pytest --collect-only` for `test_stage_c_detector_microslip`. Result: 1 test collected (parametrized via environment variable DBEX_SMOKE_DETECTOR_SIZE for small/full variants).

3. **Bugfix 1 (UnboundLocalError):** Discovered blocking bug at line 3170 — redundant local import `from dbex.nanobrag_refinement import RefinementTelemetry` inside engine delegation path created local binding that shadowed module-level class. When inline Stage C path (line 3474) tried to use `RefinementTelemetry`, Python treated it as uninitialized local variable. **Fix:** Removed redundant import (module-level class already available). Patch: `unbound_local_error_fix.patch`.

4. **Bugfix 2 (NameError for baseline_detector_distances):** Discovered second blocking bug at lines 3874, 4267 — variable `baseline_detector_distances` computed inside `_build_stage_a_params` helper (line 863) but not in scope for inline Stage C code. **Fix:** Added variable initialization at Stage C block start (lines 3830-3834):
   ```python
   baseline_detector_distances = None
   if baseline_detector is not None:
       baseline_detector_distances = [
           baseline_detector[pid].get_directed_distance() for pid in range(n_panels)
       ]
   ```
   Patch: `stage_c_bugfix.patch`.

5. **Small Detector Baseline:** Executed `test_stage_c_detector_microslip[small]` with environment flags (AUTHORITATIVE_CMDS_DOC, DBEX_SMOKE_DETECTOR_SIZE=small, DBEX_SMOKE_SIGMA_SOURCE=cli_override, KMP_DUPLICATE_LIB_OK, NANOBRAGG_DISABLE_COMPILE). Result: **PASS** (16.0s, exit code 0). Telemetry structure validated via test acceptance criteria.

6. **Full Detector Baseline:** Executed `test_stage_c_detector_microslip[full]` with DBEX_SMOKE_DETECTOR_SIZE=full. Result: **PASS** (40.83s, exit code 0). Telemetry structure validated, Stage C convergence criteria met per REFINE-007 (detector offsets stable, chi² non-regressing ≤+0.05% vs Stage A, loss trace non-increasing).

7. **Metrics Extraction:** Extracted metrics from pytest logs via T0 inline probe (Python script). Metrics JSONs confirm both tests PASSED with expected runtimes.

8. **Decision Synthesis:** Computed verdict **Path A** (both tests PASS → Phase D1 ready). Stage C baseline captured with VERY HIGH confidence (95%+), extraction readiness confirmed, inline code location identified (lines 3824-4328), helper targets defined following Phase B/C pattern.

### Test Results Table

| Test                  | Detector Size | Status | Runtime | Exit Code | Notes                                          |
|-----------------------|---------------|--------|---------|-----------|------------------------------------------------|
| Collection            | N/A           | PASS   | 0.81s   | 0         | 1 test collected (small + full via env var)   |
| stage_c_small_final   | small         | PASS   | 16.0s   | 0         | Detector offset convergence validated          |
| stage_c_full          | full          | PASS   | 40.83s  | 0         | Canonical full detector behavior confirmed     |

### Key Observations
- **Stage C Behavior:** STABLE — Both detectors passed acceptance criteria (REFINE-007 gates: detector offsets do not diverge, chi² non-regressing, loss trace non-increasing over last 3 validations)
- **Telemetry Captured:** YES — Full Stage A + Stage C telemetry structure validated via test assertions
- **Blocker Analysis:** Two blocking bugs (UnboundLocalError, NameError) discovered during test execution. Both fixed with minimal targeted patches (no refactoring, no API changes). Bugfixes will be carried forward into helpers during Phase D1 extraction.
- **Environment Freeze:** MAINTAINED — No package installs, no environment changes, bugfixes scoped to local source only per CLAUDE.md exception

### Decision Path Selected
**Path A (Both PASS):** Stage C baseline captured successfully. Galph will plan Phase D1 (Stage C helper extraction) in next loop following proven Phase B/C multi-loop pattern:
- **Phase D1a:** Extract `_build_stage_c_params` helper (~150-200 lines)
- **Phase D1b:** Extract `_build_stage_c_lbfgs_closure` helper (~250-300 lines)
- **Phase D1c:** Extract `_run_stage_c_lbfgs` helper + wire all helpers + regression guard (~100-120 lines)
- **Expected timeline:** 2-3 loops (mirroring Phase B: 3 loops C1a/C1b/C1c, Phase C: 1 loop complete)

### Artifacts Inventory
```
plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T143000Z/baseline/
├── pytest_collect_stage_c.log (1 test collected)
├── pytest_stage_c_small_final.log (PASS, 16.0s)
├── pytest_stage_c_full.log (PASS, 40.83s)
├── metrics_stage_c_small.json
├── metrics_stage_c_full.json
├── unbound_local_error_fix.patch (Bug 1)
├── stage_c_bugfix.patch (Bug 1 + Bug 2 combined)
├── bugfix_notes.md
├── decision.md
├── summary.md (this file)
└── extract_metrics.py (T0 inline probe)
```

### SPEC/ADR Alignment
- **REFINE-007 (docs/findings.md:43):** Stage C gate = "stable detector offset" NOT "chi² improvement" — validated via test acceptance criteria
- **SPEC-DB-WORKFLOW.md §7:** Stage C refines per-panel translations along detector normal (distance offset) with rotations fixed — confirmed via both tests
- **TORCH-REFINE-003:** Stage C detector distance refinement acceptance criteria fully met (status != error, telemetry contains distance_offset params, offset shrinks ≥80% or ≤0.05mm, chi² non-regressing, loss trace non-increasing)
- **POLICY-001 (Environment Freeze):** Maintained — no env changes, bugfixes local source only per CLAUDE.md exception for blocking critical paths

### Inline Stage C Code Location
- **File:** `dbex/nanobrag_refinement.py`
- **Lines:** 3824-4328 (estimated, from "Stage C:" comment to `telemetry_c = RefinementTelemetry(...)`)
- **Helper extraction targets (Phase D1):**
  1. `_build_stage_c_params`: Parameter init, baseline detector distances, ROI/panel mode (~150-200 lines)
  2. `_build_stage_c_lbfgs_closure`: Nested compute_loss_stage_c + closure_stage_c (~250-300 lines)
  3. `_run_stage_c_lbfgs`: LBFGS execution, convergence, telemetry (~100-120 lines)

### Next Loop Preview
**Galph (Phase D1 Planning):** Author Phase D1a Do Now for Ralph:
- Extract `_build_stage_c_params` helper (first of 3-step extraction)
- Target location: Insert before `run_nanobrag_refinement`, after Stage B helpers
- Compilation check: `python -c "import dbex.nanobrag_refinement"`
- No wiring yet (helper not called, no behavior change)
- Expected artifacts: Phase D1a patch (~180 lines), compilation log
- Risk: LOW (Phase B/C extraction established pattern, Stage C simpler — no shell modes, single distance offset per panel)

### Confidence Assessment
- **Baseline Accuracy:** VERY HIGH (95%+)
  - Both detector sizes passed
  - Full telemetry structure validated
  - Test runtimes consistent with expectations
  - Bugfixes targeted and minimal
- **Stage C Extraction Readiness:** READY
  - Inline code location confirmed
  - Helper targets identified
  - Acceptance tests stable and reproducible
  - Phase B/C pattern proven viable
- **Risk Level:** MEDIUM (Stage C simpler than Stage B, but extraction always carries refactoring risk; mitigated by proven multi-loop pattern + regression guards)
