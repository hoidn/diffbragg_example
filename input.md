# Input for Ralph — ARCH-REFINE-FLOW-001 Phase B3 Full Smoke Validation

**Summary:** Run full smoke validation suite (small + full detector, DB-AT selectors) to verify engine delegation path maintains parity.

**Mode:** TDD (validate engine delegation produces identical outputs to baseline)

**Focus:** ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase B3 full smoke validation)

**Branch:** integration

**Mapped tests:**
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (small + full detector)
- `tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck` (DB-AT-010)
- `tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke` (DB-AT-024)

**Artifacts:** `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T052000Z/`

---

## Do Now

### Objective
Phase B2 completed engine delegation for Stage-A-only mode (commit 2872f26). Now validate the engine path maintains numeric parity with baseline by running full smoke suite (both detector sizes) and DB-AT selectors that exercise Stage A (Gradcheck DB-AT-010, Mapping DB-AT-024).

### Tasks

1. **Review Phase B2 completion:**
   - Read `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T050432Z/phase_b2_implementation_summary.md`
   - Note that Phase B2 only tested small detector (`test_stage_a_expansion` with small assets)
   - Verify baseline telemetry exists from Phase B0: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T030000Z/baseline/telemetry_small.json` and `telemetry_full.json`

2. **Run Stage A expansion smoke (small detector, engine path):**
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
       --smoke-detector-size=small \
       | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T052000Z/pytest_stage_a_small.log
   ```
   Expected: PASSED (engine delegation active for Stage-A-only mode, default config has `enable_stage_c=False` and `enable_stage_b=False`)

3. **Run Stage A expansion smoke (full detector, engine path):**
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
       --smoke-detector-size=full \
       | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T052000Z/pytest_stage_a_full.log
   ```
   Expected: PASSED

4. **Run DB-AT-010 Gradcheck (collect-only):**
   ```bash
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest --collect-only tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck \
       | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T052000Z/collect_db_at_010.log
   ```
   Expected: 5 tests collected

5. **Run DB-AT-010 Gradcheck:**
   ```bash
   KMP_DUPLICATE_LIB_OK=TRUE \
   DBAT010_ARTIFACT_DIR=plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T052000Z \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck \
       | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T052000Z/pytest_db_at_010.log
   ```
   Expected: 5 passed (gradient safety unaffected by engine refactor — uses `simulate_forward_torch`, not refinement)

6. **Run DB-AT-024 Mapping (collect-only):**
   ```bash
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest --collect-only tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke \
       | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T052000Z/collect_db_at_024.log
   ```
   Expected: 1 test collected

7. **Run DB-AT-024 Mapping:**
   ```bash
   KMP_DUPLICATE_LIB_OK=TRUE \
   DBAT024_ARTIFACT_DIR=plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T052000Z \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke \
       --smoke-detector-size=full \
       | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T052000Z/pytest_db_at_024.log
   ```
   Expected: PASSED (corr_median ≥ 0.2, localization_success_rate ≥ 0.90 per SCALE-007)

8. **Extract metrics via T0 micro probe:**
   Create a lightweight inline probe to extract key metrics from logs:
   ```bash
   python3 -c "
   import json
   import re

   # Extract Stage A small detector metrics
   small_log = open('plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T052000Z/pytest_stage_a_small.log').read()
   full_log = open('plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T052000Z/pytest_stage_a_full.log').read()

   metrics = {
       'stage_a_small': 'PASSED' if 'test_stage_a_expansion PASSED' in small_log else 'FAILED',
       'stage_a_full': 'PASSED' if 'test_stage_a_expansion PASSED' in full_log else 'FAILED',
       'db_at_010': 'PASSED' if '5 passed' in open('plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T052000Z/pytest_db_at_010.log').read() else 'FAILED',
       'db_at_024': 'PASSED' if 'test_db_at_024_mapping_smoke PASSED' in open('plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T052000Z/pytest_db_at_024.log').read() else 'FAILED',
   }

   with open('plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T052000Z/phase_b3_validation_metrics.json', 'w') as f:
       json.dump(metrics, f, indent=2)

   print(json.dumps(metrics, indent=2))
   "
   ```

9. **Update implementation.md checklist:**
   - Mark Phase B checklist item B3 as COMPLETE with timestamp 2025-11-23T052000Z
   - Leave B4 (additional DB-AT selectors) and B5 (docs updates) for next loop if all tests PASSED

10. **Write summary.md with Turn Summary block:**
    Create `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T052000Z/summary.md` with:
    - **Turn Summary** section (concise 3-5 sentence format per Galph guidelines)
    - Phase B3 validation results (all 4 test outcomes)
    - Decision path per template below

11. **Decision synthesis per 4-path template:**
    - **Path A (all 4 tests PASS):** Phase B3 COMPLETE. Engine delegation maintains numeric parity with inline path. Mark implementation.md B3 COMPLETE. Ready for Phase B4/B5 (additional DB-AT selectors + docs updates) next loop.
    - **Path B (Stage A smokes PASS but DB-AT FAIL):** Engine delegation numeric parity achieved for refinement path, but test environment/fixture issue with DB-AT selectors. Document blocker, mark B3 blocked, escalate to Galph.
    - **Path C (Stage A smokes FAIL):** Engine delegation broke refinement path. Document failure signature, mark B3 blocked, escalate to Galph for debug.
    - **Path D (collection FAIL):** Test registry drift. Document missing tests, mark B3 blocked, escalate to Galph.

12. **Commit and push:**
    ```bash
    git add -A
    git commit -m "$(cat <<'EOF'
ARCH-REFINE-FLOW-001 Phase B3: Full smoke validation — tests: [status from metrics.json]

