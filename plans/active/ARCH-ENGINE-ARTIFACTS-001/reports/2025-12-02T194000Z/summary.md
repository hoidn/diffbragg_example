# ARCH-ENGINE-ARTIFACTS-001 Phase B.2 Parity Validation — Loop Summary

## Date
2025-12-02T194000Z

## Problem
Phase B.2 parity tests (`test_stage_a_artifact_matches_helper`, `test_stage_b_artifact_matches_helper_shell_mode`) were SKIPping due to fixture loading sigma from CLI args (setting `sigma_readout_map_source = "cli_map"`) instead of from experiment file external_lookup (which should set `sigma_readout_map_source = "external_lookup"`).

## Root Cause
Static inspection revealed that `tests/conftest.py::smoke_dataset_paths` fixture was loading regular `refGeom.expt` files and passing separate `sigma_map` pickle files via CLI args when `smoke_sigma_source=="metadata"`. This caused DataLoad to set `sigma_readout_map_source = "cli_map"` instead of "external_lookup", triggering the skip condition in test line 64.

The correct behavior is to load sigma metadata experiment files (`sp.proc/idx-0000_sigma_metadata.expt`) which have sigma embedded in `imageset.external_lookup.pedestal`, and NOT pass `sigma_map` in args, so DataLoad falls through to the external_lookup loading path.

## Changes Made
1. **tests/conftest.py:89-104** — Updated `smoke_dataset_paths` fixture to load sigma metadata experiment files when `smoke_sigma_source=="metadata"`:
   - Full detector: `sp.proc/idx-0000_sigma_metadata.expt`
   - Small detector: `sp.proc/refGeom_small/idx-0000_sigma_metadata_small.expt`

2. **tests/conftest.py:117-135** — Updated sigma_map_path resolution to keep it as `None` (unless explicitly overridden via `DBEX_SMOKE_SIGMA_MAP_PATH` env var), allowing DataLoad to use external_lookup path.

3. **tests/conftest.py:76-87** — Updated docstring to document new behavior.

## Test Results
Both parity tests now PASS with perfect parity (max_rel=0.000e+00):

```
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=metadata \
DBEX_SMOKE_DETECTOR_SIZE=full \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_artifact_parity.py --tb=short
```

**Results:**
- `test_stage_a_artifact_matches_helper` → PASSED (max_abs=0.000e+00, max_rel=0.000e+00, rms_rel=0.000e+00)
- `test_stage_b_artifact_matches_helper_shell_mode` → PASSED (max_abs=0.000e+00, max_rel=0.000e+00, rms_rel=0.000e+00)

Both tests executed (no SKIP) because `sigma_readout_map_source` correctly set to "external_lookup".

## Artifacts
- `pytest_parity_retry.log` — Full test run with both tests PASSED
- `pytest_stage_a_verbose.log` — Stage A verbose output showing parity metrics
- `summary.md` — This file

## Spec Conformance
- **docs/spec-db-workflow.md §§33-45** — Engine artifact contract validated
- **docs/spec-db-core.md §§57-68, 85-90** — Variance/loss and HKL tensor contracts honored
- **ARCH-ENGINE-ARTIFACTS-001 Exit Criterion #2** — Stage A/B artifacts match reconstruction helpers within ≤1e-6 relative MSE ✓

## Next Steps
Phase B.2 is now complete with perfect parity validation. Next: Phase B.3 (validate Stage C artifact emission or confirm already handled per implementation.md).

## Initiative Type
architecture (harness bugfix to enable parity validation)

## Mode
TDD
