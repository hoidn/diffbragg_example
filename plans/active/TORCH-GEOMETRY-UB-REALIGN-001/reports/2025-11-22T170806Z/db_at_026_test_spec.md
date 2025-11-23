# DB-AT-026 Test Specification: UB/A* Round-Trip

## Acceptance Test ID
**DB-AT-026** — UB/A* Round-Trip Test (Zero-Point Invariant Validation)

## Purpose
Validate that the incremental UB parameterization satisfies the zero-point invariants and one-way construction requirements from spec-db-core.md and spec-db-workflow.md.

## Normative Requirements Tested

1. **spec-db-core.md:61-62:**
   > "At the Stage‑A zero point (all refinement deltas = 0), implementations MUST satisfy: `U(0) = U₀`, `B(0) = B₀`, and `A*(0) = U₀ @ B₀ = A*_mapping`."

2. **spec-db-runtime.md:21-23:**
   > "Any new Stage‑A parameterization SHALL pass a round‑trip correctness check against dxtbx and Busing–Levy conventions at the zero point... with `params=0` MUST reproduce `U(0)=U₀`, `B(0)=B₀`, and `A*(0)=U₀ @ B₀` within a documented numerical tolerance."

3. **spec-db-workflow.md:40-43:**
   > "For any Stage‑A configuration that claims DB‑AT‑024 mapping parity, zero geometry parameters (all cell/angle/orientation deltas equal to zero) and baseline scale MUST reproduce the DB‑AT‑024 mapping Bragg tensor."

---

## Test File Location
**Path:** `tests/dbex/test_ub_parameterization_roundtrip.py`
**Selector:** `pytest tests/dbex/test_ub_parameterization_roundtrip.py::test_db_at_026_ub_roundtrip`
**Mark:** `@pytest.mark.acceptance` (DB-AT-026)

---

## Test Implementation

### Setup (Fixture or Test Preamble)

```python
import pytest
import numpy as np
import torch
from dxtbx.model import ExperimentList
from dbex.nanobrag_bridge import (
    derive_orientation_from_quaternion_delta,
    derive_B_from_cell_deltas,
)

@pytest.fixture
def canonical_crystal_baseline():
    """Load canonical refGeom.expt and extract baseline UB state."""
    expt = ExperimentList.from_file("refGeom.expt")[0]
    crystal = expt.crystal

    # Baseline orientation and reciprocal metric
    U₀ = np.array(crystal.get_U()).reshape(3, 3)
    B₀ = np.array(crystal.get_B()).reshape(3, 3)
    A_star_mapping = U₀ @ B₀

    # Baseline cell parameters
    cell_baseline = crystal.get_unit_cell().parameters()
    a₀, b₀, c₀, α₀, β₀, γ₀ = cell_baseline

    return {
        "U₀": U₀,
        "B₀": B₀,
        "A_star_mapping": A_star_mapping,
        "cell_baseline": cell_baseline,
    }
```

---

### Test 1: Orientation Zero-Point (U(0) = U₀)

```python
def test_db_at_026_orientation_zero_point(canonical_crystal_baseline):
    """
    DB-AT-026.1: Validate U(0) = U₀ for identity quaternion.

    Requirement: spec-db-core.md:61
    """
    U₀ = canonical_crystal_baseline["U₀"]

    # Zero-point orientation: identity quaternion
    q_delta = torch.tensor([1.0, 0.0, 0.0, 0.0], dtype=torch.float64)

    # Derive U(params) at zero point
    U_params = derive_orientation_from_quaternion_delta(
        q_delta,
        U_baseline=torch.tensor(U₀, dtype=torch.float64)
    )

    # Convert to numpy for comparison
    U_params_np = U_params.detach().cpu().numpy()

    # Assert: ||U(0) - U₀|| < 1e-12
    error = np.linalg.norm(U_params_np - U₀)
    assert error < 1e-12, (
        f"U(0) must equal U₀ (identity quaternion). "
        f"Error: {error:.3e} (threshold: 1e-12)"
    )

    # Validate orthonormality
    identity = U_params_np.T @ U_params_np
    ortho_error = np.linalg.norm(identity - np.eye(3))
    assert ortho_error < 1e-12, f"U(0) must be orthonormal: {ortho_error:.3e}"

    # Validate determinant
    det_U = np.linalg.det(U_params_np)
    assert abs(det_U - 1.0) < 1e-12, f"det(U(0)) must equal 1: {det_U:.6f}"
```

