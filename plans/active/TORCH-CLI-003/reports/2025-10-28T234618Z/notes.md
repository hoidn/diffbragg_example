# TORCH-CLI-003 Implementation Notes

**Timestamp:** 2025-10-28T234618Z
**Focus:** Wire torch backend flag into CLI
**Mode:** TDD

## Context
- Current CLI (`dbex/refine_one.py`) is a script with inline execution
- Need to refactor into testable functions and add `--backend {diffbragg,nanobrag}` flag
- Default backend must remain `diffbragg` to preserve legacy behavior
- Torch path will use `nanobrag_bridge` helpers from TORCH-BRIDGE-001

## Do Now Tasks
1. **A1**: Refactor CLI into testable entry points, add `--backend` flag
2. **A2**: Wire torch dispatch path with bridge integration
3. **B1**: Add torch metrics logging (masked-MSE, ROI coverage)
4. **B2**: Update docs/index.md with backend flag documentation

## Implementation Log

### Starting State
- `dbex/refine_one.py` has argparse at module level (lines 3-27)
- Imports happen immediately at module level (lines 31-38)
- Main execution starts at line 41 (DataLoad instantiation)
- No separation between argument parsing and execution

### Progress

#### Task A1: Refactor CLI and add --backend flag (COMPLETE)
- Refactored `dbex/refine_one.py` from script-style to testable functions
- Added `create_parser()` function that returns ArgumentParser with `--backend {diffbragg,nanobrag}` flag
- Added `main(argv=None)` entry point for testability
- Moved imports inside backend functions to avoid loading heavy dependencies at module load time
- Backend flag defaults to `diffbragg` to preserve legacy behavior
- Help text verified: `python -m dbex.refine_one --help` works and shows backend flag

#### Task A2: Implement backend dispatch (COMPLETE)
- Created `run_diffbragg_backend()` function wrapping existing legacy code (no behavior change)
- Created `run_nanobrag_backend()` function that:
  - Calls `prepare_refinement_inputs()` from bridge to hydrate torch-compatible tensors
  - Generates stub Bragg tensor via `_stub_bragg_tensor()` (placeholder for real simulator)
  - Computes masked MSE for diagnostics
  - Calls `_write_torch_outputs()` to write HDF5 with torch diagnostics group
- Backend dispatch in `main()` routes to correct backend based on `args.backend`
- All 6 CLI tests pass (tests/dbex/test_refine_one_cli.py)

#### Task B1: Add torch diagnostics (COMPLETE)
- Created `_write_torch_outputs()` helper that writes standard ROI datasets plus `/torch_diagnostics` group
- Torch diagnostics group includes HDF5 attributes:
  - `masked_mse`: float, masked mean squared error
  - `loss_mask_coverage`: float, fraction of pixels in loss mask
  - `n_rois`: int, number of ROIs processed
  - `target_shape`: str, shape of target tensor
  - `backend`: str, "nanobrag"
- Logging added to CLI for torch backend: prints target shape, loss mask coverage, n_rois, masked MSE
- Test `test_torch_diagnostics_metadata()` validates all diagnostic attributes

#### Task B2: Update documentation (COMPLETE)
- Updated `docs/index.md` Status note to reflect `--backend` flag implementation
- Replaced "legacy" CLI description with current dual-backend description
- Added usage examples for both backends
- Documented torch diagnostics HDF5 group structure and attributes
- Documented required `KMP_DUPLICATE_LIB_OK=TRUE` for torch backend

### Summary

Successfully wired `--backend {diffbragg,nanobrag}` flag into `dbex.refine_one` CLI:
- Preserves `diffbragg` as default (bit-for-bit legacy behavior)
- Nanobrag backend uses bridge helpers from TORCH-BRIDGE-001
- Stub simulator generates placeholder Bragg tensors (ready for real nanobrag_torch integration)
- Torch diagnostics written to `/torch_diagnostics` HDF5 group
- All tests pass (6/6 CLI tests, 4/4 bridge tests)
- Documentation updated to reflect new backend flag and usage

### Next Actions

1. Swap stub Bragg tensor for real `nanobrag_torch` simulator when available
2. Author additional CLI smoke tests using real DIALS data (tracked in TESTING_GUIDE.md)
3. Consider adding `--device` flag for torch backend (CPU/GPU selection)
4. Plan integration tests that compare diffbragg vs nanobrag outputs for parity validation

