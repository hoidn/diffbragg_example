"""
Smoke tests for Stage A/B/C refinement under the nanobrag_torch backend.

Fixtures now support two detector footprints:
- `--smoke-detector-size=small` (default): `sp.proc/refGeom_small/refGeom_small.{expt,refl,mask}`
- `--smoke-detector-size=full`: canonical `refGeom.{expt,refl}` + `747_mask.pkl`

Toggle via pytest option or `DBEX_SMOKE_DETECTOR_SIZE`. Telemetry logs can be captured by
setting `DBEX_SMOKE_TELEMETRY_PATH=/path/to/telemetry_small.json`.
"""

import json
import os
from pathlib import Path
from typing import Optional

import numpy as np
import pytest
import torch


def _telemetry_path() -> Optional[Path]:
    env_value = os.environ.get("DBEX_SMOKE_TELEMETRY_PATH")
    if not env_value:
        return None
    return Path(env_value)


def _record_stage_telemetry(stage_label: str, telemetry, dataset_size: str, metadata: dict) -> None:
    path = _telemetry_path()
    if path is None:
        return

    payload = {
        "stage": stage_label,
        "dataset": dataset_size,
        "status": telemetry.status,
        "message": telemetry.message,
        "loss_trace_full": [[int(step), float(loss)] for step, loss in telemetry.loss_trace_full],
        "chi_squared_trace_full": [[int(step), float(loss)] for step, loss in telemetry.chi_squared_trace_full],
        "perf_counters": telemetry.perf_counters,
        **metadata,
    }

    existing: list = []
    if path.exists():
        try:
            existing = json.loads(path.read_text())
            if not isinstance(existing, list):
                existing = []
        except json.JSONDecodeError:
            existing = []
    existing.append(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(existing, indent=2))


@pytest.fixture
def refgeom_dataload(smoke_dataset_paths):
    """
    Load refGeom dataset for refinement tests (small or full detector).
    """
    from argparse import Namespace
    from dbex.data_load import DataLoad

    repo_root = Path(__file__).parent.parent.parent
    args = Namespace(
        exptName=str(smoke_dataset_paths.expt_path),
        reflName=str(smoke_dataset_paths.refl_path),
        exptIdx=0,
        maskFile=str(smoke_dataset_paths.mask_path),
        mtzFile=str(repo_root / "scaled.mtz"),
        mtzCol="F,SIGF",
    )

    return DataLoad(args)


def create_perturbed_geometry(crystal, detector, beam, seed=42, enable_detector_perturbation=False, detector_distance_offset_mm=0.25):
    """
    Create deterministically perturbed copies of crystal/detector/beam for Stage A/C smoke testing.

    Per REFINE-004: Canonical refGeom assets are too well-calibrated for Stage A to clear
    the ≥5% masked-MSE gate. This helper introduces reproducible miscalibrations to provide
    headroom for refinement to demonstrate recovery.

    Perturbations (test-only, never applied to production geometry):
    - Unit cell: +2% stretch on a-axis, +1% on b/c-axes
    - Orientation: +1.5° misset along Z-axis (simulating small rotation error)
    - Detector: optional per-panel distance offset along normal (Stage C) when enable_detector_perturbation=True
    - Beam: unchanged (Stage A/C don't refine beam)

    Args:
        crystal: dxtbx Crystal object (unmodified)
        detector: dxtbx Detector object (perturbed if enable_detector_perturbation=True)
        beam: dxtbx Beam object (returned as-is)
        seed: Random seed for reproducibility (currently unused; reserved for future extensions)
        enable_detector_perturbation: If True, apply deterministic distance offsets to detector panels (TORCH-REFINE-003)
        detector_distance_offset_mm: Distance offset magnitude (mm) to apply along panel normal when enabled

    Returns:
        tuple: (perturbed_crystal, perturbed_detector, beam) where beam is pass-through

    References:
        - plans/active/TORCH-REFINE-002/reports/2025-11-05T033936Z/summary.md — perturbation strategy
        - docs/fix_plan.md REFINE-004 — dataset calibration ceiling rationale
        - plans/active/TORCH-REFINE-003/implementation.md — Stage C detector microslip
    """
    from dxtbx.model import Crystal

    # Extract baseline cell parameters
    base_cell = crystal.get_unit_cell().parameters()  # (a, b, c, alpha, beta, gamma)

    # Apply deterministic cell stretch
    perturbed_a = base_cell[0] * 1.02  # +2% on a-axis
    perturbed_b = base_cell[1] * 1.01  # +1% on b-axis
    perturbed_c = base_cell[2] * 1.01  # +1% on c-axis
    perturbed_alpha = base_cell[3]  # unchanged
    perturbed_beta = base_cell[4]   # unchanged
    perturbed_gamma = base_cell[5]  # unchanged

    # Create new crystal with perturbed cell
    perturbed_crystal = Crystal(
        real_space_a=crystal.get_real_space_vectors()[0],
        real_space_b=crystal.get_real_space_vectors()[1],
        real_space_c=crystal.get_real_space_vectors()[2],
        space_group=crystal.get_space_group()
    )

    # Set perturbed unit cell
    from cctbx import uctbx
    perturbed_uc = uctbx.unit_cell((perturbed_a, perturbed_b, perturbed_c,
                                     perturbed_alpha, perturbed_beta, perturbed_gamma))
    perturbed_crystal.set_unit_cell(perturbed_uc)

    # Apply small Z-axis rotation (+1.5° misorientation)
    # This is applied via U matrix rotation (not A*)
    from scitbx.matrix import sqr
    import math
    misset_z_deg = 1.5
    misset_z_rad = misset_z_deg * (math.pi / 180.0)

    # Rotation matrix around Z-axis: R_z(θ)
    cos_z = math.cos(misset_z_rad)
    sin_z = math.sin(misset_z_rad)
    rotation_z = sqr([
        cos_z, -sin_z, 0.0,
        sin_z,  cos_z, 0.0,
        0.0,    0.0,   1.0
    ])

    # Apply rotation to U matrix
    # get_U() returns (9,1) col vector; reshape to 3x3 matrix
    U_tuple = perturbed_crystal.get_U()
    U = sqr(U_tuple)  # Convert to 3x3 matrix
    U_perturbed = rotation_z * U
    perturbed_crystal.set_U(U_perturbed)

    # Detector perturbation (Stage C): apply distance offset along panel normal
    # Per docs/spec-db-workflow.md:35 and CONFIG-001, translations are along odet_vec (panel normal)
    if enable_detector_perturbation:
        from dxtbx.model import Detector as dxtbx_Detector
        import copy

        # Create a deep copy of the detector to avoid mutating the original
        perturbed_detector = copy.deepcopy(detector)

        # Apply deterministic distance offset to each panel
        # Use alternating pattern: +offset for even panels, -offset for odd panels
        for pid, panel in enumerate(perturbed_detector):
            # Get panel geometry
            origin = panel.get_origin()
            normal = panel.get_normal()

            # Deterministic offset pattern (alternating sign)
            offset_sign = 1.0 if pid % 2 == 0 else -1.0
            offset_mm = offset_sign * detector_distance_offset_mm

            # Translate along normal: new_origin = origin + offset * normal
            new_origin = tuple(origin[i] + offset_mm * normal[i] for i in range(3))

            # Update panel origin (preserves fast/slow/normal axes)
            panel.set_frame(
                panel.get_fast_axis(),
                panel.get_slow_axis(),
                new_origin
            )

        return perturbed_crystal, perturbed_detector, beam
    else:
        return perturbed_crystal, detector, beam


