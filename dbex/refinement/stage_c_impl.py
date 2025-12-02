"""
Stage C implementation helpers for detector distance offset refinement.

Extracted from dbex.nanobrag_refinement per ARCH-REFINE-001 Phase A.3.

Stage C scope (per docs/spec-db-workflow.md:62-65):
- Parameters: per-panel detector distance offsets (mm along panel normal)
- Freezes: Stage A crystal/scale/orientation parameters
- Loss: variance-weighted chi-squared with PHYSICS-LOSS-001/002 telemetry
- Warm cache: PERF-WARM-006/013 retarget cached Stage A detectors/simulators

Exports:
- _retarget_stage_a_detectors: Helper to update cached detector models with distance offsets
- _build_stage_c_params: Initialize Stage C parameters and optimizer
- _run_stage_c_lbfgs: Execute Stage C optimization and telemetry packaging

ARCH-STAGE-CONTEXT-001 Phase B.2.3:
- _build_stage_c_lbfgs_closure moved to StageC._build_lbfgs_closure (dbex/refinement/stage_c.py)
"""

import json
import math
import os
import time
import warnings
from collections import defaultdict
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import torch

# ARCH-LAZY-IMPORTS-001 / ARCH-ENGINE-002: Module-scope dependencies for Stage C
from nanobrag_torch.models import Detector, Crystal
from nanobrag_torch.simulator import Simulator
from dbex.refinement.config_factories import create_detector_config, create_crystal_config

# Import Stage A helpers for shared utilities
from dbex.refinement.stage_a_impl import (
    vec_to_unit_quaternion,
    quaternion_to_xyz_euler,
    StageAContext,
    _clamp_log_cell_deltas,
    _get_sigma_floor_sq_tensor,
    _retarget_stage_a_simulators,
    _compute_panel_loss,
)

from dbex.physics.loss import _compute_variance_weighted_loss
from dbex.refinement.context import StageCTelemetryState

# PERF-WARM-016: Debug hook for Stage C cache retargeting trace
# Opt-in via DBEX_STAGE_C_CACHE_DEBUG_PATH env var; zero overhead when unset
_STAGE_C_CACHE_DEBUG_PATH = os.environ.get("DBEX_STAGE_C_CACHE_DEBUG_PATH", None)
_STAGE_C_RETARGET_CALL_COUNTER = 0


def _retarget_stage_a_detectors(
    stage_a_ctx: StageAContext,
    distance_deltas_mm: Dict[int, torch.Tensor],
    device: torch.device,
    dtype: torch.dtype
) -> None:
    """
    Retarget cached Stage A detector models with distance offsets for Stage C.

    Mutates stage_a_ctx in place by:
    1. Updating detector configs with new distances (baseline + delta)
    2. Rebuilding Detector models with updated configs
    3. Rebuilding Simulator instances to reflect new detector geometry
    4. Refreshing ROI entry simulators when ROI cache exists

    This enables Stage C warm-cache path to reuse Stage A simulator/HKL caches
    while varying only detector distances (PERF-WARM-013).

    GRADIENT-004: Keeps distance offsets as tensors (no .item() conversion)
    so autograd graph remains intact for Stage C LBFGS optimization.

    PERF-WARM-016: When DBEX_STAGE_C_CACHE_DEBUG_PATH is set, emits JSON snapshots
    documenting panel/ROI distance updates and simulator IDs for offline analysis.

    Args:
        stage_a_ctx: StageAContext with cached detector_models/simulators
        distance_deltas_mm: Dict mapping panel_id to distance offset tensor (mm)
        device: torch device for Detector model instantiation
        dtype: torch dtype for Detector model instantiation
    """
    global _STAGE_C_RETARGET_CALL_COUNTER

    # PERF-WARM-016: Debug hook setup (opt-in only)
    debug_enabled = _STAGE_C_CACHE_DEBUG_PATH is not None
    debug_data = None
    if debug_enabled:
        call_idx = _STAGE_C_RETARGET_CALL_COUNTER
        _STAGE_C_RETARGET_CALL_COUNTER += 1
        debug_data = {
            "call_index": call_idx,
            "panel_updates": [],
            "roi_updates": [],
        }

    for pid, delta_mm in distance_deltas_mm.items():
        if pid >= len(stage_a_ctx.detector_models):
            continue

        # Get baseline distance and apply offset
        # Convert baseline to tensor on correct device/dtype before addition (GRADIENT-004)
        baseline_distance_mm = stage_a_ctx.baseline_distance_mm[pid]
        baseline_tensor = torch.tensor(baseline_distance_mm, device=device, dtype=dtype)
        new_distance_mm = baseline_tensor + delta_mm

        # PERF-WARM-016: Capture before-state for debug trace
        if debug_enabled:
            old_simulator = stage_a_ctx.simulators[pid]
            panel_debug = {
                "panel_id": pid,
                "distance_before_mm": float(baseline_distance_mm),
                "delta_mm": float(delta_mm.detach().cpu().item()),
                "distance_after_mm": float(new_distance_mm.detach().cpu().item()),
                "simulator_id_before": id(old_simulator),
            }

        # Clone detector config and update distance
        # Use dataclasses.replace to create new config without mutating the original
        old_detector_config = stage_a_ctx.detector_configs[pid]
        detector_config = replace(old_detector_config, distance_mm=new_distance_mm)

        # Rebuild detector model with updated config
        detector_model = Detector(detector_config, device=device, dtype=dtype)

        # Update stage_a_ctx references (mutate in place)
        stage_a_ctx.detector_configs[pid] = detector_config
        stage_a_ctx.detector_models[pid] = detector_model

        # Rebuild simulator with new detector and existing crystal
        # Reuse the existing crystal pointer so _retarget_stage_a_simulators
        # can reattach Stage A's final crystal without recreating HKL tensors
        old_simulator = stage_a_ctx.simulators[pid]
        crystal_model = old_simulator.crystal

        new_simulator = Simulator(
            detector=detector_model,
            crystal=crystal_model,
            beam_config=stage_a_ctx.beam_config,
            device=device,
            dtype=dtype,
        )
        stage_a_ctx.simulators[pid] = new_simulator

        # PERF-WARM-016: Capture after-state for debug trace
        if debug_enabled:
            panel_debug["simulator_id_after"] = id(new_simulator)
            debug_data["panel_updates"].append(panel_debug)

    # Refresh ROI entry simulators when ROI cache exists
    if stage_a_ctx.roi_entries is not None:
        for roi_idx, roi_entry in enumerate(stage_a_ctx.roi_entries):
            pid = roi_entry.panel_id

            # Only rebuild ROI simulators for panels that received distance deltas
            if pid not in distance_deltas_mm:
                continue

            # Get the updated distance from the panel's detector config
            # (already updated above in the panel loop)
            updated_distance_mm = stage_a_ctx.detector_configs[pid].distance_mm

            # PERF-WARM-016: Capture before-state for ROI debug trace
            if debug_enabled:
                old_roi_simulator = roi_entry.simulator
                old_roi_distance_mm = roi_entry.detector_model.config.distance_mm
                roi_debug = {
                    "roi_index": roi_idx,
                    "panel_id": pid,
                    "bbox": list(roi_entry.bbox) if hasattr(roi_entry, "bbox") else None,
                    "distance_before_mm": float(old_roi_distance_mm.detach().cpu().item()) if torch.is_tensor(old_roi_distance_mm) else float(old_roi_distance_mm),
                    "distance_after_mm": float(updated_distance_mm.detach().cpu().item()) if torch.is_tensor(updated_distance_mm) else float(updated_distance_mm),
                    "simulator_id_before": id(old_roi_simulator),
                }

            # Clone ROI detector config and update distance
            # Use dataclasses.replace to create new config without mutating the original
            old_roi_detector_config = roi_entry.detector_model.config
            roi_detector_config = replace(old_roi_detector_config, distance_mm=updated_distance_mm)

            # Rebuild ROI detector model
            roi_detector_model = Detector(roi_detector_config, device=device, dtype=dtype)

            # Rebuild ROI simulator with existing crystal (preserve HKL grid)
            old_roi_simulator = roi_entry.simulator
            roi_crystal_model = old_roi_simulator.crystal

            new_roi_simulator = Simulator(
                detector=roi_detector_model,
                crystal=roi_crystal_model,
                beam_config=stage_a_ctx.beam_config,
                device=device,
                dtype=dtype,
            )

            # Update ROI entry in place
            roi_entry.detector_model = roi_detector_model
            roi_entry.simulator = new_roi_simulator

            # PERF-WARM-016: Capture after-state for ROI debug trace
            if debug_enabled:
                roi_debug["simulator_id_after"] = id(new_roi_simulator)
                debug_data["roi_updates"].append(roi_debug)

    # PERF-WARM-016: Write debug snapshot to file (opt-in only)
    if debug_enabled and debug_data is not None:
        try:
            debug_dir = Path(_STAGE_C_CACHE_DEBUG_PATH)
            debug_dir.mkdir(parents=True, exist_ok=True)
            debug_file = debug_dir / f"retarget_call_{debug_data['call_index']:04d}.json"
            with open(debug_file, "w") as f:
                json.dump(debug_data, f, indent=2)
        except Exception as e:
            # Do not raise; debug hook failures must not break production runs
            warnings.warn(f"PERF-WARM-016: Debug snapshot write failed: {e}")


