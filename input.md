# Input for Ralph (Loop i=171)

## Summary
Execute ARCH-GRADIENT-FLOW-001 Phase B.6: Implement single-line fix to pass `crystal_overrides` to `create_crystal_config`, then validate with DB-AT-010 gradcheck test.

## BindingForRalph
- **ActionType:** implementation_ready
- **DecisionStatus:** patch_ready (confidence 0.95 from Phase B.5)
- **InitiativeType:** architecture

## SupervisorMode
Parity (gradient flow restoration)

## Focus
ARCH-GRADIENT-FLOW-001 — Gradient Flow Restoration (DB-AT-010 Unblock) — Phase B.6

## Branch
integration

## Mapped Tests
- `pytest -vv tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck_crystal_cell_a --tb=short`
- After fix: full DB-AT-010 suite (`pytest -vv tests -k DB_AT_010 --smoke-detector-size=full`)

## Artifacts
`plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T230000Z/`

## Findings Applied (Mandatory)
- **GRADIENT-001** (Gradient test patterns): Tests inject differentiable parameters via `crystal_overrides` dict; factory must accept and use them.
  - Code: `tests/dbex/test_gradients.py:379-382`, `dbex/physics/forward.py:198-226`
  - Adherence: Fix passes `crystal_overrides` to factory so MOSFLM path is skipped when overrides present
- **GRADIENT-002** (nanobrag_torch gradient fix): Upstream fix ensures Crystal cell parameter path preserves gradients when `mosflm_a_star=None`.
  - Code: `nanobrag_torch/models/crystal.py:682-716` (cell parameter path)
  - Adherence: Fix enables cell parameter path by ensuring `mosflm_a_star=None` when `crystal_overrides` provided
- **RUNTIME-001** (Runtime execution guardrails): Gradcheck requires `NANOBRAGG_DISABLE_COMPILE=1`
  - Code: `docs/TESTING_GUIDE.md:161`
  - Adherence: All test runs use canonical env flags

## Pointers
- Implementation plan: `plans/active/ARCH-GRADIENT-FLOW-001/implementation.md` (Phase B section)
- Phase B.5 audit: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T220000Z/dbex_gradient_audit.md`
- Root cause analysis: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T220000Z/summary.md`
- Fix location: `dbex/physics/forward.py:196`
- Factory that accepts overrides: `dbex/refinement/config_factories.py:278` (signature already has `crystal_overrides` param)
- Logic that skips MOSFLM: `dbex/refinement/config_factories.py:353-357` (`else` branch sets `mosflm_a_star=None`)

---

## ARCH Contracts (mandatory)
- **GRADIENT-001** (Tensor Override Pattern): `crystal_overrides` dict must flow to `create_crystal_config` to trigger MOSFLM bypass
  - Owner: `dbex/physics/forward.py::simulate_forward_torch`
  - Classification: **Implementation bug** — factory already supports overrides, caller omits them
- **ARCH-FACTORY-001** (Config Factory): `create_crystal_config` has logic to skip MOSFLM when `crystal_overrides` provided (lines 353-357)
  - Owner: `dbex/refinement/config_factories.py`
  - Enforcement: This fix activates that logic path

---

## Do Now

**Focus:** ARCH-GRADIENT-FLOW-001 Phase B.6 — Implement crystal_overrides passthrough

### Background
Phase B.5 (i=170) identified the root cause with 0.95 confidence:
- `forward.py:196` calls `create_crystal_config(crystal, experiment)` WITHOUT `crystal_overrides`
- This causes MOSFLM A* vectors to be injected from base crystal (`config_factories.py:342-347`)
- When `Crystal.compute_cell_tensors()` runs, it takes the MOSFLM path and overwrites `self.cell_a` at `crystal.py:872`
- The tensor with `requires_grad=True` is disconnected from the computational graph

The fix is a **single-line change**: pass `crystal_overrides=crystal_overrides` to the `create_crystal_config` call. This causes `config_factories.py:353-357` to set `mosflm_a_star=None`, which makes `mosflm_provided=False` in `Crystal.compute_cell_tensors()`, enabling the gradient-preserving cell parameter path.

### Phase B.6 Tasks

#### B.6.1 — Implement fix (1 line)

**File:** `dbex/physics/forward.py`
**Line:** 196

**Current:**
```python
crystal_config, _ = create_crystal_config(crystal, experiment)
```

**Change to:**
```python
crystal_config, _ = create_crystal_config(crystal, experiment, crystal_overrides=crystal_overrides)
```

This is the ONLY production code change needed.

#### B.6.2 — Validate crystal_cell_a gradcheck passes

```bash
cd /home/ollie/Documents/diffbragg_example
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1
export ARTIFACT_DIR=plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T230000Z
mkdir -p $ARTIFACT_DIR

pytest -vv tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck_crystal_cell_a --tb=short 2>&1 | tee $ARTIFACT_DIR/pytest_crystal_cell_a.log
```

