# Input — Phase D0: Stage C Baseline Artifacts

## Summary
Record baseline artifacts for Stage C (detector offset refinement) before Phase D extraction begins.

## Mode
none (baseline capture + test execution, no production code changes)

## Focus
ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase D0: Stage C baseline)

## Branch
`integration`

## Mapped Tests
- `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip[small]` (Active, validates Stage C detector offset logic)
- `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip[full]` (Active, canonical full detector)

## Artifacts
`plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T143000Z/baseline/`

## Do Now

Ralph, record baseline artifacts for Stage C extraction (Phase D0) following the proven Phase B/C pattern:

### 1. Review Phase C Completion

**Context**: Phase C (Stage B Extraction) is COMPLETE per implementation.md:180. Engine delegation working for `stage_a_b_mode`. Next: Phase D (Stage C Extraction).

**Tasks**:
1. Read `plans/active/ARCH-REFINE-FLOW-001/implementation.md` Phase C summary (lines 179-218)
2. Verify Phase C exit criteria met:
   - ✓ StageB class exists (dbex/refinement/stage_b.py)
   - ✓ Engine delegation wired (lines 3057-3180)
   - ✓ Stage B smoke PASSED (small detector, 23.7% improvement)
   - ✓ DB-AT-024 PASSED (no regression)
3. Note inline Stage C code location in `dbex/nanobrag_refinement.py` (estimate: lines ~3880-4130 based on typical structure)

### 2. Collection Check

**Tasks**:
1. Verify Stage C smoke tests exist and collect:
   ```bash
   pytest tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --collect-only > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T143000Z/baseline/pytest_collect_stage_c.log 2>&1
   echo "Exit code: $?" >> plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T143000Z/baseline/pytest_collect_stage_c.log
   ```

2. Expected: 2 tests (small + full detector variants)
3. If collection fails (0 tests): Document blocker in decision.md, escalate to Galph

### 3. Run Stage C Small Detector Baseline

**Context**: Small detector smoke validates core Stage C logic before extraction.

**Tasks**:
1. Run small detector test:
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   DBEX_SMOKE_DETECTOR_SIZE=small \
   DBEX_SMOKE_SIGMA_SOURCE=cli_override \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip[small] > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T143000Z/baseline/pytest_stage_c_small.log 2>&1
   echo "Exit code: $?" >> plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T143000Z/baseline/pytest_stage_c_small.log
   ```

2. Extract telemetry JSON if test PASSED:
   - Look for telemetry file path in test output (likely in plans/active/ARCH-REFINE-FLOW-001/reports/ or tests/fixtures/)
   - Copy to `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T143000Z/baseline/telemetry_stage_c_small.json`
   - If telemetry not written to file, extract key metrics from pytest log (chi² improvement, detector offset deltas, status)

3. Extract metrics (T0 micro probe inline):
   ```python
   import json
   metrics = {
       "test": "stage_c_small",
       "detector_size": "small",
       "status": "<PASS|FAIL|SKIP>",
       "exit_code": <int>,
       "runtime_seconds": <float>,
       "chi2_improvement_pct": <float or null>,
       "detector_offset_delta": <dict or null>,
       "notes": "<any key observations>"
   }
   with open('plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T143000Z/baseline/metrics_stage_c_small.json', 'w') as f:
       json.dump(metrics, f, indent=2)
   ```

### 4. Run Stage C Full Detector Baseline

**Context**: Full detector smoke validates canonical behavior before extraction.

**Tasks**:
1. Run full detector test:
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   DBEX_SMOKE_DETECTOR_SIZE=full \
   DBEX_SMOKE_SIGMA_SOURCE=cli_override \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip[full] > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T143000Z/baseline/pytest_stage_c_full.log 2>&1
   echo "Exit code: $?" >> plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T143000Z/baseline/pytest_stage_c_full.log
   ```

2. Extract telemetry JSON if test PASSED (same pattern as step 3)
3. Extract metrics (T0 micro probe, save to `metrics_stage_c_full.json`)

### 5. Decision Synthesis

**Tasks**:
1. Compute overall verdict:
   - Path A (Both PASS): Stage C baseline captured → Phase D1 ready (helper extraction)
   - Path B (Small PASS, Full FAIL): Baseline partial → investigate full detector failure, consider small-only extraction
   - Path C (Both FAIL): Stage C blocked → defer Phase D, escalate to Galph
   - Path D (Collection FAIL): Test infrastructure issue → escalate