**Expected Outcome:**
- `error < 1e-12` → PASS
- `ortho_error < 1e-12` → PASS
- `|det(U) - 1| < 1e-12` → PASS

**Artifacts:**
- None (fast unit test, <100ms)

---

### Test 2: Cell Zero-Point (B(0) = B₀)

```python
def test_db_at_026_cell_zero_point(canonical_crystal_baseline):
    """
    DB-AT-026.2: Validate B(0) = B₀ for zero cell deltas.

    Requirement: spec-db-core.md:61
    """
    B₀ = canonical_crystal_baseline["B₀"]
    cell_baseline = canonical_crystal_baseline["cell_baseline"]

    # Zero-point cell: zero log-length and angle deltas
    δlog_a = torch.tensor(0.0, dtype=torch.float64)
    δlog_b = torch.tensor(0.0, dtype=torch.float64)
    δlog_c = torch.tensor(0.0, dtype=torch.float64)
    Δα = torch.tensor(0.0, dtype=torch.float64)
    Δβ = torch.tensor(0.0, dtype=torch.float64)
    Δγ = torch.tensor(0.0, dtype=torch.float64)

    # Derive B(params) at zero point
    B_params = derive_B_from_cell_deltas(
        δlog_a, δlog_b, δlog_c,
        Δα, Δβ, Δγ,
        cell_baseline=cell_baseline,
        dtype=torch.float64
    )

    # Convert to numpy for comparison
    B_params_np = B_params.detach().cpu().numpy()

    # Assert: ||B(0) - B₀|| < 1e-12
    error = np.linalg.norm(B_params_np - B₀)
    assert error < 1e-12, (
        f"B(0) must equal B₀ (zero cell deltas). "
        f"Error: {error:.3e} (threshold: 1e-12)"
    )
```

**Expected Outcome:**
- `error < 1e-12` → PASS

**Artifacts:**
- None (fast unit test, <100ms)

---

### Test 3: Mapping Parity (A*(0) = A*_mapping)

```python
def test_db_at_026_mapping_parity(canonical_crystal_baseline):
    """
    DB-AT-026.3: Validate A*(0) = A*_mapping for zero params.

    Requirements:
    - spec-db-core.md:62: "A*(0) = U₀ @ B₀ = A*_mapping"
    - spec-db-workflow.md:40: mapping zero-point invariant
    """
    U₀ = canonical_crystal_baseline["U₀"]
    B₀ = canonical_crystal_baseline["B₀"]
    A_star_mapping = canonical_crystal_baseline["A_star_mapping"]
    cell_baseline = canonical_crystal_baseline["cell_baseline"]

    # Zero-point orientation
    q_delta = torch.tensor([1.0, 0.0, 0.0, 0.0], dtype=torch.float64)
    U_params = derive_orientation_from_quaternion_delta(
        q_delta,
        U_baseline=torch.tensor(U₀, dtype=torch.float64)
    )

    # Zero-point cell
    B_params = derive_B_from_cell_deltas(
        δlog_a=torch.tensor(0.0, dtype=torch.float64),
        δlog_b=torch.tensor(0.0, dtype=torch.float64),
        δlog_c=torch.tensor(0.0, dtype=torch.float64),
        Δα_deg=torch.tensor(0.0, dtype=torch.float64),
        Δβ_deg=torch.tensor(0.0, dtype=torch.float64),
        Δγ_deg=torch.tensor(0.0, dtype=torch.float64),
        cell_baseline=cell_baseline,
        dtype=torch.float64
    )

    # Construct A*(0) = U(0) @ B(0)
    A_star_params = U_params @ B_params

    # Convert to numpy
    A_star_params_np = A_star_params.detach().cpu().numpy()

    # Assert: ||A*(0) - A*_mapping|| < 1e-6
    # (spec-db-core.md:62 allows 1e-6 tolerance for mapping parity)
    error = np.linalg.norm(A_star_params_np - A_star_mapping)
    assert error < 1e-6, (
        f"A*(0) must equal A*_mapping (U₀ @ B₀). "
        f"Error: {error:.3e} (threshold: 1e-6)"
    )

    # Also test tighter tolerance (implementation should achieve 1e-12)
    if error < 1e-12:
        print(f"✓ Exceeded spec: A*(0) parity error {error:.3e} < 1e-12")
```

