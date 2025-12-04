"""
Parity tests for ARCH-ENGINE-ARTIFACTS-001: Validate artifact bragg_full matches reconstruction helpers.

Per Exit Criterion #2: Stage artifacts must match helper outputs within ≤1e-6 relative MSE.

These tests prove that the artifact channel (engine.artifacts["stage_a"].bragg_full,
engine.artifacts["stage_b"].bragg_full) produces identical outputs to the legacy reconstruction
helpers (build_final_bragg_from_stage_a_telemetry, build_final_bragg_from_stage_b_telemetry)
within the specified tolerance.

Test coverage:
- test_stage_a_artifact_matches_helper: Stage A terminal (Stage B/C disabled)
- test_stage_b_artifact_matches_helper_shell_mode: Stage B terminal shell mode (Stage C disabled)

References:
- plans/active/ARCH-ENGINE-ARTIFACTS-001/implementation.md (Phase B.2)
- dbex/refinement/stage_a.py:2022-2051 (Stage A artifact emission)
- dbex/refinement/stage_b.py:1687-1730 (Stage B artifact emission)
- dbex/refinement/reconstruction.py:148-520 (reconstruction helpers)
"""

import numpy as np
import pytest
import torch

from dbex.refinement.engine import RefinementEngine
from dbex.refinement.stage_a import StageA
from dbex.refinement.stage_b import StageB
from dbex.refinement.context import build_refinement_context
from dbex.refinement.config import RefinementConfig
from dbex.refinement.reconstruction import (
    build_final_bragg_from_stage_a_telemetry,
    build_final_bragg_from_stage_b_telemetry,
)


@pytest.fixture
def refinement_inputs(refgeom_dataload, smoke_sigma_source, request):
    """Prepare RefinementInputs from refGeom DataLoad (no perturbation)."""
    from dbex.refinement.inputs import prepare_refinement_inputs
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
    if smoke_sigma_source == "metadata":
        allow_metadata = request.node.get_closest_marker("allow_metadata_sigma") is not None
        if not allow_metadata:
            pytest.skip(
                "Metadata sigma source requested but this test is not marked with "
                "@pytest.mark.allow_metadata_sigma. Add the marker to opt-in."
            )
        sigma_map = getattr(refgeom_dataload, "sigma_readout_map", None)
        sigma_map_source = getattr(refgeom_dataload, "sigma_readout_map_source", None)
        if sigma_map is None or sigma_map_source != "external_lookup":
            pytest.skip(
                "Metadata sigma source requested but DataLoad lacks an external_lookup sigma_readout_map. "
                "Ensure sp.proc/idx-0000_sigma_metadata.expt and "
                "idx-0000_sigma_metadata.sigma_tiles.pkl exist by running "
                "plans/active/PHYSICS-LOSS-001/bin/embed_sigma_external_lookup.py "
                "with --sigma-value/--sigma-map."
            )
        sigma_readout_array = np.asarray(sigma_map, dtype=np.float32)
    else:
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