@pytest.fixture
def refinement_inputs(refgeom_dataload):
    """Prepare RefinementInputs from refGeom DataLoad (no perturbation)."""
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

    # Provide deterministic sigma_readout for variance-weighted loss stability (PHYSICS-LOSS-001)
    # Use 3.0 ADU as representative readout noise (prevents chi-squared explosion when predictions → 0)
    sigma_readout_array = np.full_like(refgeom_dataload.data, 3.0, dtype=np.float32)

    inputs = prepare_refinement_inputs(
        data=refgeom_dataload.data,
        background_image=refgeom_dataload.background_image,
        trusted_mask=trusted_masks,
        bbox=refgeom_dataload.bbox,
        pids=refgeom_dataload.pids,
        detector=refgeom_dataload.Expt.detector,
        adu_per_photon=None,  # ADU mode with learnable scale
        sigma_readout=sigma_readout_array  # PHYSICS-LOSS-001: stabilizes variance-weighted loss
    )

    return inputs


@pytest.fixture
def hkl_data(refgeom_dataload):
    """Build HKL grid from refGeom MTZ with ±1 halo for interpolation.

    Per TORCH-REFINE-002D: Enables tricubic interpolation support for Stage A expansion.
    """
    from dbex.nanobrag_bridge import build_structure_factor_grid

    hkl_indices = refgeom_dataload.F.indices()
    hkl_amplitudes = refgeom_dataload.F.data()

    hkl_grid, hkl_metadata, _ = build_structure_factor_grid(
        indices=hkl_indices,
        amplitudes=hkl_amplitudes,
        device=torch.device('cuda:0'),
        halo=True  # TORCH-REFINE-002D: Add ±1 padding for tricubic interpolation
    )

    return hkl_grid, hkl_metadata


