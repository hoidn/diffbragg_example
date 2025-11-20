# PHYSICS-LOSS-001 Initialization Audit

**Date:** 2025-11-20
**Focus:** A1 - Initialize implementation plan, A2 - Audit sigma_rdout extraction
**Status:** Complete (Audit phase)

## Summary

Audited the current state of `sigma_readout` plumbing in `dbex/nanobrag_bridge.py` and upstream data flow from CLI to identify what remains for Phase A.

## Findings

### ✅ Already Implemented (Phase A Complete)

1. **RefinementInputs dataclass** (`dbex/nanobrag_bridge.py:51-73`)
   - Already includes `sigma_readout: np.ndarray` field (line 71)
   - Documentation specifies: "Per-pixel or per-panel readout noise aligned with target units"
   - Properly annotated with units awareness (photons vs ADU)

2. **prepare_refinement_inputs function** (`dbex/nanobrag_bridge.py:76-269`)
   - **Accepts optional `sigma_readout` parameter** (line 84)
   - **Handles broadcasting** (lines 203-214):
     - Accepts scalar, per-panel, or per-pixel arrays
     - Broadcasts to full `[panel, slow, fast]` shape
     - Validates shape compatibility
   - **Applies ADU→photon conversion** (lines 227-233):
     - When `adu_per_photon` is provided, divides sigma by gain
     - Ensures units match `target_representation`
   - **Zeroes invalid pixels** (lines 247-252):
     - Applies loss_mask to zero sigma where loss shouldn't be computed
     - Fallback to zeros array if sigma_readout not provided (line 250)
   - **Returns RefinementInputs** with sigma_readout field populated (line 266)

3. **Test coverage** (`tests/dbex/test_nanobrag_bridge.py`)
   - `test_prepare_refinement_inputs_basic`: Asserts sigma_readout shape/dtype (lines 133, 139, 182-183)
   - `test_sigma_readout_broadcast_and_conversion`: Validates broadcast and photon conversion (lines 185-217)
   - Tests confirm Phase A checklist items A1, A2, A3 are complete

### ❌ Missing: CLI Integration

**Current state** (`dbex/refine_one.py:187-195`):
```python
inputs = prepare_refinement_inputs(
    data=DL.data,
    background_image=DL.background_image,
    trusted_mask=DL.trusted_mask,
    bbox=DL.bbox,
    pids=DL.pids,
    detector=DL.detector,
    adu_per_photon=args.adu_per_photon
    # ❌ sigma_readout parameter NOT PASSED
)
```

**Gap:** No `--sigma-r` CLI flag exists; `sigma_readout` defaults to zeros array.

**Per spec-db-core.md:32:**
> The bridge SHALL supply readout-noise estimates `sigma_readout` in the same units as the loss target (photons or ADU/gain).

**Per simtbx_api.md:27-30:**
- DiffBragg derives `sigma_rdout` from `params.refiner.sigma_r` (ADU) and `params.refiner.adu_per_photon`
- Detector pedestal RMS maps (e.g., Jungfrau) override scalar nominal value
- Background fits and variance models use `sigma_rdout^2 + I_model` consistently

**Required for Phase A completion:**
1. Add `--sigma-r` CLI flag (ADU units, scalar or path to per-pixel map)
2. Pass `sigma_readout=<derived_value>` to `prepare_refinement_inputs` in `refine_one.py:187`
3. If `--sigma-r` not provided, emit warning and fall back to zero (Poisson-only mode)

## Phase Status

### Phase A — Bridge Data ✅ (with CLI gap)
- [x] A1: `RefinementInputs` includes `sigma_rdout` field
- [x] A2: `prepare_refinement_inputs` extracts/converts readout noise
  - [x] ADU→photon conversion when `adu_per_photon` provided
  - [x] Fallback to zeros with no warning (should add warning)
- [x] A3: Tests assert `sigma_rdout` presence/shape

**Action:** Add `--sigma-r` flag and wire to `prepare_refinement_inputs` call (line 194).

### Phase B — Engine Logic (Not Started)
Grep for `compute_masked_mse_loss` and `run_nanobrag_refinement` shows:
- Loss function still uses homoscedastic MSE
- No variance weighting (`V = bragg.detach() + sigma_rdout**2`) implemented
- No `chi_squared` telemetry field

### Phase C — Validation (Blocked by Phase B)
- DB-AT-010 (Gradcheck) will need re-run after loss change
- DB-AT-024 (Mapping) should still pass (forward pass unchanged)
- Stage A Smoke may need tolerance retuning (Chi^2 vs MSE scale shift)

## Next Steps (per input.md Do Now)

Since `input.md` only requests A1 and A2, and both are **functionally complete** in the bridge layer:

1. **Document this audit** in `plans/active/PHYSICS-LOSS-001/reports/init/audit.md` ✅
2. **Update implementation plan** to mark A1/A2/A3 as complete (with CLI caveat)
3. **File CLI integration as separate item** or quick addendum:
   - Add `--sigma-r` argument to `create_parser()`
   - Wire to `prepare_refinement_inputs(sigma_readout=...)`
   - Log warning if not provided: "No --sigma-r; using Poisson-only variance model"

## Code Pointers

- `dbex/nanobrag_bridge.py:71` — RefinementInputs.sigma_readout field
- `dbex/nanobrag_bridge.py:84` — prepare_refinement_inputs(sigma_readout=...)
- `dbex/nanobrag_bridge.py:203-214` — Sigma broadcast logic
- `dbex/nanobrag_bridge.py:232-233` — ADU→photon conversion
- `dbex/nanobrag_bridge.py:250` — Fallback to zeros if None
- `dbex/refine_one.py:187-195` — CLI call site (missing sigma_readout param)
- `tests/dbex/test_nanobrag_bridge.py:133,139,182-183,185-217` — Test coverage

## References

- `docs/spec-db-core.md:31-32` — Variance inputs requirement
- `docs/spec-db-core.md:62-64` — Variance definition (Poisson + readout)
- `docs/simtbx_api.md:27-30` — DiffBragg sigma_rdout derivation
- `plans/active/PHYSICS-LOSS-001/implementation.md:23-29` — Phase A checklist
