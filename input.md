# Ralph Input — Loop i=219

## Summary
Verify mosaic coupling hypothesis by testing gradcheck with `experiment=None` to bypass mosaic metadata extraction.

## Focus
ARCH-GRADIENT-FLOW-001 — Phase B.9 (Mosaic Workaround Verification)

## Branch
`integration`

## Mapped Tests
- `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck_cell_a_no_mosaic --tb=short`

## Artifacts
`plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T234500Z/`

---

## Do Now (Implementation: Debug + Test)

**Focus Item:** ARCH-GRADIENT-FLOW-001 Phase B.9 — Mosaic workaround verification

**Implement:**
- `tests/dbex/test_gradients.py::test_db_at_010_gradcheck_cell_a_no_mosaic` (new test function)
- Investigation report in artifacts

**Validating pytest selector:**
`pytest -v tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck_cell_a_no_mosaic`

**Action Type:** Debug (hypothesis verification via targeted test)

---

### Background (from Phase B.8)

Loop i=218 (Phase B.8) created 5 diagnostic tests:
- **ALL synthetic tests PASS** with 1.00× gradient ratio
- **Only real refGeom data test FAILS** (magnitude mismatch 843-19,352×)

**Key finding:** The DBEX integration layer does NOT break cell parameter gradients for synthetic cubic crystals. The magnitude mismatch is specific to **real experiment metadata**.

**Suspected root cause:** Mosaic parameters extracted from experiment metadata:
- `ML_half_mosaicity_deg` at `config_factories.py:382-383` sets `mosaic_spread_deg > 0`
- When `mosaic_spread_deg > 0`, a different simulation code path is taken in nanobrag_torch
- This code path has a gradient bug (separate upstream issue filed: `mosaic_gradient_bug_2025_12_08.md`)

### Hypothesis to Verify

If we bypass the mosaic metadata extraction by passing `experiment=None` to `simulate_forward_torch`, the cell parameter gradcheck should PASS because:
1. `config_factories.py:380` guards against `experiment is None`
2. This keeps `mosaic_spread_deg = 0.0` (line 372)
3. The non-mosaic code path in nanobrag_torch has correct gradients (confirmed by upstream 6/6 tests PASS)

---

### Tasks

**B.9.1 — Create no-mosaic test:**

Add new test `test_db_at_010_gradcheck_cell_a_no_mosaic` to `tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck` class.

The test should:
1. Copy the structure of `test_db_at_010_gradcheck_crystal_cell_a` (lines 168-255)
2. Modify `loss_fn` to pass `experiment=None` instead of `experiment=experiment`
3. Use the same tolerances: `eps=1e-6, atol=1e-5, rtol=0.05`
4. Document the workaround purpose in the docstring

**Insert AFTER** `test_db_at_010_gradcheck_crystal_cell_gamma` (around line 330):

```python
def test_db_at_010_gradcheck_cell_a_no_mosaic(
    self,
    refinement_inputs,
    geometry_objects,
    hkl_data,
    artifact_dir
):
    """
    DB-AT-010 Workaround: Verify cell_a gradients with mosaic bypass.

    ARCH-GRADIENT-FLOW-001 Phase B.9: Tests the hypothesis that the gradient
    magnitude mismatch is caused by the mosaic code path in nanobrag_torch.
    By passing experiment=None, we bypass mosaic metadata extraction
    (config_factories.py:380), keeping mosaic_spread_deg=0.0.

    If this test PASSES while test_db_at_010_gradcheck_crystal_cell_a FAILS,
    it confirms the mosaic code path is the root cause.
    """
    from dbex.physics.forward import simulate_forward_torch
    from dbex.physics.loss import compute_masked_mse_loss

    device = torch.device('cpu')
    dtype = torch.float64

    # Convert inputs to torch
    target_torch = torch.tensor(refinement_inputs.target, dtype=dtype, device=device)
    loss_mask_torch = torch.tensor(refinement_inputs.loss_mask, dtype=torch.bool, device=device)
    sigma_readout_torch = torch.tensor(refinement_inputs.sigma_readout, dtype=dtype, device=device)

    # Get base crystal config
    base_crystal = geometry_objects["crystal"]
    # NOTE: experiment=None bypasses mosaic metadata extraction (ARCH-GRADIENT-FLOW-001 B.9)

    def loss_fn(cell_a_tensor):
        crystal_overrides = {'cell_a': cell_a_tensor}

        # Pass experiment=None to bypass mosaic extraction
        bragg_torch = simulate_forward_torch(
            inputs=refinement_inputs,
            detector=geometry_objects["detector"],
            beam=geometry_objects["beam"],
            crystal=base_crystal,
            experiment=None,  # WORKAROUND: bypass mosaic_spread_deg extraction
            hkl_indices=hkl_data["indices"],
            hkl_amplitudes=hkl_data["amplitudes"],
            spot_scale_override=1.0,
            device=device,
            dtype=dtype,
            crystal_overrides=crystal_overrides
        )

        loss = compute_masked_mse_loss(bragg_torch, target_torch, loss_mask_torch, sigma_readout_torch)
        return loss

    # Get base cell_a value
    uc = base_crystal.get_unit_cell()
    base_cell_a = uc.parameters()[0]

    # Create differentiable parameter tensor
    cell_a_param = torch.tensor(base_cell_a, dtype=dtype, device=device, requires_grad=True)

    # Run gradcheck
    gradcheck_passed = gradcheck(
        loss_fn,
        (cell_a_param,),
        eps=1e-6,
        atol=1e-5,
        rtol=0.05,
        raise_exception=True
    )

    # Emit metrics
    metrics = {
        "parameter": "crystal_cell_a_no_mosaic",
        "base_value": float(base_cell_a),
        "gradcheck_passed": gradcheck_passed,
        "workaround": "experiment=None to bypass mosaic extraction",
        "eps": 1e-6,
        "atol": 1e-5,
        "rtol": 0.05,
        "device": str(device),
        "dtype": str(dtype)
    }

    metrics_file = artifact_dir / "gradcheck_crystal_cell_a_no_mosaic.json"
    with open(metrics_file, 'w') as f:
        json.dump(metrics, f, indent=2)

    assert gradcheck_passed, "Gradcheck failed for crystal cell_a (no mosaic) parameter"
```

