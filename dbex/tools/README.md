# dbex.tools — Reusable Tooling Modules

This package contains refactored tooling modules extracted from bin scripts for reusability and testing.

## Modules

### stage_a_adam.py

**Purpose:** Reusable utilities for Stage A mapping/orientation debug instrumentation.

**Extracted From:** `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py` (Phase D D2.1)

**Key Components:**

**Dataclasses:**
- `StageADebugConfig`: Configuration container for Stage A debug runs (device, seed, phases, optimizer settings)
- `StageAComponents`: Shared Stage A simulator components (tensors, configs, HKL grid, baseline misset)
- `ForwardModelProbeSummary`: Summary statistics for forward model probes

**Public Functions:**
- `build_dataload(repo_root)`: Construct DataLoad with canonical assets (prefers refined geometry)
- `setup_environment(seed, device_str)`: Environment lockdown and seeding (numpy, random, torch)
- `create_debug_run_dir(base_dir)`: Create timestamped debug run directory
- `write_commands_txt(out_dir, seed, argv)`: Record command line for reproducibility
- `import_stage_a_dependencies()`: Lazy-import torch and nanobrag_torch components
- `build_stage_a_components(dataload, context, *, device_str, use_u_matrix=False)`: Construct Stage A tensors/config
- `stage_a_forward(dataload, context, components, **params)`: Execute Stage A forward model
- `run_forward_model_probe(dataload, context, *, device_str, out_dir)`: Phase 1 forward model equality probe
- `run_loss_alignment_probe(dataload, context, *, device_str, out_dir)`: Phase 2 loss definition alignment probe
- `run_zero_point_check(dataload, context, *, device_str, out_dir)`: Phase 3 zero-point alignment probe
- `run_blockwise_dof_experiments(dataload, context, *, device_str, **kwargs)`: Phase 5 block-wise DoF sweeps

**Usage Example:**

```python
from pathlib import Path
from dbex.tools.stage_a_adam import (
    build_dataload,
    setup_environment,
    build_stage_a_components,
    stage_a_forward,
)
from dbex.vis import build_mapping_stage_a_context

# Setup
repo_root = Path.cwd()
seed = setup_environment(seed=42, device_str="cpu")
dataload = build_dataload(repo_root)

# Build mapping context
context = build_mapping_stage_a_context(
    dataload,
    device="cpu",
    default_sigma_readout=3.0,
)

# Build Stage A components
components = build_stage_a_components(dataload, context, device_str="cpu")

# Execute forward model with zero params
torch = components.torch
device = components.device
dtype = components.dtype

bragg_t, roi_indices, loss_t = stage_a_forward(
    dataload,
    context,
    components,
    log_scale=torch.tensor(0.0, device=device, dtype=dtype),
    log_cell_a_delta=torch.tensor(0.0, device=device, dtype=dtype),
    log_cell_b_delta=torch.tensor(0.0, device=device, dtype=dtype),
    log_cell_c_delta=torch.tensor(0.0, device=device, dtype=dtype),
    angle_alpha_raw=torch.tensor(0.0, device=device, dtype=dtype),
    angle_beta_raw=torch.tensor(0.0, device=device, dtype=dtype),
    angle_gamma_raw=torch.tensor(0.0, device=device, dtype=dtype),
    orientation_vec=torch.zeros(3, device=device, dtype=dtype),
    q_params=None,
    sigma_floor_sq_tensor=torch.tensor(9.0, device=device, dtype=dtype),
    use_mapping_zero_geometry=True,
)

print(f"Bragg shape: {bragg_t.shape}, Loss: {loss_t.item():.2f}")
```

**Applied Findings:**
- POLICY-001 (Environment Freeze): Uses existing dependencies only
- ARCH-ENGINE-002 (Lazy Imports): Implements lazy torch import pattern
- GEOMETRY-003 (B_ideal Convention): `build_stage_a_components()` applies baseline misset derivation

**CLI Reference:**

The original CLI script remains at `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py` as a thin argparse shim over this module.

**Usage:**
```bash
# Phase 1 forward model probe
python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py --phases 1 --device cpu

# CLI help
python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py --help
```

**Test Suite:** `tests/dbex/test_stage_a_adam_tooling.py` (10 tests: 4 unit, 4 integration, 2 CLI smoke)

**Limitations:**
- Requires torch and nanobrag_torch at runtime (lazy import defers loading until needed)
- Integration tests require `dbex.vis.build_mapping_stage_a_context` for full workflow validation
- Environment freeze policy: no package installation during runs

**See Also:**
- `plans/active/ARCH-REFACTOR-001/reports/2025-11-24T092000Z/phase_d_d2_planning_analysis.md` (extraction strategy)
- `plans/active/ARCH-REFACTOR-001/implementation.md` (Phase D D2 checklist)

### mapping_dataset_metrics.py

**Purpose:** Compare Stage A mapping contexts across different HKL/calibration configurations to quantify the effect of HKL source and calibration choice on ROI correlation and scale ratios.

**Extracted From:** `plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py` (ARCH-PROBE-FREEZE-001 Phase B.5)

**Key Components:**

**Available Cases:**
- `metadata_raw`: No calibration, external sigma tiles
- `metadata_calibrated`: Calibration + refined MTZ, external sigma tiles
- `cli_raw`: No calibration, CLI sigma override
- `cli_calibrated`: Calibration + refined MTZ, CLI sigma override
- `metadata_calibrated_drop_ncells`: Calibration with N_cells suppressed
- `metadata_calibrated_spot1`: Calibration with spot_scale=1.0 override
- `metadata_calibrated_spot1_drop_ncells`: Both modifications