**Expected Outcome:**
- `error < 1e-6` → PASS (spec requirement)
- `error < 1e-12` → BONUS (implementation quality)

**Artifacts:**
- Console print if error < 1e-12 (bonus achievement)

---

### Test 4: Gradient Flow Validation (Optional)

```python
@pytest.mark.optional
def test_db_at_026_gradient_flow(canonical_crystal_baseline):
    """
    DB-AT-026.4: Validate A*(params) is differentiable w.r.t. all parameters.

    Requirement: spec-db-runtime.md:13 (differentiability)
    """
    U₀ = canonical_crystal_baseline["U₀"]
    cell_baseline = canonical_crystal_baseline["cell_baseline"]

    # Trainable parameters (small non-zero for gradient test)
    q_delta = torch.tensor([1.0, 0.001, 0.002, 0.003], requires_grad=True)
    δlog_a = torch.tensor(0.001, requires_grad=True)
    δlog_b = torch.tensor(0.002, requires_grad=True)
    δlog_c = torch.tensor(0.003, requires_grad=True)
    Δα = torch.tensor(0.1, requires_grad=True)  # degrees
    Δβ = torch.tensor(0.2, requires_grad=True)
    Δγ = torch.tensor(0.3, requires_grad=True)

    # Derive U and B
    U_params = derive_orientation_from_quaternion_delta(
        q_delta,
        U_baseline=torch.tensor(U₀, dtype=torch.float64)
    )

    B_params = derive_B_from_cell_deltas(
        δlog_a, δlog_b, δlog_c, Δα, Δβ, Δγ,
        cell_baseline=cell_baseline,
        dtype=torch.float64
    )

    # Construct A*
    A_star = U_params @ B_params

    # Dummy loss (sum of all elements)
    loss = A_star.sum()

    # Backpropagate
    loss.backward()

    # Validate gradients exist and are non-zero
    assert q_delta.grad is not None, "Quaternion must have gradients"
    assert torch.any(q_delta.grad != 0), "Quaternion gradients must be non-zero"

    assert δlog_a.grad is not None, "δlog_a must have gradients"
    assert δlog_b.grad is not None, "δlog_b must have gradients"
    assert δlog_c.grad is not None, "δlog_c must have gradients"

    assert Δα.grad is not None, "Δα must have gradients"
    assert Δβ.grad is not None, "Δβ must have gradients"
    assert Δγ.grad is not None, "Δγ must have gradients"

    print(f"✓ All gradients exist: q={q_delta.grad.norm():.3e}, "
          f"δlog_a={δlog_a.grad:.3e}, Δα={Δα.grad:.3e}")
```

**Expected Outcome:**
- All `assert` statements PASS
- Gradient norms > 0 (non-degenerate gradients)

**Artifacts:**
- Console print of gradient norms

---

### Test 5: Cross-Reference with DB-AT-024 (Integration Test)

