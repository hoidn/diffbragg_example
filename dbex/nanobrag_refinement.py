"""
LBFGS refinement nucleus for nanobrag_torch backend (Stage A/B/C).

Implements the staged refinement loop per:
- plans/nanobrag_integration_plan.md:172-244 (Refinement + Stage B contract)
- docs/spec-db-workflow.md:30-41 (Staging policy + LBFGS optimizer)
- docs/pytorch_runtime_checklist.md (vectorization, device/dtype neutrality)

Stage A scope:
- Parameters: global scale (ADU mode) + full crystal (a/b/c log-deltas, alpha/beta/gamma bounded angles, orientation 3-vector→quaternion)
- Loss: variance-weighted chi-squared per dbex.physics.loss._compute_variance_weighted_loss
        (spec-db-core.md/spec-db-workflow.md), with masked MSE tracked for telemetry.
- ROI policy: deterministic ROI sampling for LBFGS closure; periodic full validation
- Convergence: ≥0.2% loss drop within ≤30 LBFGS steps; non-increasing full-loss trace (TORCH-REFINE-002D)

Stage B (optional, TORCH-REFINE-004):
- Parameters: per-resolution shell multipliers for |F| (softplus parameterization)
- Requires: halo-padded HKL grid (hkl_metadata["has_halo"]=True) and enable_hkl_interpolation=True
- Freezes Stage A parameters; applies modifiers lazily to a copy of hkl_grid
- Convergence: ≥3% loss drop; guards against default_F fallback

Stage C (optional, TORCH-REFINE-003):
- Parameters: per-panel detector distance offsets along normal
- Freezes Stage A (and Stage B if run) parameters
- Convergence: ≥0.002% loss drop (REFINE-007)

Telemetry emitted to `/torch_diagnostics`:
- Per-stage: optimizer metadata, stage label, ROI sampling, loss traces, param_deltas, status
- Multi-stage runs return Dict[str, RefinementTelemetry] keyed by stage ("A", "B", "C")
"""

import copy
import math
import os
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import torch

# Stage A quaternion helpers relocated to stage_a_utils (ARCH-REFACTOR-001 Phase C.7)
from dbex.refinement.stage_a_utils import (
    vec_to_unit_quaternion,
    quaternion_to_rotation_matrix,
    quaternion_to_xyz_euler,
    _build_stage_a_context,
    _retarget_stage_a_simulators,
    _clamp_log_cell_deltas,
    _get_sigma_floor_sq_tensor,
)
# Stage A dataclasses relocated to context.py (ARCH-REFACTOR-001 Phase C.9)
from dbex.refinement.context import StageAROIEntry, StageAContext

# Stage B helpers relocated to dbex.refinement.stage_b_impl (ARCH-REFINE-001)
# ARCH-REFACTOR-001 Phase C.5: HKL utilities extracted to hkl_utils.py for cross-stage reuse
from dbex.refinement.hkl_utils import (
    compute_hkl_shell_lookup,
    compute_hkl_asu_map,
    initialize_asu_modifiers,
    apply_asu_modifiers,
)
# ARCH-REFACTOR-001 Phase C.6: stage_b_impl imports removed (facade no longer calls these helpers directly)

# Stage C helpers relocated to dbex.refinement.stage_c (ARCH-REFACTOR-001 Phase C.3)
# All Stage C implementation helpers now live within the StageC class as private methods.

from dbex.physics.loss import _compute_variance_weighted_loss
# ARCH-REFINE-001 Phase C.1: Import canonical RefinementTelemetry from dbex.refinement
from dbex.refinement import RefinementTelemetry

# Temporary backward compatibility re-export (Phase D.1)
# Remove after Phase D.5 facade deletion
from dbex.refinement.config import RefinementConfig  # noqa: F401


# ARCH-REFACTOR-001 Phase D.1: RefinementConfig relocated to dbex/refinement/config.py
# Original definition (former lines 74-191) deleted; facade now re-exports from canonical module
# This ensures backward compatibility during incremental migration (Phases D.2-D.4)


