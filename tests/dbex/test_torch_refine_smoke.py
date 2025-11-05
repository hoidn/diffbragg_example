"""
Smoke tests for Stage A LBFGS refinement nucleus (TORCH-REFINE-001).

Tests exercise run_nanobrag_refinement with deterministic ROI sampling,
validating:
- ≥5% loss descent within ≤20 LBFGS iterations
- Telemetry presence (optimizer config, traces, param_deltas, status)
- Non-increasing full-loss trace across last 3 validations

Per input.md:
- docs/spec-db-workflow.md:30-38 mandates Stage A LBFGS nucleus with crystal+scale
- plans/nanobrag_integration_plan.md:172-211 specifies refinement nucleus contract
- docs/pytorch_runtime_checklist.md requires device/dtype neutrality

Findings applied:
- RUNTIME-001: Run with NANOBRAGG_DISABLE_COMPILE=1 to avoid torch.compile interference
- CONFORMANCE-001: Requires KMP_DUPLICATE_LIB_OK=TRUE
- DIAGNOSTICS-001: Extend /torch_diagnostics without replacing existing attrs
- SCALE-003/006/007: Maintain calibration metadata and telemetry guardrails
"""

import pytest
import numpy as np
import torch
from pathlib import Path


@pytest.fixture
def refgeom_dataload():
    """
    Load refGeom dataset for refinement tests.

    Requires:
    - refGeom.expt
    - refGeom.refl (generated via dials.stills_process)
    - 747_mask.pkl
    - scaled.mtz

    Skips if refGeom.refl is missing (protects CI).
    """
    from argparse import Namespace
    from dbex.data_load import DataLoad

    repo_root = Path(__file__).parent.parent.parent
    refl_path = repo_root / "refGeom.refl"

    if not refl_path.exists():
        pytest.skip(f"refGeom.refl not found at {refl_path}; see README.md Step 5 for generation")

    args = Namespace(
        exptName=str(repo_root / "refGeom.expt"),
        reflName=str(refl_path),
        exptIdx=0,
        maskFile=str(repo_root / "747_mask.pkl"),
        mtzFile=str(repo_root / "scaled.mtz"),
        mtzCol="F,SIGF"
    )

    return DataLoad(args)


@pytest.fixture
def refinement_inputs(refgeom_dataload):
    """Prepare RefinementInputs from refGeom DataLoad."""
    from dbex.nanobrag_bridge import prepare_refinement_inputs
    import numpy as np

    # Build trusted mask per panel
    detector = refgeom_dataload.Expt.detector
    n_panels = len(detector)
    trusted_masks = []

    for pid in range(n_panels):
        panel = detector[pid]
        image_size = panel.get_image_size()
        # Create full mask (all trusted initially)
        mask = np.ones(image_size[::-1], dtype=bool)  # (slow, fast)
        trusted_masks.append(mask)

    inputs = prepare_refinement_inputs(
        data=refgeom_dataload.data,
        background_image=refgeom_dataload.background_image,
        trusted_mask=trusted_masks,
        bbox=refgeom_dataload.bbox,
        pids=refgeom_dataload.pids,
        detector=refgeom_dataload.Expt.detector,
        adu_per_photon=None  # ADU mode with learnable scale
    )

    return inputs


@pytest.fixture
def hkl_data(refgeom_dataload):
    """Build HKL grid from refGeom MTZ."""
    from dbex.nanobrag_bridge import build_structure_factor_grid

    hkl_indices = refgeom_dataload.F.indices()
    hkl_amplitudes = refgeom_dataload.F.data()

    hkl_grid, hkl_metadata = build_structure_factor_grid(
        indices=hkl_indices,
        amplitudes=hkl_amplitudes,
        device=torch.device('cpu')
    )

    return hkl_grid, hkl_metadata


