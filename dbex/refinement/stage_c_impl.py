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

ARCH-REFACTOR-001 Phase C.2 (2025-12-04):
- _build_stage_c_params moved to StageC._build_stage_c_params (dbex/refinement/stage_c.py)
- _run_stage_c_lbfgs moved to StageC._run_lbfgs (dbex/refinement/stage_c.py)
- _build_stage_c_lbfgs_closure moved to StageC._build_lbfgs_closure (dbex/refinement/stage_c.py)
  per ARCH-STAGE-CONTEXT-001 Phase B.2.3

This module will be deleted in Phase C.3 once _retarget_stage_a_detectors is moved in-house.
"""

import json
import os
import warnings
from dataclasses import replace
from pathlib import Path
from typing import Dict

import torch

# ARCH-LAZY-IMPORTS-001 / ARCH-ENGINE-002: Module-scope dependencies for Stage C
from nanobrag_torch.models import Detector
from nanobrag_torch.simulator import Simulator

# Import Stage A helpers for shared utilities
from dbex.refinement.stage_a_impl import StageAContext

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
