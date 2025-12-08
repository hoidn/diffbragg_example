# Input for Ralph (Loop i=165)

## Summary
Execute RUNTIME-VEC-001 Phase B (Validation & Test Execution) — run the existing source-weight test with proper environment variables, capture artifacts, and update test registry docs.

## BindingForRalph
- **ActionType:** implementation_ready
- **DecisionStatus:** patch_ready
- **InitiativeType:** perf

## SupervisorMode
none (validation execution)

## Focus
RUNTIME-VEC-001 — Runtime Vectorization Checklist Enforcement (Phase B)

## Branch
integration

## Mapped Tests
- `pytest -v tests/dbex/test_runtime_vectorization.py::TestRuntimeVectorization::test_source_weights_ignored_per_spec`
- `pytest --collect-only tests/dbex/test_runtime_vectorization.py`

## Artifacts
`plans/active/RUNTIME-VEC-001/reports/2025-12-08T160000Z/`

## Findings Applied (Mandatory)
- **RUNTIME-001** — Gradient tests require `NANOBRAGG_DISABLE_COMPILE=1` to avoid Dynamo interference
- **PROBE-FREEZE-001** — No new plan-local scripts; test already exists in production test suite

## Pointers
- Plan: `plans/active/RUNTIME-VEC-001/implementation.md` — Phase B checklist
- Fix-plan row: `docs/fix_plan.md` line 466 — [RUNTIME-VEC-001]
- Test file: `tests/dbex/test_runtime_vectorization.py` — existing test to validate
- Spec refs: `docs/pytorch_runtime_checklist.md` §4 (source equal-weight rule)

## ARCH Contracts (mandatory)
1. **ARCH-CONTRACT-RUNTIME-001**: Source equal-weighting
   - Owner: `nanobrag_torch` simulator runtime (source weight normalization)
   - Classification: implementation validation (existing test verification)

---

## Do Now

**Focus:** RUNTIME-VEC-001 Phase B (Validation & Test Execution)

### Execute Phase B tasks from `plans/active/RUNTIME-VEC-001/implementation.md`:

#### B1: Validate the existing test (test already exists — no porting needed)
1. **Confirm test exists:**
   ```bash
   pytest --collect-only tests/dbex/test_runtime_vectorization.py 2>&1 | tee plans/active/RUNTIME-VEC-001/reports/2025-12-08T160000Z/collect_runtime_vec.log
   ```
   Expected: 1 test collected (`test_source_weights_ignored_per_spec`)

2. **Note:** Per Phase A findings (a2_test_inventory.md), this test is already ported from nanoBragg. B1 from implementation.md says "Port..." but the test exists — confirm test validity instead.

#### B2: Execute the test with proper environment
1. **Run the test with artifact routing:**
   ```bash
   mkdir -p plans/active/RUNTIME-VEC-001/reports/2025-12-08T160000Z/artifacts

   RUNTIME_VEC_ARTIFACT_DIR=plans/active/RUNTIME-VEC-001/reports/2025-12-08T160000Z/artifacts \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -v tests/dbex/test_runtime_vectorization.py::TestRuntimeVectorization::test_source_weights_ignored_per_spec 2>&1 | tee plans/active/RUNTIME-VEC-001/reports/2025-12-08T160000Z/pytest_runtime_vec.log
   ```

2. **Capture result:**
   - If PASSED: Proceed to B3
   - If FAILED: Document blocker, check `blocker_log.txt` in artifact dir, record in summary

#### B3: Verify artifact output
1. **Check metrics JSON exists:**
   ```bash
   cat plans/active/RUNTIME-VEC-001/reports/2025-12-08T160000Z/artifacts/mapping_metrics.json
   ```
2. **Verify thresholds:**
   - `correlation >= 0.999` ✓
   - `|sum_ratio - 1| <= 5e-3` ✓
3. **If metrics show PASS:** Exit criteria 1 satisfied, proceed to Phase C tasks

#### B4: Document Phase B completion or deferral
1. **Update implementation.md:** Mark B1, B2 as complete (or note deferred scope for B3)
2. **Create summary.md:** Document test execution results, correlation/sum_ratio metrics