Validated engine delegation path maintains numeric parity:
- Stage A expansion (small + full detector): [PASS/FAIL]
- DB-AT-010 Gradcheck: [PASS/FAIL]
- DB-AT-024 Mapping: [PASS/FAIL]

Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T052000Z/

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
    git push
    ```

---

## How-To Map

**Environment variables (all tests):**
- `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md` (Stage A smokes)
- `KMP_DUPLICATE_LIB_OK=TRUE` (all tests)
- `NANOBRAGG_DISABLE_COMPILE=1` (all tests, per RUNTIME-001)
- `DBAT010_ARTIFACT_DIR=plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T052000Z` (DB-AT-010)
- `DBAT024_ARTIFACT_DIR=plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T052000Z` (DB-AT-024)

**Smoke detector sizes:**
- Small: `--smoke-detector-size=small` (29 ROIs, faster iteration)
- Full: `--smoke-detector-size=full` (92 ROIs, canonical parity thresholds)

**Artifacts directory:**
- All pytest logs, collect logs, and metrics JSON under `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T052000Z/`

**Inline probe:**
- T0 micro probe (≤ 120 chars, stdlib-only): `python3 -c "import json; ..."` (see Task 8)
- Paste exact command and output in `summary.md` under "Micro probes" section

---

## Pitfalls To Avoid

1. **Engine delegation path active only for Stage-A-only mode:** Default config has `enable_stage_c=False` and `enable_stage_b=False`, so `test_stage_a_expansion` uses engine path. Do not change config flags.

2. **DB-AT selectors use different helpers:** DB-AT-010 uses `simulate_forward_torch` (not refinement loop), DB-AT-024 uses `simulate_forward_once` (zero-iteration mapping). These are unaffected by engine refactor but validate that bridge helpers remain intact.

3. **Full detector is expensive:** DB-AT-024 with full detector takes ~60s. Use `--smoke-detector-size=full` flag per docs/TESTING_GUIDE.md.

4. **Baseline telemetry comparison deferred to B4:** Phase B3 validates tests PASS; detailed telemetry comparison (chi², improvement %, perf counters) will happen in B4/B5 when we compare engine vs inline paths side-by-side.

5. **Do not run Stage B/C smokes:** Phase B3 scope is Stage A validation only. Stage B/C extraction comes in Phase C/D.

6. **Respect Environment Freeze:** No package installs. Use existing pytest environment.

7. **T0 micro probe format:** Keep it simple, stdlib-only, paste both command and output in summary.md. Do not create a separate script file for T0.

8. **Turn Summary format:** Must be concise (3-5 sentences), human-readable, no test selectors/focus IDs. See Galph guidelines in prompt.

9. **Commit message status:** Use exact test counts from metrics.json (e.g., "tests: 4 passed" or "tests: 3 passed 1 failed").

10. **Phase B3 scope is validation-only:** No production code changes expected. If tests fail, document blocker and escalate to Galph. Do not attempt fixes in this loop.

---

## If Blocked

If any test FAILS:
1. Capture exact failure signature (error message, stack trace, exit code)
2. Document in `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T052000Z/blocker.md`
3. Write summary.md with Turn Summary describing the blocker
4. Commit artifacts with status "tests: blocked" in message
5. Push and hand back to Galph for review

Do NOT attempt to debug or fix failures in this loop. Phase B3 is validation-only.

---

## Findings Applied (Mandatory)

- **RUNTIME-001:** `NANOBRAGG_DISABLE_COMPILE=1` required for all PyTorch tests to avoid Dynamo interference.
- **CONFORMANCE-001:** DB-AT selectors require `KMP_DUPLICATE_LIB_OK=TRUE` environment flag.
- **TESTING-003:** Selector status transitions to Active only after `pytest --collect-only` confirms >0 tests collected.
- **SCALE-007:** DB-AT-024 requires structure-factor telemetry presence check (refined MTZ usage).
- **PHYSICS-LOSS-001:** Variance-weighted loss telemetry stack validated by DB-AT-024.
- **GEOMETRY-004:** Incremental UB parameterization tested via separate DB-AT-026 selector (not in Phase B3 scope).

---

## Pointers

**Spec references:**
- `docs/spec-db-workflow.md:32-33` — Engine Contract (ordered stages, telemetry aggregation)
- `docs/spec-db-conformance.md:12-14` — Gradient correctness (DB-AT-010)
- `docs/spec-db-conformance.md:43-46` — Mapping consistency (DB-AT-024)

**Test registry:**
- `docs/TESTING_GUIDE.md:133` (DB-AT-010 entry line 133)
- `docs/TESTING_GUIDE.md:134` (DB-AT-024 entry line 134)
- `docs/development/TEST_SUITE_INDEX.md` (parallel registry)

**Phase B2 artifacts:**
- `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T050432Z/phase_b2_implementation_summary.md`
- `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T050432Z/pytest_stage_a_expansion.log` (small detector baseline)

**Baseline telemetry:**
- `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T030000Z/baseline/telemetry_small.json`
- `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T030000Z/baseline/telemetry_full.json`

**Implementation plan:**
- `plans/active/ARCH-REFINE-FLOW-001/implementation.md:124-126` (Phase B checklist B3-B5)

---

## Next Up (optional)

If Phase B3 PASSES (all 4 tests green):
- **B4:** Additional DB-AT selectors if needed (or skip if B3 coverage sufficient)
- **B5:** Documentation updates (reference StageA class in developer docs, update architecture diagrams)
- Then proceed to **Phase C:** Stage B extraction

If Phase B3 FAILS:
- Galph reviews blocker and decides: debug/patch/escalate/simplify scope