**Public Functions:**
- `define_cases(out_dir)`: Define preset dataset cases with explicit HKL/calibration paths
- `build_dataload_for_case(case_spec, case_name)`: Build DataLoad instance for a specific case configuration
- `compute_case_metrics(case_name, case_spec, default_sigma, device, ...)`: Build mapping context and compute metrics
- `compute_diffs(base_metrics, other_metrics)`: Compute difference metrics between two cases
- `run_mapping_dataset_metrics(cases, *, out_dir, default_sigma, device, ...)`: Importable runner for programmatic invocation

**CLI Usage:**
```bash
DBEX_SMOKE_SIGMA_SOURCE=metadata \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
python -m dbex.tools.mapping_dataset_metrics \
    --cases metadata_raw metadata_calibrated \
    --emit-roi-artifacts --roi-count 16 \
    --default-sigma 3.0 --device cuda:0 \
    --out-dir plans/active/<initiative>/reports/<timestamp>/mapping_dataset_metrics
```

**Outputs:**
- `mapping_dataset_metrics.json`: Per-case metrics + pairwise diffs
- `<case_name>/roi_diagnostics/roi_*.{npz,png}`: Lowest-correlation ROI artifacts (when `--emit-roi-artifacts` is set)

**Ownership:** ARCH-PROBE-FREEZE-001 Phase B.5

**Legacy alias:** `plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py` (compatibility shim)

**Applied Findings:**
- STAGEA-001 (Calibration/Data Dependency Manifest): Uses owner APIs via `dbex.calibration.config_variants`
- SCALE-004/005 (HKL/calibration precedence): Routes dataset resolution through canonical helpers
- Diagnostic Script Policy (prompts/supervisor.md:272-309): Thin wrapper over owner modules

**See Also:**
- `dbex/calibration/config_variants.py` (calibration variant materialization helpers)
- `docs/data_dependency_manifest.md:40-140` (HKL/calibration/sigma asset resolution)
- `docs/architecture/data_telemetry_flow.md:1-180` (Stage A telemetry ownership)

### capture_smoke_calibration.py

**Purpose:** Capture smoke calibration bundles from metadata smoke datasets using DiffBragg refinement.

**Extracted From:** `plans/active/TOOLING-VIS-001/bin/capture_smoke_calibration.py` (ARCH-PROBE-FREEZE-001 Phase B.6)

**Key Components:**

**Business Logic Owner:** `dbex.calibration.smoke_capture`
- `capture_calibration_metadata()`: Execute DiffBragg macro-cycle refinement and emit calibration config JSON + manifest with SHA256 checksums
- `compute_sha256()`: Compute file checksums for manifest generation
- `to_native()`: Convert numpy/torch types to JSON-serializable native Python types

**CLI Surface:**
- `main()`: Command-line entry point exposing `--expt/--refl/--mask/--mtz/--out-config/--manifest/--refined-mtz-out/--num-macro` arguments

**Usage:**
```bash
# Full-detector smoke calibration
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
KMP_DUPLICATE_LIB_OK=TRUE \
libtbx.python -m dbex.tools.capture_smoke_calibration \
    --expt sp.proc/idx-0000_sigma_metadata.expt \
    --refl refGeom.refl \
    --mask 747_mask.pkl \
    --mtz scaled.mtz \
    --out-config sp.proc/calibration/config_torch_smoke.json \
    --refined-mtz-out sp.proc/calibration/smoke_refined_structure_factors.mtz \
    --manifest <artifacts-path>/smoke_calibration_manifest.json \
    --num-macro 3

# Small-detector smoke calibration
libtbx.python -m dbex.tools.capture_smoke_calibration \
    --expt sp.proc/refGeom_small/refGeom_small.expt \
    --refl sp.proc/refGeom_small/refGeom_small.refl \
    --mask sp.proc/refGeom_small/refGeom_small_mask.pkl \
    --mtz scaled.mtz \
    --out-config sp.proc/calibration/config_torch_smoke_small.json \
    --refined-mtz-out sp.proc/calibration/smoke_refined_structure_factors_small.mtz \
    --manifest <artifacts-path>/smoke_calibration_small_manifest.json \
    --num-macro 3
```

**Outputs:**
- Calibration config JSON (`config_torch_smoke*.json`) with `spot_scale_override`, `beam.flux`, `beam.exposure`, `beamsize_mm`, `crystal.N_cells`
- Refined structure factors MTZ (optional, via `--refined-mtz-out`)
- Manifest JSON with SHA256 checksums, generator command, git revision, input provenance

**Ownership:** ARCH-PROBE-FREEZE-001 Phase B.6

**Legacy alias:** `plans/active/TOOLING-VIS-001/bin/capture_smoke_calibration.py` (compatibility shim)

**Applied Findings:**
- STAGEA-001 (Calibration provenance): Owner modules emit DiffBragg metadata bundles
- SCALE-004 (HKL/calibration precedence): Canonical generation commands live in owner APIs
- Diagnostic Script Policy (prompts/supervisor.md:272-309): Business logic resides in `dbex.calibration`, CLI delegates

**See Also:**
- `dbex/calibration/smoke_capture.py` (business logic and helper functions)
- `docs/data_dependency_manifest.md:86-103` (refined structure factors bundle requirements)
- `docs/architecture/calibration_scaling.md` (calibration layer ownership)
