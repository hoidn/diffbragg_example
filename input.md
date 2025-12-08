# Input for Ralph (Loop i=180)

## Summary
Fix mock fixture and complete TORCH-CLI-BRIDGE-ROLLUP-001 Phase C (TORCH-CLI-003 sync).

## BindingForRalph
- **ActionType:** debug → implementation_ready
- **DecisionStatus:** patch_ready
- **InitiativeType:** test fixture fix + roll-up member closeout

## SupervisorMode
Debug (test fixture repair)

## Focus
TORCH-CLI-BRIDGE-ROLLUP-001 — CLI & Bridge Infrastructure Roll-up — Phase C (TORCH-CLI-003 Sync)

## Branch
integration

## Mapped Tests
- `tests/dbex/test_refine_one_cli.py` (15 tests)
- **Target:** 15/15 PASS after fix

## Artifacts
`plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/reports/2025-12-08T090000Z/`

## Findings Applied (Mandatory)
- **MOCK-FIXTURE-001** (Mock auto-creation gaps): When production code evolves to access nested attributes on fixture objects, Mock returns Mock instead of defaults. Fix: explicitly mock method chains with real return types.
  - Adherence: Apply torch.Tensor mock instead of np.ndarray per failing test pattern
- **PROBE-FREEZE-001**: No new persistent scripts
  - Adherence: Using existing tests only, fixing mock
- No other findings directly applicable

## Pointers
- Roll-up implementation.md: `plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/implementation.md` (Phase C checklist lines 104-124)
- TORCH-CLI-003 implementation.md: `plans/active/TORCH-CLI-003/implementation.md`
- CLI test file: `tests/dbex/test_refine_one_cli.py` (lines 793-796 — the bug)
- galph_memory.md: MOCK-FIXTURE-001 debugging insight (lines 73-87)

---

## ARCH Contracts (mandatory)
- **Environment Freeze**: No package installs
  - Owner: CLAUDE.md
  - Classification: Test fixture repair only
- **Test Registry Sync**: Check if needed after test execution
  - Owner: TESTING-003
  - Classification: Likely no changes needed (entries exist)

---

## Do Now

**Focus:** TORCH-CLI-BRIDGE-ROLLUP-001 Phase C — TORCH-CLI-003 Synchronization

**Implement:** `tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_uses_refined_mtz` mock fix

**Validating Pytest Selector:** `tests/dbex/test_refine_one_cli.py`

### Background
Phase B (TORCH-BRIDGE-001 closeout) completed successfully (27 passed, 1 skip). Phase C targets TORCH-CLI-003 synchronization but 3 of 15 CLI tests now fail with:

```
AttributeError: 'numpy.ndarray' object has no attribute 'device'
```

at `dbex/refinement/helpers.py:174`. Root cause: `test_nanobrag_backend_uses_refined_mtz` mocks `build_structure_factor_grid` return with NumPy arrays, but production code expects torch.Tensor.

### Failure Analysis
**Affected tests (all same root cause):**
1. `test_nanobrag_backend_accepts_sigma_map`
2. `test_nanobrag_backend_accepts_external_lookup_sigma_map`
3. `test_nanobrag_backend_uses_refined_mtz`

**Bug location:** `tests/dbex/test_refine_one_cli.py:793-796`
```python
# CURRENT (buggy):
hkl_grid_mock = np.zeros((10, 10, 10), dtype=np.float32)
hkl_metadata_mock = {"grid_nonzero": 3}
mock_asu_map = np.zeros((10, 10, 10), dtype=np.int32)
mock_build_grid.return_value = (hkl_grid_mock, hkl_metadata_mock, mock_asu_map)
```

**Working pattern (from other tests, e.g., line 617-621):**
```python
# CORRECT:
mock_build_grid.return_value = (
    torch.zeros((3, 3, 3), dtype=torch.float32),
    {"grid_nonzero": 1},
    torch.zeros((3, 3, 3), dtype=torch.int32),
)
```

### Phase C Tasks

#### C1 — Fix Mock Fixture
Update `tests/dbex/test_refine_one_cli.py:793-796` to use torch tensors:

```python
# Replace np.zeros with torch.zeros
hkl_grid_mock = torch.zeros((10, 10, 10), dtype=torch.float32)
hkl_metadata_mock = {"grid_nonzero": 3}
mock_asu_map = torch.zeros((10, 10, 10), dtype=torch.int32)
mock_build_grid.return_value = (hkl_grid_mock, hkl_metadata_mock, mock_asu_map)
```

**IMPORTANT:** Also check if `torch` import exists in test function — if not, add it.

#### C2 — Run CLI Tests
Execute all 15 CLI tests:

```bash
cd /home/ollie/Documents/diffbragg_example
export ART=plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/reports/2025-12-08T090000Z
mkdir -p "$ART"
KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_refine_one_cli.py 2>&1 | tee "$ART/pytest_cli.log"
```

**Expected:** 15/15 PASS

#### C3 — Update TORCH-CLI-003 Implementation.md
1. Mark Phase A (A0-A2) checklist items as checked
2. Mark Phase B (B1-B2) checklist items as checked
3. Add **Completed:** timestamp
4. Update Status: `in_progress` → `done`

#### C4 — Update Roll-up Implementation.md
1. Update member plan table: TORCH-CLI-003 → "Phases A-C complete" / "Complete"
2. Mark Phase C checklist items (C1-C4) as checked
3. Add Phase C artifacts reference

#### C5 — Capture Collect-Only Logs
```bash
KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only tests/dbex/test_refine_one_cli.py 2>&1 | tee "$ART/collect_cli.log"
```

#### C6 — Author Summary
Create `$ART/summary.md` with:
- Mock fixture fix description
- Test execution results (15/X PASS)
- Ledger updates made
- Phase C completion status

---

## How-To Map

```bash
# Environment setup
cd /home/ollie/Documents/diffbragg_example
export ART=plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/reports/2025-12-08T090000Z
mkdir -p "$ART"

# C2: Run tests after fix
KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_refine_one_cli.py 2>&1 | tee "$ART/pytest_cli.log"

# C5: Collect-only
KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only tests/dbex/test_refine_one_cli.py 2>&1 | tee "$ART/collect_cli.log"

# C3-C4, C6: Use Edit/Write tools for ledger updates and summary
```

---

## Forbidden This Loop
- **No production code changes** — Test fixture repair only
- **No package installs** — Environment Freeze
- **No new persistent scripts** — PROBE-FREEZE-001

## Pitfalls To Avoid
1. **Verify torch import exists** — The test function must import torch if not already imported
2. **Keep dtype consistent** — Use `torch.float32` and `torch.int32` to match working tests
3. **Use correct artifacts path** — `2025-12-08T090000Z` not Phase B's `2025-12-08T083000Z`
4. **Check both implementation.md files** — TORCH-CLI-003 AND roll-up

## If Blocked
If tests still fail after fix:
1. Document failure in `$ART/error.md` with test name, error message, and stack trace
2. Do NOT mark Phase C complete
3. Note regression requires separate debugging loop
4. Update summary with "BLOCKED" status

---

## Exit Criteria Validation (Phase C)

| Criterion | Expected | Validation |
|-----------|----------|------------|
| Mock fixed | np→torch | Edit diff |
| Tests pass | 15/15 PASS | pytest_cli.log |
| TORCH-CLI-003 done | Status updated | implementation.md diff |
| Roll-up Phase C done | Checklist updated | roll-up implementation.md diff |
| Collect-only captured | Log saved | collect_cli.log exists |
| Summary authored | Phase C closure | summary.md |

---

## Output Artifacts Expected

1. `plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/reports/2025-12-08T090000Z/pytest_cli.log`
2. `plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/reports/2025-12-08T090000Z/collect_cli.log`
3. `plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/reports/2025-12-08T090000Z/summary.md`
4. Updated `plans/active/TORCH-CLI-003/implementation.md` (all phases marked complete)
5. Updated `plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/implementation.md` (Phase C marked complete)
6. Fixed `tests/dbex/test_refine_one_cli.py` (line ~793-796)

---

## Implement Target
`tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_uses_refined_mtz` mock fixture fix

## Validating Pytest Selectors
`tests/dbex/test_refine_one_cli.py`

---

## Next Up (optional)
If Phase C completes successfully:
- Proceed to Phase D: TORCH-CLI-004 Synchronization (verify 2/2 diagnostics tests pass, update checklist)
- Can potentially combine with Phase E (Roll-up Closure) for efficiency