@pytest.mark.allow_metadata_sigma
def test_stage_a_artifact_matches_helper(
    refgeom_dataload,
    refinement_inputs,
    hkl_data,
    smoke_detector_size,
):
    """
    Validate that Stage A artifact bragg_full matches the reconstruction helper output
    within ≤1e-6 relative MSE when Stage A is terminal (Stage B/C disabled).

    Acceptance criteria (ARCH-ENGINE-ARTIFACTS-001 Exit Criterion #2):
    1. engine.artifacts["stage_a"].bragg_full is not None (terminal stage must emit artifact)
    2. artifact shape and dtype match helper output (float32 numpy)
    3. np.allclose(artifact, helper_output, rtol=1e-6, atol=0) passes
    4. Relative MSE ≤ 1e-6

    Environment:
    - Requires: KMP_DUPLICATE_LIB_OK=TRUE DBEX_SMOKE_DETECTOR_SIZE=small
    - Selector: pytest -vv tests/dbex/test_artifact_parity.py::test_stage_a_artifact_matches_helper
    """
    print(f"\n[test_stage_a_artifact_matches_helper] detector={smoke_detector_size}")

    hkl_grid, hkl_metadata = hkl_data

    # Configure refinement: Stage A only (B/C disabled → Stage A is terminal)
    config = RefinementConfig(
        device='cuda:0',
        dtype=torch.float32,
        history_size=10,
        max_iter=30,
        roi_sample_fraction=0.15,
        full_validation_interval=5,
        enable_hkl_interpolation=True,
        enable_stage_b=False,  # Disable Stage B → Stage A is terminal
        enable_stage_c=False,  # Disable Stage C
        sigma_readout_provenance="external_lookup",
    )

    # Use baseline geometry (no perturbation needed for parity test)
    detector = refgeom_dataload.Expt.detector
    beam = refgeom_dataload.Expt.beam
    crystal = refgeom_dataload.Expt.crystal

    # Build refinement context (no job_context needed for parity tests)
    refinement_context = build_refinement_context(
        refinement_inputs=refinement_inputs,
        detector=detector,
        beam=beam,
        crystal=crystal,
        baseline_crystal=None,  # No baseline for parity test
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
    )

    # Instantiate RefinementEngine with Stage A only
    engine = RefinementEngine([StageA()], config=config)

    # Run engine
    telemetry_dict = engine.run({"context": refinement_context})

    # Extract Stage A artifact from engine
    assert "stage_a" in engine._artifacts, "Stage A artifacts missing from engine"
    stage_a_artifacts = engine._artifacts["stage_a"]
    artifact_bragg = stage_a_artifacts.bragg_full

    # Acceptance 1: Stage A artifact bragg_full should be populated when terminal
    assert artifact_bragg is not None, (
        "Stage A artifact bragg_full should be populated when terminal "
        "(enable_stage_b=False, enable_stage_c=False)"
    )

    # Call helper directly to compute expected output
    # Extract telemetry from engine (use internal _telemetry dict)
    telemetry_a = engine._telemetry["stage_a"]

    helper_bragg = build_final_bragg_from_stage_a_telemetry(
        telemetry_a=telemetry_a,
        detector=detector,
        beam=beam,
        crystal=crystal,
        inputs=refinement_inputs,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        config=config,
        device=config.device,
        dtype=config.dtype,
        stage_a_ctx=stage_a_artifacts.stage_a_ctx,  # Warm cache context from artifact
        baseline_crystal=None,
    )

    # Acceptance 2: Shape and dtype match
    assert artifact_bragg.shape == helper_bragg.shape, (
        f"Shape mismatch: artifact={artifact_bragg.shape}, helper={helper_bragg.shape}"
    )
    assert artifact_bragg.dtype == helper_bragg.dtype, (
        f"Dtype mismatch: artifact={artifact_bragg.dtype}, helper={helper_bragg.dtype}"
    )

    # Compute parity metrics
    abs_diff = np.abs(artifact_bragg - helper_bragg)
    rel_diff = abs_diff / (np.abs(helper_bragg) + 1e-10)
    max_abs = abs_diff.max()
    max_rel = rel_diff.max()
    rms_rel = np.sqrt(np.mean(rel_diff**2))

    print(f"Stage A parity: max_abs={max_abs:.3e}, max_rel={max_rel:.3e}, rms_rel={rms_rel:.3e}")

    # Acceptance 3 & 4: Relative MSE ≤ 1e-6
    assert np.allclose(artifact_bragg, helper_bragg, rtol=1e-6, atol=0), (
        f"Stage A artifact parity failed: max_rel={max_rel:.3e} exceeds 1e-6 threshold. "
        f"max_abs={max_abs:.3e}, rms_rel={rms_rel:.3e}"
    )

    print(f"[test_stage_a_artifact_matches_helper] SUCCESS - parity within tolerance")


