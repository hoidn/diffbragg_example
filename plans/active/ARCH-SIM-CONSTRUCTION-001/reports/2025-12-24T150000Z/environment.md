# Environment Tag: nanobrag-lorentz-2025-12-24

## Summary
Removed debug print statement from Lorentz factor implementation in nanobrag_torch simulator.

## Patch Details
- **Patch file**: `plans/active/ARCH-SIM-CONSTRUCTION-001/patches/lorentz_scaling.patch`
- **Modified file**: `src/nanobrag-torch/src/nanobrag_torch/simulator.py`
- **Change type**: Debug cleanup (removed 3 lines of debug print)
- **Physics change**: None (Lorentz factor implementation unchanged, only removed diagnostic print)

## Rebuild Command
```bash
python -m pip install -e src/nanobrag-torch
```

## Rebuild Output
Successfully rebuilt nanobrag_torch 0.1.0 editable install at 2025-12-24T150000Z

## Environment State
- **Python**: 3.9
- **PyTorch**: Installed via conda
- **nanobrag_torch**: 0.1.0 (editable install from src/nanobrag-torch)
- **Git submodule**: src/nanobrag-torch HEAD detached at 28726af5

## Validation Plan
The Lorentz factor `1/sin(2θ)` is already implemented in simulator.py (lines 367-403). This change only removes the debug print statement that was logging Lorentz factor statistics. The implementation:
1. Computes normalized incident and diffracted beam vectors
2. Computes cos(2θ) with clamping to avoid NaN at acos boundaries
3. Computes 2θ = acos(cos(2θ))
4. Computes Lorentz factor = 1/sin(2θ) with clamping to avoid division by zero
5. Applies Lorentz scaling to intensity before polarization

This matches the specification in input.md line 13: "Multiply both `intensity_pre_polar` and `intensity` by the stills Lorentz term `1/sin(2θ)` right after the phi/mosaic sum but before polarization."