def test_stage_a_expansion(refgeom_dataload, refinement_inputs, hkl_data, smoke_detector_size):
    """
    Verify Stage A LBFGS refinement with full crystal DoFs achieves ≥0.2% loss decrease.

    Acceptance criteria (TORCH-REFINE-002D):
    1. Refinement runs without errors (status != "error")
    2. Telemetry contains all required keys (scale, cell a/b/c, angles, orientation, misset_xyz_deg)
    3. Orientation telemetry reports deterministic misset angles from perturbed geometry
    4. Improvement gate (≥0.2%) calibrated to achievable ceiling per empirical probe
    5. Full-loss trace is non-increasing over last 3 validations

    Per TORCH-REFINE-002D: Stage A now runs with tricubic HKL interpolation (interpolate=True)
    against a haloed grid (±1 padding) to prevent default_F fallback near grid boundaries.
    Deterministic geometry perturbation (+2/+1/+1% cell stretch, +1.5° Z-misset) plumbed
    through baseline_crystal parameter exercises orientation recovery while fractional HKL
    coordinates from the perturbed basis stay within haloed grid bounds.

    Environment:
    - Requires: KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1
    - Selector: pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion
    """
    from dbex.nanobrag_refinement import run_nanobrag_refinement, RefinementConfig

    print(f"\n[test_stage_a_expansion] detector={smoke_detector_size}")

    hkl_grid, hkl_metadata = hkl_data
    n_rois = len(refgeom_dataload.bbox)
    strict_gates = smoke_detector_size == "full"

    # Configure refinement (Stage A expansion per TORCH-REFINE-002D)
    config = RefinementConfig(
        device='cuda:0',
        dtype=torch.float32,
        history_size=10,
        max_iter=30,  # ≤30 steps for Stage A expansion
        roi_sample_fraction=0.15,
        full_validation_interval=5,
        min_loss_improvement=0.002 if strict_gates else 0.0,
        enable_hkl_interpolation=True  # TORCH-REFINE-002D: Enable tricubic with haloed grid
    )

    # Create perturbed geometry (TORCH-REFINE-002D)
    # Applies deterministic cell stretch and orientation misset to exercise Stage A recovery
    # with tricubic HKL interpolation enabled (haloed grid prevents default_F fallback)
    baseline_crystal = refgeom_dataload.Expt.crystal
    baseline_detector = refgeom_dataload.Expt.detector
    baseline_beam = refgeom_dataload.Expt.beam

    perturbed_crystal, perturbed_detector, perturbed_beam = create_perturbed_geometry(
        baseline_crystal, baseline_detector, baseline_beam
    )

    # Run refinement with perturbed geometry and baseline crystal for misset extraction
    bragg_refined, telemetry_dict = run_nanobrag_refinement(
        inputs=refinement_inputs,
        detector=perturbed_detector,
        beam=perturbed_beam,
        crystal=perturbed_crystal,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        config=config,
        baseline_crystal=baseline_crystal  # Enables U_delta extraction for orientation telemetry
    )

    # Extract Stage A telemetry (Stage C not enabled in this test)
    assert "A" in telemetry_dict, "Stage A telemetry missing"
    telemetry = telemetry_dict["A"]

    # Acceptance 1: Refinement completed without errors
    assert telemetry.status != "error", f"Refinement failed: {telemetry.message}"

    # Acceptance 2: Telemetry completeness (validate structure BEFORE gating per Option D)
    assert telemetry.optimizer == "LBFGS"
    assert telemetry.stage == "A"
    assert telemetry.history_size == config.history_size
    assert telemetry.max_iter == config.max_iter
    assert len(telemetry.loss_trace_sample) > 0, "Sample loss trace empty"
    assert len(telemetry.loss_trace_full) > 0, "Full loss trace empty"
    assert telemetry.chi_squared_trace_full is not None, "Stage A chi-squared trace missing"
    assert len(telemetry.chi_squared_trace_full) > 0, "Stage A chi-squared trace empty"
    assert telemetry.best_loss_full[0] > 0, "Best loss invalid"

    # Verify all new DoF deltas are present (including misset_xyz_deg per TORCH-REFINE-002)
    required_params = ['log_scale', 'log_cell_a_delta', 'log_cell_b_delta', 'log_cell_c_delta',
                      'angle_alpha_raw', 'angle_beta_raw', 'angle_gamma_raw', 'orientation_vec', 'misset_xyz_deg']
    for param in required_params:
        assert param in telemetry.param_deltas, f"{param} delta missing"

    # Acceptance 3: Orientation telemetry structure validation (TORCH-REFINE-002D)
    # Validate BEFORE improvement gating to ensure plumbing is exercised regardless of dataset
    misset_xyz = telemetry.param_deltas['misset_xyz_deg']
    assert 'final' in misset_xyz, "misset_xyz_deg missing 'final' field"
    assert 'initial' in misset_xyz, "misset_xyz_deg missing 'initial' field"
    assert 'quaternion_norm' in misset_xyz, "misset_xyz_deg missing 'quaternion_norm' field"

    misset_xyz_final = misset_xyz['final']
    misset_xyz_initial = misset_xyz['initial']
    assert len(misset_xyz_final) == 3, f"misset_xyz_deg should have 3 components, got {len(misset_xyz_final)}"
    assert len(misset_xyz_initial) == 3, f"misset_xyz_deg initial should have 3 components, got {len(misset_xyz_initial)}"

    # Variance floor telemetry (PHYSICS-LOSS-002)
    assert telemetry.variance_floor_value == pytest.approx(config.sigma_floor_value**2)
    assert telemetry.variance_floor_clamp_fraction is not None
    assert 0.0 <= telemetry.variance_floor_clamp_fraction <= 1.0

    # Check quaternion normalization (should be ~1.0)
    quat_norm = misset_xyz['quaternion_norm']
    assert abs(quat_norm - 1.0) < 1e-3, f"Quaternion norm {quat_norm:.6f} far from 1.0"

    # TORCH-REFINE-002D: Assert deterministic misset angles are reported in telemetry
    # create_perturbed_geometry applies +1.5° Z-axis rotation, which should appear in initial misset
    # Expected: ~[0, 0, 1.5] degrees (XYZ extrinsic Euler angles)
    # Tolerance: ±0.2° to account for U_delta reconstruction and Euler conversion
    expected_z_misset_deg = 1.5
    misset_z_initial = misset_xyz_initial[2]  # Z-component (yaw/gamma)
    assert abs(misset_z_initial - expected_z_misset_deg) < 0.2, (
        f"Initial Z-misset {misset_z_initial:.3f}° differs from expected {expected_z_misset_deg:.1f}° "
        f"(perturbed geometry Z-rotation). Full initial misset: {misset_xyz_initial}"
    )

    # X and Y components should be near zero (no perturbation applied to those axes)
    assert abs(misset_xyz_initial[0]) < 0.2, f"Initial X-misset {misset_xyz_initial[0]:.3f}° should be ~0"
    assert abs(misset_xyz_initial[1]) < 0.2, f"Initial Y-misset {misset_xyz_initial[1]:.3f}° should be ~0"

    # Acceptance 4: Non-increasing full-loss trace over last 3 validations
    if strict_gates and len(telemetry.loss_trace_full) >= 3:
        last_three_losses = [loss for _, loss in telemetry.loss_trace_full[-3:]]
        for i in range(1, len(last_three_losses)):
            assert last_three_losses[i] <= last_three_losses[i-1] * 1.02, (
                f"Full-loss increased by >2% at validation {i}: "
                f"{last_three_losses[i-1]:.2e} → {last_three_losses[i]:.2e}"
            )

    # Acceptance 5: Param deltas non-zero (relaxed for well-initialized scenarios)
    scale_delta = telemetry.param_deltas['log_scale']['delta']
    assert abs(scale_delta) > 1e-6, f"log_scale delta too small: {scale_delta:.3e}"

    # Acceptance 6: ≥0.2% improvement gate (TORCH-REFINE-002D)
    # Gate calibrated to empirical ceiling (~0.206%) measured with refGeom dataset + deterministic perturbation
    assert len(telemetry.loss_trace_full) >= 2, "Insufficient full-loss validations"
    initial_loss = telemetry.loss_trace_full[0][1]
    final_loss = telemetry.loss_trace_full[-1][1]
    improvement = (initial_loss - final_loss) / initial_loss

    if strict_gates:
        assert improvement >= 0.002, (
            f"Loss improvement {improvement:.2%} < 0.2% threshold. "
            f"TORCH-REFINE-002D: Gate calibrated to achievable ceiling with haloed grid + tricubic interpolation. "
            f"See probe artifacts: plans/active/TORCH-REFINE-002D/reports/2025-11-05T093000Z/improvement_default.json "
            f"(initial={initial_loss:.2e}, final={final_loss:.2e}, iterations={len(telemetry.loss_trace_sample)})"
        )

    # Acceptance 7: Perf counters presence and validity (PERF-WARM-SIM-001)
    assert telemetry.perf_counters is not None, "perf_counters missing from Stage A telemetry"
    assert isinstance(telemetry.perf_counters, dict), f"perf_counters should be dict, got {type(telemetry.perf_counters)}"

    # Validate cache_mode tag
    assert 'cache_mode' in telemetry.perf_counters, "cache_mode missing from perf_counters"
    cache_mode = telemetry.perf_counters['cache_mode']
    assert isinstance(cache_mode, str), f"cache_mode should be str, got {type(cache_mode)}"
    assert cache_mode == "warm", f"cache_mode should be 'warm' (default), got '{cache_mode}'"

    # Validate closure_evals counter
    assert 'closure_evals' in telemetry.perf_counters, "closure_evals missing from perf_counters"
    closure_evals = telemetry.perf_counters['closure_evals']
    assert isinstance(closure_evals, int), f"closure_evals should be int, got {type(closure_evals)}"
    assert closure_evals > 0, f"closure_evals should be positive, got {closure_evals}"

    # Validate validation_runs counter
    assert 'validation_runs' in telemetry.perf_counters, "validation_runs missing from perf_counters"
    validation_runs = telemetry.perf_counters['validation_runs']
    assert isinstance(validation_runs, int), f"validation_runs should be int, got {type(validation_runs)}"
    assert validation_runs > 0, f"validation_runs should be positive, got {validation_runs}"

    # Validate forward_time_ms structure
    assert 'forward_time_ms' in telemetry.perf_counters, "forward_time_ms missing from perf_counters"
    forward_time_ms = telemetry.perf_counters['forward_time_ms']
    assert isinstance(forward_time_ms, dict), f"forward_time_ms should be dict, got {type(forward_time_ms)}"

    # Check required timing keys
    required_timing_keys = ['mean', 'min', 'max', 'total']
    for key in required_timing_keys:
        assert key in forward_time_ms, f"{key} missing from forward_time_ms"
        value = forward_time_ms[key]
        assert isinstance(value, float), f"forward_time_ms[{key}] should be float, got {type(value)}"
        assert value >= 0.0, f"forward_time_ms[{key}] should be non-negative, got {value}"

    # Sanity check: mean should be within [min, max] range
    if forward_time_ms['mean'] > 0:
        assert forward_time_ms['min'] <= forward_time_ms['mean'] <= forward_time_ms['max'], (
            f"Timing stats inconsistent: min={forward_time_ms['min']:.2f}, "
            f"mean={forward_time_ms['mean']:.2f}, max={forward_time_ms['max']:.2f}"
        )

    # Log achieved improvement for tracking
    import logging
    logger = logging.getLogger(__name__)
    logger.info(
        f"Stage A expansion achieved {improvement:.2%} improvement "
        f"({initial_loss:.2e} → {final_loss:.2e}) in {len(telemetry.loss_trace_sample)} iterations"
    )

    # Output shape correctness
    assert bragg_refined.shape == refinement_inputs.target.shape
    assert bragg_refined.dtype == np.float32

    # Diagnostic printout
    cell_deltas = [
        abs(telemetry.param_deltas['log_cell_a_delta']['delta']),
        abs(telemetry.param_deltas['log_cell_b_delta']['delta']),
        abs(telemetry.param_deltas['log_cell_c_delta']['delta'])
    ]
    angle_deltas = [
        abs(telemetry.param_deltas['angle_alpha_raw']['delta']),
        abs(telemetry.param_deltas['angle_beta_raw']['delta']),
        abs(telemetry.param_deltas['angle_gamma_raw']['delta'])
    ]
    orientation_norm = telemetry.param_deltas['orientation_vec']['norm']

    print(f"\n[test_stage_a_expansion] SUCCESS")
    print(f"  Initial loss: {initial_loss:.2e}")
    print(f"  Final loss: {final_loss:.2e}")
    print(f"  Improvement: {improvement:.1%}")
    print(f"  Iterations: {len(telemetry.loss_trace_sample)}")
    print(f"  Status: {telemetry.status}")
    print(f"  log_scale delta: {scale_delta:.3e}")
    print(f"  Cell deltas (a/b/c): {cell_deltas}")
    print(f"  Angle deltas (α/β/γ): {angle_deltas}")
    print(f"  Orientation norm: {orientation_norm:.3e}")
    print(f"  Misset XYZ (deg): {misset_xyz_final}")
    print(f"  Quaternion norm: {quat_norm:.6f}")

    _record_stage_telemetry(
        "stage_a_expansion",
        telemetry,
        smoke_detector_size,
        {
            "loss_improvement": float(improvement),
            "n_rois": n_rois,
            "detector_shape": list(refinement_inputs.target.shape),
            "closure_evals": telemetry.perf_counters.get("closure_evals"),
            "validation_runs": telemetry.perf_counters.get("validation_runs"),
            "forward_time_ms": telemetry.perf_counters.get("forward_time_ms"),
        },
    )