**B.9.2 — Run the new test:**

```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck_cell_a_no_mosaic --tb=short 2>&1 | tee plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T234500Z/gradcheck_no_mosaic.log
```

**B.9.3 — Run the original failing test for comparison:**

```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck_crystal_cell_a --tb=short 2>&1 | head -50
```

**B.9.4 — Document results:**

Create `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T234500Z/mosaic_hypothesis_verification.md` with:
- Test results comparison (no-mosaic vs original)
- Hypothesis confirmation status
- Recommended next steps

---

## How-To Map

### Create test file edit:
1. Read `tests/dbex/test_gradients.py` to find insertion point (after `test_db_at_010_gradcheck_crystal_cell_gamma`)
2. Insert the new test function using Edit tool
3. Verify syntax by running pytest collect

### Run commands:
```bash
# Create artifacts directory
mkdir -p plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T234500Z

# Run new no-mosaic test
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck_cell_a_no_mosaic --tb=short 2>&1 | tee plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T234500Z/gradcheck_no_mosaic.log

# Run original test for comparison (expect FAIL)
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck_crystal_cell_a --tb=short 2>&1 | head -50
```

---

## Pitfalls To Avoid

1. **DO NOT** modify nanobrag_torch source (Environment Freeze)
2. **DO NOT** change tolerances to make the original test pass — this is a diagnostic
3. **DO** use float64 dtype for gradcheck (per runtime checklist)
4. **DO** use `NANOBRAGG_DISABLE_COMPILE=1` to avoid torch.compile interference
5. **DO** ensure both tests use identical parameters except for `experiment=None`
6. **DO** document the hypothesis verification result clearly
7. **DO NOT** add the new test to the official DB-AT-010 suite — it's a diagnostic workaround

---

## If Blocked

If the no-mosaic test also fails:
1. Log failure signature in artifacts
2. Check if `experiment=None` causes other issues (e.g., missing beam metadata)
3. Try creating a mock experiment object with `ML_half_mosaicity_deg=None` instead
4. Document the block and request supervisor guidance

---

## Findings Applied (Mandatory)

- **RUNTIME-001**: `NANOBRAGG_DISABLE_COMPILE=1` required for gradcheck (runtime checklist §2)
- **GRADIENT-001**: Tensor-valued overrides preserve autograd graph
- **GRADIENT-002**: Graph connectivity fixed in i=209; this investigates mosaic coupling
- **TESTING-003**: Use canonical pytest selectors from TESTING_GUIDE.md
- **PROBE-FREEZE-001**: Test is diagnostic (not enforcement); stays in test file

---

## Pointers

### Code Under Test
- `dbex/physics/forward.py:199` — `create_crystal_config(crystal, experiment, ...)` call
- `dbex/refinement/config_factories.py:380-396` — Mosaic metadata extraction with `if experiment is not None:` guard

### Existing Tests
- `tests/dbex/test_gradients.py:168-255` — Original `test_db_at_010_gradcheck_crystal_cell_a` (FAILING)
- `tests/dbex/test_gradients.py:480-520` — Synthetic diagnostic tests added in B.8 (PASSING)

### Prior Evidence
- `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T232143Z/magnitude_audit.md` — Phase B.8 findings

---

## Next Up (optional)

If Phase B.9 confirms mosaic coupling:
1. Document the workaround in `docs/findings.md::GRADIENT-003`
2. Consider adding `mosaic_spread_deg_override` parameter to `create_crystal_config` (deferred pending upstream mosaic fix)
3. Update DB-AT-010 status in TEST_SUITE_INDEX.md with "blocked_pending_upstream (mosaic gradient bug)"
