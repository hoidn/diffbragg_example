"""Architecture enforcement tests for Stage A vs reconstruction scaling parity.

ARCH-IMPL-CONFORMANCE-001 — Phase A.1 Nucleus Test

This module establishes baseline detection of scaling/calibration contract violations
between Stage A warm-cache path and reconstruction cold path.

Test Scope:
- test_stage_a_vs_reconstruction_scale: Enforces ARCH-CONTRACT-001 (Stage A vs reconstruction parity)

Design Reference:
- plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T200000Z/nucleus_test_design.md

Findings Applied:
- SCALE-008 (docs/findings.md:322-339): Stage A warm-cache baseline authority
- SCALE-009 (docs/findings.md:341-358): Reconstruction scaling provenance
- ARCH-FACTORY-001 (docs/findings.md:360-377): Unified simulator factory responsibilities
"""

import numpy as np
import pytest


def test_stage_a_vs_reconstruction_scale(refgeom_dataload):
    """Enforce ARCH-CONTRACT-001: Stage A vs reconstruction scaling parity.

    This test validates that Stage A warm-cache forward path and reconstruction
    helper cold path produce identical masked-mean outputs when given:
    - Identical geometry (detector, beam, crystal from dxtbx Experiments)
    - Identical calibration metadata (spot_scale_override, beam calibration)
    - param_state="initial" (zero refinement deltas)

    Expected Outcome (Phase A.1):
        FAIL - exposes current mismatch due to duplicated scaling logic

    Success Criteria (Phase B):
        PASS - after canonical API implementation eliminates duplicates

    Tolerance:
        1e-6 relative error (per docs/spec-db-core.md:60-140)

    Fixture:
        refgeom_dataload - loads refGeom_small with calibration metadata

    Contract References:
        - dbex/refinement/stage_a.py:442-443 (Stage A sqrt scaling pattern)
        - dbex/refinement/reconstruction.py:167-223 (reconstruction cold path duplicates)
        - dbex/refinement/stage_a_utils.py:267 (beam calibration threading)
    """
    import torch
    from dbex.vis.mapping import build_mapping_stage_a_context
    from dbex.refinement.reconstruction import build_final_bragg_from_stage_a_telemetry
    from dbex.nanobrag_bridge import build_structure_factor_grid

    # Use fixture-provided DataLoad
    dataload = refgeom_dataload

    # Extract geometry and masks
    detector = dataload.detector
    beam = dataload.beam
    crystal = dataload.crystal
    trusted_mask = dataload.trusted_mask  # np.ndarray, shape [n_panels, slow, fast], True=trusted

    # Build Stage A context (warm-cache path with sqrt scaling applied)
    stage_a_ctx = build_mapping_stage_a_context(
        dataload,
        default_sigma_readout=3.0,
        device="cpu",
        apply_calibration_n_cells=True,
    )

    # Extract Stage A outputs
    bragg_stage_a = stage_a_ctx.bragg_zero_iter  # np.ndarray, shape [n_panels, slow, fast]
    inputs = stage_a_ctx.inputs  # RefinementInputs with panel_slices, trusted_mask

    # Compute masked mean for Stage A (use inputs.loss_mask per spec-db-core.md:55 and ARCH-IMPL-CONFORMANCE-001 Phase B.8)
    # loss_mask = (background >= 0) & trusted_mask (ROI pixels only, matching mapping.py:287-288 contract)
    loss_mask = inputs.loss_mask
    masked_sum_stage_a = (bragg_stage_a[loss_mask]).sum()
    masked_count_stage_a = loss_mask.sum()
    masked_mean_stage_a = masked_sum_stage_a / masked_count_stage_a

    # Build reconstruction path (cold path, param_state="initial" forces zero deltas)
    # This should return the cached zero-iteration Bragg stack when param_state="initial"
    # and stage_a_ctx is provided (per ARCH-SIM-CONSTRUCTION-001 Phase C.8).
    # However, if reconstruction applies calibration differently or duplicates scaling logic,
    # the masked mean may diverge.

    # Reconstruction requires telemetry, so we need to simulate Stage A telemetry.
    # For param_state="initial", we expect zero deltas, so construct minimal telemetry.
    from collections import namedtuple
    RefinementTelemetry = namedtuple('RefinementTelemetry', ['param_deltas'])
    zero_deltas = {
        'log_scale': {'initial': 0.0, 'final': 0.0},
        'log_cell_a_delta': {'initial': 0.0, 'final': 0.0},
        'log_cell_b_delta': {'initial': 0.0, 'final': 0.0},
        'log_cell_c_delta': {'initial': 0.0, 'final': 0.0},
        'angle_alpha_raw': {'initial': 0.0, 'final': 0.0},
        'angle_beta_raw': {'initial': 0.0, 'final': 0.0},
        'angle_gamma_raw': {'initial': 0.0, 'final': 0.0},
        'misset_xyz_deg': {'initial': [0.0, 0.0, 0.0], 'delta': [0.0, 0.0, 0.0]},
    }
    telemetry_initial = RefinementTelemetry(param_deltas=zero_deltas)

    # Build HKL grid for reconstruction (same process as in test_artifact_parity.py)
    hkl_indices = dataload.F.indices()
    hkl_amplitudes = dataload.F.data()

    hkl_grid, hkl_metadata, _ = build_structure_factor_grid(
        indices=hkl_indices,
        amplitudes=hkl_amplitudes,
        device=torch.device('cpu'),
        halo=True  # TORCH-REFINE-002D: Add ±1 padding for tricubic interpolation
    )

    # RefinementInputs doesn't have a config attribute; we need to create a minimal config
    # ARCH-IMPL-CONFORMANCE-001 Phase B.5: thread calibration_metadata
    from dbex.refinement.config import RefinementConfig
    config = RefinementConfig(
        device="cpu",
        dtype=torch.float32,
        calibration_metadata=stage_a_ctx.calibration,
    )

    bragg_reconstruction = build_final_bragg_from_stage_a_telemetry(
        telemetry_a=telemetry_initial,
        detector=detector,
        beam=beam,
        crystal=crystal,
        inputs=inputs,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        config=config,
        device="cpu",
        dtype=config.dtype if hasattr(config, 'dtype') else None,
        stage_a_ctx=stage_a_ctx,
        baseline_crystal=None,
        param_state="initial",
    )

    # Compute masked mean for reconstruction (use same loss_mask as Stage A measurement)
    masked_sum_reconstruction = (bragg_reconstruction[loss_mask]).sum()
    masked_count_reconstruction = loss_mask.sum()
    masked_mean_reconstruction = masked_sum_reconstruction / masked_count_reconstruction

    # Compute relative error
    rel_error = abs(masked_mean_stage_a - masked_mean_reconstruction) / masked_mean_stage_a
    ratio = masked_mean_stage_a / masked_mean_reconstruction if masked_mean_reconstruction != 0 else np.inf

    # Print metrics for baseline documentation
    print(f"\n[ARCH-IMPL-CONFORMANCE-001 A.1 Baseline Metrics]")
    print(f"  masked_mean_stage_a      = {masked_mean_stage_a:.6e}")
    print(f"  masked_mean_reconstruction = {masked_mean_reconstruction:.6e}")
    print(f"  rel_error                 = {rel_error:.6e}")
    print(f"  ratio (stage_a/reconstruction) = {ratio:.6f}")

    # Assertion with 1e-6 tolerance (per docs/spec-db-core.md:60-140)
    assert rel_error <= 1e-6, (
        f"Stage A vs reconstruction masked mean mismatch: "
        f"stage_a={masked_mean_stage_a:.6e}, "
        f"reconstruction={masked_mean_reconstruction:.6e}, "
        f"rel_error={rel_error:.6e} (tolerance=1e-6)"
    )


