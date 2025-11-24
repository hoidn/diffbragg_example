# TORCH-REFINE-004 Phase 8: Default Enforcement & Per-Reflection E2E Validation

## Summary
Fix test fixture to enable per-reflection path validation, change default to per_reflection mode per spec:59, and validate end-to-end convergence.

## Mode
TDD (test fixture fix) + Parity (per-reflection vs shell convergence)

## Focus
TORCH-REFINE-004 — Stage B Per-Reflection Mode Migration (Phase 8: Default Enforcement & E2E Validation)

## Branch
integration

## Mapped tests
- `tests/dbex/test_stage_b_asu_mapping.py` — Phase 6 unit regression (5 tests)
- `tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke` — Per-reflection E2E smoke (MUST run per-reflection path, not fallback)
- `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` — Shell mode explicit regression

## Artifacts
`plans/active/TORCH-REFINE-004/reports/2025-11-24T095000Z/`

---

## Do Now

**Objective:** Fix test fixture to validate per-reflection path, enforce default per spec:59, validate convergence.

**Tasks:**

1. **Fix test fixture** (`tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke`):
   - Import: `from cctbx import sgtbx, crystal as cctbx_crystal`
   - Create mock crystal_symmetry (P1, unit_cell=(79,79,38,90,90,90))
   - Inject into hkl_metadata before Stage B
   - Add assertions: stage_b_mode=="per_reflection", n_asu_unique>0

2. **Change default** (`dbex/nanobrag_refinement.py::RefinementConfig`):
   - `stage_b_mode: str = "per_reflection"` (was "shell")

3. **Validate** (5-step protocol):
   - Compilation check
   - Phase 6 unit regression (5 tests)
   - Per-reflection smoke (MUST use per-reflection path)
   - Shell explicit test
   - Decision synthesis

4. **Artifacts**: decision.json, summary.md, logs

---

## How-To Map

### Fixture Fix Pattern
```python
# In test_stage_b_per_reflection_smoke, after HKL grid built:
from cctbx import crystal as cctbx_crystal
unit_cell = (79, 79, 38, 90, 90, 90)
crystal_symmetry = cctbx_crystal.symmetry(
    unit_cell=unit_cell,
    space_group_symbol="P1"
)
hkl_metadata["crystal_symmetry"] = crystal_symmetry

# After Stage B, assert:
assert telemetry["B"]["stage_b_mode"] == "per_reflection"
assert telemetry["B"]["n_asu_unique"] > 0
```

### Validation Commands
```bash
# Phase 6 regression
NANOBRAGG_DISABLE_COMPILE=1 pytest tests/dbex/test_stage_b_asu_mapping.py -v

# Per-reflection smoke
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke

# Shell explicit
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers
```

---

## Pitfalls To Avoid

1. Mock symmetry must match fixture unit cell (79,79,38,90,90,90)
2. Lazy imports for cctbx (import inside test function)
3. Test assertions must validate per-reflection path (not fallback)
4. Default change impacts all Stage B paths (shell tests need explicit config)
5. Environment Freeze (use existing cctbx only)
6. Convergence validation uses chi² improvement (vs Stage A), not absolute
7. Per-reflection telemetry fields dynamically attached
8. Protected Assets: DB-AT-024, Stage A/C smokes (no Stage B enabled)

---

## If Blocked

**crystal_symmetry injection fails:** Try extracting from dxtbx_crystal, document, escalate

**Per-reflection convergence fails:** Capture metrics, compare vs shell, check ASU map, return to Galph

**Shell regression fails:** Verify mode branching, check telemetry, bisect, return to Galph

---

## Findings Applied

- REFINE-001/002/005, SCALE-001/002, PHYSICS-LOSS-001, POLICY-001, ARCH-ENGINE-002
- spec:59 (per-reflection SHALL be default — PRIMARY OBJECTIVE)
- spec:60 (shell fallback permitted)
- spec:107 (optimizer flexibility LBFGS/Adam)

---

## Pointers

- `docs/spec-db-workflow.md:59` — Per-reflection SHALL be default
- `plans/active/TORCH-REFINE-004/reports/2025-11-24T095000Z/phase_8_assessment.md` — Planning analysis
- Commit 936d6e0 — Phase 7 implementation
- `docs/fix_plan.md:227-243` — Exit Criteria 1-4