# ARCH-REFINE-001 Phase C.1: RefinementTelemetry now imported from dbex.refinement (canonical definition)
# Duplicate class definition removed; see dbex/refinement/stage.py for the authoritative schema


# ARCH-ENGINE-ARTIFACTS-001 Phase C.1: Final Bragg arrays now exclusively sourced from artifact channel
# Reconstruction helpers (build_final_bragg_from_stage_a/b_telemetry) no longer called from this module
# See dbex/refinement/reconstruction.py for reconstruction helpers used by parity tests


def run_nanobrag_refinement(
    inputs,
    detector,
    beam,
    crystal,
    hkl_grid: torch.Tensor,
    hkl_metadata: Dict,
    config: Optional[RefinementConfig] = None,
    baseline_crystal=None,
    baseline_detector=None,
    job_context: Optional['JobContext'] = None
) -> Tuple[np.ndarray, Dict[str, RefinementTelemetry], Dict[str, Any]]:
    """
    Run Stage A (+ optional Stage C) LBFGS refinement on nanobrag_torch simulator.

    Stage A optimizes:
    - log_scale: global intensity scale (ADU mode)
    - log_cell_*_delta: unit cell length perturbations (a/b/c)
    - angle_*_raw: unit cell angle perturbations (alpha/beta/gamma)
    - orientation_vec: crystal misorientation (3-vector → quaternion → XYZ Euler)

    Stage C (when config.enable_stage_c=True) optimizes:
    - per-panel detector distance offsets along panel normal (odet_vec)

    Args:
        inputs: RefinementInputs with target, loss_mask, panel_slices, trusted_mask
        detector: dxtbx Detector object (multi-panel, possibly perturbed for Stage C smoke)
        beam: dxtbx Beam object
        crystal: dxtbx Crystal object (possibly perturbed from baseline)
        hkl_grid: torch.Tensor structure factor grid (P1 dense)
        hkl_metadata: dict with grid dimensions and metadata
        config: Optional RefinementConfig; uses defaults if None
        baseline_crystal: Optional baseline dxtbx Crystal object for extracting deterministic
                        misset when `crystal` is perturbed (TORCH-REFINE-002D). When provided,
                        computes U_delta = U_perturbed @ U_baseline^{-1} and adds it to the
                        orientation refinement path as a tensor to preserve differentiability.
        baseline_detector: Optional dxtbx Detector capturing the unperturbed geometry. When
                        provided, Stage C telemetry records initial/final offsets relative to this
                        baseline; otherwise offsets are reported relative to the perturbed detector.
        job_context: Optional JobContext from dbex.refinement.context encapsulating CLI args,
                    DataLoad, calibration metadata, sigma provenance, HKL metadata/ASU map, and
                    RefinementConfig so stages can access consistent job metadata without recomputing.
                    When provided, RefinementEngine inputs include 'job_context' key for future
                    telemetry/IO work. (ARCH-REFINE-001 Phase B.2)

    Returns:
        Tuple of:
        - Bragg: np.ndarray [panel, slow, fast] final simulated intensities after all stages (CPU, float32)
        - telemetry_dict: Dict[str, RefinementTelemetry] keyed by stage label ("A", "B", "C")
                         Always contains "A"; contains "B"/"C" when respective stages enabled
        - artifacts: Dict[str, Any] from RefinementEngine.artifacts containing stage-specific metadata
                    (ARCH-STAGE-CONTEXT-001 Phase B.4: enables writer to access Stage B baseline metrics
                    without telemetry shims)

    Raises:
        RuntimeError: If simulator fails or gradients are NaN/Inf
    """
    if os.environ.get("NANOBRAGG_DISABLE_COMPILE") == "1":
        os.environ.setdefault("TORCHDYNAMO_DISABLE", "1")
    from nanobrag_torch.simulator import Simulator
    from nanobrag_torch.models.detector import Detector
    from nanobrag_torch.models.crystal import Crystal
    from dbex.refinement.config_factories import (
        create_detector_config,
        create_beam_config,
        create_crystal_config,
    )
    from dbex.nanobrag_bridge import compute_baseline_misset_deg

    if config is None:
        config = RefinementConfig()

    # Detect Stage-A-only mode for conditional engine delegation (Phase B2)
    stage_a_only_mode = (not config.enable_stage_c and not config.enable_stage_b)

    # Detect Stage A→B mode for conditional engine delegation (Phase C2)
    stage_a_b_mode = (not config.enable_stage_c and config.enable_stage_b)

    if stage_a_only_mode:
        # === ENGINE DELEGATION PATH (Phase B2) ===
        # Lazy imports to avoid circular dependencies at module load time
        from dbex.refinement.context import build_refinement_context
        from dbex.refinement.engine import RefinementEngine
        from dbex.refinement.stage_a import StageA

        # Build RefinementContext per ARCH-REFINE-001 Phase B.1/B.3
        # Thread CLI-built HKL halo + ASU metadata from job_context (REFINE-005, REFINE-010)
        context = build_refinement_context(
            refinement_inputs=inputs,
            detector=detector,
            beam=beam,
            crystal=crystal,
            hkl_grid=hkl_grid,
            hkl_metadata=hkl_metadata,
            baseline_crystal=baseline_crystal,
            baseline_detector=baseline_detector,
            job_context=job_context,
        )

        # Build inputs dict per StageA.run() contract (dbex/refinement/stage_a.py:71-78)
        # Pass context via 'context' key per ARCH-REFINE-001 Phase B.1
        engine_inputs = {
            'context': context,
            'refinement_inputs': inputs,
            'detector': detector,
            'beam': beam,
            'crystal': crystal,
            'hkl_grid': hkl_grid,
            'hkl_metadata': hkl_metadata,
            'baseline_crystal': baseline_crystal,
            'baseline_detector': baseline_detector,
            'job_context': job_context,  # ARCH-REFINE-001 Phase B.2
        }

        # Instantiate RefinementEngine with StageA
        engine = RefinementEngine(stages=[StageA()], config=config)

        # Execute engine and get telemetry dict (keyed by stage.name = "stage_a")
        telemetry_dict = engine.run(engine_inputs)

        # ARCH-STAGE-CONTEXT-001 Phase B.1: Extract stage_a_ctx from artifacts instead of private cache
        stage_a_artifacts = engine.artifacts.get("stage_a")
        stage_a_ctx = stage_a_artifacts.stage_a_ctx if stage_a_artifacts is not None else None

        # Extract StageA telemetry (keyed by "stage_a" per StageA.name property)
        telemetry_a = telemetry_dict["stage_a"]

        # Phase E: Enrich telemetry with engine protocol and stage modes
        from dataclasses import asdict
        telemetry_a_dict = asdict(telemetry_a)
        telemetry_a_dict["engine_protocol"] = "stage_a"  # Stage-A-only mode
        telemetry_a_dict["stage_modes"] = {}  # No Stage B/C enabled
        telemetry_a_enriched = RefinementTelemetry(**telemetry_a_dict)

        # ARCH-ENGINE-ARTIFACTS-001 Phase C.1: Build final Bragg from artifact channel
        # Stage A unconditionally populates bragg_full in StageAArtifacts (verified by parity tests)
        if stage_a_artifacts is None or not hasattr(stage_a_artifacts, 'bragg_full') or stage_a_artifacts.bragg_full is None:
            raise RuntimeError(
                "Stage A did not produce final Bragg array in artifacts. "
                "This is a bug in the Stage A wrapper."
            )
        bragg_full = stage_a_artifacts.bragg_full

        # Return with telemetry dict using "A" key for backward compatibility
        # (Legacy code expects {"A": RefinementTelemetry, ...})
        # ARCH-STAGE-CONTEXT-001 Phase B.4: Also return engine artifacts for writer plumbing
        return bragg_full, {"A": telemetry_a_enriched}, engine.artifacts

    elif stage_a_b_mode:
        # === ENGINE DELEGATION PATH (Phase C2: A→B) ===
        from dbex.refinement.context import build_refinement_context
        from dbex.refinement.engine import RefinementEngine
        from dbex.refinement.stage_a import StageA
        from dbex.refinement.stage_b import StageB

        # Build RefinementContext per ARCH-REFINE-001 Phase B.1/B.3
        # Thread CLI-built HKL halo + ASU metadata from job_context (REFINE-005, REFINE-010)
        context = build_refinement_context(
            refinement_inputs=inputs,
            detector=detector,
            beam=beam,
            crystal=crystal,
            hkl_grid=hkl_grid,
            hkl_metadata=hkl_metadata,
            baseline_crystal=baseline_crystal,
            baseline_detector=baseline_detector,
            job_context=job_context,
        )

        # Build inputs dict per StageA/StageB.run() contract
        # Pass context via 'context' key per ARCH-REFINE-001 Phase B.1
        engine_inputs = {
            'context': context,
            'refinement_inputs': inputs,
            'detector': detector,
            'beam': beam,
            'crystal': crystal,
            'hkl_grid': hkl_grid,
            'hkl_metadata': hkl_metadata,
            'baseline_crystal': baseline_crystal,
            'baseline_detector': baseline_detector,
            'job_context': job_context,  # ARCH-REFINE-001 Phase B.2
        }

        # Instantiate RefinementEngine with StageA → StageB sequence
        # Note: CPU fallback for Stage B (PERF-WARM-011/012) is handled internally by
        # _build_stage_b_params which receives stage_a_ctx from StageA via engine propagation
        engine = RefinementEngine(stages=[StageA(), StageB()], config=config)

        # Execute engine and get telemetry dict (keyed by stage.name = "stage_a", "stage_b")
        telemetry_dict = engine.run(engine_inputs)

        # Extract Stage A and Stage B telemetry (keyed by "stage_a", "stage_b" per stage.name property)
        telemetry_a_raw = telemetry_dict["stage_a"]
        telemetry_b_raw = telemetry_dict["stage_b"]

        # Build final Bragg array using Stage B optimized shell modifiers
        device = torch.device(config.device)
        dtype = config.dtype

        # ARCH-STAGE-CONTEXT-001 Phase B.1: Extract stage_a_ctx from artifacts
        stage_a_artifacts = engine.artifacts.get("stage_a")
        stage_a_ctx = stage_a_artifacts.stage_a_ctx if stage_a_artifacts is not None else None

        # PERF-WARM-011: Recompute CPU fallback decision for final Bragg reconstruction
        # Same logic as in _build_stage_b_params (lines 2178-2182)
        panel_slices = inputs.panel_slices
        canonical_roi_count = len(panel_slices)
        use_stage_a_roi_mode = bool(
            config.enable_stage_a_roi_mode
            and canonical_roi_count > 0
            and (config.enable_stage_a_warm_cache or config.allow_cold_stage_a_roi_mode)
        )
        use_stage_b_cpu_fallback = (
            config.stage_b_full_eval_on_cpu
            and str(device).startswith("cuda")
            and not use_stage_a_roi_mode  # ROI mode is disabled (panel mode)
        )

        # If CPU fallback is active, use CPU device for final Bragg reconstruction
        final_device = torch.device("cpu") if use_stage_b_cpu_fallback else device

        # PERF-WARM-012: Clone Stage A context to CPU when CPU fallback is active
        # (Mirrors logic in _build_stage_b_params lines 2199-2220)
        stage_b_eval_stage_a_ctx = None
        if use_stage_b_cpu_fallback and stage_a_ctx is not None and config.enable_stage_a_warm_cache:
            # Build a fresh Stage A context on CPU device
            cpu_device = torch.device("cpu")
            stage_b_eval_stage_a_ctx = _build_stage_a_context(
                detector=detector,
                beam=beam,
                crystal=crystal,
                trusted_mask=inputs.trusted_mask,
                hkl_grid=hkl_grid,
                hkl_metadata=hkl_metadata,
                enable_hkl_interpolation=config.enable_hkl_interpolation,
                device=cpu_device,
                dtype=dtype,
                panel_slices=panel_slices,
                enable_roi_mode=False,  # CPU fallback is panel-mode only
                calibration_metadata=config.calibration_metadata,
                log_scale_baseline=config.log_scale_baseline,
                apply_calibration_n_cells=config.apply_calibration_n_cells,
            )
        elif not use_stage_b_cpu_fallback:
            # No CPU fallback: reuse the original CUDA Stage A context
            stage_b_eval_stage_a_ctx = stage_a_ctx

        # ARCH-STAGE-CONTEXT-001 Phase B.1: Extract shell metadata and custom attrs from artifacts
        stage_b_artifacts = engine.artifacts.get("stage_b")
        if stage_b_artifacts is not None:
            shell_edges = stage_b_artifacts.shell_edges
            shell_indices = stage_b_artifacts.shell_indices
            n_shells = stage_b_artifacts.n_shells
            stage_b_mode = stage_b_artifacts.stage_b_mode
            n_asu_unique = stage_b_artifacts.n_asu_unique
            optimizer_type = stage_b_artifacts.optimizer_type
            asu_modifier_stats = stage_b_artifacts.asu_modifier_stats
        else:
            shell_edges = None
            shell_indices = None
            n_shells = None
            stage_b_mode = None
            n_asu_unique = None
            optimizer_type = None
            asu_modifier_stats = None

        # ARCH-ENGINE-ARTIFACTS-001 Phase C.1: Build final Bragg from artifact channel
        # Stage B unconditionally populates bragg_full in StageBartifacts (verified by parity tests)
        if stage_b_artifacts is None or not hasattr(stage_b_artifacts, 'bragg_full') or stage_b_artifacts.bragg_full is None:
            raise RuntimeError(
                "Stage B did not produce final Bragg array in artifacts. "
                "This is a bug in the Stage B wrapper."
            )
        bragg_full = stage_b_artifacts.bragg_full

        # Repackage telemetry with backward-compatible keys ("A", "B")
        # Use engine's telemetry objects directly to preserve custom attributes (Phase 8 Alternative pattern)
        # The engine already restored custom attributes (stage_b_mode, n_asu_unique, etc.) per engine.py:161-168
        telemetry_a = telemetry_a_raw
        telemetry_b = telemetry_b_raw

        # Add engine protocol and stage modes for Phase E telemetry enrichment
        engine_protocol_value = "stage_a→stage_b"
        stage_modes_value = {
            "B": config.stage_b_mode  # Use actual config value ("per_reflection" or "shell")
        }
        telemetry_a.engine_protocol = engine_protocol_value
        telemetry_a.stage_modes = stage_modes_value
        telemetry_b.engine_protocol = engine_protocol_value
        telemetry_b.stage_modes = stage_modes_value

        # ARCH-STAGE-CONTEXT-001 Phase B.4: Also return engine artifacts for writer plumbing
        return bragg_full, {"A": telemetry_a, "B": telemetry_b}, engine.artifacts

    else:
        # === ENGINE DELEGATION PATH (Phase A.4: A→C or A→B→C) ===
        # Lazy imports to avoid circular dependencies
        from dbex.refinement.engine import RefinementEngine
        from dbex.refinement.stage_a import StageA
        from dbex.refinement.stage_b import StageB
        from dbex.refinement.stage_c import StageC

        # Build stage list based on config flags
        stages = [StageA()]  # Stage A always runs

        if config.enable_stage_b:
            # Guard: Stage B requires baseline_detector
            if baseline_detector is None:
                raise ValueError(
                    "Stage B requires baseline_detector parameter. "
                    "Pass the baseline dxtbx Detector object to run_nanobrag_refinement()."
                )
            stages.append(StageB())

        if config.enable_stage_c:
            # Guard: Stage C requires baseline_detector
            if baseline_detector is None:
                raise ValueError(
                    "Stage C requires baseline_detector parameter. "
                    "Pass the baseline dxtbx Detector object to run_nanobrag_refinement()."
                )
            stages.append(StageC())

        # Build engine protocol string for telemetry
        stage_names = [s.name for s in stages]
        engine_protocol = "→".join(stage_names)  # e.g., "stage_a→stage_c", "stage_a→stage_b→stage_c"

        # Build stage_modes dict for telemetry
        stage_modes = {}
        if config.enable_stage_b:
            stage_modes["B"] = config.stage_b_mode  # "per_reflection" or "shell"
        if config.enable_stage_c:
            stage_modes["C"] = "detector_offsets"

        # Build RefinementContext per ARCH-REFINE-001 Phase B.1
        from dbex.refinement.context import build_refinement_context
        context = build_refinement_context(
            refinement_inputs=inputs,
            detector=detector,
            beam=beam,
            crystal=crystal,
            hkl_grid=hkl_grid,
            hkl_metadata=hkl_metadata,
            baseline_crystal=baseline_crystal,
            baseline_detector=baseline_detector,
        )

        # Prepare RefinementInputs for engine
        # Pass context via 'context' key per ARCH-REFINE-001 Phase B.1
        engine_inputs = {
            "context": context,
            "refinement_inputs": inputs,
            "detector": detector,
            "beam": beam,
            "crystal": crystal,
            "hkl_grid": hkl_grid,
            "hkl_metadata": hkl_metadata,
            "baseline_crystal": baseline_crystal,
            "baseline_detector": baseline_detector,
            "job_context": job_context,  # ARCH-REFINE-001 Phase B.2
        }

        # Execute engine
        engine = RefinementEngine(stages=stages, config=config)
        engine_telemetry = engine.run(inputs=engine_inputs, telemetry_sink=None)

        # Extract final Bragg array based on last stage
        last_stage_name = stage_names[-1]
        device = torch.device(config.device)
        dtype = config.dtype

        if last_stage_name == "stage_c":
            # Stage C produces final Bragg directly
            # ARCH-STAGE-CONTEXT-001 Phase B.1: Extract bragg_full from artifacts
            stage_c_artifacts = engine.artifacts.get("stage_c")
            bragg_full = stage_c_artifacts.bragg_full if stage_c_artifacts is not None else None
            if bragg_full is None:
                raise RuntimeError(
                    "Stage C did not produce final Bragg array. "
                    "This is a bug in the Stage C wrapper."
                )
        elif last_stage_name == "stage_b":
            # Build final Bragg from Stage B telemetry
            # (This path already handled above in stage_a_b_mode, shouldn't reach here)
            raise RuntimeError(
                "Unexpected: Stage A→B path should have been handled by stage_a_b_mode branch. "
                "This is a bug in run_nanobrag_refinement control flow."
            )
        else:
            # Stage A only
            # (This path already handled above in stage_a_only_mode, shouldn't reach here)
            raise RuntimeError(
                "Unexpected: Stage A-only path should have been handled by stage_a_only_mode branch. "
                "This is a bug in run_nanobrag_refinement control flow."
            )

        # Enrich telemetry with engine protocol + stage modes
        telemetry_out = {}
        stage_name_map = {"stage_a": "A", "stage_b": "B", "stage_c": "C"}

        for stage_name, telem_obj in engine_telemetry.items():
            # Add engine protocol fields directly to existing object
            telem_obj.engine_protocol = engine_protocol
            telem_obj.stage_modes = stage_modes

            legacy_key = stage_name_map.get(stage_name, stage_name)
            telemetry_out[legacy_key] = telem_obj

        # ARCH-STAGE-CONTEXT-001 Phase B.4: Also return engine artifacts for writer plumbing
        return bragg_full, telemetry_out, engine.artifacts