def test_stage_a_vs_reconstruction_scale_cold_path(refgeom_dataload):
    """Enforce ARCH-CONTRACT-001 for reconstruction cold path (no cache).

    This test validates that reconstruction cold path (stage_a_ctx=None)
    produces masked_mean outputs matching Stage A warm-cache path when
    given identical geometry, calibration metadata, and param_state="initial".

    Expected outcome (Phase A.2): FAIL - exposes duplicated scaling logic drift
    Success criteria (Phase B): PASS - after canonical scaling_utils refactor

    Difference from test_stage_a_vs_reconstruction_scale:
        - Calls build_final_bragg_from_stage_a_telemetry with stage_a_ctx=None
        - Forces reconstruction to rebuild from scratch (no cache optimization)
        - Exposes whether cold path duplicates/drifts from Stage A scaling logic

    Tolerance:
        1e-6 relative error (per docs/spec-db-core.md:60-140)

    Fixture:
        refgeom_dataload - loads refGeom_small with calibration metadata

    Contract References:
        - dbex/refinement/stage_a.py:442-443 (Stage A sqrt scaling pattern)
        - dbex/refinement/reconstruction.py:88-223 (cold path duplicated logic)
        - dbex/refinement/stage_a_utils.py:267 (beam calibration threading)
    """
    import torch
    from dbex.vis.mapping import build_mapping_stage_a_context
    from dbex.refinement.reconstruction import build_final_bragg_from_stage_a_telemetry
    from dbex.nanobrag_bridge import build_structure_factor_grid

    # Use fixture-provided DataLoad
    dataload = refgeom_dataload

    # Extract geometry and masks
    detector = dataload.detector
    beam = dataload.beam
    crystal = dataload.crystal
    trusted_mask = dataload.trusted_mask  # np.ndarray, shape [n_panels, slow, fast], True=trusted

    # Build Stage A context (warm-cache path) to get baseline masked_mean
    stage_a_ctx = build_mapping_stage_a_context(
        dataload,
        default_sigma_readout=3.0,
        device="cpu",
        apply_calibration_n_cells=True,
    )

    # Extract Stage A outputs
    bragg_stage_a = stage_a_ctx.bragg_zero_iter  # np.ndarray, shape [n_panels, slow, fast]
    inputs = stage_a_ctx.inputs  # RefinementInputs with panel_slices, trusted_mask

    # Compute masked mean for Stage A (use inputs.loss_mask per spec-db-core.md:55 and ARCH-IMPL-CONFORMANCE-001 Phase B.8)
    # loss_mask = (background >= 0) & trusted_mask (ROI pixels only, matching mapping.py:287-288 contract)
    loss_mask = inputs.loss_mask
    masked_sum_stage_a = (bragg_stage_a[loss_mask]).sum()
    masked_count_stage_a = loss_mask.sum()
    masked_mean_stage_a = masked_sum_stage_a / masked_count_stage_a

    # Build cold-path reconstruction: force stage_a_ctx=None to bypass cache
    # This forces reconstruction to rebuild simulators from scratch (lines 88-223)
    # instead of returning cached bragg_zero_iter (lines 83-86).

    # Construct minimal telemetry with zero deltas for param_state="initial"
    from collections import namedtuple
    RefinementTelemetry = namedtuple('RefinementTelemetry', ['param_deltas'])
    zero_deltas = {
        'log_scale': {'initial': 0.0, 'final': 0.0},
        'log_cell_a_delta': {'initial': 0.0, 'final': 0.0},
        'log_cell_b_delta': {'initial': 0.0, 'final': 0.0},
        'log_cell_c_delta': {'initial': 0.0, 'final': 0.0},
        'angle_alpha_raw': {'initial': 0.0, 'final': 0.0},
        'angle_beta_raw': {'initial': 0.0, 'final': 0.0},
        'angle_gamma_raw': {'initial': 0.0, 'final': 0.0},
        'misset_xyz_deg': {'initial': [0.0, 0.0, 0.0], 'delta': [0.0, 0.0, 0.0]},
    }
    telemetry_initial = RefinementTelemetry(param_deltas=zero_deltas)

    # Build HKL grid for reconstruction using SAME HKL data as Stage A context
    # ARCH-IMPL-CONFORMANCE-001 Phase B.5: Stage A may use refined structure factors;
    # cold path must match to ensure parity
    hkl_indices = stage_a_ctx.hkl_indices
    hkl_amplitudes = stage_a_ctx.hkl_amplitudes

    hkl_grid, hkl_metadata, _ = build_structure_factor_grid(
        indices=hkl_indices,
        amplitudes=hkl_amplitudes,
        device=torch.device('cpu'),
        halo=True  # TORCH-REFINE-002D: Add ±1 padding for tricubic interpolation
    )

    # Create minimal config with calibration_metadata from Stage A context
    # ARCH-IMPL-CONFORMANCE-001 Phase B.5: thread calibration_metadata to cold path
    # so apply_sqrt_spot_scale receives correct spot_scale_override value
    from dbex.refinement.config import RefinementConfig
    config = RefinementConfig(
        device="cpu",
        dtype=torch.float32,
        calibration_metadata=stage_a_ctx.calibration,  # CRITICAL: pass calibration from Stage A
    )

    # CRITICAL: Set stage_a_ctx=None to force cold-path reconstruction
    # This bypasses the cache optimization (reconstruction.py:83-86)
    # and exercises the cold-path simulator construction (lines 88-223)
    bragg_reconstruction_cold = build_final_bragg_from_stage_a_telemetry(
        telemetry_a=telemetry_initial,
        detector=detector,
        beam=beam,
        crystal=crystal,
        inputs=inputs,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        config=config,
        device="cpu",
        dtype=config.dtype if hasattr(config, 'dtype') else None,
        stage_a_ctx=None,  # CRITICAL: bypass cache, force cold path
        baseline_crystal=None,
        param_state="initial",
    )

    # Compute masked mean for cold-path reconstruction (use same loss_mask as Stage A measurement)
    masked_sum_reconstruction_cold = (bragg_reconstruction_cold[loss_mask]).sum()
    masked_count_reconstruction_cold = loss_mask.sum()
    masked_mean_reconstruction_cold = masked_sum_reconstruction_cold / masked_count_reconstruction_cold

    # Compute relative error
    rel_error = abs(masked_mean_stage_a - masked_mean_reconstruction_cold) / masked_mean_stage_a
    ratio = masked_mean_stage_a / masked_mean_reconstruction_cold if masked_mean_reconstruction_cold != 0 else np.inf

    # Print metrics for baseline documentation
    print(f"\n[ARCH-IMPL-CONFORMANCE-001 A.2 Cold-Path Baseline Metrics]")
    print(f"  masked_mean_stage_a            = {masked_mean_stage_a:.6e}")
    print(f"  masked_mean_reconstruction_cold = {masked_mean_reconstruction_cold:.6e}")
    print(f"  rel_error                       = {rel_error:.6e}")
    print(f"  ratio (stage_a/reconstruction_cold) = {ratio:.6f}")

    # Assertion with 1e-6 tolerance (per docs/spec-db-core.md:60-140)
    # Expected outcome: FAIL (drift > 1e-6) exposes duplicated scaling logic in cold path
    assert rel_error <= 1e-6, (
        f"Cold-path drift: stage_a={masked_mean_stage_a:.6e}, "
        f"reconstruction_cold={masked_mean_reconstruction_cold:.6e}, "
        f"rel_error={rel_error:.6e} (tolerance=1e-6)"
    )
