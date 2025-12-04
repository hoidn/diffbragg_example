# Environment State: Lorentz Scaling Patch

**Tag:** `nanobragg-lorentz-2025-12-03`

## Patch Applied

**Patch File:** `plans/active/ARCH-SIM-CONSTRUCTION-001/patches/lorentz_scaling.patch`

**Patch Location:** `/home/ollie/Documents/diffbragg_example_2/diffbragg_example/src/nanobrag-torch/src/nanobrag_torch/simulator.py`

**Changes:**
- Added stills Lorentz factor computation in `compute_physics_for_position` function
- Applied Lorentz scaling `1/sin(2θ)` after summing over phi/mosaic but before polarization
- Compute 2θ from angle between incident and diffracted beam unit vectors
- Clamped cos(2θ) to [-1+1e-6, 1-1e-6] to avoid NaN at acos boundaries
- Clamped sin(2θ) to minimum 1e-6 to avoid division by zero near beam axis
- Updated both `intensity` and `intensity_pre_polar` to include Lorentz factor
- Fully vectorized for multi-source runs

## Rebuild Command

```bash
python -m pip install -e /home/ollie/Documents/diffbragg_example_2/diffbragg_example/src/nanobrag-torch --no-deps
```

## Rationale

Prior to this patch, the simulator output `|F|²·F_latt²` but was missing the stills Lorentz factor that accounts for the geometry-dependent weighting in a stationary crystal experiment. Evidence from the physics ledger (`plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-23T150000Z/spot_profile_summary.md`) showed median Stage A/|F|²·LP = 0.0201 with LP factors ranging 2.6–11.7×, proving the simulator was missing the Lorentz boost. This patch restores the Stage A vs reference contract by applying the correct stills Lorentz weighting before polarization.

## Related Evidence

- **DB-AT-028/029:** Tests fail with chi²/pixel = 2.097e5 due to missing Lorentz factor
- **Physics Ledger:** `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-23T150000Z/spot_profile_summary.md` lines 79-117
- **Spec Reference:** §spec-db-core.md "Simulator produces physical intensity in photons"