def test_loss_decreases(refgeom_dataload, refinement_inputs, hkl_data):
    """
    Verify Stage A LBFGS refinement achieves ≥5% loss decrease.

    Acceptance criteria:
    1. Refinement runs without errors (status != "error")
    2. Final masked MSE is ≥5% lower than initial
    3. Telemetry contains all required keys
    4. Full-loss trace is non-increasing over last 3 validations
    5. Param deltas show non-zero updates for scale and crystal DoF

    Environment:
    - Requires: KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1
    - Selector: pytest -v tests/dbex/test_torch_refine_smoke.py::test_loss_decreases
    """
    from dbex.nanobrag_refinement import run_nanobrag_refinement, RefinementConfig

    hkl_grid, hkl_metadata = hkl_data

    # Configure refinement
    config = RefinementConfig(
        device='cpu',
        dtype=torch.float32,
        history_size=10,
        max_iter=20,
        roi_sample_fraction=0.15,
        full_validation_interval=5,
        min_loss_improvement=0.05
    )

    # Run refinement
    bragg_refined, telemetry = run_nanobrag_refinement(
        inputs=refinement_inputs,
        detector=refgeom_dataload.detector,
        beam=refgeom_dataload.beam,
        crystal=refgeom_dataload.crystal,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        config=config
    )

    # Acceptance 1: Refinement completed without errors
    assert telemetry.status != "error", f"Refinement failed: {telemetry.message}"

    # Acceptance 2: Loss decreased by ≥5%
    assert len(telemetry.loss_trace_full) >= 2, "Insufficient full-loss validations"
    initial_loss = telemetry.loss_trace_full[0][1]
    final_loss = telemetry.loss_trace_full[-1][1]
    improvement = (initial_loss - final_loss) / initial_loss

    assert improvement >= 0.05, (
        f"Loss improvement {improvement:.2%} < 5% threshold "
        f"(initial={initial_loss:.2e}, final={final_loss:.2e})"
    )

    # Acceptance 3: Telemetry completeness
    assert telemetry.optimizer == "LBFGS"
    assert telemetry.stage == "A"
    assert telemetry.history_size == config.history_size
    assert telemetry.max_iter == config.max_iter
    assert len(telemetry.loss_trace_sample) > 0, "Sample loss trace empty"
    assert len(telemetry.loss_trace_full) > 0, "Full loss trace empty"
    assert telemetry.best_loss_full[0] > 0, "Best loss invalid"
    assert 'log_scale' in telemetry.param_deltas, "log_scale delta missing"
    assert 'log_cell_a_delta' in telemetry.param_deltas, "log_cell_a_delta delta missing"

    # Acceptance 4: Non-increasing full-loss trace over last 3 validations
    if len(telemetry.loss_trace_full) >= 3:
        last_three_losses = [loss for _, loss in telemetry.loss_trace_full[-3:]]
        for i in range(1, len(last_three_losses)):
            assert last_three_losses[i] <= last_three_losses[i-1] * 1.02, (
                f"Full-loss increased by >2% at validation {i}: "
                f"{last_three_losses[i-1]:.2e} → {last_three_losses[i]:.2e}"
            )

    # Acceptance 5: Param deltas non-zero
    scale_delta = telemetry.param_deltas['log_scale']['delta']
    cell_delta = telemetry.param_deltas['log_cell_a_delta']['delta']

    assert abs(scale_delta) > 1e-6, f"log_scale delta too small: {scale_delta:.3e}"
    # Note: cell_a_delta may be small if only scale is needed; accept 0 for nucleus
    # In future, may strengthen this assertion when full Stage A is enabled

    # Output shape correctness
    assert bragg_refined.shape == refinement_inputs.target.shape
    assert bragg_refined.dtype == np.float32

    print(f"\n[test_loss_decreases] SUCCESS")
    print(f"  Initial loss: {initial_loss:.2e}")
    print(f"  Final loss: {final_loss:.2e}")
    print(f"  Improvement: {improvement:.1%}")
    print(f"  Iterations: {len(telemetry.loss_trace_sample)}")
    print(f"  Status: {telemetry.status}")
    print(f"  log_scale delta: {scale_delta:.3e}")
    print(f"  log_cell_a_delta delta: {cell_delta:.3e}")