@pytest.mark.allow_metadata_sigma
def test_stage_b_artifact_matches_helper_shell_mode(
    refgeom_dataload,
    refinement_inputs,
    hkl_data,
    smoke_detector_size,
):
    """
    Validate that Stage B artifact bragg_full matches the reconstruction helper output
    within ≤1e-6 relative MSE when Stage B is terminal (Stage C disabled) in shell mode.

    Acceptance criteria (ARCH-ENGINE-ARTIFACTS-001 Exit Criterion #2):
    1. engine.artifacts["stage_b"].bragg_full is not None (terminal stage must emit artifact)
    2. artifact shape and dtype match helper output (float32 numpy)
    3. np.allclose(artifact, helper_output, rtol=1e-6, atol=0) passes
    4. Relative MSE ≤ 1e-6

    Environment:
    - Requires: KMP_DUPLICATE_LIB_OK=TRUE DBEX_SMOKE_DETECTOR_SIZE=small
    - Selector: pytest -vv tests/dbex/test_artifact_parity.py::test_stage_b_artifact_matches_helper_shell_mode
    """
    print(f"\n[test_stage_b_artifact_matches_helper_shell_mode] detector={smoke_detector_size}")

    hkl_grid, hkl_metadata = hkl_data

    # Configure refinement: Stage A + B (C disabled → Stage B is terminal, shell mode)
    config = RefinementConfig(
        device='cuda:0',
        dtype=torch.float32,
        history_size=10,
        max_iter=30,
        roi_sample_fraction=0.15,
        full_validation_interval=5,
        enable_hkl_interpolation=True,
        enable_stage_b=True,  # Enable Stage B
        enable_stage_c=False,  # Disable Stage C → Stage B is terminal
        stage_b_n_shells=5,  # Shell mode with 5 shells
        stage_b_mode="shell",
        sigma_readout_provenance="external_lookup",
    )

    # Use baseline geometry (no perturbation needed for parity test)
    detector = refgeom_dataload.Expt.detector
    beam = refgeom_dataload.Expt.beam
    crystal = refgeom_dataload.Expt.crystal

    # Build refinement context (pass crystal as baseline_crystal for Stage B)
    refinement_context = build_refinement_context(
        refinement_inputs=refinement_inputs,
        detector=detector,
        beam=beam,
        crystal=crystal,
        baseline_crystal=crystal,  # Stage B requires baseline_crystal for cell parameter reconstruction
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
    )

    # Instantiate RefinementEngine with Stage A and B
    engine = RefinementEngine([StageA(), StageB()], config=config)

    # Run engine
    telemetry_dict = engine.run({"context": refinement_context})

    # Extract Stage B artifact from engine
    assert "stage_b" in engine._artifacts, "Stage B artifacts missing from engine"
    stage_b_artifacts = engine._artifacts["stage_b"]
    artifact_bragg = stage_b_artifacts.bragg_full

    # Acceptance 1: Stage B artifact bragg_full should be populated when terminal
    assert artifact_bragg is not None, (
        "Stage B artifact bragg_full should be populated when terminal "
        "(enable_stage_c=False)"
    )

    # Call helper directly to compute expected output
    # Extract telemetry from engine (use internal _telemetry dict)
    telemetry_a = engine._telemetry["stage_a"]
    telemetry_b = engine._telemetry["stage_b"]

    # Build reconstruction payload: merge telemetry dict with shell metadata from artifacts
    # This pattern matches stage_b.py:1698-1708
    reconstruction_payload = telemetry_b.to_dict()
    reconstruction_payload['shell_edges'] = stage_b_artifacts.shell_edges
    reconstruction_payload['shell_indices'] = stage_b_artifacts.shell_indices
    reconstruction_payload['n_shells'] = stage_b_artifacts.n_shells
    reconstruction_payload['stage_b_mode'] = stage_b_artifacts.stage_b_mode

    # Extract Stage A artifacts for helper call
    stage_a_artifacts = engine._artifacts["stage_a"]

    helper_bragg = build_final_bragg_from_stage_b_telemetry(
        telemetry_a=telemetry_a,
        telemetry_b=reconstruction_payload,
        detector=detector,
        beam=beam,
        crystal=crystal,
        baseline_crystal=crystal,  # Stage B helper also requires baseline_crystal
        inputs=refinement_inputs,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        config=config,
        device=config.device,
        dtype=config.dtype,
        use_stage_b_cpu_fallback=config.stage_b_full_eval_on_cpu,
        stage_a_ctx=stage_a_artifacts.stage_a_ctx,
    )

    # Acceptance 2: Shape and dtype match
    assert artifact_bragg.shape == helper_bragg.shape, (
        f"Shape mismatch: artifact={artifact_bragg.shape}, helper={helper_bragg.shape}"
    )
    assert artifact_bragg.dtype == helper_bragg.dtype, (
        f"Dtype mismatch: artifact={artifact_bragg.dtype}, helper={helper_bragg.dtype}"
    )

    # Compute parity metrics
    abs_diff = np.abs(artifact_bragg - helper_bragg)
    rel_diff = abs_diff / (np.abs(helper_bragg) + 1e-10)
    max_abs = abs_diff.max()
    max_rel = rel_diff.max()
    rms_rel = np.sqrt(np.mean(rel_diff**2))

    print(f"Stage B shell mode parity: max_abs={max_abs:.3e}, max_rel={max_rel:.3e}, rms_rel={rms_rel:.3e}")

    # Acceptance 3 & 4: Relative MSE ≤ 1e-6
    assert np.allclose(artifact_bragg, helper_bragg, rtol=1e-6, atol=0), (
        f"Stage B shell mode artifact parity failed: max_rel={max_rel:.3e} exceeds 1e-6 threshold. "
        f"max_abs={max_abs:.3e}, rms_rel={rms_rel:.3e}"
    )

    print(f"[test_stage_b_artifact_matches_helper_shell_mode] SUCCESS - parity within tolerance")