```python
@pytest.mark.acceptance
@pytest.mark.slow
def test_db_at_026_mapping_bragg_parity(canonical_crystal_baseline):
    """
    DB-AT-026.5: Validate zero-point Bragg tensor matches DB-AT-024 mapping.

    Requirement: spec-db-workflow.md:40
    Dependencies: DB-AT-024 must pass first
    """
    pytest.importorskip("nanobrag_torch")  # Skip if nanobrag_torch unavailable

    from dbex.nanobrag_refinement import simulate_forward_once
    from dbex.nanobrag_bridge import create_crystal_config

    # Load canonical experiment
    expt = ExperimentList.from_file("refGeom.expt")[0]

    # Extract baseline state
    U₀ = canonical_crystal_baseline["U₀"]
    B₀ = canonical_crystal_baseline["B₀"]
    A_star_mapping = canonical_crystal_baseline["A_star_mapping"]

    # Zero-point params → derive A*(0)
    # (use helpers from Test 3)
    q_delta = torch.tensor([1.0, 0.0, 0.0, 0.0], dtype=torch.float64)
    U_zero = derive_orientation_from_quaternion_delta(
        q_delta, U_baseline=torch.tensor(U₀, dtype=torch.float64)
    )

    B_zero = derive_B_from_cell_deltas(
        δlog_a=0.0, δlog_b=0.0, δlog_c=0.0,
        Δα_deg=0.0, Δβ_deg=0.0, Δγ_deg=0.0,
        cell_baseline=canonical_crystal_baseline["cell_baseline"],
        dtype=torch.float64
    )

    A_star_zero = U_zero @ B_zero

    # Create CrystalConfig with derived A*
    # (inject via MOSFLM a/b/c_star)
    mosflm_a_star = A_star_zero[:, 0].detach().cpu().numpy()
    mosflm_b_star = A_star_zero[:, 1].detach().cpu().numpy()
    mosflm_c_star = A_star_zero[:, 2].detach().cpu().numpy()

    crystal_config = create_crystal_config(
        expt=expt,
        mosflm_a_star=tuple(mosflm_a_star),
        mosflm_b_star=tuple(mosflm_b_star),
        mosflm_c_star=tuple(mosflm_c_star),
        misset_deg=[0.0, 0.0, 0.0],  # zero misset deltas
        # ... other config params
    )

    # Run forward model with zero-point params
    bragg_zero, _ = simulate_forward_once(
        expt=expt,
        crystal_config=crystal_config,
        device="cpu",
        dtype=torch.float32,
    )

    # Load DB-AT-024 mapping baseline
    # (assume DB-AT-024 test saves mapping Bragg tensor)
    bragg_mapping = load_db_at_024_baseline()  # implementation TBD

    # Compute chi² between zero-point and mapping
    chi2 = torch.sum((bragg_zero - bragg_mapping) ** 2).item()

    # Compute correlation
    cc = torch.corrcoef(
        torch.stack([bragg_zero.flatten(), bragg_mapping.flatten()])
    )[0, 1].item()

    # Assert: chi² < threshold, CC > 0.99
    # (thresholds TBD based on DB-AT-024 baseline variance)
    chi2_threshold = 1e6  # example, tune based on DB-AT-024
    assert chi2 < chi2_threshold, (
        f"Zero-point chi² must match DB-AT-024: {chi2:.3e} > {chi2_threshold:.3e}"
    )

    assert cc > 0.99, (
        f"Zero-point correlation must match DB-AT-024: CC={cc:.6f} < 0.99"
    )

    print(f"✓ DB-AT-026.5 PASS: chi²={chi2:.3e}, CC={cc:.6f}")
```

**Expected Outcome:**
- `chi2 < threshold` → PASS
- `CC > 0.99` → PASS

**Dependencies:**
- DB-AT-024 must pass first (provides mapping baseline).
- `simulate_forward_once` and `create_crystal_config` must be implemented.

**Artifacts:**
- `bragg_zero.npy` (zero-point Bragg tensor, for debugging)
- JSON with chi² and CC metrics

---

## Acceptance Criteria Summary

| Test | Criterion | Threshold | Normative Source |
|------|-----------|-----------|------------------|
| 1 | `\|\|U(0) - U₀\|\|` | < 1e-12 | spec-db-core.md:61 |
| 2 | `\|\|B(0) - B₀\|\|` | < 1e-12 | spec-db-core.md:61 |
| 3 | `\|\|A*(0) - A*_mapping\|\|` | < 1e-6 | spec-db-core.md:62 |
| 4 | Gradients exist (all params) | Non-zero | spec-db-runtime.md:13 |
| 5 | chi² (zero vs mapping) | < threshold | spec-db-workflow.md:40 |
| 5 | CC (zero vs mapping) | > 0.99 | spec-db-workflow.md:40 |

**Overall DB-AT-026 Status:**
- Tests 1-4 must PASS for Phase B completion.
- Test 5 may be deferred to Phase C (requires full forward model integration).

