# Phase C1b — StageB Wrapper Implementation

## Summary
Implement StageB wrapper class calling the 3 extracted Stage B helpers directly (mirroring Phase B1b StageA pattern), package telemetry with RefinementTelemetry schema + stage_type/mode fields, and validate via regression guard.

## Mode
none

## Focus
ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase C1b)

## Branch
integration

## Mapped Tests
- **Primary**: `pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` (regression guard, MUST PASS)
- **Engine Contract**: `pytest -v tests/dbex/test_refinement_engine.py::test_engine_executes_mock_stage` (validates RefinementStage protocol compliance, MUST PASS)
- **Environment**: `DBEX_SMOKE_DETECTOR_SIZE=small`, `DBEX_SMOKE_SIGMA_SOURCE=cli_override`, `KMP_DUPLICATE_LIB_OK=TRUE`, `NANOBRAGG_DISABLE_COMPILE=1`

## Artifacts
`plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T230000Z/`
- `stage_b_wrapper_implementation.md` (implementation summary)
- `compilation_check.log` (python -c "import dbex.refinement.stage_b" exit code 0)
- `pytest_stage_b_shell_modifiers.log` (regression guard MUST PASS)
- `pytest_engine_contract.log` (test_engine_executes_mock_stage validation)
- `summary.md` (Turn Summary block)

---

## Do Now

**Objective**: Implement `StageB` class (dbex/refinement/stage_b.py) that calls the 3 extracted helpers (`_build_stage_b_params`, `_build_stage_b_lbfgs_closure`, `_run_stage_b_lbfgs`) directly, packages telemetry with all RefinementTelemetry fields + stage_type="B" + mode="shell_modifiers", and validates via regression guard test_stage_b_shell_modifiers.

**Implement:**  
dbex/refinement/stage_b.py::StageB (class definition, run() method ~200 lines total mirroring StageA pattern)

**Validating pytest selector:**  
tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers (regression guard)

**Artifacts path:**  
plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T230000Z/

**Context from Phase C1a-loop3** (commit ed30183, artifacts 2025-11-22T070000Z):
- Helper1: `_build_stage_b_params` (dbex/nanobrag_refinement.py:2087-2270, ~184 lines)
- Helper2: `_build_stage_b_lbfgs_closure` (dbex/nanobrag_refinement.py:2273-2589, ~317 lines)
- Helper3: `_run_stage_b_lbfgs` (dbex/nanobrag_refinement.py:2593-2708, ~118 lines)
- All 3 helpers wired into run_nanobrag_refinement Stage B section (lines 3152-3302, ~150 lines orchestration)
- Regression guard test_stage_b_shell_modifiers PASSED

**Pattern to Follow**: StageA (dbex/refinement/stage_a.py) — Phase B1b completion (commit 6d1d925, artifacts 2025-11-23T045012Z). StageB.run() MUST follow identical structure:
1. Import helpers via lazy imports (avoid circular dependencies)
2. Extract inputs from dict
3. Call helper1 → unpack result dicts
4. Call helper2 → unpack closure tuple `(compute_loss_stage_b, closure_stage_b)`
5. Call helper3 → unpack status/metrics
6. Build param_deltas dict (shell_modifier_raw initial/final/delta)
7. Package telemetry dict with ALL RefinementTelemetry fields + stage_type="B" + mode="shell_modifiers"
8. Return telemetry dict

---

## How-To Map

### Compilation Check
```bash
python -c "import dbex.refinement.stage_b" > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T230000Z/compilation_check.log 2>&1
echo "Exit code: $?" >> plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T230000Z/compilation_check.log
```

### Regression Guard Test
```bash
DBEX_SMOKE_DETECTOR_SIZE=small \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
  > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T230000Z/pytest_stage_b_shell_modifiers.log 2>&1
echo "Exit code: $?" >> plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T230000Z/pytest_stage_b_shell_modifiers.log
```

### Engine Contract Test
```bash
pytest -v tests/dbex/test_refinement_engine.py::test_engine_executes_mock_stage \
  > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T230000Z/pytest_engine_contract.log 2>&1
echo "Exit code: $?" >> plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T230000Z/pytest_engine_contract.log
```

---

## Pitfalls To Avoid