---

## Phase C Tasks (Docs Update — Complete in this loop if Phase B passes)

#### C1: Update docs/TESTING_GUIDE.md
Add RUNTIME-VEC-001 entry under §2 (Test Selectors) or appropriate section:

```markdown
### Runtime Vectorization Tests (RUNTIME-VEC-001)

**Selector:**
```bash
RUNTIME_VEC_ARTIFACT_DIR=/path/to/artifacts \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -v tests/dbex/test_runtime_vectorization.py::TestRuntimeVectorization::test_source_weights_ignored_per_spec
```

**Status:** Active
**Exit Criteria:** correlation ≥0.999, |sum_ratio−1| ≤5e-3
**Artifacts:** `$RUNTIME_VEC_ARTIFACT_DIR/mapping_metrics.json`
**Reference:** docs/pytorch_runtime_checklist.md §4
```

#### C2: Update docs/development/TEST_SUITE_INDEX.md
Add row for RUNTIME-VEC-001 tests:

| Test File | Selector | Status | Description |
|-----------|----------|--------|-------------|
| `tests/dbex/test_runtime_vectorization.py` | `-k test_source_weights` | Active | Source equal-weight enforcement per RUNTIME-VEC-001 |

#### C3: Update fix_plan.md Attempts History
Add Loop i=165 entry to [RUNTIME-VEC-001] section documenting:
- Test execution result (PASSED/FAILED)
- Metrics: correlation, sum_ratio
- Artifacts path
- Phase B/C completion status

---

## How-To Map

```bash
# Set environment
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
cd /home/ollie/Documents/diffbragg_example

# B1: Collect-only verification
pytest --collect-only tests/dbex/test_runtime_vectorization.py

# B2: Run test with artifact routing
mkdir -p plans/active/RUNTIME-VEC-001/reports/2025-12-08T160000Z/artifacts

RUNTIME_VEC_ARTIFACT_DIR=plans/active/RUNTIME-VEC-001/reports/2025-12-08T160000Z/artifacts \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -v tests/dbex/test_runtime_vectorization.py::TestRuntimeVectorization::test_source_weights_ignored_per_spec

# B3: Verify artifacts
cat plans/active/RUNTIME-VEC-001/reports/2025-12-08T160000Z/artifacts/mapping_metrics.json 2>/dev/null || echo "No metrics (test may have failed)"

# C1/C2: Doc updates (edit files manually)
```

## Pitfalls To Avoid
1. **Do not skip RUNTIME_VEC_ARTIFACT_DIR** — test will skip without this env var
2. **Do not forget KMP_DUPLICATE_LIB_OK** — required for Intel MKL compatibility
3. **Do not forget NANOBRAGG_DISABLE_COMPILE** — per RUNTIME-001 finding
4. **Do not create new probe scripts** — PROBE-FREEZE-001 applies
5. **Do not modify production code** — Phase B is validation only
6. **Capture all logs** — pytest output + collect-only to reports directory

## Forbidden This Loop
- No new plan-local scripts (per PROBE-FREEZE-001)
- No production code changes (validation-only loop)
- No new probes (DecisionStatus=patch_ready)

## If Blocked
If test FAILS with CLI error:
- Check `blocker_log.txt` in artifact directory
- Record error signature in summary.md
- Mark RUNTIME-VEC-001 as `blocked_environment_issue` if nanobrag_torch CLI unavailable
- Do NOT extend probe scripts; record minimal error and escalate

---

## Exit Criteria Validation (for Phase B/C)

| Criterion | Expected | Validation |
|-----------|----------|------------|
| Test runs | 1 collected, PASSED | pytest exit code 0 |
| Correlation | ≥0.999 | mapping_metrics.json |
| Sum ratio delta | ≤5e-3 | mapping_metrics.json |
| Docs updated | TESTING_GUIDE.md + TEST_SUITE_INDEX.md | File edits |
| Attempts History | fix_plan.md Loop i=165 entry | File edit |