def test_stage_a_cached_zero_iter_bragg_matches_initial_reconstruction(
    refgeom_dataload,
    refinement_inputs,
    hkl_data,
    smoke_detector_size,
):
    """
    Validate that build_final_bragg_from_stage_a_telemetry(..., param_state="initial")
    returns the cached zero-iteration Bragg array when Stage A artifacts provide one.

    This test ensures ARCH-SIM-CONSTRUCTION-001 cache path guards the new fast-path:
    when Stage A populates stage_a_ctx.bragg_zero_iter during warm-cache baseline derivation,
    reconstruction helpers must reuse that array for param_state="initial" instead of rerunning
    simulators. This keeps bragg_before aligned with Stage A telemetry.

    Acceptance criteria:
    1. After engine.run, stage_a_ctx.bragg_zero_iter is not None (cache populated)
    2. build_final_bragg_from_stage_a_telemetry(..., param_state="initial") returns
       an array that exactly matches stage_a_ctx.bragg_zero_iter (not just close - exact copy)
    3. The cached array shape and dtype match expected [n_panels, slow, fast] float32

    Environment:
    - Requires: KMP_DUPLICATE_LIB_OK=TRUE DBEX_SMOKE_DETECTOR_SIZE=small
    - Selector: pytest -vv tests/dbex/test_artifact_parity.py::test_stage_a_cached_zero_iter_bragg_matches_initial_reconstruction

    References:
    - ARCH-SIM-CONSTRUCTION-001 (cache implementation)
    - dbex/refinement/stage_a.py:446-454 (cache population)
    - dbex/refinement/reconstruction.py:80-86 (cache reuse fast-path)
    """
    print(f"\n[test_stage_a_cached_zero_iter_bragg_matches_initial_reconstruction] detector={smoke_detector_size}")

    hkl_grid, hkl_metadata = hkl_data

    # Configure refinement: Stage A only (B/C disabled)
    config = RefinementConfig(
        device='cuda:0',
        dtype=torch.float32,
        history_size=10,
        max_iter=30,
        roi_sample_fraction=0.15,
        full_validation_interval=5,
        enable_hkl_interpolation=True,
        enable_stage_b=False,
        enable_stage_c=False,
        sigma_readout_provenance="external_lookup",
    )

    detector = refgeom_dataload.Expt.detector
    beam = refgeom_dataload.Expt.beam
    crystal = refgeom_dataload.Expt.crystal

    refinement_context = build_refinement_context(
        refinement_inputs=refinement_inputs,
        detector=detector,
        beam=beam,
        crystal=crystal,
        baseline_crystal=None,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
    )

    # Run engine to populate Stage A cache
    engine = RefinementEngine([StageA()], config=config)
    telemetry_dict = engine.run({"context": refinement_context})

    # Extract Stage A artifacts
    assert "stage_a" in engine._artifacts, "Stage A artifacts missing from engine"
    stage_a_artifacts = engine._artifacts["stage_a"]
    stage_a_ctx = stage_a_artifacts.stage_a_ctx

    # Acceptance 1: Cache should be populated after Stage A warm-cache run
    assert stage_a_ctx is not None, "Stage A context should be available in artifacts"
    assert hasattr(stage_a_ctx, 'bragg_zero_iter'), "Stage A context missing bragg_zero_iter field"
    assert stage_a_ctx.bragg_zero_iter is not None, (
        "Stage A should populate bragg_zero_iter during warm-cache baseline derivation"
    )

    # Extract cached array for comparison
    cached_bragg = stage_a_ctx.bragg_zero_iter

    # Acceptance 3: Shape and dtype should match expected [n_panels, slow, fast] float32
    n_panels = len(detector)
    panel_shape = (detector[0].get_image_size()[1], detector[0].get_image_size()[0])
    expected_shape = (n_panels, *panel_shape)
    assert cached_bragg.shape == expected_shape, (
        f"Cached bragg_zero_iter shape mismatch: got {cached_bragg.shape}, expected {expected_shape}"
    )
    assert cached_bragg.dtype == np.float32, (
        f"Cached bragg_zero_iter dtype mismatch: got {cached_bragg.dtype}, expected float32"
    )

    # Call reconstruction helper with param_state="initial"
    telemetry_a = engine._telemetry["stage_a"]
    reconstructed_bragg_initial = build_final_bragg_from_stage_a_telemetry(
        telemetry_a=telemetry_a,
        detector=detector,
        beam=beam,
        crystal=crystal,
        inputs=refinement_inputs,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        config=config,
        device=config.device,
        dtype=config.dtype,
        stage_a_ctx=stage_a_ctx,
        baseline_crystal=None,
        param_state="initial",  # Request initial state → should hit cache path
    )

    # Acceptance 2: Reconstructed array should match cached array exactly
    # (cache path returns a copy, so values should be identical)
    assert reconstructed_bragg_initial.shape == cached_bragg.shape, (
        f"Reconstructed bragg shape mismatch: got {reconstructed_bragg_initial.shape}, expected {cached_bragg.shape}"
    )
    assert reconstructed_bragg_initial.dtype == cached_bragg.dtype, (
        f"Reconstructed bragg dtype mismatch: got {reconstructed_bragg_initial.dtype}, expected {cached_bragg.dtype}"
    )
    assert np.array_equal(reconstructed_bragg_initial, cached_bragg), (
        "Reconstructed bragg for param_state='initial' should exactly match cached bragg_zero_iter. "
        f"Found discrepancy: max_abs_diff={np.abs(reconstructed_bragg_initial - cached_bragg).max():.3e}"
    )

    # Acceptance 4 (ARCH-SIM-CONSTRUCTION-001): Cached masked mean should match telemetry model_mean_masked
    # This ensures the scale factor was applied to both bragg_zero_iter and the telemetry field
    # so downstream probes/tests see the calibrated intensity
    if hasattr(stage_a_artifacts, 'telemetry') and stage_a_artifacts.telemetry is not None:
        telemetry_model_mean_masked = stage_a_artifacts.telemetry.get('model_mean_masked')
        if telemetry_model_mean_masked is not None and refinement_inputs.loss_mask is not None:
            # Compute masked mean from cached bragg using the same mask
            cached_masked_mean = float(cached_bragg[refinement_inputs.loss_mask].mean())

            # They should match within floating-point tolerance (both were scaled by the same factor)
            rel_diff = abs(cached_masked_mean - telemetry_model_mean_masked) / (abs(telemetry_model_mean_masked) + 1e-10)
            assert rel_diff < 1e-6, (
                f"Cached masked mean ({cached_masked_mean:.6e}) should match telemetry model_mean_masked "
                f"({telemetry_model_mean_masked:.6e}). Relative difference: {rel_diff:.3e}"
            )
            print(f"  Cached masked mean: {cached_masked_mean:.6e} matches telemetry: {telemetry_model_mean_masked:.6e}")

    print(f"[test_stage_a_cached_zero_iter_bragg_matches_initial_reconstruction] SUCCESS - cache path verified")
    print(f"  cached_bragg shape: {cached_bragg.shape}, mean: {cached_bragg.mean():.6e}")
    print(f"  reconstructed_bragg_initial shape: {reconstructed_bragg_initial.shape}, mean: {reconstructed_bragg_initial.mean():.6e}")
