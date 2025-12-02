# ARCH-REFACTOR-001 Phase D.3 Batch 2 Planning Notes
## Loop: 2025-12-02T220618Z

### Context
- **Previous loop**: Phase D.4 import cleanup complete (commit fcc53a33, 4/4 tests PASSED)
- **Current Phase D status**:
  - D.1 RefinementConfig migration: ✓ COMPLETE
  - D.2 CLI refactor: ✓ COMPLETE
  - D.3 Batch 1 (test_torch_refine_smoke.py): ✓ COMPLETE (5/6 functions migrated, 4/5 passed, 1 has separate Stage B ASU issue)
  - D.4 Import cleanup: ✓ COMPLETE
  - D.3 Batch 2 (test_stage_a_smoke_parity.py): **← THIS LOOP**
  - D.3 Batch 3 (dbex/tools/stage_a_adam.py): pending
  - D.5 Facade deletion: pending

### Remaining Facade Usage
```bash
$ grep -r "from dbex.nanobrag_refinement import" tests/ dbex/ --include="*.py" | grep -v pyc
tests/dbex/test_torch_refine_smoke.py:    from dbex.nanobrag_refinement import run_nanobrag_refinement  # DEAD CODE (all 6 tests migrated to Engine)
tests/dbex/test_stage_a_smoke_parity.py:from dbex.nanobrag_refinement import (  # TARGET THIS LOOP
dbex/tools/stage_a_adam.py:    from dbex.nanobrag_refinement import (  # Batch 3
```

**Note**: test_torch_refine_smoke.py has a dead import (from an inline import within test_stage_b_asu_mapping_smoke line ~1700 that was missed). That function was migrated but the import wasn't removed. Will clean that up in this loop or next.

### Scope: test_stage_a_smoke_parity.py
**File**: `tests/dbex/test_stage_a_smoke_parity.py` (489 lines)

**Facade usage**: Lines 13-16
```python
from dbex.nanobrag_refinement import (
    RefinementConfig,
    run_nanobrag_refinement,
)
```

**Migration target**:
- Fixture `stage_a_smoke_result` (lines 68-269) uses `run_nanobrag_refinement` at line 148
- 2 test functions consume the fixture (no direct facade calls):
  - `test_db_at_028_loss_scale_sanity` (line 296)
  - `test_db_at_029_structure_parity` (line 376)

### Implementation Strategy

Follow D.2 CLI blueprint 5-step Engine pattern:

#### 1. Update imports (lines 13-16)
**Remove**:
```python
from dbex.nanobrag_refinement import (
    RefinementConfig,
    run_nanobrag_refinement,
)
```

**Add**:
```python
from dbex.refinement.config import RefinementConfig
from dbex.refinement.context import build_refinement_context
from dbex.refinement.engine import RefinementEngine
from dbex.refinement.stage_a import StageA
```

#### 2. Update fixture stage_a_smoke_result (lines 148-158)
**Current code** (lines 148-158):
```python
    bragg_final, telemetry_dict, _ = run_nanobrag_refinement(
        inputs=refinement_inputs,
        detector=perturbed_detector,
        beam=perturbed_beam,
        crystal=perturbed_crystal,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        config=config,
        baseline_crystal=baseline_crystal,
        baseline_detector=baseline_detector,
    )
```

**Replace with** (5-step Engine pattern):
```python
    # ARCH-REFACTOR-001 Phase D.3 Batch 2: Direct RefinementEngine usage
    refinement_context = build_refinement_context(
        refinement_inputs=refinement_inputs,
        detector=perturbed_detector,
        beam=perturbed_beam,
        crystal=perturbed_crystal,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        baseline_crystal=baseline_crystal,
        baseline_detector=baseline_detector,  # Stage C disabled (enable_stage_c=False)
    )
    stages = [StageA()]
    engine = RefinementEngine(stages, config=config)
    telemetry_dict = engine.run({"context": refinement_context})

    # Extract Bragg from Stage A artifacts
    bragg_final = engine._artifacts["stage_a"].bragg_full
```

**Rationale**:
- Config already has `enable_stage_b=False`, `enable_stage_c=False` (Stage A only)
- Stages list contains only StageA() (no conditional needed)
- Extract bragg_full from engine._artifacts["stage_a"] (no precedence logic needed)
- Preserve all downstream logic unchanged (fixture consumers expect telemetry_dict["A"], bragg_final, etc.)

### Validation Plan

**Mapped tests** (both consume the fixture):
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
pytest -vv tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity \
              tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity \
              --smoke-detector-size=small
```

**Expected outcome**: 2/2 tests PASSED

**Success criteria**:
- Zero import errors
- Fixture builds successfully
- test_db_at_028 validates loss/scale sanity (chi² reduction, parameter ranges)
- test_db_at_029 validates structure parity (ROI correlations, U-matrix norms)
- No telemetry/artifacts regression (same fields, same values)

**Rollback plan**: If tests fail with Engine-specific errors (not Stage A physics issues), revert to facade call and mark blocked pending investigation.

### Risks & Mitigations

**Risk 1**: Fixture uses mapping_context.inputs instead of standard refinement_inputs construction
- **Mitigation**: mapping_context already provides properly formatted RefinementInputs; build_refinement_context consumes it directly (no changes needed)

**Risk 2**: Fixture computes bragg_before/bragg_after via build_final_bragg_from_stage_a_telemetry
- **Mitigation**: Telemetry structure unchanged (engine returns same "A" key with same fields); downstream reconstruction logic works as-is

**Risk 3**: Calibration metadata threading (TOOLING-VIS-001 requirement)
- **Mitigation**: config.calibration_metadata already set from mapping_context.calibration (line 140); Engine preserves this path

**Risk 4**: apply_calibration_n_cells flag (TOOLING-VIS-001 Phase D.C gate)
- **Mitigation**: config.apply_calibration_n_cells already set (line 144); Engine honors config flags

### Expected Metrics
- **Files touched**: 1 (test_stage_a_smoke_parity.py)
- **Lines changed**:
  - Import block: -4 lines (remove facade imports), +4 lines (add Engine imports) = net 0
  - Fixture refactor: +7 lines (context build + Engine instantiation) -11 lines (facade call + unpacking) = net -4 lines
  - Comment added: +1 line
  - **Total**: ~-3 to -4 lines (consolidation via Engine pattern)
- **Consumers migrated**: 1 fixture (2 test functions indirect)
- **Tests validated**: 2/2

### Artifacts
- `pytest_parity_batch2.log` — Full pytest output for both tests
- `import_verification.txt` — Confirm zero facade imports in this file
- `summary.md` — Turn summary (prepend to existing file if present)

### Next Action After This Loop
- **If 2/2 tests PASSED**: Proceed to D.3 Batch 3 (dbex/tools/stage_a_adam.py migration)
- **If any tests FAILED**:
  - Debug Engine-specific issues if related to migration
  - If Stage A physics regression, mark blocked and open separate bugfix initiative
