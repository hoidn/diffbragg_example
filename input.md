# ARCH-REFINE-FLOW-001 Phase C Full Validation — Ralph Do Now (Loop i=211)

## Summary
Validate Phase C Stage B extraction completion: run Stage B smokes (small + full detectors), verify telemetry completeness, validate DB-AT-024 mapping parity.

## Mode
none

## Focus
ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase C validation)

## Branch
integration

## Mapped Tests
- `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` (small detector, Active)
- `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` (full detector, env override)
- `tests/dbex/test_mapping_consistency.py::test_db_at_024_nanobrag_torch_mapping_consistency` (DB-AT-024, Active)

## Artifacts
`plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T084458Z/`
  - `collect_stage_b_smoke.log` (collection verification)
  - `pytest_stage_b_small.log` (Stage B smoke small detector)
  - `pytest_stage_b_full.log` (Stage B smoke full detector)
  - `collect_db_at_024.log` (DB-AT-024 collection)
  - `pytest_db_at_024.log` (DB-AT-024 mapping parity)
  - `phase_c_validation_metrics.json` (T0 probe output: 3 test statuses + telemetry structure)
  - `phase_c_decision.md` (decision synthesis per 4-path template)
  - `summary.md` (Turn Summary block prepended)

## Do Now

**Context:** Phase C extraction is COMPLETE (verified via code review):
- C0: Baseline artifacts ✓ (2025-11-23T061726Z)
- C1a: 3 helpers extracted ✓ (loops i=200-202, _build_stage_b_params, _build_stage_b_lbfgs_closure, _run_stage_b_lbfgs)
- C1b: StageB wrapper class ✓ (2025-11-22T230000Z, commit visible in fix_plan line 205)
- C2: Engine delegation A→B ✓ (already implemented dbex/nanobrag_refinement.py:2988-3100, stage_a_b_mode detection + RefinementEngine([StageA(), StageB()]))
- Bugfix: Cell param base fixed ✓ (loop i=210/Ralph, commit a038ac1, test PASSED 23.7% improvement)

**Objective:** Validate complete Phase C implementation meets all exit criteria (telemetry completeness, smoke tests, DB-AT selectors).

### Tasks