2. Write `decision.md`:
   ```markdown
   # Phase D0 Baseline Decision

   ## Verdict
   <Path A|B|C|D>

   ## Test Results
   - Collection: <2 tests|0 tests> (<exit_code>)
   - Small detector: <PASS|FAIL|SKIP> (<runtime>s, chi² improvement <X%>)
   - Full detector: <PASS|FAIL|SKIP> (<runtime>s, chi² improvement <X%>)

   ## Key Observations
   - Stage C detector offset refinement behavior: <stable|unstable|blocked>
   - Telemetry captured: <yes|partial|no>
   - Blocker details (if Path C/D): <description>

   ## Next Actions
   - Path A: Galph plans Phase D1 (Stage C helper extraction)
   - Path B: Galph reviews full detector failure, decides small-only vs debug
   - Path C: Defer Phase D, escalate to Galph with blocker analysis
   - Path D: Escalate collection failure to Galph

   ## Confidence Assessment
   - Baseline accuracy: <VERY HIGH|HIGH|MEDIUM|LOW> (<percentage>%)
   - Stage C extraction readiness: <READY|PARTIAL|BLOCKED>
   ```

3. Save to `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T143000Z/baseline/decision.md`

### 6. Update Implementation Plan

**Tasks**:
1. Update `plans/active/ARCH-REFINE-FLOW-001/implementation.md` Phase D section (lines 220-227):
   - Mark D0 status: COMPLETE or BLOCKED
   - Add baseline artifacts reference
   - Note decision path (A/B/C/D)

2. Example update:
   ```markdown
   - [x] D0: Baseline Stage C artifacts recorded. ✓ COMPLETE (2025-11-23T143000Z)
     - Small detector: <PASS|FAIL> (<runtime>s, chi² improvement <X%>)
     - Full detector: <PASS|FAIL> (<runtime>s, chi² improvement <X%>)
     - Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T143000Z/baseline/
     - Decision: Path <A|B|C|D>
   ```

### 7. Write Summary

**Tasks**:
1. Create `summary.md` with Turn Summary block (prepend to file):
   ```markdown
   ### Turn Summary
   Recorded Stage C baseline artifacts for Phase D extraction kickoff by running test_stage_c_detector_microslip on small and full detectors.
   <Small detector result: PASS/FAIL with chi² improvement X%>, <full detector result: PASS/FAIL>.
   <Key observation about Stage C behavior: stable detector offset logic, or unstable convergence, or blocker>.
   Next: <Galph plans Phase D1 helper extraction | Galph reviews blocker and decides deferral vs debug>.
   Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T143000Z/baseline/ (decision.md, pytest logs, telemetry JSONs, metrics)
   ```

2. Append detailed summary:
   - Phase D0 objective (baseline capture)
   - Test results table (collection, small, full)
   - Decision path selected
   - Artifacts inventory
   - Next loop preview

3. Save to `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T143000Z/baseline/summary.md`

### 8. Commit and Push

```bash
git add plans/active/ARCH-REFINE-FLOW-001/
git commit -m "ARCH-REFINE-FLOW-001 Phase D0: Stage C baseline artifacts — tests: 2 collected"
git push
```

## How-To Map

### Test Collection
```bash
# Stage C smoke (should collect 2 tests: small + full)
pytest tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --collect-only
```

### Test Execution
```bash
# Small detector (fast, ~15-20s expected)
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_DETECTOR_SIZE=small \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip[small]

# Full detector (slower, ~25-35s expected)
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_DETECTOR_SIZE=full \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip[full]
```

### Artifact Paths
- Collection log: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T143000Z/baseline/pytest_collect_stage_c.log`
- Test logs: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T143000Z/baseline/pytest_stage_c_{small,full}.log`
- Telemetry: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T143000Z/baseline/telemetry_stage_c_{small,full}.json`
- Metrics: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T143000Z/baseline/metrics_stage_c_{small,full}.json`
- Decision: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T143000Z/baseline/decision.md`
- Summary: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T143000Z/baseline/summary.md`

## Pitfalls To Avoid

