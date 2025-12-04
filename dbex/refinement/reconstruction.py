"""
Shared final Bragg reconstruction helpers (ARCH-STAGE-CONTEXT-001 Phase D).

This module exports the helpers previously defined in `dbex/nanobrag_refinement.py`
so that both stage wrappers (StageA.run, StageB.run) and the engine path can import
them without touching the monolith.

Provides:
- build_final_bragg_from_stage_a_telemetry: Final Bragg reconstruction from Stage A telemetry
- build_final_bragg_from_stage_b_telemetry: Final Bragg reconstruction from Stage B telemetry

Per ARCH-STAGE-CONTEXT-001 Phase D:
- These helpers remain device/dtype neutral
- Stage A/B wrappers call them when they are the terminal stage
- run_nanobrag_refinement uses them as fallbacks when artifacts are unavailable

References:
- docs/spec-db-workflow.md §33 (engine artifact channel)
- ARCH-STAGE-CONTEXT-001 (artifact propagation)
- ARCH-ENGINE-ARTIFACTS-001 (final Bragg unification)
"""

import hashlib
import numpy as np
import torch
from typing import Any, Dict, Optional


def build_final_bragg_from_stage_a_telemetry(
    telemetry_a,
    detector,
    beam,
    crystal,
    inputs,
    hkl_grid,
    hkl_metadata,
    config,
    device,
    dtype,
    stage_a_ctx=None,
    baseline_crystal=None,
    param_state="final",
):
    """
    Build final Bragg array from Stage A telemetry (optimized crystal/scale params).

    Extracts Stage A parameters from telemetry and regenerates full Bragg image.

    Args:
        telemetry_a: RefinementTelemetry instance with Stage A optimized param_deltas
        detector: dxtbx Detector object
        beam: dxtbx Beam object
        crystal: dxtbx Crystal object
        inputs: RefinementInputs with panel_slices, trusted_mask
        hkl_grid: torch.Tensor structure factor grid
        hkl_metadata: dict with grid dimensions
        config: RefinementConfig with device, dtype
        device: torch.device for tensor operations
        dtype: torch.dtype for tensor operations
        stage_a_ctx: Optional Stage A context (detectors/simulators for warm cache)
        baseline_crystal: Optional baseline dxtbx Crystal for misset extraction
        param_state: str, "initial" or "final" - which telemetry parameter state to replay
                     (ARCH-SIM-CONSTRUCTION-001 Phase C.8)

    Returns:
        bragg_full: np.ndarray, shape [n_panels, slow, fast], final Bragg image
    """
    # Lazy imports to avoid circular dependencies
    from nanobrag_torch.simulator import Simulator
    from nanobrag_torch.models.detector import Detector
    from nanobrag_torch.models.crystal import Crystal
    from dbex.refinement.config_factories import (
        create_detector_config,
        create_crystal_config,
    )
    from dbex.nanobrag_bridge import compute_baseline_misset_deg
    # ARCH-REFACTOR-001 Phase C.7: Import shared Stage A helper from stage_a_utils
    from dbex.refinement.stage_a_utils import _clamp_log_cell_deltas

    # Extract param_deltas from telemetry
    param_deltas_a = telemetry_a.param_deltas if hasattr(telemetry_a, 'param_deltas') else telemetry_a['param_deltas']

    # Helper to extract parameter value from telemetry with fallback logic
    def _get_param_value(param_dict, param_name):
        """Extract param value for requested state with fallback to 'final' if 'initial' missing."""
        if param_state == "initial":
            if "initial" in param_dict:
                return param_dict["initial"]
            else:
                # Fallback to 'final' when 'initial' not available (legacy telemetry)
                print(f"[ARCH-SIM-CONSTRUCTION-001 C.8 WARNING] param_deltas['{param_name}']['initial'] missing; falling back to 'final'")
                return param_dict.get("final", 0.0)
        else:
            # param_state == "final"
            return param_dict.get("final", 0.0)

    # Extract Stage A parameters according to param_state
    log_scale = torch.tensor(_get_param_value(param_deltas_a['log_scale'], 'log_scale'), device=device, dtype=dtype, requires_grad=False)
    log_cell_a_delta = torch.tensor(_get_param_value(param_deltas_a['log_cell_a_delta'], 'log_cell_a_delta'), device=device, dtype=dtype, requires_grad=False)
    log_cell_b_delta = torch.tensor(_get_param_value(param_deltas_a['log_cell_b_delta'], 'log_cell_b_delta'), device=device, dtype=dtype, requires_grad=False)
    log_cell_c_delta = torch.tensor(_get_param_value(param_deltas_a['log_cell_c_delta'], 'log_cell_c_delta'), device=device, dtype=dtype, requires_grad=False)
    angle_alpha_raw = torch.tensor(_get_param_value(param_deltas_a['angle_alpha_raw'], 'angle_alpha_raw'), device=device, dtype=dtype, requires_grad=False)
    angle_beta_raw = torch.tensor(_get_param_value(param_deltas_a['angle_beta_raw'], 'angle_beta_raw'), device=device, dtype=dtype, requires_grad=False)
    angle_gamma_raw = torch.tensor(_get_param_value(param_deltas_a['angle_gamma_raw'], 'angle_gamma_raw'), device=device, dtype=dtype, requires_grad=False)

    # For misset, use delta field with param_state selection
    misset_xyz_deg_delta_dict = param_deltas_a.get('misset_xyz_deg', {})
    if param_state == "initial":
        # Try to get initial misset delta; fall back to delta or final
        if "initial" in misset_xyz_deg_delta_dict:
            misset_xyz_deg_delta = misset_xyz_deg_delta_dict["initial"]
        elif "delta" in misset_xyz_deg_delta_dict:
            print(f"[ARCH-SIM-CONSTRUCTION-001 C.8 WARNING] param_deltas['misset_xyz_deg']['initial'] missing; using 'delta'")
            misset_xyz_deg_delta = misset_xyz_deg_delta_dict["delta"]
        else:
            print(f"[ARCH-SIM-CONSTRUCTION-001 C.8 WARNING] param_deltas['misset_xyz_deg'] has no 'initial' or 'delta'; falling back to zero")
            misset_xyz_deg_delta = [0.0, 0.0, 0.0]
    else:
        # For final state, prefer delta field (historical convention)
        misset_xyz_deg_delta = misset_xyz_deg_delta_dict.get('delta', [0.0, 0.0, 0.0])

    misset_xyz_deg = torch.tensor(misset_xyz_deg_delta, device=device, dtype=dtype, requires_grad=False)

    # Apply Stage A cell perturbations (mirroring Stage B reconstruction pattern)
    cell_params = crystal.get_unit_cell().parameters()
    log_cell_a_delta_clamped, log_cell_b_delta_clamped, log_cell_c_delta_clamped = _clamp_log_cell_deltas(
        log_cell_a_delta,
        log_cell_b_delta,
        log_cell_c_delta,
        getattr(config, "log_cell_max_delta", 1.0),
    )
    cell_a_tensor = cell_params[0] * torch.exp(log_cell_a_delta_clamped)
    cell_b_tensor = cell_params[1] * torch.exp(log_cell_b_delta_clamped)
    cell_c_tensor = cell_params[2] * torch.exp(log_cell_c_delta_clamped)

    max_angle_delta = 10.0  # degrees
    cell_alpha_tensor = cell_params[3] + torch.tanh(angle_alpha_raw) * max_angle_delta
    cell_beta_tensor = cell_params[4] + torch.tanh(angle_beta_raw) * max_angle_delta
    cell_gamma_tensor = cell_params[5] + torch.tanh(angle_gamma_raw) * max_angle_delta

    # Build crystal overrides
    crystal_overrides = {
        'cell_a': cell_a_tensor,
        'cell_b': cell_b_tensor,
        'cell_c': cell_c_tensor,
        'cell_alpha': cell_alpha_tensor,
        'cell_beta': cell_beta_tensor,
        'cell_gamma': cell_gamma_tensor
    }

    # Compute baseline misset if baseline_crystal provided (GEOMETRY-003)
    baseline_misset_deg_tensor = compute_baseline_misset_deg(
        crystal,
        baseline_crystal,
        device=device,
        dtype=dtype,
    )

    # Compute final misset (baseline + delta if baseline provided)
    if baseline_misset_deg_tensor is not None:
        final_misset = baseline_misset_deg_tensor + misset_xyz_deg
    else:
        final_misset = misset_xyz_deg

    # Extract N_cells from calibration metadata for domain count gating (SCALE-008)
    # Thread the apply_calibration_n_cells gate to honor the same gating as Stage A/mapping
    N_cells = None
    if config.calibration_metadata is not None:
        N_cells = config.calibration_metadata.get('N_cells')

    # Apply N_cells only when gate is True (matching stage_a_utils.py:289-291)
    apply_n_cells = (N_cells is not None) and config.apply_calibration_n_cells

    # Build crystal config with refined parameters using override API
    crystal_config, n_cells_applied = create_crystal_config(
        crystal=crystal,
        experiment=None,
        N_cells=N_cells,
        apply_n_cells=apply_n_cells,
        crystal_overrides=crystal_overrides,
        misset_deg_override=final_misset,
    )

    # Extract panel counts and full panel shape
    n_panels = len(detector)
    panel_shape = (
        detector[0].get_image_size()[1],  # slow
        detector[0].get_image_size()[0]   # fast
    )
    sampled_panel_ids = list(range(n_panels))

    # Extract spot_scale_override for post-run scaling (matches stage_a.py:442-443, SCALE-009)
    spot_scale_override = None
    if config.calibration_metadata is not None:
        spot_scale_override = config.calibration_metadata.get('spot_scale_override')

    sqrt_spot_scale = float(np.sqrt(spot_scale_override)) if spot_scale_override and spot_scale_override > 0 else 1.0

    # Build full Bragg array (panel mode)
    # Reuse warm cache simulators if available
    use_warm_path = False
    if stage_a_ctx is not None and hasattr(stage_a_ctx, 'simulators'):
        # Warm cache path: retarget existing simulators with refined crystal (GRADIENT-004, ARCH-FACTORY-001)
        # Build Crystal model with beam_config from context (BUGFIX: pass at construction time)
        crystal_model = Crystal(
            crystal_config,
            beam_config=stage_a_ctx.beam_config,  # FIXED: pass beam_config at construction time
            device=device,
            dtype=dtype,
        )
        crystal_model.interpolate = config.enable_hkl_interpolation
        crystal_model.hkl_data = hkl_grid.to(device=device, dtype=dtype)
        crystal_model.hkl_metadata = hkl_metadata

        # ARCH-REFACTOR-001 Phase C.7: Import shared Stage A helper from stage_a_utils
        from dbex.refinement.stage_a_utils import _retarget_stage_a_simulators
        _retarget_stage_a_simulators(stage_a_ctx, crystal_model)
        simulators = stage_a_ctx.simulators
        use_warm_path = True
    else:
        # Cold path: build simulators via unified factory (ARCH-FACTORY-001 Phase B.4)
        from dbex.refinement.config_factories import create_beam_config
        from dbex.refinement.helpers import create_unified_simulator

        # Extract beam calibration for architectural consistency with Stage A (stage_a_utils.py:267)
        beam_flux = None
        beam_exposure = None
        beamsize_mm = None
        if config.calibration_metadata is not None:
            beam_flux = config.calibration_metadata.get('beam_flux')
            beam_exposure = config.calibration_metadata.get('beam_exposure')
            beamsize_mm = config.calibration_metadata.get('beamsize_mm')

        beam_config = create_beam_config(beam, flux=beam_flux, exposure=beam_exposure, beamsize_mm=beamsize_mm)
        simulators = []
        for pid in sampled_panel_ids:
            # Thread trusted mask into cold-path detector config (ARCH-SIM-CONSTRUCTION-001 Phase C.6)
            # When inputs.trusted_mask exists, pass per-panel mask so reconstruction zeros
            # untrusted pixels the same way Stage A warm cache does (spec-db-core.md:34,109)
            # Guard: skip mask injection for panels with <50% coverage (fallback to None)
            panel_trusted_mask = None
            if inputs.trusted_mask is not None:
                panel_mask_candidate = inputs.trusted_mask[pid]
                # Convert to tensor if needed to compute coverage
                if isinstance(panel_mask_candidate, np.ndarray):
                    panel_mask_tensor = torch.from_numpy(panel_mask_candidate).to(device=device, dtype=torch.bool)
                else:
                    panel_mask_tensor = panel_mask_candidate.to(device=device, dtype=torch.bool)

                coverage = float(panel_mask_tensor.float().mean().item())
                coverage_threshold = 0.50
                epsilon = 1e-6

                if coverage >= (coverage_threshold - epsilon):
                    # Coverage is sufficient, use the mask
                    panel_trusted_mask = panel_mask_candidate
                else:
                    # Coverage too low, skip mask injection and log
                    print(f"[ARCH-SIM-CONSTRUCTION-001 MASK COVERAGE] Panel {pid}: coverage={coverage:.4f} < {coverage_threshold}, skipping mask injection (fallback to None)")
                    panel_trusted_mask = None

            detector_config = create_detector_config(
                detector[pid],
                beam=beam,
                trusted_mask=panel_trusted_mask,
                oversample=3  # Force 3-fold oversampling matching simulate_forward_once
            )

            # Normalize mask_array to device/dtype after detector config creation (ARCH-SIM-CONSTRUCTION-001)
            # Mirror Stage A's mask normalization (stage_a_utils.py:315-321) so reconstruction
            # preserves trusted-mask gating on CUDA runs
            mask_array_for_factory = detector_config.mask_array
            if mask_array_for_factory is not None:
                if not isinstance(mask_array_for_factory, torch.Tensor):
                    mask_array_for_factory = torch.tensor(mask_array_for_factory, dtype=torch.float32, device=device)
                elif mask_array_for_factory.device != device or mask_array_for_factory.dtype != torch.float32:
                    mask_array_for_factory = mask_array_for_factory.to(device=device, dtype=torch.float32)
                # Update detector_config so it carries the normalized tensor
                detector_config.mask_array = mask_array_for_factory

            # Use unified factory for forward-only reconstruction (ARCH-FACTORY-001)
            # Pass mask_array explicitly so helpers.py normalization branch executes (ARCH-SIM-CONSTRUCTION-001)
            # Pass spot_scale_override so factory can compute sqrt_scale for post-run application
            simulator, normalized_mask, sqrt_scale_from_factory, metadata = create_unified_simulator(
                detector_config=detector_config,
                crystal_config=crystal_config,
                beam_config=beam_config,
                hkl_grid=hkl_grid,
                hkl_metadata=hkl_metadata,
                mask_array=mask_array_for_factory,  # Pass normalized mask so factory can validate/attach
                spot_scale_override=spot_scale_override,  # Factory needs this to compute sqrt_scale
                device=device,
                dtype=dtype,
                calibration_metadata=getattr(config, 'calibration_metadata', None),
            )
            simulator.interpolate = config.enable_hkl_interpolation
            simulators.append(simulator)

    # Run forward model with refined parameters
    bragg_full = np.zeros((n_panels, *panel_shape), dtype=np.float32)

    # Mask coverage diagnostics (ARCH-SIM-CONSTRUCTION-001 Phase C.6)
    mask_coverage_stats = []

    # ARCH-SIM-CONSTRUCTION-001 Phase C.7 / C.8: Prefer recorded scale_factor from Stage A telemetry
    # When available, use the authoritative log_scale_effective and scale_factor from Stage A's
    # forward pass instead of recomputing from baseline+delta. Fall back to legacy computation
    # when telemetry doesn't include the new fields.
    # ARCH-SIM-CONSTRUCTION-001 Phase C.8: Apply param_state selection to scale_factor extraction
    log_scale_effective_dict = param_deltas_a.get('log_scale_effective', {})
    if log_scale_effective_dict and 'scale_factor' in log_scale_effective_dict:
        # New path: use recorded scale_factor directly from Stage A telemetry
        # For param_state="initial", we want the baseline (initial) value; for "final", the refined value
        if param_state == "initial":
            # For initial state, use the baseline value (log_scale_effective['initial'] = baseline)
            log_scale_baseline_value = log_scale_effective_dict.get('initial')
            if log_scale_baseline_value is not None:
                # Compute initial scale_factor from baseline (delta should be zero at initial)
                log_scale_clamped = torch.tensor(log_scale_baseline_value, device=device, dtype=dtype)
                scale_factor = torch.exp(log_scale_clamped)
                print(f"[ARCH-SIM-CONSTRUCTION-001 Phase C.8] Using initial (baseline) scale_factor from Stage A telemetry:")
                print(f"  log_scale_baseline (initial): {log_scale_baseline_value:.6f}")
                print(f"  scale_factor (initial): {scale_factor.item():.6e}")
            else:
                # Fallback: no initial value recorded, recompute from log_scale param (which should be zero-ish for initial)
                print(f"[ARCH-SIM-CONSTRUCTION-001 Phase C.8 WARNING] log_scale_effective['initial'] missing; recomputing from log_scale baseline")
                log_scale_baseline_value = param_deltas_a.get('log_scale_baseline', {}).get('final', 0.0)
                log_scale_clamped = torch.tensor(log_scale_baseline_value, device=device, dtype=dtype)
                scale_factor = torch.exp(log_scale_clamped)
        else:
            # For final state, use the recorded final scale_factor
            scale_factor = torch.tensor(log_scale_effective_dict['scale_factor'], device=device, dtype=dtype)
            log_scale_clamped = torch.tensor(log_scale_effective_dict['final'], device=device, dtype=dtype)
            log_scale_baseline_value = log_scale_effective_dict.get('initial')

            # Emit diagnostic when available
            print(f"[ARCH-SIM-CONSTRUCTION-001 Phase C.7] Using recorded scale_factor from Stage A telemetry:")
            print(f"  scale_factor (recorded): {log_scale_effective_dict['scale_factor']:.6e}")
            print(f"  log_scale_effective (recorded): {log_scale_effective_dict['final']:.6f}")
            if log_scale_baseline_value is not None:
                print(f"  log_scale_baseline: {log_scale_baseline_value:.6f}")
                print(f"  log_scale_delta_clamped (recorded): {log_scale_effective_dict.get('log_scale_delta_clamped', 'N/A')}")
    else:
        # Legacy path: reconstruct scale_factor from baseline + delta (backward compatible)
        print(f"[ARCH-SIM-CONSTRUCTION-001 Phase C.7] log_scale_effective not found in telemetry; falling back to legacy computation")
        log_scale_baseline_value = param_deltas_a.get('log_scale_baseline', {}).get('final')

        # Apply Stage A's log-scale clamp logic (matching stage_a.py lines 1194-1202)
        # When calibration metadata is present:
        #   log_scale_baseline = log(sqrt(spot_scale_override)) is the fixed baseline
        #   log_scale is a delta parameter, clamped to ±config.log_scale_max_delta (default ±3)
        #   Final scale = exp(log_scale_baseline + clamped_delta)
        # Otherwise (uncalibrated):
        #   log_scale is the direct learnable parameter, clamped to ±config.log_scale_max_delta_uncalibrated (default ±10)
        #   Final scale = exp(clamped_log_scale)
        max_delta_uncal = getattr(config, "log_scale_max_delta_uncalibrated", 10.0)
        delta_bound = getattr(config, "log_scale_max_delta", 3.0) if log_scale_baseline_value is not None else max_delta_uncal

        if log_scale_baseline_value is not None:
            # Calibrated path: add baseline to clamped delta
            log_scale_baseline_tensor = torch.tensor(log_scale_baseline_value, device=device, dtype=dtype)
            log_scale_delta_clamped = torch.clamp(log_scale, min=-delta_bound, max=delta_bound)
            log_scale_clamped = log_scale_baseline_tensor + log_scale_delta_clamped
        else:
            # Uncalibrated path: clamp absolute log_scale (legacy behavior)
            log_scale_clamped = torch.clamp(log_scale, min=-delta_bound, max=delta_bound)

        scale_factor = torch.exp(log_scale_clamped)

        # Emit warning if recomputation differs from recorded value (when both available)
        if 'scale_factor' in log_scale_effective_dict:
            recorded_scale = log_scale_effective_dict['scale_factor']
            recomputed_scale = float(scale_factor.item())
            rel_diff = abs(recomputed_scale - recorded_scale) / max(abs(recorded_scale), 1e-12)
            if rel_diff > 1e-6:
                print(f"[ARCH-SIM-CONSTRUCTION-001 WARNING] scale_factor recomputation disagrees with recorded value:")
                print(f"  recorded: {recorded_scale:.6e}, recomputed: {recomputed_scale:.6e}, rel_diff: {rel_diff:.2e}")


    # Legacy DEBUG block retained for sqrt_spot_scale / spot_scale_override visibility
    print(f"  sqrt_spot_scale: {sqrt_spot_scale}")
    print(f"  spot_scale_override: {spot_scale_override}")

    for pid, sim in zip(sampled_panel_ids, simulators):
        # Mask coverage diagnostics (ARCH-SIM-CONSTRUCTION-001 Phase C.6)
        # Record coverage for this panel when mask is provided
        if inputs.trusted_mask is not None:
            panel_trusted_mask_tensor = inputs.trusted_mask[pid]
            if isinstance(panel_trusted_mask_tensor, np.ndarray):
                panel_trusted_mask_tensor = torch.from_numpy(panel_trusted_mask_tensor).to(device=device, dtype=torch.bool)
            coverage = float(panel_trusted_mask_tensor.float().mean().item())

            # Determine if mask was actually injected (based on guard logic above in cold path)
            # In cold path, we already applied the guard when building detector_config
            # In warm cache path, simulators are pre-built so mask state is fixed
            coverage_threshold = 0.50
            epsilon = 1e-6
            mask_injected = coverage >= (coverage_threshold - epsilon)
            fallback_reason = None if mask_injected else "coverage_below_threshold"

            mask_coverage_stats.append({
                "panel_id": pid,
                "coverage": coverage,
                "mask_injected": mask_injected,
                "fallback_reason": fallback_reason,
            })

        bragg_panel = sim.run()
        # DEBUG: print first panel's raw output
        if pid == 0:
            print(f"  bragg_panel[0] mean (raw sim output): {bragg_panel.mean().item():.6e}")
            print(f"  bragg_panel[0] max: {bragg_panel.max().item():.6e}")

        # TOOLING-VIS-001 Phase D.D / ARCH-SIM-CONSTRUCTION-001 Phase C.9:
        # Apply scale_factor from telemetry (exp(log_scale_effective)).
        # scale_factor already incorporates sqrt_spot_scale either via:
        #  - Standard path: log_scale_baseline = log(sqrt_spot_scale), so scale_factor = sqrt_spot_scale * exp(delta)
        #  - Global hint path: log_scale_baseline = log(global_scale_hint), where global_scale_hint already accounts for sqrt_spot_scale via mapping forward
        # Do NOT multiply by sqrt_spot_scale again here (that would double-apply it).
        bragg_scaled = bragg_panel * scale_factor

        if pid == 0:
            print(f"  bragg_scaled[0] mean (after scale_factor): {bragg_scaled.mean().item():.6e}")
        bragg_full[pid] = bragg_scaled.cpu().numpy().astype(np.float32)

    # DEBUG: final output summary
    print(f"  bragg_full mean (final output): {bragg_full.mean():.6e}")
    print(f"  bragg_full max: {bragg_full.max():.6e}")
    print(f"[END DEBUG]")

    # Write mask coverage stats to artifacts directory if available
    # (ARCH-SIM-CONSTRUCTION-001 Phase C.6)
    if mask_coverage_stats:
        import json
        import os
        from datetime import datetime

        # Try to determine artifacts path from environment or use default
        artifact_dir = os.environ.get('DBAT028_ARTIFACT_DIR') or os.environ.get('DBAT029_ARTIFACT_DIR')
        if not artifact_dir:
            # Default fallback to initiative reports directory
            artifact_dir = "plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-10T090000Z"

        # Ensure artifact_dir is absolute or at least non-empty
        if not artifact_dir or artifact_dir == '':
            artifact_dir = "."

        mask_coverage_path = os.path.join(artifact_dir, "mask_coverage.json")
        os.makedirs(artifact_dir, exist_ok=True)

        # Append to existing file or create new
        existing_data = []
        if os.path.exists(mask_coverage_path):
            with open(mask_coverage_path, 'r') as f:
                existing_data = json.load(f)
                if not isinstance(existing_data, list):
                    existing_data = []

        # Add timestamp to this run's stats
        run_record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "panels": mask_coverage_stats,
        }
        existing_data.append(run_record)

        with open(mask_coverage_path, 'w') as f:
            json.dump(existing_data, f, indent=2)

        print(f"[ARCH-SIM-CONSTRUCTION-001 MASK COVERAGE] Wrote coverage stats to {mask_coverage_path}")

    # Log whether N_cells was applied for this reconstruction run (SCALE-008)
    n_cells_status = "applied" if n_cells_applied else "suppressed"
    n_cells_value = N_cells if N_cells is not None else "None"
    print(f"[ARCH-SIM-CONSTRUCTION-001 N_CELLS] N_cells={n_cells_value}, status={n_cells_status} (apply_calibration_n_cells={config.apply_calibration_n_cells})")

    # ARCH-SIM-CONSTRUCTION-001 Phase C.9: Baseline stats instrumentation
    # Compute masked/unmasked means and compare against telemetry values
    # This helps quantify the reconstruction vs telemetry gap that drives DB-AT-028/029 failures
    if inputs.loss_mask is not None and inputs.target is not None:
        import json
        import os
        from datetime import datetime

        # Compute masked/unmasked means for both bragg_full and target
        loss_mask_bool = inputs.loss_mask.astype(bool)
        target_np = inputs.target

        bragg_masked = bragg_full[loss_mask_bool]
        target_masked = target_np[loss_mask_bool]

        bragg_mean_masked = float(np.mean(bragg_masked)) if bragg_masked.size > 0 else float("nan")
        target_mean_masked = float(np.mean(target_masked)) if target_masked.size > 0 else float("nan")
        bragg_mean_unmasked = float(np.mean(bragg_full))
        target_mean_unmasked = float(np.mean(target_np))

        # Extract telemetry values (when available) for comparison
        # ARCH-SIM-CONSTRUCTION-001 Phase C.9: Read from top-level telemetry fields
        target_mean_masked_telem = float("nan")
        model_mean_masked_telem = float("nan")
        if hasattr(telemetry_a, 'target_mean_masked'):
            target_mean_masked_telem = float(telemetry_a.target_mean_masked) if telemetry_a.target_mean_masked is not None else float("nan")
        if hasattr(telemetry_a, 'model_mean_masked'):
            model_mean_masked_telem = float(telemetry_a.model_mean_masked) if telemetry_a.model_mean_masked is not None else float("nan")

        # Fallback: try to extract from log_scale_effective dict (legacy path)
        if not np.isfinite(target_mean_masked_telem) or not np.isfinite(model_mean_masked_telem):
            log_scale_effective_dict = param_deltas_a.get('log_scale_effective', {})
            if log_scale_effective_dict:
                target_mean_masked_telem = float(log_scale_effective_dict.get('target_mean_masked', float("nan")))
                model_mean_masked_telem = float(log_scale_effective_dict.get('model_mean_masked', float("nan")))

        # Compute chi²-per-pixel for this reconstruction (matching DB-AT-028 logic)
        residual_masked = target_masked - bragg_masked
        variance_floor_value = 1.0
        if hasattr(telemetry_a, 'variance_floor_value'):
            variance_floor_value = float(telemetry_a.variance_floor_value)
        variance_masked = np.maximum(bragg_masked, variance_floor_value)
        chi_squared_masked = float(np.sum(residual_masked ** 2 / variance_masked)) if bragg_masked.size > 0 else float("nan")
        n_masked_pixels = int(np.count_nonzero(loss_mask_bool))
        chi_squared_per_pixel = chi_squared_masked / n_masked_pixels if n_masked_pixels > 0 else float("nan")

        # Compute ratios
        bragg_vs_telem_ratio = bragg_mean_masked / model_mean_masked_telem if np.isfinite(model_mean_masked_telem) and model_mean_masked_telem != 0 else float("nan")
        bragg_vs_target_ratio = bragg_mean_masked / target_mean_masked if target_mean_masked != 0 else float("nan")

        # Compute reconstruction mask metadata (ARCH-SIM-CONSTRUCTION-001 C.10)
        reconstruction_mask_metadata = None
        telemetry_mask_metadata = None
        mask_checksum_mismatch = False

        if inputs.loss_mask is not None:
            try:
                # Compute reconstruction mask metadata
                loss_mask_pixel_count = int(np.count_nonzero(inputs.loss_mask))
                mask_array = np.ascontiguousarray(inputs.loss_mask, dtype=np.uint8)
                mask_checksum = hashlib.sha1(mask_array).hexdigest()

                reconstruction_mask_metadata = {
                    'loss_mask_pixel_count': loss_mask_pixel_count,
                    'mask_checksum': mask_checksum,
                }

                # Extract telemetry mask metadata if available
                if hasattr(telemetry_a, 'mask_metadata') and telemetry_a.mask_metadata is not None:
                    telemetry_mask_metadata = telemetry_a.mask_metadata

                    # Check for checksum mismatch
                    telem_checksum = telemetry_mask_metadata.get('mask_checksum')
                    if telem_checksum is not None and telem_checksum != mask_checksum:
                        mask_checksum_mismatch = True
                        print(f"[ARCH-SIM-CONSTRUCTION-001 C.10 WARNING] Mask checksum mismatch:")
                        print(f"  Telemetry checksum: {telem_checksum}")
                        print(f"  Reconstruction checksum: {mask_checksum}")
                        print(f"  This suggests Stage A and reconstruction are using different masks")

            except Exception as e:
                print(f"[ARCH-SIM-CONSTRUCTION-001 C.10 WARNING] Mask metadata computation failed: {e}")
                reconstruction_mask_metadata = None

        baseline_stats = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "param_state": param_state,
            "reconstructed_bragg": {
                "mean_masked": bragg_mean_masked,
                "mean_unmasked": bragg_mean_unmasked,
            },
            "target": {
                "mean_masked": target_mean_masked,
                "mean_unmasked": target_mean_unmasked,
            },
            "telemetry_values": {
                "target_mean_masked": target_mean_masked_telem,
                "model_mean_masked": model_mean_masked_telem,
            },
            "ratios": {
                "bragg_vs_telem_model": bragg_vs_telem_ratio,
                "bragg_vs_target": bragg_vs_target_ratio,
            },
            "chi_squared": {
                "per_pixel": chi_squared_per_pixel,
                "n_masked_pixels": n_masked_pixels,
            },
            "scale_factor_used": float(scale_factor.item()) if isinstance(scale_factor, torch.Tensor) else float(scale_factor),
            "mask_metadata": {
                "telemetry": telemetry_mask_metadata,
                "reconstruction": reconstruction_mask_metadata,
                "checksum_mismatch": mask_checksum_mismatch,
            },
        }

        # Write baseline stats to artifacts directory
        artifact_dir = os.environ.get('DBAT028_ARTIFACT_DIR') or os.environ.get('DBAT029_ARTIFACT_DIR')
        if not artifact_dir:
            artifact_dir = "plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-13T235500Z"

        if artifact_dir and artifact_dir != '':
            baseline_stats_path = os.path.join(artifact_dir, "baseline_stats.json")
            os.makedirs(artifact_dir, exist_ok=True)

            # Append to existing file or create new
            existing_stats = []
            if os.path.exists(baseline_stats_path):
                with open(baseline_stats_path, 'r') as f:
                    try:
                        existing_stats = json.load(f)
                        if not isinstance(existing_stats, list):
                            existing_stats = []
                    except json.JSONDecodeError:
                        existing_stats = []

            existing_stats.append(baseline_stats)

            with open(baseline_stats_path, 'w') as f:
                json.dump(existing_stats, f, indent=2)

            print(f"[ARCH-SIM-CONSTRUCTION-001 BASELINE STATS] Wrote baseline stats to {baseline_stats_path}")
            print(f"  Reconstructed bragg mean (masked): {bragg_mean_masked:.6e}")
            print(f"  Telemetry model mean (masked): {model_mean_masked_telem:.6e}")
            print(f"  Ratio (bragg/telem): {bragg_vs_telem_ratio:.6f}")
            print(f"  Chi²/pixel: {chi_squared_per_pixel:.6e}")

    return bragg_full