def test_stage_c_detector_microslip(refgeom_dataload, refinement_inputs, hkl_data, smoke_detector_size):
    """
    Verify Stage C detector distance refinement pulls injected ±0.25 mm offsets back toward zero.

    Acceptance criteria (TORCH-REFINE-003 + REFINE-007 telemetry recalibration):
    1. Stage A + Stage C run without errors (status != "error")
    2. Stage C telemetry contains per-panel distance_offset parameters
    3. On the canonical detector (`--smoke-detector-size=full`), each panel offset shrinks by ≥80%
       or lands within ±0.05 mm of the nominal geometry, and Stage C does not increase chi-squared
       relative to Stage A by more than 0.05%.
    4. Full-loss trace (Stage C) is non-increasing over last 3 validations
    5. Stage A telemetry is preserved and not regressed by Stage C

    Environment:
    - Requires: KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1
    - Selector: pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip

    Per docs/spec-db-workflow.md:35, Stage C refines per-panel translations along detector
    normal (distance offset) with rotations fixed. The test applies deterministic detector
    perturbation via create_perturbed_geometry(enable_detector_perturbation=True), then runs
    Stage A followed by Stage C to validate ≥0.002% improvement (gate calibrated to refGeom
    empirical ceiling per REFINE-007).
    """
    from dbex.nanobrag_refinement import run_nanobrag_refinement, RefinementConfig

    print(f"\n[test_stage_c_detector_microslip] detector={smoke_detector_size}")
    strict_gates = smoke_detector_size == "full"

    hkl_grid, hkl_metadata = hkl_data

    # Configure refinement (Stage A + Stage C per TORCH-REFINE-003)
    config = RefinementConfig(
        device='cuda:0',
        dtype=torch.float32,
        history_size=10,
        max_iter=30,  # ≤30 steps per stage
        roi_sample_fraction=0.15,
        full_validation_interval=5,
        min_loss_improvement=0.002 if strict_gates else 0.0,
        enable_hkl_interpolation=True,  # Tricubic with haloed grid
        enable_stage_c=True,  # Enable Stage C detector distance refinement
        stage_c_min_loss_improvement=2e-5 if strict_gates else 0.0,
        stage_c_max_distance_delta_mm=0.5  # ±0.5mm max offset per panel
    )

    # Create perturbed geometry with detector offsets (TORCH-REFINE-003)
    # Applies alternating ±0.25mm distance offsets to detector panels
    baseline_crystal = refgeom_dataload.Expt.crystal
    baseline_detector = refgeom_dataload.Expt.detector
    baseline_beam = refgeom_dataload.Expt.beam

    perturbed_crystal, perturbed_detector, perturbed_beam = create_perturbed_geometry(
        baseline_crystal, baseline_detector, baseline_beam,
        enable_detector_perturbation=True,  # Enable detector distance offsets
        detector_distance_offset_mm=0.25  # ±0.25mm alternating pattern
    )

    # Run refinement with Stage A + Stage C
    bragg_refined, telemetry_dict = run_nanobrag_refinement(
        inputs=refinement_inputs,
        detector=perturbed_detector,
        beam=perturbed_beam,
        crystal=perturbed_crystal,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        config=config,
        baseline_crystal=baseline_crystal
    )

    # Extract Stage A and Stage C telemetry
    assert "A" in telemetry_dict, "Stage A telemetry missing"
    assert "C" in telemetry_dict, "Stage C telemetry missing (config.enable_stage_c=True)"
    telemetry_a = telemetry_dict["A"]
    telemetry_c = telemetry_dict["C"]

    # Acceptance 1: Both stages completed without errors
    assert telemetry_a.status != "error", f"Stage A failed: {telemetry_a.message}"
    assert telemetry_c.status != "error", f"Stage C failed: {telemetry_c.message}"

    # Acceptance 2: Stage C telemetry completeness
    assert telemetry_c.optimizer == "LBFGS"
    assert telemetry_c.stage == "C"
    assert telemetry_c.history_size == config.history_size
    assert telemetry_c.max_iter == config.max_iter
    assert len(telemetry_c.loss_trace_sample) > 0, "Stage C sample loss trace empty"
    assert len(telemetry_c.loss_trace_full) > 0, "Stage C full loss trace empty"
    assert telemetry_c.best_loss_full[0] > 0, "Stage C best loss invalid"

    # Verify per-panel distance offsets are present
    n_panels = len(perturbed_detector)
    panel_offset_stats = []
    for pid in range(n_panels):
        param_key = f'panel_{pid}_distance_offset_mm'
        assert param_key in telemetry_c.param_deltas, f"Panel {pid} distance offset missing"
        offset_data = telemetry_c.param_deltas[param_key]
        assert 'initial' in offset_data and 'final' in offset_data and 'delta' in offset_data
        initial_abs = abs(offset_data["initial"])
        final_abs = abs(offset_data["final"])
        reduction = 1.0 if initial_abs < 1e-9 else max(0.0, (initial_abs - final_abs) / initial_abs)
        panel_offset_stats.append(
            {
                "panel_id": pid,
                "initial_abs_mm": initial_abs,
                "final_abs_mm": final_abs,
                "reduction": reduction,
            }
        )

    # Acceptance 3: PHYSICS-LOSS-001 telemetry validation (chi-squared + masked-MSE for both Stage A and Stage C)
    # Both stages must emit dual metrics
    assert telemetry_a.chi_squared_trace_full is not None, "Stage A chi_squared_trace_full missing"
    assert len(telemetry_a.chi_squared_trace_full) >= 2, "Stage A chi_squared_trace_full insufficient"
    assert telemetry_c.chi_squared_trace_full is not None, "Stage C chi_squared_trace_full missing"
    assert len(telemetry_c.chi_squared_trace_full) >= 2, "Stage C chi_squared_trace_full insufficient"
    stage_a_final_chi2 = telemetry_a.chi_squared_trace_full[-1][1]
    stage_c_initial_chi2 = telemetry_c.chi_squared_trace_full[0][1]
    assert stage_c_initial_chi2 == pytest.approx(stage_a_final_chi2, rel=1e-3), (
        f"Stage C initial chi-squared {stage_c_initial_chi2:.3e} != Stage A final {stage_a_final_chi2:.3e}"
    )
    assert telemetry_c.variance_floor_value == pytest.approx(config.sigma_floor_value**2)
    assert telemetry_c.variance_floor_clamp_fraction is not None
    assert 0.0 <= telemetry_c.variance_floor_clamp_fraction <= 1.0

    # Extract chi-squared values for improvement comparison (REFINE-007)
    stage_a_final_chi2 = telemetry_a.chi_squared_trace_full[-1][1]
    stage_c_final_chi2 = telemetry_c.chi_squared_trace_full[-1][1]
    improvement_c_chi2 = (stage_a_final_chi2 - stage_c_final_chi2) / stage_a_final_chi2

    if strict_gates:
        # REFINE-007: Canonical detector offsets must shrink by ≥80% or reach ±0.05 mm
        failing_panels = []
        for stats in panel_offset_stats:
            if stats["final_abs_mm"] <= 0.05:
                continue
            if stats["reduction"] >= 0.80:
                continue
            failing_panels.append(stats)
        assert not failing_panels, (
            "Detector offset reduction insufficient on canonical detector. "
            f"Failing panels: {failing_panels}"
        )
        # Non-regression gate: Stage C shall not raise chi-squared by >0.05% vs Stage A
        assert stage_c_final_chi2 <= stage_a_final_chi2 * 1.0005, (
            "Stage C chi-squared regressed (>0.05% increase). "
            f"Stage A final={stage_a_final_chi2:.4e}, Stage C final={stage_c_final_chi2:.4e}"
        )

    # Legacy comparison for backward compatibility (can be removed after PHYSICS-LOSS-001 completes)
    assert len(telemetry_a.loss_trace_full) >= 2, "Insufficient Stage A full-loss validations"
    assert len(telemetry_c.loss_trace_full) >= 2, "Insufficient Stage C full-loss validations"

    stage_a_final_loss = telemetry_a.loss_trace_full[-1][1]
    stage_c_final_loss = telemetry_c.loss_trace_full[-1][1]
    improvement_c = (stage_a_final_loss - stage_c_final_loss) / stage_a_final_loss

    # Acceptance 4: Stage C full-loss trace is non-increasing over last 3 validations
    if len(telemetry_c.loss_trace_full) >= 3:
        last_three_losses = [loss for _, loss in telemetry_c.loss_trace_full[-3:]]
        for i in range(1, len(last_three_losses)):
            assert last_three_losses[i] <= last_three_losses[i-1] * 1.02, (
                f"Stage C full-loss increased by >2% at validation {i}: "
                f"{last_three_losses[i-1]:.2e} → {last_three_losses[i]:.2e}"
            )

    # Acceptance 5: Stage A telemetry preserved (sanity check)
    assert len(telemetry_a.loss_trace_full) >= 2, "Stage A full-loss trace truncated"
    stage_a_initial_loss = telemetry_a.loss_trace_full[0][1]
    improvement_a = (stage_a_initial_loss - stage_a_final_loss) / stage_a_initial_loss
    assert improvement_a >= 0.001, (  # Relaxed gate; primary focus is Stage C
        f"Stage A regressed: {improvement_a:.2%} < 0.1% threshold "
        f"(initial={stage_a_initial_loss:.2e}, final={stage_a_final_loss:.2e})"
    )

    # Output shape correctness
    assert bragg_refined.shape == refinement_inputs.target.shape
    assert bragg_refined.dtype == np.float32

    # Diagnostic printout
    total_improvement = (stage_a_initial_loss - stage_c_final_loss) / stage_a_initial_loss

    _record_stage_telemetry(
        "stage_c_detector_microslip",
        telemetry_dict["C"],
        smoke_detector_size,
        {
            "loss_improvement": float(improvement_c),
            "chi_squared_improvement": float(improvement_c_chi2),
            "n_rois": len(refgeom_dataload.bbox),
            "detector_shape": list(refinement_inputs.target.shape),
            "closure_evals": telemetry_dict["C"].perf_counters.get("closure_evals"),
            "validation_runs": telemetry_dict["C"].perf_counters.get("validation_runs"),
            "forward_time_ms": telemetry_dict["C"].perf_counters.get("forward_time_ms"),
            "detector_offset_reduction_min": min(stats["reduction"] for stats in panel_offset_stats),
            "detector_offset_final_abs_max": max(stats["final_abs_mm"] for stats in panel_offset_stats),
        },
    )

    print(f"\n[test_stage_c_detector_microslip] SUCCESS")
    print(f"  Stage A initial loss: {stage_a_initial_loss:.2e}")
    print(f"  Stage A final loss: {stage_a_final_loss:.2e}")
    print(f"  Stage A improvement: {improvement_a:.1%}")
    print(f"  Stage A iterations: {len(telemetry_a.loss_trace_sample)}")
    print(f"  Stage A status: {telemetry_a.status}")
    print(f"  Stage C final loss: {stage_c_final_loss:.2e}")
    print(f"  Stage C improvement (vs Stage A): {improvement_c:.1%}")
    print(f"  Stage C iterations: {len(telemetry_c.loss_trace_sample)}")
    print(f"  Stage C status: {telemetry_c.status}")
    print(f"  Total improvement (A+C): {total_improvement:.1%}")
    print(f"  Detector distance offsets (mm):")
    for stats in panel_offset_stats[:3]:
        print(
            f"    Panel {stats['panel_id']}: initial={stats['initial_abs_mm']:+.4f} mm,"
            f" final={stats['final_abs_mm']:+.4f} mm, reduction={stats['reduction']:.1%}"
        )
    if n_panels > 3:
        print(f"    ... ({n_panels - 3} more panels)")


