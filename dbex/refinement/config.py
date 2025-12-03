"""
Refinement job configuration for RefinementEngine.

Defines RefinementConfig dataclass encapsulating hyperparameters, feature flags,
and job-level metadata for Stage A/B/C LBFGS refinement.

See:
- docs/spec-db-workflow.md §§30-41 (Staging policy)
- docs/pytorch_runtime_checklist.md (device/dtype neutrality)
- ARCH-REFACTOR-001 Phase D.1 (config extraction from facade)
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import torch


@dataclass
class RefinementConfig:
    """Configuration for Stage A and Stage C LBFGS refinement."""
    # LBFGS hyperparameters (shared across stages)
    history_size: int = 10
    max_iter: int = 30
    tolerance_grad: float = 1e-7
    tolerance_change: float = 1e-9

    # ROI sampling for LBFGS closure
    roi_sample_fraction: float = 0.15  # ~15% of ROIs per iteration
    full_validation_interval: int = 5  # Validate on full loss every N steps

    # Convergence guards (Stage A)
    min_loss_improvement: float = 0.002  # 0.2% minimum improvement (TORCH-REFINE-002D)
    early_stop_window: int = 3  # Stop if no improvement over last K validations
    max_loss_increase: float = 0.02  # 2% max increase before rollback

    # HKL interpolation (TORCH-REFINE-002D, REFINE-005)
    # Enable tricubic interpolation for structure factors; requires halo-padded grid
    # Defaults to False (nearest-neighbor) to protect datasets without halo support
    enable_hkl_interpolation: bool = False

    # U-matrix parameterization (TORCH-GEOMETRY-PARITY-002 Phase B)
    # Enable direct U-matrix quaternion parameterization for Stage A orientation.
    # When False (default), uses existing cell+misset decomposition path (GEOMETRY-003).
    # When True, parameterizes orientation as quaternion → U-matrix, preserving
    # mapping MOSFLM A* strain and eliminating the 1.37e-3 symmetric strain artifact.
    use_u_matrix_parameterization: bool = False

    # LBFGS optimizer for U-matrix path (TORCH-GEOMETRY-CONVERGENCE-001 Phase B Test B1)
    # When True, uses LBFGS optimizer instead of Adam for quaternion U-matrix refinement.
    # LBFGS eliminates momentum accumulation (H4), uses line search (H3), proven for scale-only.
    # Only applies when use_u_matrix_parameterization=True.
    use_lbfgs_for_u_matrix: bool = False

    # Learning rate for U-matrix path (TORCH-GEOMETRY-CONVERGENCE-001 Phase C2)
    # Learning rate for Adam optimizer when use_u_matrix_parameterization=True.
    # Default 1e-5 (10× lower than cell/misset LR) to accommodate quaternion gradient
    # scale O(150k). Per CONVERGENCE-001 Phase C1 root cause analysis.
    # Only applies when use_u_matrix_parameterization=True and use_lbfgs_for_u_matrix=False.
    u_matrix_learning_rate: float = 1e-5

    # Incremental UB parameterization (TORCH-GEOMETRY-UB-REALIGN-001 Phase B3)
    # Enable incremental UB parameterization around baseline dxtbx crystal state.
    # When False (default), uses existing cell+misset default path.
    # When True, parameterizes geometry as U(params) = ΔR(q_delta) @ U₀ and
    # B(params) via log-perturbations for lengths + angle deltas, constructing
    # A*(params) = U(params) @ B(params) in a single direction per spec-db-core.md:64-67.
    # Supersedes use_u_matrix_parameterization when both are enabled.
    use_incremental_ub: bool = False

    # Warm cache (PERF-WARM-SIM-001)
    # Enable Stage A warm cache (prebuild detector models/masks/HKL once).
    # Default True for production (2-5× speedup). Disable for benchmarking cold baseline.
    enable_stage_a_warm_cache: bool = True
    # Enable ROI-aware sampling/cropping when Stage A closures run (PERF-WARM-SIM-001 ROI follow-up)
    enable_stage_a_roi_mode: bool = True
    # Allow ROI sampling even when the warm cache is disabled (default False so cold benchmarks stay panel-scoped)
    allow_cold_stage_a_roi_mode: bool = False
    # Minimum ROI count threshold for ROI mode (ARCH-REFINE-001, REFINE-010)
    # When canonical ROI count ≤ this threshold, Stage A/B/C automatically switch to panel mode
    # (both optimization closures AND validations) to ensure sufficient signal for convergence.
    # Calibrated per refGeom_small probe: 29 ROIs with 15% sampling (4 ROIs) achieves 0% improvement,
    # while panel mode achieves 57.4%. Default 32 so refGeom_small (29 ROIs) uses panel mode.
    stage_a_min_roi_for_roi_mode: int = 32

    # nanobrag_torch oversampling (DIAG-NANOBRAGG-OVERSAMPLE-001 Phase C)
    # Oversampling factor for detector simulation (1, 2, 3, ...).
    # Default 3 matches calibration metadata standard and prevents auto-selection.
    # -1 triggers auto-selection based on detector size (not recommended for reproducibility).
    oversample: int = 3

    # Stage B structure factor modifiers (TORCH-REFINE-004)
    enable_stage_b: bool = False  # Enable Fhkl shell modifiers
    stage_b_mode: str = "per_reflection"  # "per_reflection" (default per spec:59) or "shell" (fallback per spec:60)
    stage_b_n_shells: int = 5  # Number of resolution shells for shell mode
    stage_b_min_loss_improvement: float = 1e-8  # 0.000001% minimum improvement for Stage B (calibrated per TORCH-REFINE-004 refGeom probe: measured ceiling ~6.4e-8%, essentially zero)
    stage_b_max_modifier: float = 2.0  # Maximum shell modifier (softplus clamp)
    stage_b_regularization: float = 0.0  # L2 regularization strength (reserved for future)
    stage_b_full_eval_on_cpu: bool = True  # Run Stage B evaluations on CPU to avoid GPU OOM when gradients require large buffers

    # Stage B per-reflection ASU mode (TORCH-REFINE-004 Phase 6)
    stage_b_optimizer_gate: int = 10000  # n_asu threshold for LBFGS vs Adam selection
    stage_b_adam_lr: float = 1e-2  # Adam learning rate for large parameter counts (≥10K) - Phase 7 tuned
    stage_b_modifier_clamp: Tuple[float, float] = (-3.0, 3.0)  # log-space clamp range (modifiers ∈ [0.05, 20.1])

    # Stage C detector microslip (TORCH-REFINE-003)
    enable_stage_c: bool = False  # Enable detector distance refinement
    stage_c_min_loss_improvement: float = 2e-5  # 0.002% minimum improvement for Stage C (calibrated per REFINE-007)
    stage_c_max_distance_delta_mm: float = 0.5  # Maximum distance adjustment per panel (mm)

    # Stage A panel validation (ARCH-REFINE-001, REFINE-007)
    # Force baseline/final validations to use panel mode instead of ROI sampling when Stage C is enabled
    # or when the canonical ROI count is small (≤32), ensuring Stage A telemetry reports panel-level chi²
    # that matches Stage C's initial state and satisfies REFINE-007 improvement gates.
    stage_a_force_panel_validation: bool = False  # Manually force panel-mode validations
    stage_a_panel_validation_roi_threshold: int = 32  # Auto-enable panel validations when ROI count ≤ threshold

    # Variance floor guard (PHYSICS-LOSS-002, spec-db-core.md:67)
    # Prevents infinite weights when I_model → 0 on GPU backends
    # Shares units with sigma_readout (target units: photons or ADU)
    sigma_floor_value: float = 1.0  # Default: ~1 photon equivalent

    # Sigma provenance metadata (PHYSICS-LOSS-001 A4)
    sigma_readout_provenance: Optional[str] = None
    sigma_readout_reference_value: Optional[float] = None

    # Calibration metadata (TOOLING-VIS-001 Phase D.C, DB-AT-027)
    # When provided, calibration payload from mapping (spot_scale_override,
    # beam flux/exposure, N_cells) is reused in Stage A context builders.
    # log_scale is then treated as a bounded delta (±3) around the calibrated baseline.
    calibration_metadata: Optional[Dict[str, Any]] = None
    # log_scale baseline when calibration is present (recorded in telemetry)
    log_scale_baseline: Optional[float] = None
    # Apply N_cells from calibration metadata (TOOLING-VIS-001 Phase D.C, SCALE-008)
    # When True (default), N_cells is applied if present in calibration_metadata.
    # When False, N_cells is suppressed even when present (for small-detector metadata fixtures).
    apply_calibration_n_cells: bool = True

    # Device and dtype for PyTorch operations
    device: str = "cpu"
    dtype: Any = torch.float32  # Actual dtype at runtime
