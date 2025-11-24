# Ralph Input — TORCH-API-ALIGN-001 Phase A Test Stub Authoring

## Summary
Author 4 xfail-guarded test stubs (A1-A4) encoding DIALS mapping, simulator factory, ExperimentModel parity, and CUSTOM override acceptance criteria for TDD (Tests First) approach.

## Mode
TDD

## Focus
TORCH-API-ALIGN-001 — Adopt ExperimentModel, Unify Simulator Wiring, DIALS Mapping (Phase A: Tests First)

## Branch
integration

## Mapped Tests
- `tests/dbex/test_bridge_mapping.py::test_dials_mapping_parity` (A1, xfail)
- `tests/dbex/test_sim_factory.py::test_panel_and_stitched_shapes` (A2, xfail)
- `tests/dbex/test_experiment_parity.py::test_parity_small_fixture` (A3, xfail)
- `tests/dbex/test_bridge_custom_override.py::test_custom_override_exploratory` (A4, xfail, optional)

## Artifacts
`plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T200000Z/`
- `pytest_collect_phase_a.log` (collect-only validation, ≥4 tests expected)
- `test_stubs_summary.md` (test specs, fixtures, xfail rationale)
- `summary.md` (Turn Summary)

## Do Now

**Context:** TORCH-API-ALIGN-001 Phase A uses TDD: write minimal failing tests encoding acceptance criteria BEFORE Phase B wiring. All tests xfail-marked to prevent CI failures. Tests validate contracts per implementation.md:41-58 (DIALS mapping, factory shape/dtype, ExperimentModel parity, CUSTOM override).

**This loop's task:** Author 4 test stub files with xfail markers, minimal assertions, warm_cache_off fixture. Validate with `pytest --collect-only`. Update test registry. DO NOT implement wiring code.

### Step 1: Create Test Stubs

Ralph should create 4 test files under `tests/dbex/` following the patterns below. Each test:
- Has `@pytest.mark.xfail(reason="TORCH-API-ALIGN-001 Phase B wiring not yet implemented")`
- Uses `warm_cache_off` fixture to force `enable_stage_a_warm_cache=False` + `NANOBRAGG_DISABLE_COMPILE=1`
- Contains minimal docstring with acceptance criteria from implementation.md
- Has `pytest.skip()` call with message "Phase B/C wiring pending"

**Test File Structure:**

1. **`tests/dbex/test_bridge_mapping.py`** (A1):
   - Test `test_dials_mapping_parity()`
   - Acceptance: beam-center swap (fast,slow)→(s,f), Euler from panel axes, custom_beam_vector ignored under DIALS
   - Fixture: tiny dxtbx beam/panel

2. **`tests/dbex/test_sim_factory.py`** (A2):
   - Test `test_panel_and_stitched_shapes(warm_cache_off)`
   - Test `test_factory_cuda(warm_cache_off)` with `@pytest.mark.skipif(not torch.cuda.is_available())`
   - Acceptance: factory validates shape/dtype/device, one-panel + multi-panel stitched, spot_scale_override, mask normalized

3. **`tests/dbex/test_experiment_parity.py`** (A3):
   - Test `test_parity_small_fixture(warm_cache_off)`
   - Acceptance: ExperimentModel(param_init="frozen") outputs match legacy within 1e-6, ROI cropping parity

4. **`tests/dbex/test_bridge_custom_override.py`** (A4, optional):
   - Test `test_custom_override_exploratory()`
   - Acceptance: CUSTOM DetectorConfig with custom_beam_vector, measure parity deltas vs DIALS

**warm_cache_off fixture** (add to each test file):
```python
@pytest.fixture
def warm_cache_off():
    """Force warm-cache OFF + NANOBRAGG_DISABLE_COMPILE=1 for determinism."""
    import os
    old_val = os.environ.get("NANOBRAGG_DISABLE_COMPILE")
    os.environ["NANOBRAGG_DISABLE_COMPILE"] = "1"
    yield {"enable_stage_a_warm_cache": False}
    if old_val is not None:
        os.environ["NANOBRAGG_DISABLE_COMPILE"] = old_val
    else:
        del os.environ["NANOBRAGG_DISABLE_COMPILE"]
```

### Step 2: Validate Collection

After authoring, run `pytest --collect-only` to verify ≥4 tests discoverable:

```bash
pytest --collect-only tests/dbex/test_bridge_mapping.py tests/dbex/test_sim_factory.py tests/dbex/test_experiment_parity.py tests/dbex/test_bridge_custom_override.py 2>&1 | tee plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T200000Z/pytest_collect_phase_a.log
```

**Gate:** ≥4 tests collected (A1-A4).

### Step 3: Update Test Registry

Add 4 rows to `docs/TESTING_GUIDE.md` §2 table:

| ID | Name | Status | Selector | Count | Acceptance | Env | Artifacts | Findings |
|----|------|--------|----------|-------|------------|-----|-----------|----------|
| DB-API-A1 | DIALS Mapping Parity | Active (xfail) | pytest -v tests/dbex/test_bridge_mapping.py::test_dials_mapping_parity | 1 | beam_center swap + Euler angles + custom_beam_vector ignored | NANOBRAGG_DISABLE_COMPILE=1 | plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T200000Z/ | GEOMETRY-001, CONFIG-001 |
| DB-API-A2 | Unified Factory | Active (xfail) | pytest -v tests/dbex/test_sim_factory.py::test_panel_and_stitched_shapes | 2 | factory shape/dtype validation | NANOBRAGG_DISABLE_COMPILE=1 | plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T200000Z/ | SCALE-004 |
| DB-API-A3 | ExperimentModel Parity | Active (xfail) | pytest -v tests/dbex/test_experiment_parity.py::test_parity_small_fixture | 1 | param_init="frozen" parity <1e-6 | NANOBRAGG_DISABLE_COMPILE=1 | plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T200000Z/ | ARCH-ENGINE-002 |
| DB-API-A4 | CUSTOM Override | Active (xfail) | pytest -v tests/dbex/test_bridge_custom_override.py::test_custom_override_exploratory | 1 | exploratory parity deltas | NANOBRAGG_DISABLE_COMPILE=1 | plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T200000Z/ | CONFIG-001 |