def _build_stage_c_params(
    shared_context: Optional['RefinementSharedContext'] = None,
    config: Optional['RefinementConfig'] = None,
    device: Optional[torch.device] = None,
    dtype: Optional[torch.dtype] = None,
    n_panels: Optional[int] = None,
    baseline_detector: Optional[Any] = None,  # dxtbx.model.Detector
    detector: Optional[Any] = None,  # dxtbx.model.Detector
    sampled_panel_ids: Optional[List[int]] = None,
    panel_slices: Optional[List[Tuple[int, int, int, int, int]]] = None,
    stage_a_ctx: Optional['StageAContext'] = None,
    sigma_floor_sq_cache: Optional[Dict[str, torch.Tensor]] = None,
    params: Optional[List[torch.Tensor]] = None,  # Stage A params to freeze
    stage_a_telemetry: Optional[Dict[str, Any]] = None  # Stage A telemetry for ROI mode check (ARCH-REFINE-001)
) -> Dict[str, Any]:
    """
    Initialize Stage C detector distance offset parameters and optimizer.

    Stage C refines per-panel translations along detector normal (distance offset)
    with crystal orientation/cell frozen from Stage A.

    ARCH-STAGE-CONTEXT-001 Phase A.4: Compatibility shim accepts either:
    - shared_context: RefinementSharedContext dataclass (new path)
    - Legacy individual parameters (backward compatibility)

    When shared_context is provided, derive config/device/dtype/detector/inputs/
    hkl_grid/hkl_metadata/panel_slices/sigma_floor_sq_cache from it.

    Returns dict with keys:
        - 'distance_offset_raw': torch.Tensor (n_panels,) trainable parameter
        - 'stage_c_params': List[torch.Tensor] (optimizer params)
        - 'stage_c_optimizer': torch.optim.LBFGS
        - 'baseline_detector_distances': Optional[List[float]] (mm per panel)
        - 'stage_c_use_warm_cache': bool
        - 'stage_c_cache_mode': str ('warm' or 'cold')
        - 'stage_c_roi_mode_active': bool
        - 'stage_c_roi_mode_label': str ('roi' or 'panel')
        - 'stage_c_roi_count_total': int
        - 'stage_c_roi_count_sampled': int
        - 'roi_slices_by_pid': Dict[int, List[Tuple[int, int, int, int]]]
        - 'force_panel_validation': bool (REFINE-011: bypass ROI for full validations when True)
        - 'perf_closure_evals_c': List[int] (mutable counter)
        - 'perf_validation_runs_c': List[int] (mutable counter)
        - 'perf_forward_times_ms_c': List[float] (mutable accumulator)
        - 'loss_trace_sample_c': List[float]
        - 'loss_trace_full_c': List[float]
        - 'best_loss_full_c': Tuple[float, int] (value, iteration)
        - 'best_params_snapshot_c': Optional[List[torch.Tensor]]
        - 'iteration_count_c': List[int] (mutable counter)
        - 'chi_squared_trace_sample_c': List[float]
        - 'chi_squared_trace_full_c': List[float]
        - 'chi_squared_best_c': Tuple[float, int]
        - 'masked_mse_trace_sample_c': List[float]
        - 'masked_mse_trace_full_c': List[float]
        - 'masked_mse_best_c': Tuple[float, int]
        - 'variance_floor_clamped_pixels_c': List[int]
        - 'variance_floor_masked_pixels_c': List[int]
        - 'sigma_floor_sq_tensor_stage_c': torch.Tensor
    """
    # ARCH-STAGE-CONTEXT-001 Phase A.4: Compatibility shim
    # When shared_context provided, extract legacy parameters from it
    if shared_context is not None:
        if config is None:
            config = shared_context.config
        if device is None:
            device = shared_context.device
        if dtype is None:
            dtype = shared_context.dtype
        if detector is None:
            detector = shared_context.detector
        if baseline_detector is None:
            baseline_detector = shared_context.baseline_detector
        if panel_slices is None:
            panel_slices = shared_context.inputs.panel_slices
        if sigma_floor_sq_cache is None:
            sigma_floor_sq_cache = shared_context.sigma_floor_sq_cache
        # n_panels derived from detector
        if n_panels is None:
            n_panels = len(detector)
    else:
        # Legacy path: validate all required parameters provided
        if config is None or device is None or dtype is None or detector is None:
            raise ValueError(
                "_build_stage_c_params requires either shared_context or "
                "(config, device, dtype, detector, ...) legacy parameters"
            )
        if panel_slices is None:
            raise ValueError("_build_stage_c_params requires panel_slices")
        if sigma_floor_sq_cache is None:
            sigma_floor_sq_cache = {}
        if n_panels is None:
            n_panels = len(detector)

    # Compute baseline_detector_distances for Stage C telemetry (TORCH-REFINE-003)
    # This is used to report initial detector offsets relative to nominal geometry
    baseline_detector_distances = None
    if baseline_detector is not None:
        baseline_detector_distances = [
            baseline_detector[pid].get_directed_distance() for pid in range(n_panels)
        ]

    # Freeze Stage A parameters (no grad)
    for p in params:
        p.requires_grad = False

    # Initialize per-panel distance offsets (mm along panel normal)
    # Start at zero (identity), bounded by tanh to ±max_distance_delta_mm
    distance_offset_raw = torch.zeros(n_panels, device=device, dtype=dtype, requires_grad=True)

    stage_c_params = [distance_offset_raw]
    # PERF-WARM-SIM-001: Stage C warm cache mirrors Stage B logic (ARCH-REFINE-001 auto-panel fix)
    # Only check stage_a_ctx existence and warm cache config flag (device/dtype always match config)
    stage_c_use_warm_cache = (
        stage_a_ctx is not None
        and config.enable_stage_a_warm_cache
    )
    stage_c_cache_mode = "warm" if stage_c_use_warm_cache else "cold"
    perf_closure_evals_c = [0]
    perf_validation_runs_c = [0]
    perf_forward_times_ms_c: List[float] = []
    roi_slices_by_pid: Dict[int, List[Tuple[int, int, int, int]]] = defaultdict(list)
    for pid, bbox in panel_slices:
        roi_slices_by_pid[int(pid)].append(tuple(int(v) for v in bbox))
    # ARCH-REFINE-001, REFINE-010: Stage C ROI mode mirrors Stage A's actual ROI mode
    # (from telemetry), not the config flag, to support auto-panel threshold
    stage_a_used_roi_mode = (stage_a_telemetry.get("roi_mode") == "roi")

    # REFINE-011: Extract Stage A validation scope to control Stage C full validations
    # When Stage A used panel-mode validations, Stage C full validations must also use panel mode
    # to ensure chi² measurements are comparable (REFINE-007 non-regression gate)
    stage_a_perf_counters = stage_a_telemetry.get('perf_counters', {})
    stage_a_validation_scope = stage_a_perf_counters.get('validation_scope', 'roi')
    force_panel_validation = (stage_a_validation_scope == 'panel')

    # REFINE-012 (revised 2025-12-01T200900Z): Re-enable ROI closures while keeping
    # panel validations. ROI closures optimize via ROI minibatching; validation_scope
    # forces panel mode independently per REFINE-011/012.
    stage_c_roi_mode_active = (
        stage_c_use_warm_cache
        and stage_a_used_roi_mode
        and len(roi_slices_by_pid) > 0
    )

    # Compute roi_mode_reason for telemetry provenance (REFINE-012 extension)
    # Only report reason when ROI mode is disabled; otherwise use empty string
    if not stage_c_roi_mode_active:
        if not stage_c_use_warm_cache:
            roi_mode_reason = "warm_cache_disabled"
        elif not stage_a_used_roi_mode:
            roi_mode_reason = "stage_a_panel_mode"
        elif len(roi_slices_by_pid) == 0:
            roi_mode_reason = "no_rois"
        else:
            roi_mode_reason = "unknown"  # should not happen
    else:
        roi_mode_reason = ""  # ROI mode active, no reason needed

    stage_c_roi_mode_label = "roi" if stage_c_roi_mode_active else "panel"

    # REFINE-011 extension: validation_scope is independent from closure ROI mode
    # Full validations MUST use panel mode whenever Stage A forced panel validations,
    # even when closures use ROI minibatching (spec-db-workflow.md:127)
    validation_scope = "panel" if force_panel_validation else stage_c_roi_mode_label
    sampled_pid_set = set(sampled_panel_ids)
    if stage_c_roi_mode_active:
        stage_c_roi_count_total = sum(len(bboxes) for bboxes in roi_slices_by_pid.values())
        stage_c_roi_count_sampled = sum(len(roi_slices_by_pid.get(pid, [])) for pid in sampled_pid_set)
    else:
        # REFINE-010: Report canonical ROI count even in panel mode (mirrors Stage A/B telemetry)
        stage_c_roi_count_total = len(panel_slices)
        stage_c_roi_count_sampled = len(panel_slices)

    # Setup LBFGS optimizer for Stage C
    stage_c_optimizer = torch.optim.LBFGS(
        stage_c_params,
        history_size=config.history_size,
        max_iter=config.max_iter,
        tolerance_grad=config.tolerance_grad,
        tolerance_change=config.tolerance_change,
        line_search_fn="strong_wolfe"
    )

    # ARCH-STAGE-CONTEXT-001 Phase B.3.2: Build Stage C telemetry state dataclass
    # Compute sigma_floor_sq_tensor once for dataclass initialization
    sigma_floor_sq_tensor_stage_c = _get_sigma_floor_sq_tensor(
        sigma_floor_sq_cache, device, dtype, config.sigma_floor_value
    )

    # Optional panel diagnostics list (PERF-WARM-SIM-001)
    panel_loss_diag_c = [] if os.environ.get('DBEX_STAGE_C_PANEL_DIAG_DIR') else None

    # Instantiate StageCTelemetryState dataclass
    telemetry_state = StageCTelemetryState(
        iteration_count=[0],
        loss_trace_sample=[],
        loss_trace_full=[],
        best_loss_full=(float('inf'), -1),
        best_params_snapshot=None,
        chi_squared_trace_sample=[],
        chi_squared_trace_full=[],
        chi_squared_best=(float('inf'), -1),
        masked_mse_trace_sample=[],
        masked_mse_trace_full=[],
        masked_mse_best=(float('inf'), -1),
        perf_closure_evals=[0],
        perf_validation_runs=[0],
        perf_forward_times_ms=[],
        variance_floor_clamped_pixels=[0],
        variance_floor_masked_pixels=[0],
        sigma_floor_sq_tensor=sigma_floor_sq_tensor_stage_c,
        panel_loss_diag=panel_loss_diag_c,
    )

    return {
        'distance_offset_raw': distance_offset_raw,
        'stage_c_params': stage_c_params,
        'stage_c_optimizer': stage_c_optimizer,
        'baseline_detector_distances': baseline_detector_distances,
        'stage_c_use_warm_cache': stage_c_use_warm_cache,
        'stage_c_cache_mode': stage_c_cache_mode,
        'stage_c_roi_mode_active': stage_c_roi_mode_active,
        'stage_c_roi_mode_label': stage_c_roi_mode_label,
        'stage_c_roi_count_total': stage_c_roi_count_total,
        'stage_c_roi_count_sampled': stage_c_roi_count_sampled,
        'roi_slices_by_pid': roi_slices_by_pid,
        'force_panel_validation': force_panel_validation,  # REFINE-011: For Stage C full validation bypass
        'roi_mode_reason': roi_mode_reason,  # REFINE-012: Provenance tag for ROI-mode decision
        'validation_scope': validation_scope,  # REFINE-011/012: Independent from closure mode (panel when forced)
        # ARCH-STAGE-CONTEXT-001 Phase B.3.2: Replace individual telemetry fields with dataclass
        'telemetry_state': telemetry_state,
        # Legacy fields for backward compatibility (to be removed in Phase C)
        'perf_closure_evals_c': telemetry_state.perf_closure_evals,
        'perf_validation_runs_c': telemetry_state.perf_validation_runs,
        'perf_forward_times_ms_c': telemetry_state.perf_forward_times_ms,
        'loss_trace_sample_c': telemetry_state.loss_trace_sample,
        'loss_trace_full_c': telemetry_state.loss_trace_full,
        'best_loss_full_c': telemetry_state.best_loss_full,
        'best_params_snapshot_c': telemetry_state.best_params_snapshot,
        'iteration_count_c': telemetry_state.iteration_count,
        'chi_squared_trace_sample_c': telemetry_state.chi_squared_trace_sample,
        'chi_squared_trace_full_c': telemetry_state.chi_squared_trace_full,
        'chi_squared_best_c': telemetry_state.chi_squared_best,
        'masked_mse_trace_sample_c': telemetry_state.masked_mse_trace_sample,
        'masked_mse_trace_full_c': telemetry_state.masked_mse_trace_full,
        'masked_mse_best_c': telemetry_state.masked_mse_best,
        'variance_floor_clamped_pixels_c': telemetry_state.variance_floor_clamped_pixels,
        'variance_floor_masked_pixels_c': telemetry_state.variance_floor_masked_pixels,
        'sigma_floor_sq_tensor_stage_c': telemetry_state.sigma_floor_sq_tensor,
    }


