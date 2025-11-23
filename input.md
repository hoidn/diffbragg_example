# Phase B3: Stage A Closure Wiring for Incremental UB Parameterization

## Summary
Integrate the validated incremental UB parameterization helpers (B1/B2) into the Stage A LBFGS closure to enable geometry refinement using quaternion-based ΔR and log-exp cell perturbations around the dxtbx baseline crystal state.

## Mode
none

## Focus
TORCH-GEOMETRY-UB-REALIGN-001 — Stage A UB Parameterization Realignment (Phase B3: Closure Wiring)

## Branch
integration

## Mapped Tests
- **Validation test:** `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -xvs tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`
  - Run with `use_incremental_ub=True` (new path) — expect convergence, chi² improvement ≥0.2%
  - Run with `use_incremental_ub=False` (default path, regression guard) — expect PASS as before
- **Round-trip tests (already passing):** `pytest -xvs tests/dbex/test_ub_parameterization_roundtrip.py -k "test_db_at_026_orientation_zero_point or test_db_at_026_cell_zero_point or test_db_at_026_mapping_parity"`

## Artifacts
`plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-23T015000Z/`
- `phase_b3_closure_implementation.md` (implementation notes)
- `pytest_stage_a_incremental_ub_true.log` (validation with new path)
- `pytest_stage_a_incremental_ub_false.log` (regression guard with default path)
- `summary.md` (Turn Summary)

---

## Do Now

### Context
Phase B tasks B1/B2/B4/B5 are complete and validated:
- **B1:** `derive_orientation_from_quaternion_delta(q_delta, U_baseline)` implemented in `dbex/nanobrag_bridge.py:1158-1221` (~64 lines)
- **B2:** `derive_B_from_cell_deltas(δlog_a, δlog_b, δlog_c, Δα, Δβ, Δγ, cell_baseline)` and `busing_levy_B_torch(a, b, c, α, β, γ)` implemented in `dbex/nanobrag_bridge.py:1224-1388` (~145 lines)
- **B4:** DB-AT-026 Tests 1-3 PASS with bonus precision (||A*(0)-A*_mapping|| = 3.469e-18 < 1e-12)
- **B5:** Regression guard `test_stage_a_expansion` PASS with cell+misset default path

**B3 (this loop):** Wire incremental UB parameterization into Stage A LBFGS closure in `dbex/nanobrag_refinement.py`.

### Implementation Tasks

#### Task 1: Add `use_incremental_ub` Configuration Flag
**File:** `dbex/nanobrag_refinement.py`
**Location:** `build_stage_a_lbfgs_closure` function (currently around line 722-1008)

1. Add `use_incremental_ub: bool = False` parameter to `build_stage_a_lbfgs_closure` function signature
2. Add `use_incremental_ub: bool = False` field to `RefinementConfig` dataclass (if not already present)
3. Thread the flag through from `run_nanobrag_refinement` → `build_stage_a_lbfgs_closure`

#### Task 2: Initialize Trainable Parameters (Incremental UB Path)
**File:** `dbex/nanobrag_refinement.py`
**Location:** Inside `build_stage_a_lbfgs_closure`, before the closure definition

When `use_incremental_ub=True`:
1. Extract baseline crystal state from `crystal`:
   ```python
   U_baseline = torch.tensor(
       np.array(crystal.get_U()).reshape(3, 3),
       dtype=torch.float64,
       device=device
   )
   unit_cell = crystal.get_unit_cell()
   cell_baseline = torch.tensor(
       [unit_cell.parameters()[i] for i in range(6)],  # [a, b, c, α, β, γ]
       dtype=torch.float64,
       device=device
   )
   ```

2. Initialize trainable parameters (10 DOF total):
   ```python
   # Orientation: quaternion delta (4 params)
   # Initialize to identity quaternion [w=1, x=0, y=0, z=0]
   q_delta = torch.tensor([1.0, 0.0, 0.0, 0.0], dtype=torch.float64, device=device, requires_grad=True)

   # Cell: log-perturbations for lengths (3 params) + angle deltas (3 params)
   # Initialize to zero perturbations
   delta_log_a = torch.tensor(0.0, dtype=torch.float64, device=device, requires_grad=True)
   delta_log_b = torch.tensor(0.0, dtype=torch.float64, device=device, requires_grad=True)
   delta_log_c = torch.tensor(0.0, dtype=torch.float64, device=device, requires_grad=True)
   delta_alpha = torch.tensor(0.0, dtype=torch.float64, device=device, requires_grad=True)
   delta_beta = torch.tensor(0.0, dtype=torch.float64, device=device, requires_grad=True)
   delta_gamma = torch.tensor(0.0, dtype=torch.float64, device=device, requires_grad=True)

   # Global scale (1 param) — preserve existing log_scale logic
   log_scale = torch.tensor(
       math.log(calib_hint or 1.0),
       dtype=torch.float64,
       device=device,
       requires_grad=True
   )

   # Parameter list for optimizer
   trainable_params = [q_delta, delta_log_a, delta_log_b, delta_log_c,
                       delta_alpha, delta_beta, delta_gamma, log_scale]
   ```

#### Task 3: Construct A* from Incremental UB (Inside Closure)
**File:** `dbex/nanobrag_refinement.py`
**Location:** Inside the `compute_loss` closure, replace crystal_overrides logic

When `use_incremental_ub=True`:
1. Derive U and B from parameters using helpers:
   ```python
   from dbex.nanobrag_bridge import derive_orientation_from_quaternion_delta, derive_B_from_cell_deltas

   # Derive U(params) = ΔR(q_delta) @ U_baseline
   U_current = derive_orientation_from_quaternion_delta(q_delta, U_baseline)

   # Derive B(params) from cell perturbations
   B_current = derive_B_from_cell_deltas(
       delta_log_a, delta_log_b, delta_log_c,
       delta_alpha, delta_beta, delta_gamma,
       cell_baseline
   )

   # Construct A* = U @ B (one-way construction per spec-db-core.md)
   A_star = U_current @ B_current  # Shape: [3, 3]
   ```