1. **Environment Flags**: MUST use all 5 flags (AUTHORITATIVE_CMDS_DOC, DBEX_SMOKE_DETECTOR_SIZE, DBEX_SMOKE_SIGMA_SOURCE, KMP_DUPLICATE_LIB_OK, NANOBRAGG_DISABLE_COMPILE) for reproducibility
2. **Exit Codes**: Always append `echo "Exit code: $?"` to capture test result status
3. **Telemetry Location**: Stage C may write telemetry to different path than Stage A/B — check pytest output for actual file path
4. **No Code Changes**: This is a baseline-only loop (no production code modifications, no helper extraction yet)
5. **Decision Synthesis**: Write decision.md even if tests fail (blocker analysis is part of baseline capture)
6. **Commit Message**: Use "tests: 2 collected" (collection confirms Stage C tests exist, baseline establishes pre-extraction behavior)
7. **Path B Handling**: If only small detector passes, this is ACCEPTABLE (can extract with small-only validation, mirroring Stage B CPU fallback pattern)
8. **REFINE-007 Gate**: Stage C acceptance is "stable detector offset" NOT "chi² improvement" — detector offsets should not diverge, but chi² may stay flat

## If Blocked

**Scenario A: Collection fails (0 tests)**
- Check test file exists: `tests/dbex/test_torch_refine_smoke.py`
- Verify function name: `def test_stage_c_detector_microslip`
- Document in decision.md: "Stage C test not found, collection blocked"
- Mark D0: BLOCKED
- Escalate to Galph with collection log

**Scenario B: Both tests FAIL**
- Extract failure signatures from pytest logs
- Check if failures are Stage C logic bugs vs test infrastructure issues
- Document in decision.md: "Stage C baseline FAIL, root cause: <signature>"
- Mark D0: BLOCKED
- Escalate to Galph with pytest logs + metrics

**Scenario C: Test timeout (>120s)**
- Document in decision.md: "Stage C timeout, likely detector offset divergence"
- Check pytest log for last known state
- Escalate to Galph with timeout analysis

**Scenario D: Telemetry not found**
- Document in decision.md: "Telemetry capture PARTIAL, extracted metrics from pytest log"
- Use T0 inline probe to extract key metrics from log output
- Proceed with decision synthesis (telemetry absence is not a blocker for baseline)

## Findings Applied

- **REFINE-007** (Stage C Gate: Stable Detector Offset): Stage C acceptance is "detector offsets do not diverge" (chi² improvement optional), apply this criterion in decision synthesis
- **PHYSICS-LOSS-001/002** (Variance-Weighted Loss + Sigma Floor): Stage C should inherit variance-weighted loss behavior from inline implementation
- **POLICY-001** (Environment Freeze): Baseline-only loop, no environment changes, no package installs
- **TESTING-003** (Selector Status Transitions): Collection log confirms Stage C tests exist before extraction begins
- **CONFORMANCE-001** (DB-AT Environment Flags): Use canonical environment flags for Stage C smoke (AUTHORITATIVE_CMDS_DOC, detector size, sigma source, KMP/compile flags)

## Pointers

- **Implementation Plan**: `plans/active/ARCH-REFINE-FLOW-001/implementation.md` Phase D (lines 220-232)
- **Phase B/C Pattern**: implementation.md Phase B (lines 80-178), Phase C (lines 179-218) — proven multi-loop extraction strategy
- **Test Location**: `tests/dbex/test_torch_refine_smoke.py` (line ~1400+ estimated, grep for `def test_stage_c_detector_microslip`)
- **Inline Stage C Code**: `dbex/nanobrag_refinement.py` lines ~3880-4130 (estimated, verify with grep for "Stage C:" comment)
- **Findings**: `docs/findings.md` REFINE-007 (Stage C gate), PHYSICS-LOSS-001/002 (variance model)
- **Spec**: `docs/spec-db-workflow.md` §7 (Stage C definition: detector offset refinement)
- **TESTING_GUIDE**: `docs/TESTING_GUIDE.md` §2 (Stage smoke selectors, environment flags)

## Next Up

After Phase D0 baseline complete, Galph next loop will plan Phase D1 (Stage C helper extraction):
- **Path A (both PASS)**: Extract Stage C helpers (~250 lines) following Phase B/C multi-loop pattern (likely 2-3 loops for helper extraction + wrapper)
- **Path B (small PASS, full FAIL)**: Review full detector failure, decide small-only extraction vs debug (mirroring Stage B CPU fallback decision pattern)
- **Path C (both FAIL)**: Defer Phase D, proceed to Phase E (orchestration hooks) without Stage C extraction
- **Risk**: MEDIUM (~30% Stage C failure, detector offset refinement less stable than geometry/shell modifiers)

**FSM Note**: This loop is `ready_for_implementation` (baseline capture + test execution + decision synthesis). Dwell resets to 0 after completion. Next Galph loop will be `planning` or `ready_for_implementation` depending on decision path.
