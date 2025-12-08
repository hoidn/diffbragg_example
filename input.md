# input.md — Loop i=218

## Summary
Phase B.8 — Investigate cell parameter gradient magnitude mismatch (843-19352×) by creating minimal reproduction bypassing DBEX factories.

## Focus
**ARCH-GRADIENT-FLOW-001** — Gradient Flow Restoration (Phase B.8: DBEX-side magnitude investigation)

## Branch
`integration`

## Mapped Tests
- `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_gradients.py::test_db_at_010_gradcheck_crystal_cell_a --tb=short`

## Artifacts
`plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T232143Z/`

---

## Do Now (Implementation: Debug)

**Focus Item:** ARCH-GRADIENT-FLOW-001 Phase B.8 — Cell parameter gradient magnitude investigation

**Implement:**
- `tests/dbex/test_gradients.py::test_minimal_nanobrag_gradcheck` (new test function)
- Investigation report in artifacts

**Validating pytest selector:**
`pytest -v tests/dbex/test_gradients.py::test_minimal_nanobrag_gradcheck`

**Action Type:** Debug (hypothesis-driven minimal reproduction)

---

### Background (from upstream response)

Loop i=209 fixed graph connectivity — analytical gradients are now non-zero:
- cell_a: analytical=7.04e7, numerical=8.36e4 → **843× mismatch**
- cell_gamma: analytical=4.64e7, numerical=2.40e3 → **19,352× mismatch**

Upstream `inbox/nanobrag_torch_cell_gradient_response_2025_12_08.md` confirms:
- nanobrag_torch cell parameter gradcheck tests **PASS** (6/6)
- Issue is in **DBEX integration layer**, not nanobrag_torch
- **Hypotheses** (from upstream):
  1. Double unit conversion (Å→m applied twice)
  2. Intermediate scalar extraction (.item()/.detach()/.numpy())
  3. Fluence scaling mismatch (DBEX vs upstream fluence=1e28)

---

### Tasks (B.8.1-B.8.3)

**B.8.1 — Create minimal reproduction test** (bypasses DBEX factories):
```python
# tests/dbex/test_gradients.py — add new test function

def test_minimal_nanobrag_gradcheck():
    """
    Minimal reproduction of nanobrag_torch cell parameter gradcheck.

    Bypasses all DBEX factories to isolate the integration layer.
    This test should PASS if the issue is in DBEX config_factories/helpers.
    """
    import os
    os.environ["NANOBRAGG_DISABLE_COMPILE"] = "1"
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

    import torch
    from torch.autograd import gradcheck
    from nanobrag_torch.config import CrystalConfig, DetectorConfig, BeamConfig
    from nanobrag_torch.models.crystal import Crystal
    from nanobrag_torch.models.detector import Detector
    from nanobrag_torch.simulator import Simulator

    device = torch.device("cpu")
    dtype = torch.float64

    # Differentiable cell parameter
    cell_a = torch.tensor(100.0, dtype=dtype, requires_grad=True, device=device)

    def loss_fn(cell_a_param):
        crystal_config = CrystalConfig(
            cell_a=cell_a_param,
            cell_b=100.0,
            cell_c=100.0,
            cell_alpha=90.0,
            cell_beta=90.0,
            cell_gamma=90.0,
            N_cells=(5, 5, 5),
            default_F=100.0,
        )

        detector_config = DetectorConfig(
            distance_mm=100.0,
            pixel_size_mm=0.1,
            spixels=64,
            fpixels=64,
        )

        beam_config = BeamConfig(
            wavelength_A=1.0,
            fluence=1e28,
        )

        crystal = Crystal(config=crystal_config, device=device, dtype=dtype)
        detector = Detector(config=detector_config, device=device, dtype=dtype)

        simulator = Simulator(
            crystal=crystal,
            detector=detector,
            beam_config=beam_config,
            device=device,
            dtype=dtype,
        )

        result = simulator.run()
        return result.sum()

    # Run gradcheck with upstream tolerances
    assert gradcheck(loss_fn, (cell_a,), eps=1e-6, atol=1e-5, rtol=0.05), \
        "Minimal nanobrag_torch gradcheck failed - issue is NOT in DBEX integration"
```

**B.8.2 — Run minimal test and compare**:
- If test PASSES: Confirms issue is in DBEX integration layer (proceed to B.8.3)
- If test FAILS: Issue is in nanobrag_torch (unexpected per upstream response)

**B.8.3 — If B.8.2 passes, audit config_factories.py**:
Search for unit conversion or magnitude-altering code paths:
```bash
grep -n "1000\|1e-\|1e+\|Angstrom\|meter\|mm\|fluence" dbex/refinement/config_factories.py
grep -n "1000\|1e-\|1e+\|fluence" dbex/refinement/helpers.py
```

Document findings in `magnitude_audit.md`.

---

## How-To Map

### Environment setup:
```bash
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1
```

### Run minimal reproduction:
```bash
pytest -v tests/dbex/test_gradients.py::test_minimal_nanobrag_gradcheck --tb=short 2>&1 | tee plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T232143Z/minimal_gradcheck.log
```

### Run existing failing test for comparison:
```bash
pytest -v tests/dbex/test_gradients.py::test_db_at_010_gradcheck_crystal_cell_a --tb=short 2>&1 | head -100
```

---

## Pitfalls To Avoid

1. **DO NOT** modify nanobrag_torch source (Environment Freeze)
2. **DO NOT** change tolerances to make tests pass — investigate magnitude source
3. **DO** use float64 dtype for gradcheck (per runtime checklist)
4. **DO** use `NANOBRAGG_DISABLE_COMPILE=1` to avoid torch.compile interference
5. **DO** match upstream test parameters (fluence=1e28, eps=1e-6, atol=1e-5, rtol=0.05)
6. **DO** capture both minimal test and DBEX test outputs for comparison

---

## If Blocked

If minimal test also fails (unexpected):
1. Log failure signature in artifacts
2. Document environment difference from upstream
3. File follow-up inquiry to nanoBragg inbox with detailed reproduction steps

---

## Findings Applied (Mandatory)

- **RUNTIME-001**: `NANOBRAGG_DISABLE_COMPILE=1` required for gradcheck (runtime checklist §2)
- **GRADIENT-001**: Tensor-valued overrides preserve autograd graph
- **GRADIENT-002**: Graph connectivity fixed in i=209; this investigates magnitude
- **TESTING-003**: Use canonical pytest selectors from TESTING_GUIDE.md

---

## Pointers

### Upstream Response
- `inbox/nanobrag_torch_cell_gradient_response_2025_12_08.md` — Cell gradient confirmation + hypotheses

### Code Modules Under Investigation
- `dbex/refinement/config_factories.py:278-468` — create_crystal_config
- `dbex/refinement/helpers.py:83-228` — create_unified_simulator
- `dbex/physics/forward.py:73-276` — simulate_forward_torch

### Prior Loop Evidence
- `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T212500Z/` — Loop i=209 (graph fix)

---

## Next Up (optional)

If B.8 succeeds (minimal passes, DBEX fails):
- B.8.4: Trace specific magnitude source in DBEX integration layer
- B.8.5: Implement fix and re-run full DB-AT-010 suite