# ARCH-STAGE-CONTEXT-001 Phase B.2.3: _build_stage_c_lbfgs_closure moved to StageC._build_lbfgs_closure
# See dbex/refinement/stage_c.py::StageC._build_lbfgs_closure for the implementation


def _run_stage_c_lbfgs(
    config: 'RefinementConfig',
    device: torch.device,
    dtype: torch.dtype,
    param_values: Dict[str, Any],
    telemetry_state: Dict[str, Any],
    stage_c_context: Dict[str, Any],
    compute_loss_stage_c: Callable,
    closure_stage_c: Callable,
    crystal,  # dxtbx Crystal
    hkl_grid: torch.Tensor,
    hkl_metadata: Dict,
    detector,  # dxtbx Detector
    beam,  # dxtbx Beam
    inputs,  # DataLoad (untyped to avoid import)
    canonical_baseline: Dict[str, Any],
    stage_a_ctx: Optional[StageAContext],
    n_panels: int,
    collector: Any,
) -> Dict[str, Any]:
    """
    Execute Stage C LBFGS optimization, final validation, improvement gate,
    best snapshot restore, final Bragg regeneration, and telemetry packaging.

    Args:
        collector: StageCTelemetryCollector for observer-based telemetry
                   (ARCH-TELEMETRY-001 Phase C.1). Required parameter.

    Returns dict with keys:
        - 'status_c': str ('ok', 'early_stop', 'error')
        - 'message_c': str
        - 'telemetry_c': RefinementTelemetry
        - 'bragg_full': np.ndarray (n_panels, slow, fast)
        - 'final_step_c': int
        - 'final_loss_value_c': float
        - 'final_mse_value_c': float
    """
    # Import RefinementTelemetry (lazy to avoid circular import at module load)
    # ARCH-REFINE-001 Phase C.1: Import from canonical location
    from dbex.refinement import RefinementTelemetry

    # Extract from param_values dict
    distance_offset_raw = param_values['distance_offset_raw']
    stage_c_params = param_values['stage_c_params']
    stage_c_optimizer = param_values['stage_c_optimizer']
    log_scale = param_values['log_scale']
    log_scale_baseline = param_values.get('log_scale_baseline')  # REFINE-015: Stage A baseline for clamp logic
    log_cell_a_delta = param_values.get('log_cell_a_delta')
    log_cell_b_delta = param_values.get('log_cell_b_delta')
    log_cell_c_delta = param_values.get('log_cell_c_delta')
    angle_alpha_raw = param_values.get('angle_alpha_raw')
    angle_beta_raw = param_values.get('angle_beta_raw')
    angle_gamma_raw = param_values.get('angle_gamma_raw')
    orientation_vec = param_values.get('orientation_vec')
    baseline_misset_deg_tensor = param_values.get('baseline_misset_deg_tensor')

    # Extract from telemetry_state dataclass (ARCH-STAGE-CONTEXT-001 Phase E: dataclass-only)
    chi_squared_best_c = telemetry_state.chi_squared_best
    masked_mse_best_c = telemetry_state.masked_mse_best
    best_params_snapshot_c = telemetry_state.best_params_snapshot
    iteration_count_c = telemetry_state.iteration_count
    loss_trace_sample_c = telemetry_state.loss_trace_sample
    loss_trace_full_c = telemetry_state.loss_trace_full
    chi_squared_trace_sample_c = telemetry_state.chi_squared_trace_sample
    chi_squared_trace_full_c = telemetry_state.chi_squared_trace_full
    masked_mse_trace_sample_c = telemetry_state.masked_mse_trace_sample
    masked_mse_trace_full_c = telemetry_state.masked_mse_trace_full
    variance_floor_clamped_pixels_c = telemetry_state.variance_floor_clamped_pixels
    variance_floor_masked_pixels_c = telemetry_state.variance_floor_masked_pixels
    perf_closure_evals_c = telemetry_state.perf_closure_evals
    perf_validation_runs_c = telemetry_state.perf_validation_runs
    perf_forward_times_ms_c = telemetry_state.perf_forward_times_ms
    best_loss_full_c = telemetry_state.best_loss_full

    # Extract from stage_c_context dict
    stage_c_use_warm_cache = stage_c_context['stage_c_use_warm_cache']
    stage_c_cache_mode = stage_c_context['stage_c_cache_mode']
    stage_c_roi_mode_label = stage_c_context['stage_c_roi_mode_label']
    stage_c_roi_count_total = stage_c_context['stage_c_roi_count_total']
    stage_c_roi_count_sampled = stage_c_context['stage_c_roi_count_sampled']
    baseline_detector_distances = stage_c_context.get('baseline_detector_distances')
    sampled_panel_ids = stage_c_context['sampled_panel_ids']
    _apply_baseline_detector_prior = stage_c_context['_apply_baseline_detector_prior']
    misset_deg_for_crystal = stage_c_context['misset_deg_for_crystal']
    force_panel_validation = stage_c_context['force_panel_validation']  # REFINE-011
    roi_mode_reason = stage_c_context['roi_mode_reason']  # REFINE-012
    validation_scope = stage_c_context['validation_scope']  # REFINE-012

    # Extract from canonical_baseline dict (needed for improvement gate)
    best_loss_full = (canonical_baseline['chi_squared'], canonical_baseline['iteration'])

    # Derived variables
    panel_shape = inputs.target.shape[1:]

    # Run Stage C LBFGS optimization
    status_c = "ok"
    message_c = ""

    try:
        # PERF-WARM-SIM-001: Evaluate baseline loss BEFORE applying baseline detector prior
        # This captures the Stage A final state (distance_offset_raw still zero) as iteration -1
        # so telemetry traces always include the canonical reference for REFINE-007 diagnostics
        with torch.no_grad():
            baseline_chi2_c, baseline_mse_c = compute_loss_stage_c(
                list(range(n_panels)), is_full=True, force_panel_eval=force_panel_validation
            )
            baseline_chi2_value = float(baseline_chi2_c.item())
            baseline_mse_value = float(baseline_mse_c.item())

            # Build baseline snapshot
            snapshot_data = {
                'distance_offset_raw': distance_offset_raw.detach().cpu().tolist()
            }

            # ARCH-TELEMETRY-001 Phase C.1: Route baseline validation through collector (observer pattern)
            # Observer path: emit baseline validation via collector (iteration -1)
            payload = {
                'loss': baseline_chi2_value,
                'masked_mse': baseline_mse_value,
                'best_snapshot': snapshot_data,
            }
            # Temporarily override iteration_count to -1 for baseline
            saved_iter = telemetry_state.iteration_count[0]
            telemetry_state.iteration_count[0] = -1
            collector.on_validation(
                scope='baseline',
                chi2=baseline_chi2_value,
                payload=payload,
            )
            telemetry_state.iteration_count[0] = saved_iter

        # Apply baseline detector prior BEFORE LBFGS so the warm-start is captured in best snapshot
        # (REFINE-013: The rehydration after LBFGS reloads best_params_snapshot_c, which must include the prior)
        _apply_baseline_detector_prior()

        stage_c_optimizer.step(closure_stage_c)

        # ARCH-TELEMETRY-001 Phase C.1: Fallback when LBFGS exits without running closure
        # If no closure evals occurred, seed baseline sample so loss_trace_sample is never empty
        # Treat the seeded baseline as a synthetic closure so perf_closure_evals stays consistent
        if perf_closure_evals_c[0] == 0:
            collector.ensure_sample_trace(
                loss=baseline_chi2_value,
                metrics={
                    'chi_squared': baseline_chi2_value,
                    'masked_mse': baseline_mse_value,
                },
                increment_counter=True
            )

        # Assert that at least one full validation populated the best snapshot
        if chi_squared_best_c[0] >= float('inf'):
            raise RuntimeError(
                "Stage C best snapshot never recorded: chi_squared_best_c remains infinite after LBFGS. "
                "Check that full_validation_interval allows at least one periodic validation."
            )

    except Exception as e:
        status_c = "error"
        message_c = str(e)
        # Use best snapshot if available
        if best_params_snapshot_c is not None:
            distance_offset_raw.data = torch.tensor(best_params_snapshot_c['distance_offset_raw'], device=device, dtype=dtype)

    # ARCH-TELEMETRY-001 Phase C.1: Extract current best tuples from telemetry_state before final validation
    # (Will be finalized after final validation is recorded)
    chi_squared_best_c = telemetry_state.chi_squared_best
    masked_mse_best_c = telemetry_state.masked_mse_best
    best_loss_full_c = telemetry_state.best_loss_full
    best_params_snapshot_c = telemetry_state.best_params_snapshot

    # ARCH-TELEMETRY-001 Phase C.1: Ensure sample traces are populated before finalization
    # When LBFGS exits without closure evals, seed baseline sample so gates can read meaningful data
    # Treat the seeded baseline as a synthetic closure so perf_closure_evals stays consistent
    if len(telemetry_state.loss_trace_sample) == 0:
        collector.ensure_sample_trace(
            loss=baseline_chi2_value,
            metrics={
                'chi_squared': baseline_chi2_value,
                'masked_mse': baseline_mse_value,
            },
            increment_counter=True
        )

    final_step_c = telemetry_state.iteration_count[0]
    with torch.no_grad():
        # REFINE-011: Use panel mode for final validation when Stage A used panel mode
        candidate_final_chi2, candidate_final_mse = compute_loss_stage_c(
            list(range(n_panels)), is_full=True, force_panel_eval=force_panel_validation
        )
    candidate_loss_value_c = float(candidate_final_chi2.item())
    candidate_mse_value_c = float(candidate_final_mse.item())
    if candidate_loss_value_c < chi_squared_best_c[0]:
        chi_squared_best_c = (candidate_loss_value_c, final_step_c)
        best_loss_full_c = (candidate_loss_value_c, final_step_c)
        best_params_snapshot_c = {
            'distance_offset_raw': distance_offset_raw.detach().cpu().tolist()
        }
        # REFINE-013: Persist best tuples to telemetry_state so final telemetry reflects best snapshot
        # ARCH-STAGE-CONTEXT-001 Phase E: dataclass-only
        telemetry_state.chi_squared_best = chi_squared_best_c
        telemetry_state.best_loss_full = best_loss_full_c
        telemetry_state.best_params_snapshot = best_params_snapshot_c
    if candidate_mse_value_c < masked_mse_best_c[0]:
        masked_mse_best_c = (candidate_mse_value_c, final_step_c)
        # REFINE-013: Persist masked_mse_best_c to telemetry_state
        # ARCH-STAGE-CONTEXT-001 Phase E: dataclass-only
        telemetry_state.masked_mse_best = masked_mse_best_c

    # REFINE-013: Use best chi-squared from periodic validations for final telemetry
    # The best snapshot was already validated during LBFGS, so use stored values directly
    final_loss_value_c = chi_squared_best_c[0] if chi_squared_best_c[0] < float('inf') else candidate_loss_value_c
    final_mse_value_c = masked_mse_best_c[0] if masked_mse_best_c[0] < float('inf') else candidate_mse_value_c

    # REFINE-013: Reload best parameters before final trace entry
    # This ensures final Bragg regeneration uses optimal parameters, not last iterate
    if best_params_snapshot_c is not None and chi_squared_best_c[0] < float('inf'):
        distance_offset_raw.data = torch.tensor(
            best_params_snapshot_c['distance_offset_raw'],
            device=device,
            dtype=dtype,
        )

    # ARCH-TELEMETRY-001 Phase C.1: Route final validation through collector (observer pattern)
    # Emit final validation to capture end-of-optimization metrics
    final_snapshot_data = {
        'distance_offset_raw': distance_offset_raw.detach().cpu().tolist()
    }
    final_payload = {
        'loss': final_loss_value_c,
        'masked_mse': final_mse_value_c,
        'best_snapshot': final_snapshot_data,
    }
    collector.on_validation(
        scope='final',
        chi2=final_loss_value_c,
        payload=final_payload,
    )

    # ARCH-TELEMETRY-001 Phase C.1: Finalize collector AFTER final validation is recorded
    # Now extract telemetry via StageResult.to_legacy_dict() for RefinementTelemetry construction
    stage_result = collector.finalize()
    legacy_telemetry_dict = stage_result.to_legacy_dict()

    # Refresh telemetry fields from finalized collector (includes final validation)
    # Note: to_legacy_dict() wraps perf counters in lists for legacy schema compatibility
    loss_trace_sample_c = legacy_telemetry_dict['loss_trace_sample']
    loss_trace_full_c = legacy_telemetry_dict['loss_trace_full']
    chi_squared_trace_sample_c = legacy_telemetry_dict['chi_squared_trace_sample']
    chi_squared_trace_full_c = legacy_telemetry_dict['chi_squared_trace_full']
    masked_mse_trace_sample_c = legacy_telemetry_dict['masked_mse_trace_sample']
    masked_mse_trace_full_c = legacy_telemetry_dict['masked_mse_trace_full']
    iteration_count_c = legacy_telemetry_dict['iteration_count']
    perf_closure_evals_c = legacy_telemetry_dict['perf_closure_evals'][0]
    perf_validation_runs_c = legacy_telemetry_dict['perf_validation_runs'][0]
    perf_forward_times_ms_c = legacy_telemetry_dict['perf_forward_times_ms']
    variance_floor_clamped_pixels_c = legacy_telemetry_dict['variance_floor_clamped_pixels'][0]
    variance_floor_masked_pixels_c = legacy_telemetry_dict['variance_floor_masked_pixels'][0]

    # Check convergence: did we achieve ≥5% improvement on top of Stage A?
    if best_loss_full[0] is not None and best_loss_full[0] > 0:
        stage_a_final_loss = best_loss_full[0]
        improvement_c = (stage_a_final_loss - final_loss_value_c) / stage_a_final_loss
        if improvement_c < config.stage_c_min_loss_improvement:
            status_c = "early_stop"
            message_c = f"Stage C improvement {improvement_c:.4%} < {config.stage_c_min_loss_improvement:.4%} (≥0.002% gate calibrated per REFINE-007)"

    # Generate final Bragg array with Stage C adjustments
    with torch.no_grad():
        bragg_full_stage_c = np.zeros((n_panels, *panel_shape), dtype=np.float32)
        cell_params = crystal.get_unit_cell().parameters()
        log_cell_a_delta_clamped, log_cell_b_delta_clamped, log_cell_c_delta_clamped = _clamp_log_cell_deltas(
            log_cell_a_delta,
            log_cell_b_delta,
            log_cell_c_delta,
            getattr(config, "log_cell_max_delta", 1.0),
        )
        perturbed_cell_a = cell_params[0] * torch.exp(log_cell_a_delta_clamped)
        perturbed_cell_b = cell_params[1] * torch.exp(log_cell_b_delta_clamped)
        perturbed_cell_c = cell_params[2] * torch.exp(log_cell_c_delta_clamped)
        max_angle_delta = 10.0
        perturbed_alpha = cell_params[3] + torch.tanh(angle_alpha_raw) * max_angle_delta
        perturbed_beta = cell_params[4] + torch.tanh(angle_beta_raw) * max_angle_delta
        perturbed_gamma = cell_params[5] + torch.tanh(angle_gamma_raw) * max_angle_delta
        max_orientation_deg = 3.0
        bounded_orientation_vec = torch.tanh(orientation_vec) * max_orientation_deg * (np.pi / 180.0)
        quat = vec_to_unit_quaternion(bounded_orientation_vec)
        misset_xyz_deg = quaternion_to_xyz_euler(quat)

        if baseline_misset_deg_tensor is not None:
            misset_xyz_deg = misset_xyz_deg + baseline_misset_deg_tensor

        crystal_overrides = {
            'cell_a': perturbed_cell_a,
            'cell_b': perturbed_cell_b,
            'cell_c': perturbed_cell_c,
            'cell_alpha': perturbed_alpha,
            'cell_beta': perturbed_beta,
            'cell_gamma': perturbed_gamma
        }
        crystal_config, _ = create_crystal_config(
            crystal,
            None,
            crystal_overrides=crystal_overrides,
            misset_deg_override=misset_deg_for_crystal
        )
        crystal_model = Crystal(crystal_config, device=device, dtype=dtype)
        crystal_model.interpolate = config.enable_hkl_interpolation
        crystal_model.hkl_data = hkl_grid.to(device=device, dtype=dtype)
        crystal_model.hkl_metadata = hkl_metadata

        # PERF-WARM-013: Retarget cached detectors before final reconstruction loop
        if stage_c_use_warm_cache:
            distance_deltas_mm_final = {}
            for pid in range(n_panels):
                bounded_offset = torch.tanh(distance_offset_raw[pid]) * config.stage_c_max_distance_delta_mm
                # Keep as tensor to preserve autograd graph (GRADIENT-004)
                distance_deltas_mm_final[pid] = bounded_offset

            _retarget_stage_a_detectors(
                stage_a_ctx=stage_a_ctx,
                distance_deltas_mm=distance_deltas_mm_final,
                device=device,
                dtype=dtype
            )

        for pid in range(n_panels):
            panel = detector[pid]

            if stage_c_use_warm_cache:
                # Warm path: reuse retargeted detector/simulator from stage_a_ctx
                detector_model = stage_a_ctx.detector_models[pid]
                simulator = stage_a_ctx.simulators[pid]
                # Attach final crystal model
                simulator.crystal = crystal_model
                simulator.beam_config = stage_a_ctx.beam_config
            else:
                # Cold path: instantiate fresh (existing code, keep AS-IS)
                # Apply final bounded distance offset
                bounded_offset = torch.tanh(distance_offset_raw[pid]) * config.stage_c_max_distance_delta_mm
                baseline_distance_mm = panel.get_directed_distance()
                distance_mm_override = baseline_distance_mm + bounded_offset

                detector_config = create_detector_config(
                    panel=panel,
                    beam=beam,
                    trusted_mask=inputs.trusted_mask[pid],
                    distance_mm_override=distance_mm_override
                )

                if detector_config.mask_array is not None and not isinstance(detector_config.mask_array, torch.Tensor):
                    detector_config.mask_array = torch.tensor(
                        detector_config.mask_array, dtype=torch.float32, device=device
                    )

                detector_model = Detector(detector_config, device=device, dtype=dtype)
                simulator = Simulator(detector=detector_model, crystal=crystal_model, device=device, dtype=dtype)

            panel_bragg = simulator.run()

            # REFINE-015: Apply Stage A's log-scale clamp logic in final Stage C reconstruction
            # When calibration metadata supplied the baseline:
            #   log_scale_clamped = log_scale_baseline + clamp(delta, ±config.log_scale_max_delta)
            # Otherwise (uncalibrated):
            #   log_scale_clamped = clamp(delta, ±config.log_scale_max_delta_uncalibrated)
            max_delta_uncal = getattr(config, "log_scale_max_delta_uncalibrated", 10.0)
            delta_bound = config.log_scale_max_delta if log_scale_baseline is not None else max_delta_uncal
            if log_scale_baseline is not None:
                log_scale_delta_clamped = torch.clamp(log_scale, min=-delta_bound, max=delta_bound)
                log_scale_clamped = log_scale_baseline + log_scale_delta_clamped
            else:
                # Absolute clamp when no baseline is available
                log_scale_clamped = torch.clamp(log_scale, min=-delta_bound, max=delta_bound)
            panel_bragg_scaled = panel_bragg * torch.exp(log_scale_clamped)
            bragg_full_stage_c[pid] = panel_bragg_scaled.cpu().numpy().astype(np.float32)

    # Assemble Stage C telemetry
    param_deltas_c = {}
    for pid in range(n_panels):
        bounded_offset = torch.tanh(distance_offset_raw[pid]) * config.stage_c_max_distance_delta_mm
        bounded_offset_value = float(bounded_offset.item())
        initial_offset_mm = 0.0
        if baseline_detector_distances is not None:
            initial_offset_mm = detector[pid].get_directed_distance() - baseline_detector_distances[pid]
        final_offset_mm = initial_offset_mm + bounded_offset_value
        param_deltas_c[f'panel_{pid}_distance_offset_mm'] = {
            'initial': initial_offset_mm,
            'final': final_offset_mm,
            'delta': bounded_offset_value
        }

    forward_stats_c = {
        'mean': float(np.mean(perf_forward_times_ms_c)) if perf_forward_times_ms_c else 0.0,
        'min': float(np.min(perf_forward_times_ms_c)) if perf_forward_times_ms_c else 0.0,
        'max': float(np.max(perf_forward_times_ms_c)) if perf_forward_times_ms_c else 0.0,
        'total': float(np.sum(perf_forward_times_ms_c)) if perf_forward_times_ms_c else 0.0,
    }
    perf_counters_c = {
        'cache_mode': stage_c_cache_mode,
        'roi_mode': stage_c_roi_mode_label,
        'roi_mode_reason': roi_mode_reason,  # REFINE-012: Provenance for ROI-mode decision
        'validation_scope': validation_scope,  # REFINE-011/012: Independent from closure mode (panel when forced)
        'roi_count_total': stage_c_roi_count_total,
        'roi_count_sampled': stage_c_roi_count_sampled,
        'closure_evals': perf_closure_evals_c,
        'validation_runs': perf_validation_runs_c,
        'forward_time_ms': forward_stats_c,
    }

    telemetry_c = RefinementTelemetry(
        optimizer="LBFGS",
        stage="C",
        history_size=config.history_size,
        max_iter=config.max_iter,
        tolerance_grad=config.tolerance_grad,
        tolerance_change=config.tolerance_change,
        roi_sample_fraction=config.roi_sample_fraction,
        roi_count_sampled=stage_c_roi_count_sampled,
        roi_count_total=stage_c_roi_count_total,
        loss_trace_sample=loss_trace_sample_c,
        loss_trace_full=loss_trace_full_c,
        best_loss_full=best_loss_full_c,
        param_deltas=param_deltas_c,
        status=status_c,
        message=message_c,
        perf_counters=perf_counters_c,
        # PHYSICS-LOSS-001: Dual loss metrics
        chi_squared_trace_sample=chi_squared_trace_sample_c,
        chi_squared_trace_full=chi_squared_trace_full_c,
        chi_squared_best=chi_squared_best_c,
        masked_mse_trace_sample=masked_mse_trace_sample_c,
        masked_mse_trace_full=masked_mse_trace_full_c,
        masked_mse_best=masked_mse_best_c,
        sigma_readout_provenance=config.sigma_readout_provenance,
        sigma_readout_reference_value=config.sigma_readout_reference_value,
        # PHYSICS-LOSS-002: Variance floor telemetry
        variance_floor_value=config.sigma_floor_value**2,
        variance_floor_clamp_fraction=(
            float(variance_floor_clamped_pixels_c) / float(variance_floor_masked_pixels_c)
            if variance_floor_masked_pixels_c > 0 else 0.0
        ),
        canonical_stage_label=canonical_baseline["stage_label"],
        canonical_chi_squared=canonical_baseline["chi_squared"],
        canonical_chi_squared_iteration=canonical_baseline["iteration"],
        canonical_roi_count=canonical_baseline["roi_count"],
        canonical_detector_distances_mm=canonical_baseline["detector_distances_mm"],
        roi_mode=stage_c_roi_mode_label,
    )

    # PERF-WARM-SIM-001 Phase D.4: Write panel-loss diagnostics JSON if collected
    panel_diag_dir = os.environ.get('DBEX_STAGE_C_PANEL_DIAG_DIR')
    # ARCH-STAGE-CONTEXT-001 Phase E: dataclass-only
    if panel_diag_dir and telemetry_state.panel_loss_diag is not None:
        diag_path = Path(panel_diag_dir)
        diag_path.mkdir(parents=True, exist_ok=True)
        diag_file = diag_path / 'stage_c_panel_diag.json'
        with open(diag_file, 'w') as f:
            json.dump({
                'stage': 'C',
                'panels': telemetry_state.panel_loss_diag,
                'n_panels': len(set(p['panel_id'] for p in telemetry_state.panel_loss_diag)) if telemetry_state.panel_loss_diag else 0,
            }, f, indent=2)

    return {
        'status_c': status_c,
        'message_c': message_c,
        'telemetry_c': telemetry_c,
        'bragg_full': bragg_full_stage_c,
        'final_step_c': final_step_c,
        'final_loss_value_c': final_loss_value_c,
        'final_mse_value_c': final_mse_value_c,
    }