2. Extract MOSFLM a/b/c_star for crystal_config injection:
   ```python
   # A* columns are reciprocal lattice vectors a*, b*, c*
   a_star = A_star[:, 0].detach().cpu().numpy()  # Shape: [3]
   b_star = A_star[:, 1].detach().cpu().numpy()
   c_star = A_star[:, 2].detach().cpu().numpy()

   # Inject into crystal_config via mosflm_a/b/c_star
   crystal_overrides = {
       "mosflm_a_star": tuple(a_star.tolist()),
       "mosflm_b_star": tuple(b_star.tolist()),
       "mosflm_c_star": tuple(c_star.tolist()),
   }
   ```

3. **Critical:** Do NOT inject cell parameters into `crystal_overrides` when using MOSFLM a/b/c_star injection (per GRADIENT-001 finding)

#### Task 4: Preserve Cell+Misset Default Path
**File:** `dbex/nanobrag_refinement.py`
**Location:** Wrap incremental UB logic in if/else branch

```python
if use_incremental_ub:
    # Incremental UB path (Tasks 2-3 above)
    trainable_params = [q_delta, delta_log_a, delta_log_b, delta_log_c,
                        delta_alpha, delta_beta, delta_gamma, log_scale]

    def compute_loss():
        # Derive A* = U(q_delta) @ B(cell_deltas)
        U_current = derive_orientation_from_quaternion_delta(q_delta, U_baseline)
        B_current = derive_B_from_cell_deltas(
            delta_log_a, delta_log_b, delta_log_c,
            delta_alpha, delta_beta, delta_gamma,
            cell_baseline
        )
        A_star = U_current @ B_current

        # Inject MOSFLM a/b/c_star
        a_star = A_star[:, 0].detach().cpu().numpy()
        b_star = A_star[:, 1].detach().cpu().numpy()
        c_star = A_star[:, 2].detach().cpu().numpy()
        crystal_overrides = {
            "mosflm_a_star": tuple(a_star.tolist()),
            "mosflm_b_star": tuple(b_star.tolist()),
            "mosflm_c_star": tuple(c_star.tolist()),
        }

        # Rest of closure logic (scale, HKL, loss computation)
        # ... (preserve existing)
else:
    # Cell+misset default path (preserve existing logic EXACTLY)
    # ... (existing trainable_params, compute_loss closure)
```

---

## How-To Map

See full task breakdown in **Do Now** section above.

Key file changes:
- `dbex/nanobrag_refinement.py` (~100 lines modified in `build_stage_a_lbfgs_closure`)
- Optional: `tests/dbex/test_torch_refine_smoke.py` (~10 lines for config override)

Test execution:
```bash
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
export DBEX_SMOKE_SIGMA_SOURCE=cli_override
export DBEX_SMOKE_DETECTOR_SIZE=small
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1

# Regression guard
pytest -xvs tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
    2>&1 | tee plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-23T015000Z/pytest_stage_a_incremental_ub_false.log

# Validation (may require code edit to set use_incremental_ub=True)
pytest -xvs tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
    2>&1 | tee plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-23T015000Z/pytest_stage_a_incremental_ub_true.log
```

---

## Pitfalls To Avoid

1. **GRADIENT-001:** Use MOSFLM a/b/c_star ONLY (no cell overrides)
2. **CONVERGENCE-001:** Zero-point must match DB-AT-024 (A* parity <1e-6, chi² delta <1%)
3. **Device/Dtype:** All tensors on `device` with `dtype=torch.float64`
4. **Gradient Flow (Deferred):** B1/B2 use scipy/cctbx (breaks autograd); use `.detach()` for crystal_overrides extraction
5. **Protected Assets:** Preserve cell+misset default path EXACTLY
6. **Quaternion Order:** [w,x,y,z] convention
7. **Cell Angles:** DEGREES (not radians)
8. **A* Columns:** `A_star[:, 0/1/2]` for a*/b*/c*

---

## Findings Applied

- **GRADIENT-001:** MOSFLM a/b/c_star injection (not cell overrides). Applied in Task 3.
- **CONVERGENCE-001:** Zero-point consistency critical. Applied in validation protocol.
- **REFINE-001:** Warm-start log_scale from calib_hint. Applied in Task 2.
- **REFINE-002/REFINE-006:** Chi² improvement ≥0.2%. Applied in validation criteria.

---

## Pointers

**Specs:**
- docs/spec-db-core.md:48-68 (Baseline State & Parameterization)
- docs/spec-db-workflow.md:36-45 (Stage A trainable params)
- docs/spec-db-runtime.md:18-28 (UB/A* round-trip)

**Design:**
- plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-22T170806Z/phase_a_design_document.md
- plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-23T013025Z/phase_b_implementation_summary.md

**Helpers:**
- dbex/nanobrag_bridge.py:1158-1221 (derive_orientation_from_quaternion_delta)
- dbex/nanobrag_bridge.py:1224-1288 (busing_levy_B_torch)
- dbex/nanobrag_bridge.py:1291-1388 (derive_B_from_cell_deltas)

**Tests:**
- tests/dbex/test_ub_parameterization_roundtrip.py (DB-AT-026 Tests 1-3 PASS)
- tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion (regression guard)

**Fix Plan:**
- docs/fix_plan.md:63-79 (TORCH-GEOMETRY-UB-REALIGN-001 entry)
- plans/active/TORCH-GEOMETRY-UB-REALIGN-001/implementation.md (Phase B checklist)