1. **Circular imports**: Use lazy imports INSIDE StageB.run() method (NOT at module top) to avoid circular dependencies between dbex.refinement.stage_b ↔ dbex.nanobrag_refinement.
2. **Helper2 signature bug**: Helper2 returns **tuple** `(compute_loss_stage_b, closure_stage_b)` NOT scalar (fixed in Phase C1a-loop3). Unpack correctly.
3. **Telemetry nested access**: telemetry_state dict is updated in-place by closures. Extract all fields AFTER helper3 execution, not before.
4. **Frozen Stage A params**: Extract from stage_a_telemetry['param_deltas'] using 'final' key (NOT raw tensors). Convert to scalars if needed.
5. **param_deltas transform**: Apply softplus transform to shell_modifier_raw for interpretable shell_modifiers output (F.softplus(x) * 2.0).
6. **Stage type/mode fields**: MUST include stage_type="B" and mode="shell_modifiers" per Phase A4 engine protocol schema (backward compatible).
7. **Device/dtype neutrality**: Extract device/dtype from config, do NOT hardcode "cuda" or torch.float32.
8. **Panel slices**: Extract from refinement_inputs.panel_slices (NOT inputs.panel_slices), pass to helper1.
9. **Telemetry schema completeness**: Include ALL RefinementTelemetry fields even if optional (variance_floor_*, perf_*, traces) to match StageA pattern and ensure test serialization compatibility.
10. **Test environment**: Run regression guard with EXACT environment from Phase C1a-loop3 (DBEX_SMOKE_DETECTOR_SIZE=small, DBEX_SMOKE_SIGMA_SOURCE=cli_override, KMP_DUPLICATE_LIB_OK=TRUE, NANOBRAGG_DISABLE_COMPILE=1).

---

## If Blocked

1. **Compilation fails (ImportError/CircularImportError)**:
   - Verify lazy imports are INSIDE run() method (NOT module top)
   - Check helper imports match Phase C1a-loop3 names exactly (_build_stage_b_params, _build_stage_b_lbfgs_closure, _run_stage_b_lbfgs)
   - Document exact error traceback in summary.md, mark blocker, commit docs-only artifacts (no code changes)

2. **Regression guard test FAILS**:
   - Capture full pytest log with traceback
   - Document first divergence point (helper1/helper2/helper3 call or telemetry packaging)
   - Do NOT commit code changes if test fails
   - Write blocker analysis in summary.md with 3 hypotheses (signature mismatch, missing field, transform error)
   - Galph will review blocker next loop

3. **Telemetry field missing/mismatch**:
   - Compare StageB telemetry dict keys against StageA telemetry dict (dbex/refinement/stage_a.py:227-315)
   - Cross-reference RefinementTelemetry schema (dbex/nanobrag_refinement.py:96-227)
   - Add missing fields with appropriate defaults (e.g., default_f_fallback_count=0)
   - Rerun compilation check + regression guard

---

## Findings Applied

- **REFINE-008** (Stage B calibrated gate ≥0.002% improvement): Helper3 implements improvement gate check; telemetry includes chi_squared_best/masked_mse_best comparison with Stage A baseline.
- **PERF-WARM-009** (Force panel evaluation): Helper2 initial/final validation uses is_full=True flag for comprehensive metrics.
- **PERF-WARM-011/012** (CPU fallback logic): Helper1 preserves CPU context cloning when device mismatch detected; telemetry includes use_stage_b_cpu_fallback flag.
- **PHYSICS-LOSS-001/002** (Variance-weighted loss + dual metric tracking): Helper2 closure implements chi_squared + masked_mse parallel computation with sigma_floor guard; telemetry includes both metric traces.
- **POLICY-001** (Environment Freeze): NO new packages installed. Use existing torch, nanobrag_torch, dbex imports ONLY.
- **GRADIENT-001** (Autograd graph preservation): Helper2 closure maintains requires_grad=True on shell_modifier_raw; no .detach() calls inside optimization loop.

---

## Pointers

- **Spec**: docs/spec-db-workflow.md:33 (Refinement Protocol Architecture §7, Stage B definition)
- **Implementation Plan**: plans/active/ARCH-REFINE-FLOW-001/implementation.md:180-217 (Phase C checklist, exit criteria)
- **Phase C1a Completion Evidence**: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T070000Z/summary.md (helper extraction SUCCESS)
- **Helper Signatures**: dbex/nanobrag_refinement.py:2087-2708 (3 extracted helpers with full docstrings)
- **StageB Orchestration Pattern**: dbex/nanobrag_refinement.py:3152-3453 (run_nanobrag_refinement Stage B section, ~150 lines)
- **StageA Reference Implementation**: dbex/refinement/stage_a.py:1-315 (Phase B1b wrapper class, identical structure)
- **RefinementTelemetry Schema**: dbex/nanobrag_refinement.py:96-227 (dataclass with required/optional fields)
- **Phase A4 Engine Protocol**: dbex/refinement/stage.py:159-227 (stage_type/mode fields per engine contract)
- **TESTING_GUIDE**: docs/TESTING_GUIDE.md:1-150 (canonical test environment flags, selector naming)

---

## Next Up (Optional)

If StageB wrapper completes successfully AND regression guard passes AND you finish ahead of schedule:
- Preview Phase C2 planning by reading run_nanobrag_refinement Stage B section (lines 3152-3453) and identifying the exact replacement logic for engine delegation (similar to Phase B2 pattern: detect Stage-B-only mode → delegate to RefinementEngine([StageB()]) → return telemetry with backward-compatible key).
- Document preliminary Phase C2 scope estimate in summary.md (expected changes: add stage detection logic, wrap Stage B inline code in else branch, extract final Bragg generation helper if needed).
