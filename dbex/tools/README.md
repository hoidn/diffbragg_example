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
