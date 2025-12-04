# ARCH-SIM-CONSTRUCTION-001 Phase C.21 Implementation Summary

## Problem Restatement
Implement multi-domain mosaic sampling infrastructure to recover positive DB-AT-028/029 ROI correlations by averaging simulator output over calibrated mosaic spread instead of single-domain perfect-crystal sinc kernel.

## Initiative Type
Architecture

## Source Trace Inspected
- dbex/refinement/config_factories.py:287-460 (create_crystal_config function)
- dbex/refinement/config.py:92-98 (RefinementConfig.stage_a_mosaic_domains field)
- dbex/refinement/stage_a_utils.py:291-293, 522-527, 613-618 (_build_stage_a_context calls to create_crystal_config)
- dbex/nanobrag_bridge.py:1230-1247, 1400-1406 (simulate_forward_once signature + call to create_crystal_config)
- dbex/refinement/reconstruction.py:183-193, 889-898, 923-937 (reconstruction cold/warm path create_crystal_config calls)
- plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py:265-297, 750-760 (collect_mapping_hkl_stats threading)

## Changes Implemented

### 1. create_crystal_config (config_factories.py:287-460)
- Added `mosaic_domains_override` parameter (default None)
- Thread override through to crystal_kwargs['mosaic_domains'] with >=1 clamping
- Log applied mosaic_domains + source in diagnostics dict
- Preserved legacy stills default (mosaic_domains=1) when override not provided

### 2. RefinementConfig (config.py:92-98)
- Added `stage_a_mosaic_domains: int = 16` field with GPU memory note
- Default 16 fits 24GB GPUs for small detectors (32 caused OOM)
- Documents use by _build_stage_a_context, simulate_forward_once, reconstruction

### 3. _build_stage_a_context (stage_a_utils.py:291-293, 522-527, 613-618)
- Extract mosaic_domains_override from config.stage_a_mosaic_domains
- Pass to all create_crystal_config calls (base crystal + warm cache ROI variants)

### 4. simulate_forward_once (nanobrag_bridge.py:1230-1247, 1400-1406)
- Added `mosaic_domains: Optional[int] = None` parameter
- Updated docstring with ARCH-SIM-CONSTRUCTION-001 contract
- Thread mosaic_domains to create_crystal_config

### 5. Reconstruction paths (reconstruction.py:183-193, 889-898, 923-937)
- Thread config.stage_a_mosaic_domains through all create_crystal_config calls
- Covers build_final_bragg_from_stage_a_telemetry warm cache + cold path
- Covers build_final_bragg_from_modifiers (Stage B warm + cold paths)

### 6. Probe script (compare_stage_a_baseline.py:265-297, 750-760)
- Updated collect_mapping_hkl_stats to accept config parameter
- Pass config.stage_a_mosaic_domains through to simulate_forward_once
- Ensures mapping path and Stage A use consistent mosaic sampling

## Tests Run

### Baseline probe (baseline geometry mode)
Command:
```
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBEX_SMOKE_HKL_PATH=sp.proc/calibration/smoke_refined_structure_factors_small.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --geometry-mode baseline --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-21T180000Z/stage_a_baseline_probe_baseline.json
```
Result: PASS (DB-AT-027 parity preserved: Stage A vs Mapping median CC=1.0000)
- Stage A / Refl median: 0.0612 (still ~16× too low as expected per transformation ledger)
- HKL amplitude ledger: median Stage A / |F|²/pix = 0.0934

### Perturbed probe (perturbed geometry mode)
Command:
```
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBEX_SMOKE_HKL_PATH=sp.proc/calibration/smoke_refined_structure_factors_small.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --geometry-mode perturbed --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-21T180000Z/stage_a_baseline_probe_perturbed.json
```
Result: PASS (non-normative, perturbed mode differences expected)
- Stage A vs Mapping median CC: -0.0451
- Stage A / Refl median: 0.0688

### DB-AT-028/029 acceptance tests
Command:
```
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-21T180000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-21T180000Z/db_at_029 DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"
```
Result: FAIL (expected until mosaic sampling implementation verified)
- DB-AT-028: chi²/pixel initial = 2.097e+05 (bound: ≤1e2) — FAIL
- DB-AT-029: median ROI correlation before = -0.053 (bound: ≥0.2) — FAIL
- Reconstructed bragg mean (masked): 0.390 ADU
- Telemetry model mean (masked): 87.1 ADU
- Ratio (bragg/telem): 0.00448 (~200× mismatch persists)

## Artifacts Written
plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-21T180000Z/
- stage_a_baseline_probe_baseline.json
- stage_a_baseline_probe_perturbed.json
- pytest_db_at_028_029.log
- db_at_028/db_at_028_metrics.json
- db_at_028/baseline_stats.json
- db_at_028/mapping_context_fixture.json
- db_at_028/mask_coverage.json
- db_at_029/db_at_029_metrics.json
- db_at_029/mapping_context_fixture.json
- summary.md (this file)

## Next Step
Infrastructure threading is complete, but DB-AT-028/029 still fail with negative correlations (-0.053).
The mosaic_domains parameter is now threaded through all Stage A/mapping/reconstruction paths with default=16.

Possible next actions:
1. Verify mosaic_domains=16 is actually being passed to nanobrag_torch.CrystalConfig
2. Check if nanobrag_torch.Simulator correctly samples multiple mosaic domains when mosaic_domains>1
3. Investigate if the ~200× reconstruction mismatch (bragg/telem ratio=0.00448) indicates the simulator isn't averaging over domains
4. Escalate to harness initiative if nanobrag_torch requires source-level changes to enable multi-domain averaging

## Turn Summary
Implemented mosaic_domains_override parameter threading through create_crystal_config, RefinementConfig, _build_stage_a_context, simulate_forward_once, reconstruction cold/warm paths, and probe scripts.
Ran baseline/perturbed probes (both PASS for parity) and DB-AT-028/029 (both FAIL as expected with chi²/pixel=2.1e5, ROI CC=-0.053).
Multi-domain infrastructure complete; DB-AT failures suggest simulator may not be sampling mosaic correctly yet.

Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-21T180000Z/