1. **Review Phase C completion evidence** (5 minutes):
   - Read `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T083100Z/summary.md` (Ralph's bugfix loop)
   - Verify engine delegation code exists: `grep -A 30 "stage_a_b_mode =" dbex/nanobrag_refinement.py`
   - Confirm StageB class exists: `ls -lh dbex/refinement/stage_b.py`

2. **Run Stage B smoke small detector** (~15s expected):
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   DBEX_SMOKE_DETECTOR_SIZE=small \
   DBEX_SMOKE_SIGMA_SOURCE=cli_override \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
   > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T084458Z/pytest_stage_b_small.log 2>&1
   ```
   - Expected: PASSED, Stage B improvement ≥3% (REFINE-008 gate lowered from ≥5% during calibration), chi² stable
   - Capture exit code: `echo $?` (must be 0)

3. **Run Stage B smoke full detector** (~20s expected, CPU fallback per PERF-WARM-011):
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   DBEX_SMOKE_DETECTOR_SIZE=full \
   DBEX_SMOKE_SIGMA_SOURCE=cli_override \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
   > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T084458Z/pytest_stage_b_full.log 2>&1
   ```
   - Expected: PASSED, Stage B improvement ≥3%, CPU fallback active (stage_b_full_eval_on_cpu=True), cache_mode="warm"
   - Capture exit code: `echo $?` (must be 0)

4. **Extract smoke metrics via T0 micro probe** (inline, paste command + output in summary.md):
   ```python
   python3 -c "
   import re, json
   from pathlib import Path

   artifacts = Path('plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T084458Z')

   # Parse small detector log
   small_log = (artifacts / 'pytest_stage_b_small.log').read_text()
   small_passed = 'PASSED' in small_log and '1 passed' in small_log

   # Parse full detector log
   full_log = (artifacts / 'pytest_stage_b_full.log').read_text()
   full_passed = 'PASSED' in full_log and '1 passed' in full_log

   # Check for Stage B telemetry structure (stage_type, mode, shell_modifier stats)
   telemetry_complete = (
       'stage_type' in small_log and
       'shell_modifiers' in small_log and
       'initial' in small_log and 'final' in small_log
   )

   metrics = {
       'stage_b_small': 'PASSED' if small_passed else 'FAILED',
       'stage_b_full': 'PASSED' if full_passed else 'FAILED',
       'telemetry_structure_complete': telemetry_complete,
       'overall_verdict': 'PASS' if (small_passed and full_passed and telemetry_complete) else 'FAIL'
   }

   (artifacts / 'phase_c_smoke_metrics.json').write_text(json.dumps(metrics, indent=2))
   print(json.dumps(metrics, indent=2))
   "
   ```

5. **Verify telemetry completeness** (review test output or telemetry JSON if captured):
   - Stage B telemetry MUST include:
     - `stage_type: "B"`
     - `mode: "shell_modifiers"`
     - `param_deltas` with `shell_modifier_<n>` entries showing `initial`/`final`/`delta` (3 shells expected)
     - Stage A frozen parameters: `log_scale`, `cell_a/b/c`, `cell_alpha/beta/gamma`, `misset_xyz_deg` from `stage_a_telemetry`
   - If telemetry incomplete: record which fields missing in `phase_c_decision.md`

6. **Run DB-AT-024 collection** (verify selector active):
   ```bash
   pytest --collect-only -v tests/dbex/test_mapping_consistency.py::test_db_at_024_nanobrag_torch_mapping_consistency \
   > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T084458Z/collect_db_at_024.log 2>&1
   ```
   - Expected: 1 test collected
   - If 0 collected: STOP, escalate to Galph

7. **Run DB-AT-024 mapping parity** (~30s expected):
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   DBEX_SMOKE_DETECTOR_SIZE=full \
   DBEX_SMOKE_SIGMA_SOURCE=cli_override \
   KMP_DUPLICATE_LIB_OK=TRUE \
   pytest -vv tests/dbex/test_mapping_consistency.py::test_db_at_024_nanobrag_torch_mapping_consistency \
   > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T084458Z/pytest_db_at_024.log 2>&1
   ```
   - Expected: PASSED, median correlation ≥0.2, localization ≥90%
   - Capture exit code: `echo $?` (must be 0)

8. **Extract DB-AT-024 metrics via T0 micro probe** (inline):
   ```python
   python3 -c "
   import re, json
   from pathlib import Path

   artifacts = Path('plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T084458Z')
   log = (artifacts / 'pytest_db_at_024.log').read_text()

   passed = 'PASSED' in log and '1 passed' in log

   metrics = {
       'db_at_024': 'PASSED' if passed else 'FAILED'
   }

   (artifacts / 'phase_c_db_at_024_metrics.json').write_text(json.dumps(metrics, indent=2))
   print(json.dumps(metrics, indent=2))
   "
   ```

9. **Decision synthesis** per 4-path template (write to `phase_c_decision.md`):
   - **Path A (all tests PASS + telemetry complete)**: Phase C COMPLETE — mark implementation.md C3/C4/C5 complete, proceed to Phase D planning next loop
   - **Path B (Stage B smoke FAIL)**: Debug Stage B execution — check logs for errors, verify engine delegation wiring, check helper signatures
   - **Path C (telemetry incomplete)**: Fix telemetry structure — identify missing fields, update StageB.run() or telemetry packaging code
   - **Path D (DB-AT-024 FAIL)**: Mapping regression — verify bridge helpers unaffected, check for HKL grid changes, compare baseline vs current
   - Write decision rationale, confidence assessment (HIGH/MEDIUM/LOW), and next-step recommendations

10. **Update implementation.md** Phase C status:
    - If Path A: Mark `[ ] C3`, `[ ] C4`, `[ ] C5` as `[x]` with completion timestamp `2025-11-23T084458Z`
    - Add Phase C Completion Summary section documenting: validation results, test timings, telemetry verification, confidence assessment
    - If Path B/C/D: Document blocker in Attempts History with timestamp + path letter + next actions

11. **Write summary.md** with Turn Summary block (prepend to existing summary.md):
    ```markdown
    ### Turn Summary (Ralph, Loop i=211)
    <One-line what shipped/advanced>
    <Main problem and how handled OR note it's still open>
    <Single next step>
    Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T084458Z/ (pytest_stage_b_small.log, pytest_stage_b_full.log, pytest_db_at_024.log, phase_c_decision.md)
    ```

12. **Commit and push**:
    ```bash
    git add plans/active/ARCH-REFINE-FLOW-001/
    git commit -m "ARCH-REFINE-FLOW-001 Phase C validation: Stage B smokes + DB-AT-024 — tests: <result>"
    git push
    ```

## How-To Map

### Environment Setup
```bash
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
export DBEX_SMOKE_SIGMA_SOURCE=cli_override
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1
```

### Test Execution Order
1. Stage B smoke small (DBEX_SMOKE_DETECTOR_SIZE=small)
2. Stage B smoke full (DBEX_SMOKE_DETECTOR_SIZE=full)
3. DB-AT-024 collection check
4. DB-AT-024 mapping parity (DBEX_SMOKE_DETECTOR_SIZE=full)

### Metrics Extraction
- Use T0 inline Python probes (paste command + output in summary.md "Micro probes" section)
- Save JSON metrics to artifacts directory
- Decision synthesis must reference JSON files and log evidence

### Decision Tree
```
┌─ All 3 tests PASS + telemetry complete?
│  ├─ YES → Path A: Phase C COMPLETE
│  └─ NO  → Check which failed:
│     ├─ Stage B smoke → Path B: Debug execution
│     ├─ Telemetry incomplete → Path C: Fix telemetry
│     └─ DB-AT-024 → Path D: Mapping regression
```

## Pitfalls To Avoid

1. **Environment flags**: Must set ALL 4 env vars (AUTHORITATIVE_CMDS_DOC, DBEX_SMOKE_SIGMA_SOURCE, KMP_DUPLICATE_LIB_OK, NANOBRAGG_DISABLE_COMPILE) for every test invocation
2. **Full detector size**: DB-AT-024 requires `DBEX_SMOKE_DETECTOR_SIZE=full` (not small)
3. **CPU fallback**: Stage B full detector runs on CPU per PERF-WARM-011 (GPU OOM), expect `stage_b_full_eval_on_cpu=True` in telemetry
4. **Collection verification**: ALWAYS run `pytest --collect-only` for DB-AT-024 BEFORE running the test to verify selector is active (0 collected = STOP)
5. **Telemetry structure**: Verify Stage B telemetry has NESTED param_deltas structure (`{'initial': X, 'final': Y, 'delta': Z}` per param), NOT flat scalars
6. **REFINE-008 gate**: Stage B improvement gate is ≥3% (NOT ≥5%, calibrated lower during earlier phases)
7. **Baseline crystal**: Stage B now requires `baseline_crystal` parameter (bugfix just applied), verify test passes it correctly
8. **T0 inline probes**: Paste BOTH command AND output in summary.md "Micro probes" section (not separate files for T0)
9. **Decision synthesis**: Must explicitly state Path letter (A/B/C/D), confidence (HIGH/MEDIUM/LOW), and next actions
10. **Phase C scope**: This validates C3/C4/C5 COMBINED (telemetry + smokes + DB-AT), NOT individual sub-tasks

## If Blocked

1. **Stage B smoke fails**:
   - Check pytest log for errors (NoneType, signature mismatches, CUDA OOM, etc.)
   - Verify engine delegation code exists: `grep "stage_a_b_mode" dbex/nanobrag_refinement.py`
   - Verify StageB.run() signature matches engine contract
   - Verify baseline_crystal parameter passed in test
   - Document error signature + traceback in `phase_c_decision.md` Path B section
   - Mark focus=ARCH-REFINE-FLOW-001 as blocked in Attempts History with return conditions

2. **Telemetry incomplete**:
   - List missing fields (stage_type, mode, shell_modifier stats, Stage A metadata)
   - Check StageB.run() telemetry packaging code (dbex/refinement/stage_b.py ~lines 200-400)
   - Check if StageA telemetry propagated correctly to StageB.run() inputs
   - Document in `phase_c_decision.md` Path C section
   - Create targeted bugfix initiative if >3 fields missing

3. **DB-AT-024 fails**:
   - Extract correlation + localization metrics from pytest log
   - Compare current vs baseline mapping artifacts
   - Check if bridge helpers changed during Phase C extraction
   - Verify HKL grid unchanged
   - Document in `phase_c_decision.md` Path D section
   - Escalate if correlation <0.1 or localization <50%

4. **Collection returns 0**:
   - STOP immediately (selector broken or moved)
   - Verify test file exists: `ls tests/dbex/test_mapping_consistency.py`
   - Check test name spelling: `grep "def test_db_at_024" tests/dbex/test_mapping_consistency.py`
   - Escalate to Galph with collection log

## Findings Applied

- **REFINE-008** (Stage B ±1% gate calibrated to ≥3% improvement during earlier phases)
- **PHYSICS-LOSS-001** (variance-weighted loss telemetry stack, chi² vs masked-MSE)
- **PHYSICS-LOSS-002** (sigma_floor guard enforced, telemetry records floor value + clamp fraction)
- **PERF-WARM-011** (canonical Stage B runs on CPU to avoid GPU OOM, stage_b_full_eval_on_cpu=True)
- **PERF-WARM-012** (CPU fallback reuses Stage A warm cache, cache_mode="warm")
- **TESTING-003** (collection verification before pytest execution, >0 tests required)
- **CONFORMANCE-001** (KMP_DUPLICATE_LIB_OK=TRUE environment flag for all tests)
- **RUNTIME-001** (NANOBRAGG_DISABLE_COMPILE=1 for all gradient/refinement tests)

## Pointers

- Implementation plan: `plans/active/ARCH-REFINE-FLOW-001/implementation.md:179-211` (Phase C tasks C3-C5)
- Engine delegation code: `dbex/nanobrag_refinement.py:2988-3100` (stage_a_b_mode + RefinementEngine([StageA(), StageB()]))
- StageB class: `dbex/refinement/stage_b.py` (wrapper calling 3 extracted helpers)
- Stage B helpers: `dbex/nanobrag_refinement.py:~2087-2700` (_build_stage_b_params, _build_stage_b_lbfgs_closure, _run_stage_b_lbfgs)
- TESTING_GUIDE.md: `docs/TESTING_GUIDE.md:§2` (Stage B smoke selectors)
- REFINE-008 finding: `docs/findings.md` (Stage B shell modifier ±1% gate calibrated)
- Phase C bugfix artifacts: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T083100Z/` (cell param base fix)

## Next Up

If Phase C validation PASSES (Path A):
- Galph plans Phase D (Stage C extraction) next loop following proven multi-loop strategy from Phases B/C

If Phase C validation FAILS (Path B/C/D):
- Galph reviews blocker decision.md and chooses: debug/patch/escalate/simplify scope