**Expected:** PASS (was FAIL before fix)

#### B.6.3 — Run remaining DB-AT-010 crystal tests

```bash
pytest -vv tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck -k "crystal" --tb=short 2>&1 | tee $ARTIFACT_DIR/pytest_crystal_all.log
```

**Expected:** All crystal parameter tests PASS

#### B.6.4 — Run full DB-AT-010 suite

```bash
pytest -vv tests -k DB_AT_010 --smoke-detector-size=full --tb=short 2>&1 | tee $ARTIFACT_DIR/pytest_db_at_010_full.log
```

**Expected:** 5/5 PASS

#### B.6.5 — Author summary

Output: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T230000Z/summary.md`

Include:
1. What was implemented (single-line fix)
2. Test results (expected all PASS)
3. Exit criteria validation status
4. Next steps (Phase B.7 docs update OR Phase C closure)

---

## How-To Map

```bash
# Set environment
cd /home/ollie/Documents/diffbragg_example
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1
export ARTIFACT_DIR=plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T230000Z

# Create artifacts directory
mkdir -p $ARTIFACT_DIR

# B.6.1: Edit forward.py:196
# Use Edit tool to change:
#   crystal_config, _ = create_crystal_config(crystal, experiment)
# To:
#   crystal_config, _ = create_crystal_config(crystal, experiment, crystal_overrides=crystal_overrides)

# B.6.2: Validate crystal_cell_a
pytest -vv tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck_crystal_cell_a --tb=short 2>&1 | tee $ARTIFACT_DIR/pytest_crystal_cell_a.log

# B.6.3: Run all crystal tests
pytest -vv tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck -k "crystal" --tb=short 2>&1 | tee $ARTIFACT_DIR/pytest_crystal_all.log

# B.6.4: Run full DB-AT-010 suite
pytest -vv tests -k DB_AT_010 --smoke-detector-size=full --tb=short 2>&1 | tee $ARTIFACT_DIR/pytest_db_at_010_full.log

# B.6.5: Write summary to $ARTIFACT_DIR/summary.md
```

---

## Forbidden This Loop
- **No new probes** — DecisionStatus=patch_ready prohibits additional instrumentation
- **Do not extend plan-local diagnostic scripts** — Phase B.5 evidence is sufficient
- **Do not modify nanobrag_torch** — That layer is already fixed (Phase B i=153)
- **No additional exploratory changes** — Focus on the single-line fix only

## Pitfalls To Avoid
1. **Do not over-engineer** — This is a 1-line fix; do not refactor surrounding code
2. **Do not add defensive code** — The factory already handles `crystal_overrides=None` (MOSFLM path)
3. **Do not add comments** — The code intent is already documented in config_factories.py docstring
4. **Environment Freeze** — Do not install/upgrade packages
5. **Verify correct line** — Ensure editing line 196 specifically, not similar code elsewhere

## If Blocked
If the fix does not resolve gradcheck failures:
1. Document the new failure mode (is it still "disconnected graph"?)
2. Re-run with `-vvv --tb=long` to capture extended traceback
3. Check if other `create_crystal_config` call sites exist in the test path
4. Mark blocked and spawn spec_change or architecture follow-up

---

## Exit Criteria Validation

| Criterion | Expected | Validation |
|-----------|----------|------------|
| B.6.1 complete | forward.py:196 edited | git diff shows 1 line changed |
| B.6.2 complete | crystal_cell_a PASS | pytest exit code 0 |
| B.6.3 complete | all crystal tests PASS | pytest log shows 0 failures |
| B.6.4 complete | 5/5 DB-AT-010 PASS | pytest log shows 5 passed |
| B.6.5 complete | summary.md exists | File in artifacts dir |

---

## Output Artifacts Expected

1. `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T230000Z/pytest_crystal_cell_a.log`
2. `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T230000Z/pytest_crystal_all.log`
3. `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T230000Z/pytest_db_at_010_full.log`
4. `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T230000Z/summary.md`

---

## DMI Section
N/A — This is implementation_ready, not parity_localization.

## Doc Sync Plan
Deferred to Phase B.7 (if all tests pass) or Phase C (closure):
- Update `docs/development/TEST_SUITE_INDEX.md` DB-AT-010 row to PASSING
- Update `docs/findings.md` with GRADIENT-002 fix confirmation
- Update `docs/fix_plan.md` Attempts History

---

## Implement Target
**File:** `dbex/physics/forward.py::simulate_forward_torch`
**Line:** 196
**Change:** Add `crystal_overrides=crystal_overrides` parameter to `create_crystal_config` call

## Validating Pytest Selector
`pytest -vv tests -k DB_AT_010 --smoke-detector-size=full` (5/5 expected PASS)
