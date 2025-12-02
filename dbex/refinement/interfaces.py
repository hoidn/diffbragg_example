# dbex/refinement/interfaces.py
"""
Observer interfaces and telemetry result dataclasses for refinement stages.

Per ARCH-TELEMETRY-001 Phase A, this module defines:
- RefinementObserver protocol: Typed callback interface for telemetry collection
- StageResult: Per-stage telemetry/metrics container returned by StageX.run()
- StagePerfCounters: Performance counters (closure evals, validations, timing)
- Serialization helpers: Convert typed results back to legacy telemetry dicts

Normative Requirements:
- docs/spec-db-workflow.md §§Calibration & Pipeline telemetry requirements
- docs/spec-db-core.md §Objective Function & Variance Model (chi², variance floor stats)
- docs/spec-db-interfaces.md §HDF5 Output Schema (/torch_diagnostics keyset)
- PHYSICS-LOSS-001/003: Variance-weighted chi² and sigma-floor clamp telemetry
- ARCH-STAGE-CTX-001/002: Ban telemetry dict mutation; stages emit observer events

Key Design Points:
- Observer protocol decouples telemetry emission from physics/optimization logic
- StageResult carries typed telemetry + artifacts; engine/writer consume dataclasses
- Serialization preserves /torch_diagnostics schema for downstream consumers (writer, tests)
- Migration path: collectors wrap existing TelemetryState dataclasses initially

IDL Contract Reference:
- docs/architecture/dbex/refinement/interfaces.idl.md (detailed observer contracts)
- problems.md "Refactor: Decouple Telemetry from Refinement Logic using Observer Pattern"

Provenance:
- ARCH-TELEMETRY-001 Phase A.1: Observer protocol and result dataclass scaffolding
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Literal, Mapping, Optional, Protocol, Union


class RefinementObserver(Protocol):
    """
    Observer protocol for refinement stage telemetry collection.

    Stages emit telemetry via typed callbacks instead of mutating shared dicts.
    Collectors implement this protocol, wrapping TelemetryState dataclasses and
    accumulating traces/counters during LBFGS optimization.

    Per ARCH-TELEMETRY-001, the observer pattern:
    - Separates telemetry concerns from physics/optimization logic
    - Enables type-safe telemetry emission within closures
    - Supports multiple collectors (debugging, validation, export)
    - Preserves allocation-free operation (no tensor.item() on autograd tensors)

    Normative Requirements:
    - on_step: Called per LBFGS closure evaluation with loss/metrics
    - on_validation: Called per full-validation run with chi²/snapshot
    - finalize: Called after optimization completes to produce StageResult

    Observer Invariants:
    - Callbacks MUST NOT modify optimizer state or simulation outputs
    - Callbacks MUST avoid tensor.item() on autograd-tracked tensors (breaks gradients)
    - Callbacks SHOULD be allocation-free (append to pre-allocated lists)
    - Observers SHOULD tolerate redundant calls (e.g., multiple finalizes)

    IDL Contract Reference:
    - docs/architecture/dbex/refinement/interfaces.idl.md §RefinementObserver
    """

    def on_step(
        self,
        iteration: int,
        loss: float,
        metrics: Mapping[str, float],
    ) -> None:
        """
        Record per-iteration telemetry during LBFGS closure evaluation.

        Args:
            iteration: Current LBFGS iteration index
            loss: Scalar loss value (variance-weighted chi²)
            metrics: Dict with chi_squared, masked_mse, forward_time_ms, etc.

        Normative Requirements:
        - Called once per LBFGS closure evaluation (sampled ROI loss)
        - loss and metrics['chi_squared'] MUST reflect variance-weighted chi²
        - metrics['variance_floor_clamped_pixels'] MUST record sigma_floor clamp count
        - metrics['variance_floor_masked_pixels'] MUST record trusted mask exclusion count

        Provenance:
        - ARCH-TELEMETRY-001 Phase A.1: Observer protocol definition
        - PHYSICS-LOSS-001: Variance-weighted chi² invariants
        """
        ...

    def on_validation(
        self,
        scope: str,
        chi2: float,
        payload: Mapping[str, Any],
    ) -> None:
        """
        Record full-validation telemetry (panel/ROI/full scope).

        Args:
            scope: Validation scope ("panel" | "roi" | "full")
            chi2: Full-validation chi² value
            payload: Dict with masked_mse, best_snapshot, convergence info, etc.

        Normative Requirements:
        - Called per full-validation run (not per closure eval)
        - chi2 MUST reflect variance-weighted chi² on full validation set
        - payload['best_snapshot'] MAY contain parameter snapshot at best loss
        - payload SHOULD include lifecycle logs (U-matrix/A* checksums) when applicable

        Provenance:
        - ARCH-TELEMETRY-001 Phase A.1: Observer protocol definition
        """
        ...

    def finalize(self) -> "StageResult":
        """
        Finalize telemetry collection and return typed StageResult.

        Called after LBFGS optimization completes. Constructs StageResult from
        accumulated traces/counters and freezes the observer state.

        Returns:
            StageResult: Typed result containing stage name, telemetry, perf counters

        Normative Requirements:
        - MUST produce a StageResult with all required telemetry fields
        - Telemetry MUST serialize to /torch_diagnostics schema (legacy compatibility)
        - Multiple finalize calls SHOULD return the same StageResult (idempotent)

        Provenance:
        - ARCH-TELEMETRY-001 Phase A.1: Observer protocol definition
        """
        ...


@dataclass
class StagePerfCounters:
    """
    Performance counters for a refinement stage.

    Records closure evaluations, validation runs, forward pass timings, and
    variance-floor statistics. These counters feed observer telemetry and
    enable perf/convergence diagnostics.

    Attributes:
        closure_evals: Total LBFGS closure evaluations
        validation_runs: Total full-validation runs
        forward_times_ms: List of forward pass times in milliseconds
        variance_floor_clamped_pixels: Total pixels where sigma_floor clamp engaged
        variance_floor_masked_pixels: Total pixels excluded by trusted mask

    Normative Requirements:
    - closure_evals/validation_runs: Track optimizer convergence behavior
    - forward_times_ms: Enable perf regression detection
    - variance_floor_*: PHYSICS-LOSS-001 sigma-floor clamp telemetry

    IDL Contract Reference:
    - docs/spec-db-workflow.md:48-84 (telemetry requirements)
    - PHYSICS-LOSS-001/002: Variance floor stats

    Provenance:
    - ARCH-TELEMETRY-001 Phase A.1: Typed perf counters extracted from telemetry state
    """
    closure_evals: int = 0
    validation_runs: int = 0
    forward_times_ms: List[float] = field(default_factory=list)
    variance_floor_clamped_pixels: int = 0
    variance_floor_masked_pixels: int = 0


@dataclass
class StageATelemetry:
    """
    Typed telemetry payload for Stage A (geometry/scale refinement).

    Contains loss traces, chi²/MSE metrics, best snapshots, lifecycle logs,
    and variance-floor stats. Replaces the legacy telemetry_state dict.

    Attributes:
        iteration_count: Total LBFGS iterations
        loss_trace_sample: Per-closure loss values (sampled ROI)
        loss_trace_full: Full-validation loss values
        best_loss_full: Best full-validation loss seen
        chi_squared_trace_sample: Per-closure chi² (sampled ROI)
        chi_squared_trace_full: Full-validation chi² values
        chi_squared_best: Tuple (best_chi2, iteration)
        masked_mse_trace_sample: Per-closure masked MSE
        masked_mse_trace_full: Full-validation masked MSE
        masked_mse_best: Tuple (best_mse, iteration)
        best_params_snapshot: Parameter snapshot at best loss
        u_matrix_lifecycle_log: U-matrix checksum trace (convergence diagnostics)
        a_star_lifecycle_log: A* reconstruction trace
        panel_loss_diag: Optional per-panel diagnostics (PERF-WARM-SIM-001)

    Normative Requirements:
    - loss_trace_*, chi_squared_trace_*: PHYSICS-LOSS-001 variance-weighted chi²
    - best_params_snapshot: Enable final Bragg reconstruction
    - lifecycle_logs: TORCH-GEOMETRY-CONVERGENCE-001 convergence tracking
    - panel_loss_diag: PERF-WARM-SIM-001 warm-cache diagnostics (optional)

    Serialization:
    - asdict() produces legacy /torch_diagnostics schema for writer/tests

    IDL Contract Reference:
    - docs/spec-db-workflow.md:48-84 (Stage A telemetry)
    - docs/spec-db-core.md:57-68 (variance-weighted loss)

    Provenance:
    - ARCH-TELEMETRY-001 Phase A.1: Typed telemetry dataclass
    - ARCH-STAGE-CONTEXT-001 Phase B.3.1: Migrated from StageATelemetryState dict
    """
    iteration_count: int = 0
    loss_trace_sample: List[float] = field(default_factory=list)
    loss_trace_full: List[float] = field(default_factory=list)
    best_loss_full: List[float] = field(default_factory=list)
    chi_squared_trace_sample: List[float] = field(default_factory=list)
    chi_squared_trace_full: List[float] = field(default_factory=list)
    chi_squared_best: List[float] = field(default_factory=lambda: [float('inf'), -1])
    masked_mse_trace_sample: List[float] = field(default_factory=list)
    masked_mse_trace_full: List[float] = field(default_factory=list)
    masked_mse_best: List[float] = field(default_factory=lambda: [float('inf'), -1])
    best_params_snapshot: List[Any] = field(default_factory=list)
    u_matrix_lifecycle_log: List[Any] = field(default_factory=list)
    a_star_lifecycle_log: List[Any] = field(default_factory=list)
    panel_loss_diag: Optional[List[Any]] = None


@dataclass
class StageBTelemetry:
    """
    Typed telemetry payload for Stage B (shell modifiers / per-reflection).

    Similar to Stage A but without lifecycle logs (crystal frozen in Stage B).
    Includes Stage B baseline parity diagnostics per REFINE-FLOW-001.

    Attributes:
        iteration_count: Total LBFGS iterations
        loss_trace_sample: Per-closure loss values (sampled ROI)
        loss_trace_full: Full-validation loss values
        best_loss_full: Best full-validation loss seen
        chi_squared_trace_sample: Per-closure chi² (sampled ROI)
        chi_squared_trace_full: Full-validation chi² values
        chi_squared_best: Tuple (best_chi2, iteration)
        masked_mse_trace_sample: Per-closure masked MSE
        masked_mse_trace_full: Full-validation masked MSE
        masked_mse_best: Tuple (best_mse, iteration)
        best_params_snapshot: Parameter snapshot at best loss
        stage_b_baseline_rel_diff: Stage A→B chi² relative diff (parity guard)
        stage_b_baseline_abs_diff: Stage A→B chi² absolute diff
        stage_b_baseline_diff_path: Path to parity diff JSON

    Normative Requirements:
    - loss_trace_*, chi_squared_trace_*: PHYSICS-LOSS-001 variance-weighted chi²
    - stage_b_baseline_*: REFINE-FLOW-001 parity guard telemetry

    Serialization:
    - asdict() produces legacy /torch_diagnostics schema for writer/tests

    IDL Contract Reference:
    - docs/spec-db-workflow.md:48-84 (Stage B telemetry)
    - REFINE-FLOW-001: Stage B baseline parity guard

    Provenance:
    - ARCH-TELEMETRY-001 Phase A.1: Typed telemetry dataclass
    - ARCH-STAGE-CONTEXT-001 Phase B.3.2: Migrated from StageBTelemetryState dict
    """
    iteration_count: int = 0
    loss_trace_sample: List[float] = field(default_factory=list)
    loss_trace_full: List[float] = field(default_factory=list)
    best_loss_full: List[float] = field(default_factory=list)
    chi_squared_trace_sample: List[float] = field(default_factory=list)
    chi_squared_trace_full: List[float] = field(default_factory=list)
    chi_squared_best: List[float] = field(default_factory=lambda: [float('inf'), -1])
    masked_mse_trace_sample: List[float] = field(default_factory=list)
    masked_mse_trace_full: List[float] = field(default_factory=list)
    masked_mse_best: List[float] = field(default_factory=lambda: [float('inf'), -1])
    best_params_snapshot: List[Any] = field(default_factory=list)
    stage_b_baseline_rel_diff: Optional[float] = None
    stage_b_baseline_abs_diff: Optional[float] = None
    stage_b_baseline_diff_path: Optional[str] = None


@dataclass
class StageCTelemetry:
    """
    Typed telemetry payload for Stage C (detector refinement).

    Similar to Stage B but may include per-panel diagnostics for warm-cache debugging.

    Attributes:
        iteration_count: Total LBFGS iterations
        loss_trace_sample: Per-closure loss values (sampled ROI)
        loss_trace_full: Full-validation loss values
        best_loss_full: Tuple (best_loss, iteration)
        chi_squared_trace_sample: Per-closure chi² (sampled ROI)
        chi_squared_trace_full: Full-validation chi² values
        chi_squared_best: Tuple (best_chi2, iteration)
        masked_mse_trace_sample: Per-closure masked MSE
        masked_mse_trace_full: Full-validation masked MSE
        masked_mse_best: Tuple (best_mse, iteration)
        best_params_snapshot: Optional parameter snapshot at best loss
        panel_loss_diag: Optional per-panel diagnostics (PERF-WARM-SIM-001)

    Normative Requirements:
    - loss_trace_*, chi_squared_trace_*: PHYSICS-LOSS-001 variance-weighted chi²
    - panel_loss_diag: PERF-WARM-SIM-001 warm-cache diagnostics (optional)

    Serialization:
    - asdict() produces legacy /torch_diagnostics schema for writer/tests

    IDL Contract Reference:
    - docs/spec-db-workflow.md:48-84 (Stage C telemetry)
    - PERF-WARM-SIM-001: Warm-cache panel diagnostics

    Provenance:
    - ARCH-TELEMETRY-001 Phase A.1: Typed telemetry dataclass
    - ARCH-STAGE-CONTEXT-001 Phase B.3.2: Migrated from StageCTelemetryState dict
    """
    iteration_count: int = 0
    loss_trace_sample: List[float] = field(default_factory=list)
    loss_trace_full: List[float] = field(default_factory=list)
    best_loss_full: List[float] = field(default_factory=lambda: [float('inf'), -1])
    chi_squared_trace_sample: List[float] = field(default_factory=list)
    chi_squared_trace_full: List[float] = field(default_factory=list)
    chi_squared_best: List[float] = field(default_factory=lambda: [float('inf'), -1])
    masked_mse_trace_sample: List[float] = field(default_factory=list)
    masked_mse_trace_full: List[float] = field(default_factory=list)
    masked_mse_best: List[float] = field(default_factory=lambda: [float('inf'), -1])
    best_params_snapshot: Optional[List[Any]] = None
    panel_loss_diag: Optional[List[Any]] = None


@dataclass
class StageResult:
    """
    Typed result container returned by StageX.run() after refinement.

    Carries stage name, typed telemetry payload, and performance counters.
    Replaces the legacy practice of returning telemetry_state dicts.

    Attributes:
        stage: Stage identifier ("A" | "B" | "C")
        telemetry: Stage-specific telemetry dataclass (StageATelemetry | StageBTelemetry | StageCTelemetry)
        perf_counters: Performance counters (closure evals, validations, timing)

    Normative Requirements:
    - RefinementEngine caches StageResult artifacts per stage name
    - Writer consumes StageResult.telemetry without dict introspection
    - Tests assert on StageResult fields (no dict scraping)

    Serialization:
    - to_legacy_dict() converts telemetry/perf_counters to /torch_diagnostics schema

    IDL Contract Reference:
    - docs/spec-db-workflow.md:33 (engine artifact channel)
    - docs/spec-db-interfaces.md (HDF5 schema requirements)

    Provenance:
    - ARCH-TELEMETRY-001 Phase A.1: Typed result container
    - ARCH-STAGE-CONTEXT-001: Artifact channel refactoring
    """
    stage: Literal["A", "B", "C"]
    telemetry: Union[StageATelemetry, StageBTelemetry, StageCTelemetry]
    perf_counters: StagePerfCounters

    def to_legacy_dict(self) -> Dict[str, Any]:
        """
        Convert StageResult to legacy telemetry_state dict for /torch_diagnostics schema.

        Flattens telemetry + perf_counters into a single dict matching the existing
        HDF5 writer expectations. Enables gradual migration: stages emit StageResult,
        writer consumes legacy dict until Phase C.2 refactor.

        Returns:
            Dict with all telemetry fields + perf counters in legacy schema

        Normative Requirements:
        - Output MUST match /torch_diagnostics keyset per docs/spec-db-interfaces.md
        - Perf counters MUST be serialized with "_trace" or scalar keys
        - Missing optional fields (panel_loss_diag, lifecycle_logs) SHOULD be omitted

        Provenance:
        - ARCH-TELEMETRY-001 Phase A.1: Legacy serialization helper
        - ARCH-STAGE-CONTEXT-001 Phase D: Writer compatibility shim
        """
        # Start with telemetry dataclass dict
        result = asdict(self.telemetry)

        # Add perf counters with legacy naming
        result['perf_closure_evals'] = [self.perf_counters.closure_evals]
        result['perf_validation_runs'] = [self.perf_counters.validation_runs]
        result['perf_forward_times_ms'] = self.perf_counters.forward_times_ms
        result['variance_floor_clamped_pixels'] = [self.perf_counters.variance_floor_clamped_pixels]
        result['variance_floor_masked_pixels'] = [self.perf_counters.variance_floor_masked_pixels]

        return result