def build_final_bragg_from_stage_b_telemetry(
    telemetry_a,
    telemetry_b,
    detector,
    beam,
    crystal,
    baseline_crystal,
    inputs,
    hkl_grid,
    hkl_metadata,
    config,
    device,
    dtype,
    use_stage_b_cpu_fallback=False,
    stage_a_ctx=None,
):
    """
    Build final Bragg array from Stage B telemetry (shell modifiers + Stage A frozen params).

    Extracts Stage A frozen parameters and Stage B shell modifiers from telemetry,
    applies modifiers to HKL grid, and regenerates full Bragg image.

    Args:
        telemetry_a: RefinementTelemetry instance or dict with Stage A optimized param_deltas
        telemetry_b: RefinementTelemetry instance or dict with Stage B shell modifiers
        detector: dxtbx Detector object
        beam: dxtbx Beam object
        crystal: dxtbx Crystal object
        baseline_crystal: Optional baseline dxtbx Crystal object for extracting deterministic
                          misset when `crystal` is perturbed. When provided, computes
                          U_delta = U_perturbed @ U_baseline^{-1} and adds it to the orientation
                          path as a tensor to preserve differentiability. Defaults to None.
        inputs: RefinementInputs with panel_slices, trusted_mask
        hkl_grid: torch.Tensor structure factor grid (unmodified baseline)
        hkl_metadata: dict with grid dimensions
        config: RefinementConfig with device, dtype, Stage B settings
        device: torch.device for tensor operations
        dtype: torch.dtype for tensor operations
        use_stage_b_cpu_fallback: Route computation to CPU (Stage B CPU fallback mode)
        stage_a_ctx: Optional Stage A context (detectors/simulators for warm cache)

    Returns:
        bragg_full: np.ndarray, shape [n_panels, slow, fast], final Bragg image with shell modifiers
    """
    # Route device to CPU when CPU fallback is active
    final_device = torch.device("cpu") if use_stage_b_cpu_fallback else device

    # Lazy imports to avoid circular dependencies
    from nanobrag_torch.simulator import Simulator
    from nanobrag_torch.models.detector import Detector
    from nanobrag_torch.models.crystal import Crystal
    from dbex.refinement.config_factories import (
        create_detector_config,
        create_crystal_config,
    )
    from dbex.nanobrag_bridge import compute_baseline_misset_deg
    # ARCH-REFACTOR-001 Phase C.7: Import shared Stage A helper from stage_a_utils
    from dbex.refinement.stage_a_utils import _clamp_log_cell_deltas, _retarget_stage_a_simulators

    # Extract param_deltas from telemetry (handle both RefinementTelemetry and dict)
    if hasattr(telemetry_a, 'param_deltas'):
        param_deltas_a = telemetry_a.param_deltas
    else:
        param_deltas_a = telemetry_a['param_deltas']

    if hasattr(telemetry_b, 'param_deltas'):
        param_deltas_b = telemetry_b.param_deltas
    else:
        param_deltas_b = telemetry_b['param_deltas']

    # Extract Stage A frozen parameters (final values)
    # Use final_device for tensor creation to respect CPU fallback mode
    log_scale = torch.tensor(param_deltas_a['log_scale']['final'], device=final_device, dtype=dtype, requires_grad=False)
    log_cell_a_delta = torch.tensor(param_deltas_a['log_cell_a_delta']['final'], device=final_device, dtype=dtype, requires_grad=False)
    log_cell_b_delta = torch.tensor(param_deltas_a['log_cell_b_delta']['final'], device=final_device, dtype=dtype, requires_grad=False)
    log_cell_c_delta = torch.tensor(param_deltas_a['log_cell_c_delta']['final'], device=final_device, dtype=dtype, requires_grad=False)
    angle_alpha_raw = torch.tensor(param_deltas_a['angle_alpha_raw']['final'], device=final_device, dtype=dtype, requires_grad=False)
    angle_beta_raw = torch.tensor(param_deltas_a['angle_beta_raw']['final'], device=final_device, dtype=dtype, requires_grad=False)
    angle_gamma_raw = torch.tensor(param_deltas_a['angle_gamma_raw']['final'], device=final_device, dtype=dtype, requires_grad=False)

    # Extract misset from Stage A (this is the delta, not frozen in Stage B inline code but added to baseline)
    misset_xyz_deg_delta = param_deltas_a['misset_xyz_deg']['delta']
    misset_xyz_deg = torch.tensor(misset_xyz_deg_delta, device=final_device, dtype=dtype, requires_grad=False)

    # Check Stage B mode (per-reflection or shell)
    # Per-reflection mode doesn't have shell_edges/shell_indices
    stage_b_mode = None
    if hasattr(telemetry_b, 'stage_b_mode'):
        stage_b_mode = telemetry_b.stage_b_mode
    elif isinstance(telemetry_b, dict) and 'stage_b_mode' in telemetry_b:
        stage_b_mode = telemetry_b['stage_b_mode']

    # Extract shell metadata from Stage B telemetry (shell mode only)
    if stage_b_mode == "per_reflection":
        # Per-reflection mode: no shell metadata, skip shell modifier application
        shell_edges = None
        shell_indices = None
        n_shells = 0
        shell_modifiers_final = None
    else:
        # Shell mode: extract shell metadata and modifiers
        # Use final_device for tensor creation to respect CPU fallback mode
        if hasattr(telemetry_b, 'shell_edges'):
            shell_edges = torch.tensor(telemetry_b.shell_edges, device=final_device, dtype=dtype)
            shell_indices = torch.tensor(telemetry_b.shell_indices, device=final_device, dtype=torch.long)
            n_shells = telemetry_b.n_shells
        else:
            shell_edges = torch.tensor(telemetry_b['shell_edges'], device=final_device, dtype=dtype)
            shell_indices = torch.tensor(telemetry_b['shell_indices'], device=final_device, dtype=torch.long)
            n_shells = telemetry_b['n_shells']

        # Extract shell modifiers from Stage B param_deltas
        shell_modifiers_final = torch.zeros(n_shells, device=final_device, dtype=dtype)
        for shell_idx in range(n_shells):
            # Find the shell modifier key in param_deltas_b
            shell_key = None
            for key in param_deltas_b.keys():
                if key.startswith(f'shell_{shell_idx}_modifier'):
                    shell_key = key
                    break
            if shell_key is None:
                raise RuntimeError(f"Missing shell_{shell_idx}_modifier in Stage B telemetry param_deltas")
            shell_modifiers_final[shell_idx] = param_deltas_b[shell_key]['final']

    # Get n_panels and panel_shape
    n_panels = len(detector)
    panel_shape = inputs.target.shape[1:]  # (slow, fast)

    # Compute baseline misset if baseline_crystal provided (matches inline path lines 3115-3120)
    # Use final_device for tensor creation to respect CPU fallback mode
    baseline_misset_deg_tensor = compute_baseline_misset_deg(
        crystal,
        baseline_crystal,
        device=final_device,
        dtype=dtype,
    )

    # Apply Stage A cell perturbations
    cell_params = crystal.get_unit_cell().parameters()
    log_cell_a_delta_clamped, log_cell_b_delta_clamped, log_cell_c_delta_clamped = _clamp_log_cell_deltas(
        log_cell_a_delta,
        log_cell_b_delta,
        log_cell_c_delta,
        getattr(config, "log_cell_max_delta", 1.0),
    )
    cell_a_tensor = cell_params[0] * torch.exp(log_cell_a_delta_clamped)
    cell_b_tensor = cell_params[1] * torch.exp(log_cell_b_delta_clamped)
    cell_c_tensor = cell_params[2] * torch.exp(log_cell_c_delta_clamped)

    max_angle_delta = 10.0  # degrees
    cell_alpha_tensor = cell_params[3] + torch.tanh(angle_alpha_raw) * max_angle_delta
    cell_beta_tensor = cell_params[4] + torch.tanh(angle_beta_raw) * max_angle_delta
    cell_gamma_tensor = cell_params[5] + torch.tanh(angle_gamma_raw) * max_angle_delta

    # Apply shell modifiers to HKL grid (shell mode only; per-reflection uses base grid)
    if stage_b_mode == "per_reflection":
        # Per-reflection mode: use unmodified HKL grid (ASU modifiers applied per-reflection during forward pass)
        hkl_grid_modified = hkl_grid
    else:
        # Shell mode: apply shell modifiers to HKL grid (mirroring inline code lines 3314-3317)
        with torch.no_grad():
            hkl_grid_modified = hkl_grid.clone()
            for shell_idx in range(n_shells):
                mask = (shell_indices == shell_idx)
                hkl_grid_modified[mask] = hkl_grid[mask] * shell_modifiers_final[shell_idx]

    bragg_full = np.zeros((n_panels, *panel_shape), dtype=np.float32)

    # Build crystal overrides
    crystal_overrides = {
        'cell_a': cell_a_tensor,
        'cell_b': cell_b_tensor,
        'cell_c': cell_c_tensor,
        'cell_alpha': cell_alpha_tensor,
        'cell_beta': cell_beta_tensor,
        'cell_gamma': cell_gamma_tensor
    }

    # Compute final misset (baseline + delta if baseline provided)
    if baseline_misset_deg_tensor is not None:
        final_misset = baseline_misset_deg_tensor + misset_xyz_deg
    else:
        final_misset = misset_xyz_deg

    # Check if warm cache is enabled AND stage_a_ctx is available
    stage_b_use_warm_cache = config.enable_stage_a_warm_cache and stage_a_ctx is not None

    if stage_b_use_warm_cache:
        # Warm cache path: retarget Stage A simulators with modified crystal
        warm_crystal_config, _ = create_crystal_config(
            crystal,
            None,
            crystal_overrides=crystal_overrides,
            misset_deg_override=final_misset,
            apply_n_cells=False,
        )
        warm_crystal_model = Crystal(
            warm_crystal_config,
            beam_config=stage_a_ctx.beam_config,
            device=final_device,
            dtype=dtype,
        )
        warm_crystal_model.interpolate = True
        warm_crystal_model.hkl_data = hkl_grid_modified.to(device=final_device, dtype=dtype)
        warm_crystal_model.hkl_metadata = hkl_metadata
        _retarget_stage_a_simulators(stage_a_ctx, warm_crystal_model)

        for pid in range(n_panels):
            simulator = stage_a_ctx.simulators[pid]
            bragg_panel = simulator.run()
            log_scale_clamped = torch.clamp(log_scale, min=-10.0, max=10.0)
            bragg_scaled = bragg_panel * torch.exp(log_scale_clamped)
            bragg_full[pid] = bragg_scaled.cpu().numpy().astype(np.float32)
    else:
        # Cold path: instantiate simulators via unified factory (ARCH-FACTORY-001 Phase B.4)
        from dbex.refinement.config_factories import create_beam_config
        from dbex.refinement.helpers import create_unified_simulator
        # Transfer shell-modified HKL grid to final_device before factory invocation (CPU fallback determinism)
        hkl_grid_final = hkl_grid_modified.to(device=final_device, dtype=dtype)
        beam_config = create_beam_config(beam)
        for pid in range(n_panels):
            detector_config = create_detector_config(
                panel=detector[pid],
                beam=beam,
                trusted_mask=inputs.trusted_mask[pid]
            )
            crystal_config, _ = create_crystal_config(
                crystal, None,
                crystal_overrides=crystal_overrides,
                misset_deg_override=final_misset,
                apply_n_cells=False
            )
            # Use unified factory for forward-only reconstruction (ARCH-FACTORY-001)
            simulator, normalized_mask, sqrt_scale, metadata = create_unified_simulator(
                detector_config=detector_config,
                crystal_config=crystal_config,
                beam_config=beam_config,
                hkl_grid=hkl_grid_final,
                hkl_metadata=hkl_metadata,
                mask_array=None,  # mask already in detector_config from create_detector_config
                spot_scale_override=None,  # scale handled via log_scale parameter
                device=final_device,
                dtype=dtype,
                calibration_metadata=getattr(config, 'calibration_metadata', None),
            )
            simulator.interpolate = True
            bragg_panel = simulator.run()
            log_scale_clamped = torch.clamp(log_scale, min=-10.0, max=10.0)
            bragg_scaled = bragg_panel * torch.exp(log_scale_clamped)
            bragg_full[pid] = bragg_scaled.cpu().numpy().astype(np.float32)

    return bragg_full