---

## Test Execution Commands

### Run All DB-AT-026 Tests

```bash
# Fast unit tests only (Tests 1-4)
pytest -v tests/dbex/test_ub_parameterization_roundtrip.py::test_db_at_026_orientation_zero_point
pytest -v tests/dbex/test_ub_parameterization_roundtrip.py::test_db_at_026_cell_zero_point
pytest -v tests/dbex/test_ub_parameterization_roundtrip.py::test_db_at_026_mapping_parity
pytest -v tests/dbex/test_ub_parameterization_roundtrip.py::test_db_at_026_gradient_flow

# Integration test (Test 5, slow)
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -v tests/dbex/test_ub_parameterization_roundtrip.py::test_db_at_026_mapping_bragg_parity
```

### Run DB-AT-026 Mark

```bash
# All DB-AT-026 tests (once mark is added)
pytest -v -m "acceptance and not slow" tests/dbex/test_ub_parameterization_roundtrip.py
```

**Expected Runtime:**
- Tests 1-4: <1 second total
- Test 5: ~30 seconds (forward model simulation)

---

## Artifacts Policy

### Test 1-4 (Fast Unit Tests)
- **Artifacts:** None (pytest console output sufficient)
- **Failures:** Print error values to stdout for debugging

### Test 5 (Integration Test)
- **Artifacts Directory:** `plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/<timestamp>/db_at_026/`
- **Files:**
  - `bragg_zero.npy` — Zero-point Bragg tensor
  - `bragg_mapping.npy` — DB-AT-024 baseline Bragg tensor (reference)
  - `metrics.json` — chi², CC, max_abs_diff
  - `pytest_db_at_026.log` — Full pytest output

**Example `metrics.json`:**
```json
{
  "test_id": "DB-AT-026.5",
  "chi2": 8.4e5,
  "cc": 0.9999,
  "max_abs_diff": 3.2e-5,
  "threshold_chi2": 1e6,
  "threshold_cc": 0.99,
  "status": "PASS"
}
```

---

## Regression Guard

After DB-AT-026 implementation, add to regression suite:

**File:** `docs/TESTING_GUIDE.md` §2 Active Acceptance Tests

```markdown
### DB-AT-026 — UB/A* Round-Trip

**Status:** Active (Phase B)
**Selector:** `pytest tests/dbex/test_ub_parameterization_roundtrip.py -m acceptance`
**Purpose:** Validate incremental UB parameterization zero-point invariants
**Dependencies:** refGeom.expt (canonical), DB-AT-024 baseline (for Test 5)
**Runtime:** <1s (unit tests), ~30s (integration)
```

---

## Phase B Implementation Checklist

- [ ] Implement `derive_orientation_from_quaternion_delta()` in `dbex/nanobrag_bridge.py`
- [ ] Implement `derive_B_from_cell_deltas()` in `dbex/nanobrag_bridge.py`
- [ ] Implement `busing_levy_B_torch()` helper
- [ ] Implement `quaternion_to_matrix()` helper (or import from pytorch3d/kornia)
- [ ] Author `tests/dbex/test_ub_parameterization_roundtrip.py` with all 5 tests
- [ ] Run Tests 1-4, verify all PASS
- [ ] Defer Test 5 to Phase C if `simulate_forward_once` not ready
- [ ] Update `docs/TESTING_GUIDE.md` §2 with DB-AT-026 entry
- [ ] Update `docs/development/TEST_SUITE_INDEX.md` with DB-AT-026 status
- [ ] Run `pytest --collect-only` and archive selector log

---

## References

- `docs/spec-db-core.md:61-62` — Zero-point invariant (normative)
- `docs/spec-db-workflow.md:40-43` — Mapping zero-point requirement (normative)
- `docs/spec-db-runtime.md:20-23` — Round-trip test mandate (normative)
- `docs/spec-db-conformance.md` — DB-AT-024 mapping parity baseline
- `plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-22T170806Z/phase_a_design_document.md` — Design rationale

---

**DB-AT-026 is the executable contract for UB-REALIGN-001 correctness.**