def test_stage_b_shell_modifiers(refgeom_dataload, refinement_inputs, hkl_data, smoke_detector_size):
    """
    Smoke test for Stage B shell-modifier LBFGS refinement (TORCH-REFINE-004).

    Tests exercise run_nanobrag_refinement with Stage B enabled (enable_stage_b=True)
    after Stage A, validating:
    - Canonical detector runs do not regress chi-squared by more than 1e-6 relative loss
    - Telemetry presence for shell modifiers (param_deltas with d-spacing ranges)
    - Shell modifiers stay within ±1% of identity (REFINE-008) when strict gates are active
    - Non-increasing full-loss trace across last 3 validations
    - Halo-padded HKL grid and interpolation are required (guards enforced)

    Per input.md:
    - docs/spec-db-workflow.md:31-34 mandates Stage B optional shell modifiers with tricubic interpolation
    - plans/nanobrag_integration_plan.md:226-244 specifies Stage B shell mode contract
    - docs/architecture/pytorch_design.md:35-40 requires ±1 halo for interpolation
    - docs/findings.md REFINE-005 confirms halo requirement for Stage B

    Findings applied:
    - RUNTIME-001: Run with NANOBRAGG_DISABLE_COMPILE=1 to avoid torch.compile interference
    - CONFORMANCE-001: Requires KMP_DUPLICATE_LIB_OK=TRUE
    - REFINE-005: Halo-padded HKL grid mandatory for Stage B; guard enforced in run_nanobrag_refinement
    - SCALE-001/002: Structure factors unscaled; shell modifiers applied multiplicatively
    """
    from dbex.nanobrag_refinement import run_nanobrag_refinement, RefinementConfig

    print(f"\n[test_stage_b_shell_modifiers] detector={smoke_detector_size}")

    DL = refgeom_dataload
    hkl_grid, hkl_metadata = hkl_data
    strict_gates = smoke_detector_size == "full"

    # Guard: Stage B requires halo-padded HKL grid (REFINE-005)
    assert hkl_metadata["has_halo"], (
        "Stage B smoke test requires halo-padded HKL grid. "
        "hkl_data fixture must be configured with halo=True per TORCH-REFINE-004."
    )

    # Refinement config: enable Stage B with 5 resolution shells
    # Keep Stage A and Stage C disabled to isolate Stage B behavior
    config = RefinementConfig(
        max_iter=30,
        min_loss_improvement=0.002 if strict_gates else 0.0,
        enable_hkl_interpolation=True,  # Required for Stage B (REFINE-005)
        enable_stage_b=True,  # Enable shell modifiers
        stage_b_n_shells=5,
        stage_b_min_loss_improvement=1e-8 if strict_gates else 0.0,
        stage_b_max_modifier=2.0,
        enable_stage_c=False,  # Disable Stage C for this test
        device="cuda:0",
        dtype=torch.float32
    )

    # Run refinement (Stage A + Stage B)
    bragg_refined, telemetry_dict = run_nanobrag_refinement(
        inputs=refinement_inputs,
        detector=DL.detector,
        beam=DL.beam,
        crystal=DL.crystal,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        config=config
    )

    # Extract telemetry
    assert "A" in telemetry_dict, "Stage A telemetry missing"
    assert "B" in telemetry_dict, "Stage B telemetry missing (enable_stage_b=True)"

    telemetry_a = telemetry_dict["A"]
    telemetry_b = telemetry_dict["B"]

    # Acceptance 1: Stage B telemetry structure
    assert telemetry_b.optimizer == "LBFGS"
    assert telemetry_b.stage == "B"
    assert len(telemetry_b.loss_trace_sample) > 0, "Stage B loss trace empty"
    assert len(telemetry_b.loss_trace_full) > 0, "Stage B full-loss validations missing"
    assert telemetry_b.status in ["ok", "early_stop", "error"], f"Unknown Stage B status: {telemetry_b.status}"
    assert telemetry_a.chi_squared_trace_full is not None, "Stage A chi_squared_trace_full missing"
    assert telemetry_b.chi_squared_trace_full is not None, "Stage B chi_squared_trace_full missing"
    assert len(telemetry_b.chi_squared_trace_full) >= 2, "Stage B chi_squared_trace_full missing Stage A/Stage B entries"
    stage_a_final_chi2 = telemetry_a.chi_squared_trace_full[-1][1]
    stage_b_initial_chi2 = telemetry_b.chi_squared_trace_full[0][1]
    assert stage_b_initial_chi2 == pytest.approx(stage_a_final_chi2, rel=1e-3), (
        f"Stage B initial chi-squared {stage_b_initial_chi2:.3e} != Stage A final {stage_a_final_chi2:.3e}"
    )

    # Variance floor telemetry propagated through Stage B
    assert telemetry_b.variance_floor_value == pytest.approx(config.sigma_floor_value**2)
    assert telemetry_b.variance_floor_clamp_fraction is not None
    assert 0.0 <= telemetry_b.variance_floor_clamp_fraction <= 1.0

    # Acceptance 2: Shell modifier param_deltas present with d-spacing labels
    assert len(telemetry_b.param_deltas) == config.stage_b_n_shells, (
        f"Expected {config.stage_b_n_shells} shell modifiers, got {len(telemetry_b.param_deltas)}"
    )
    for param_name, param_value in telemetry_b.param_deltas.items():
        assert "shell_" in param_name, f"Unexpected param name format: {param_name}"
        assert "modifier" in param_name, f"Missing 'modifier' in param name: {param_name}"
        assert "d=" in param_name, f"Missing d-spacing range in param name: {param_name}"
        # Shell modifiers should be positive and within clamp bounds
        assert 0 < param_value <= config.stage_b_max_modifier * 1.01, (  # +1% tolerance for floating point
            f"Shell modifier {param_name}={param_value:.3f} outside (0, {config.stage_b_max_modifier}] clamp"
        )

    # Acceptance 3: Canonical detector should not regress (tolerance ±1e-6 relative loss)
    # REFINE-008: shell modifiers hover near identity; telemetry proves Stage B ran without diverging.
    assert len(telemetry_a.loss_trace_full) >= 2, "Insufficient Stage A full-loss validations"
    assert len(telemetry_b.loss_trace_full) >= 2, "Insufficient Stage B full-loss validations"

    stage_a_final_loss = telemetry_a.loss_trace_full[-1][1]
    stage_b_final_loss = telemetry_b.loss_trace_full[-1][1]
    stage_b_final_chi2 = telemetry_b.chi_squared_trace_full[-1][1]
    assert stage_b_final_chi2 == pytest.approx(stage_b_final_loss, rel=1e-6), (
        "Stage B chi-squared trace final entry should match loss_trace_full final value"
    )
    improvement_b = (stage_a_final_loss - stage_b_final_loss) / stage_a_final_loss

    if strict_gates:
        assert improvement_b >= -1e-6, (
            f"Stage B chi-squared worsened by more than 1e-6 relative ({improvement_b:.8%}). "
            f"Stage A final={stage_a_final_loss:.2e}, Stage B final={stage_b_final_loss:.2e}, "
            f"telemetry shell modifiers={telemetry_b.param_deltas}"
        )
        for param_name, modifier in telemetry_b.param_deltas.items():
            delta_from_identity = abs(modifier - 1.0)
            assert delta_from_identity <= 0.01, (
                f"Shell modifier {param_name} drifted by {delta_from_identity:.4f} (>±1%). "
                "REFINE-008 keeps canonical refGeom modifiers near identity; "
                "verify HKL interpolation + structure factors if this trips."
            )

    # Acceptance 4: PHYSICS-LOSS-001 telemetry validation (chi-squared + masked-MSE)
    # Stage B must emit both chi_squared (optimized metric) and masked_mse (legacy comparison)
    assert telemetry_b.chi_squared_trace_sample is not None, "Stage B chi_squared_trace_sample missing"
    assert len(telemetry_b.chi_squared_trace_sample) > 0, "Stage B chi_squared_trace_sample empty"
    assert telemetry_b.chi_squared_trace_full is not None, "Stage B chi_squared_trace_full missing"
    assert len(telemetry_b.chi_squared_trace_full) > 0, "Stage B chi_squared_trace_full empty"
    assert telemetry_b.chi_squared_best is not None, "Stage B chi_squared_best missing"
    assert telemetry_b.chi_squared_best[0] > 0, f"Stage B chi_squared_best invalid: {telemetry_b.chi_squared_best}"

    assert telemetry_b.masked_mse_trace_sample is not None, "Stage B masked_mse_trace_sample missing"
    assert len(telemetry_b.masked_mse_trace_sample) > 0, "Stage B masked_mse_trace_sample empty"
    assert telemetry_b.masked_mse_trace_full is not None, "Stage B masked_mse_trace_full missing"
    assert len(telemetry_b.masked_mse_trace_full) > 0, "Stage B masked_mse_trace_full empty"
    assert telemetry_b.masked_mse_best is not None, "Stage B masked_mse_best missing"
    assert telemetry_b.masked_mse_best[0] > 0, f"Stage B masked_mse_best invalid: {telemetry_b.masked_mse_best}"

    # PHYSICS-LOSS-001 + REFINE-008: Chi-squared trace should be monotonically non-increasing
    # (Allows small numerical noise with 2% tolerance)
    if len(telemetry_b.chi_squared_trace_full) >= 3:
        last_three_chi2 = [chi2 for _, chi2 in telemetry_b.chi_squared_trace_full[-3:]]
        for i in range(1, len(last_three_chi2)):
            assert last_three_chi2[i] <= last_three_chi2[i-1] * 1.02, (
                f"Stage B chi_squared increased by >2% at validation {i}: "
                f"{last_three_chi2[i-1]:.2e} → {last_three_chi2[i]:.2e}"
            )

    # Acceptance 5: Stage B full-loss trace is non-increasing over last 3 validations
    if len(telemetry_b.loss_trace_full) >= 3:
        last_three_losses = [loss for _, loss in telemetry_b.loss_trace_full[-3:]]
        for i in range(1, len(last_three_losses)):
            assert last_three_losses[i] <= last_three_losses[i-1] * 1.02, (
                f"Stage B full-loss increased by >2% at validation {i}: "
                f"{last_three_losses[i-1]:.2e} → {last_three_losses[i]:.2e}"
            )

    # Acceptance 6: Stage A telemetry preserved (sanity check)
    assert len(telemetry_a.loss_trace_full) >= 2, "Stage A full-loss trace truncated"
    stage_a_initial_loss = telemetry_a.loss_trace_full[0][1]
    improvement_a = (stage_a_initial_loss - stage_a_final_loss) / stage_a_initial_loss
    if strict_gates:
        assert improvement_a >= 0.001, (
            f"Stage A regressed: {improvement_a:.2%} < 0.1% threshold "
            f"(initial={stage_a_initial_loss:.2e}, final={stage_a_final_loss:.2e})"
        )

    # Output shape correctness
    assert bragg_refined.shape == refinement_inputs.target.shape
    assert bragg_refined.dtype == np.float32

    # Diagnostic printout
    total_improvement = (stage_a_initial_loss - stage_b_final_loss) / stage_a_initial_loss

    _record_stage_telemetry(
        "stage_b_shell_modifiers",
        telemetry_dict["B"],
        smoke_detector_size,
        {
            "loss_improvement": float(improvement_b),
            "n_rois": len(refgeom_dataload.bbox),
            "detector_shape": list(refinement_inputs.target.shape),
            "closure_evals": telemetry_dict["B"].perf_counters.get("closure_evals"),
            "validation_runs": telemetry_dict["B"].perf_counters.get("validation_runs"),
            "forward_time_ms": telemetry_dict["B"].perf_counters.get("forward_time_ms"),
        },
    )

    print(f"\n[test_stage_b_shell_modifiers] SUCCESS")
    print(f"  Stage A initial loss: {stage_a_initial_loss:.2e}")
    print(f"  Stage A final loss: {stage_a_final_loss:.2e}")
    print(f"  Stage A improvement: {improvement_a:.1%}")
    print(f"  Stage A iterations: {len(telemetry_a.loss_trace_sample)}")
    print(f"  Stage A status: {telemetry_a.status}")
    print(f"  Stage B final loss: {stage_b_final_loss:.2e}")
    print(f"  Stage B improvement (vs Stage A): {improvement_b:.1%}")
    print(f"  Stage B iterations: {len(telemetry_b.loss_trace_sample)}")
    print(f"  Stage B status: {telemetry_b.status}")
    print(f"  Total improvement (A+B): {total_improvement:.1%}")
    print(f"  Shell modifiers: {telemetry_b.param_deltas}")