Update `docs/development/TEST_SUITE_INDEX.md` with same 4 rows.

### Step 4: Write Summary

**File:** `plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T200000Z/summary.md`

Include Turn Summary (3-5 sentences): what shipped (4 test stubs xfail-guarded), main accomplishment (Phase A TDD stubs complete), next step (Phase B wiring to satisfy test contracts).

### Step 5: Commit and Push

```bash
git add tests/dbex/test_bridge_mapping.py tests/dbex/test_sim_factory.py tests/dbex/test_experiment_parity.py tests/dbex/test_bridge_custom_override.py docs/TESTING_GUIDE.md docs/development/TEST_SUITE_INDEX.md plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T200000Z/

git commit -m "TORCH-API-ALIGN-001 Phase A: Test stubs authored (A1-A4 xfail-guarded) — tests: xfail (Phase B pending)

4 test stubs: DIALS mapping, unified factory, ExperimentModel parity, CUSTOM override.
All xfail-marked until Phase B wiring lands. Registry updated with DB-API-A1/A2/A3/A4."

git push
```

## How-To Map

### Test Pattern
Each test file contains:
- Imports (pytest, relevant libraries)
- warm_cache_off fixture
- xfail-marked test function(s)
- Docstring with acceptance criteria
- pytest.skip() with "Phase B/C wiring pending" message

### Acceptance Criteria Sources
- A1: implementation.md:42-44 (DIALS mapping, beam-center swap, Euler angles)
- A2: implementation.md:46-49 (factory shape/dtype, spot_scale_override, calibration)
- A3: implementation.md:50-54 (ExperimentModel parity, ROI cropping)
- A4: implementation.md:55-57 (CUSTOM override, parity deltas)

### Registry Update
- Insert rows in TESTING_GUIDE.md §2 table after existing DB-AT-* entries
- Preserve table column structure (ID, Name, Status, Selector, Count, Acceptance, Env, Artifacts, Findings)
- Mark Status as "Active (xfail)" to indicate tests exist but expected to fail until Phase B

### Exact Commands
```bash
# Step 2
pytest --collect-only tests/dbex/test_bridge_mapping.py tests/dbex/test_sim_factory.py tests/dbex/test_experiment_parity.py tests/dbex/test_bridge_custom_override.py 2>&1 | tee plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T200000Z/pytest_collect_phase_a.log

# Step 5
git add tests/dbex/ docs/TESTING_GUIDE.md docs/development/TEST_SUITE_INDEX.md plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T200000Z/
git commit -m "TORCH-API-ALIGN-001 Phase A: Test stubs authored (A1-A4 xfail-guarded) — tests: xfail (Phase B pending)"
git push
```

## Pitfalls To Avoid

1. **DO NOT implement wiring code** — Phase A is test stubs only (TDD pattern)
2. **xfail markers MANDATORY** — All 4 tests must have `@pytest.mark.xfail(reason="...")`
3. **Warm-cache OFF** — All tests use warm_cache_off fixture
4. **Minimal assertions** — Tests encode criteria, not full validation logic (expand in Phase B)
5. **Tiny fixtures** — Use 100x100 px or smaller (no full detectors)
6. **Device/dtype neutral** — Tests work on CPU (CUDA skipif not available)
7. **Protected Assets** — DO NOT touch production code (dbex/nanobrag_refinement.py, etc.)
8. **Environment Freeze** — No package installs

## If Blocked

**Collection fails:** Fix imports/syntax, log error in `blocker_collection.md`, commit partial progress, return to Galph

**Fixture unclear:** Read PERF-WARM-001 artifacts, log in `blocker_fixtures.md`, commit tests without fixture, return to Galph

**Acceptance criteria ambiguous:** Re-read implementation.md:41-58, log questions in `blocker_acceptance_criteria.md`, commit with TODO comments, return to Galph

**Registry conflicts:** Preserve existing entries, log in `blocker_registry.md`, commit tests only (skip registry), return to Galph

## Findings Applied

- **GEOMETRY-001/002:** DIALS beam-center + Euler inversion (A1)
- **CONFIG-001/002:** Beam-center swap, DetectorConvention enum (A1)
- **SCALE-004:** Calibration metadata (A2)
- **PERF-WARM-001:** Warm-cache OFF pattern (A2, A3)
- **ARCH-ENGINE-002:** Telemetry packaging (A3)
- **POLICY-001:** Environment Freeze (all tests)

## Pointers

- **Implementation plan:** `plans/active/TORCH-API-ALIGN-001/implementation.md:41-58` (Phase A checklist)
- **Spec references:** `docs/nanobrag_api.md:44-47` (DIALS), `docs/spec-db-workflow.md §5` (per-panel)
- **Config hydration:** `docs/config_crosswalk.md:29` (beam-center swap)
- **Test registry:** `docs/TESTING_GUIDE.md §2` (existing DB-AT-* rows for format)

## Next Up

After Phase A complete (tests authored + collection validated + registry updated):
1. **Galph reviews:** Verify test contracts align, fixtures sufficient
2. **Phase B planning:** Galph authors Phase B Do Now (B1: factory, B2: wiring replacement, B3: ExperimentModel adapter)
3. **xfail removal:** After Phase B wiring lands and tests PASS, remove xfail markers
