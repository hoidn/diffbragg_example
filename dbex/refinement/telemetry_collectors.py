# dbex/refinement/telemetry_collectors.py
"""
Telemetry collectors implementing RefinementObserver for Stage A/B/C.

Per ARCH-TELEMETRY-001 Phase A.2/B, collectors wrap existing TelemetryState
dataclasses and implement the observer protocol, allowing closures to emit
telemetry via typed callbacks instead of mutating shared dicts.

Normative Requirements:
- docs/spec-db-workflow.md §§Calibration & Pipeline telemetry requirements
- docs/spec-db-core.md §Objective Function & Variance Model (chi², variance floor)
- PHYSICS-LOSS-001/003: Variance-weighted chi² and sigma-floor clamp telemetry
- ARCH-STAGE-CTX-001/002: Ban telemetry dict mutation; collectors own accumulation

Key Design Points:
- Collectors wrap StageXTelemetryState dataclasses (Phase A migration shim)
- Observer callbacks update wrapped state, preserving existing trace/counter logic
- finalize() constructs StageResult from wrapped state + performance counters
- Collectors are stateful and NOT thread-safe (single LBFGS optimization per stage)

IDL Contract Reference:
- docs/architecture/dbex/refinement/interfaces.idl.md §TelemetryCollector contracts

Provenance:
- ARCH-TELEMETRY-001 Phase A.2: Collector scaffolding with StageATelemetryState wrapper
- ARCH-TELEMETRY-001 Phase B.1: StageATelemetryCollector wiring through Stage A closures
"""

from typing import Any, Dict, Mapping, Optional

from .context import StageATelemetryState, StageBTelemetryState, StageCTelemetryState
from .interfaces import (
    RefinementObserver,
    StageResult,
    StagePerfCounters,
    StageATelemetry,
    StageBTelemetry,
    StageCTelemetry,
)


class StageATelemetryCollector:
    """
    Observer implementation for Stage A telemetry collection.

    Wraps StageATelemetryState and implements RefinementObserver protocol,
    allowing Stage A LBFGS closures to emit telemetry via typed callbacks.

    Per ARCH-TELEMETRY-001 Phase B.1:
    - Replaces direct telemetry_state dict mutation in _build_lbfgs_closure
    - Maintains all existing trace/counter fields from StageATelemetryState
    - Preserves allocation-free operation (append to existing lists)
    - Returns StageResult via finalize() for engine artifact channel

    Attributes:
        _state: Wrapped StageATelemetryState dataclass (mutable lists/counters)

    Normative Requirements:
    - on_step: Record per-iteration loss/chi²/MSE and update closure eval counter
    - on_validation: Record full-validation chi²/MSE and update validation run counter
    - finalize: Construct StageResult with typed telemetry + perf counters

    Observer Invariants:
    - Callbacks MUST NOT call tensor.item() on autograd-tracked tensors
    - Callbacks SHOULD be allocation-free (append to pre-allocated lists)
    - finalize() MAY be called multiple times (idempotent)

    IDL Contract Reference:
    - docs/architecture/dbex/refinement/interfaces.idl.md §StageATelemetryCollector

    Provenance:
    - ARCH-TELEMETRY-001 Phase A.2: Collector scaffolding
    - ARCH-TELEMETRY-001 Phase B.1: Integration with Stage A closures
    """

    def __init__(self, state: StageATelemetryState):
        """
        Initialize collector with wrapped StageATelemetryState.

        Args:
            state: StageATelemetryState instance (mutable telemetry accumulators)

        Normative Requirements:
        - state MUST be a fresh StageATelemetryState instance (no shared state)
        - Caller MUST NOT mutate state directly after passing to collector
        """
        self._state = state

    def on_step(
        self,
        iteration: int,
        loss: float,
        metrics: Mapping[str, float],
    ) -> None:
        """
        Record per-iteration telemetry during LBFGS closure evaluation.

        Updates iteration counter, appends loss/chi²/MSE to sample traces,
        and increments closure eval counter.

        Args:
            iteration: Current LBFGS iteration index
            loss: Scalar loss value (variance-weighted chi²)
            metrics: Dict with chi_squared, masked_mse, forward_time_ms,
                    variance_floor_clamped_pixels, variance_floor_masked_pixels

        Normative Requirements:
        - loss MUST be variance-weighted chi² per PHYSICS-LOSS-001
        - metrics['chi_squared'] MUST match loss (dual metric tracking)
        - metrics['variance_floor_clamped_pixels'] MUST reflect sigma_floor clamp count
        - Forward time (if present) recorded in perf_forward_times_ms trace

        Provenance:
        - ARCH-TELEMETRY-001 Phase B.1: Observer callback implementation
        - PHYSICS-LOSS-001: Variance-weighted chi² invariants
        """
        # Update iteration counter (mutable list for closure capture)
        self._state.iteration_count[0] = iteration

        # Append loss to sample trace
        self._state.loss_trace_sample.append(loss)

        # Record chi² and masked MSE (dual metrics per PHYSICS-LOSS-001)
        chi2 = metrics.get('chi_squared', loss)  # fallback: loss IS chi²
        mse = metrics.get('masked_mse', 0.0)
        self._state.chi_squared_trace_sample.append(chi2)
        self._state.masked_mse_trace_sample.append(mse)

        # Increment closure eval counter
        self._state.perf_closure_evals[0] += 1

        # Record forward time if available
        if 'forward_time_ms' in metrics:
            self._state.perf_forward_times_ms.append(metrics['forward_time_ms'])

        # Update variance floor stats (cumulative counters)
        if 'variance_floor_clamped_pixels' in metrics:
            # These are delta counts per step; accumulate them
            self._state.variance_floor_clamped_pixels[0] += int(metrics['variance_floor_clamped_pixels'])
        if 'variance_floor_masked_pixels' in metrics:
            self._state.variance_floor_masked_pixels[0] += int(metrics['variance_floor_masked_pixels'])

    def on_validation(
        self,
        scope: str,
        chi2: float,
        payload: Mapping[str, Any],
    ) -> None:
        """
        Record full-validation telemetry (panel/ROI/full scope).

        Updates validation run counter, appends chi²/MSE to full traces,
        and records best snapshots when applicable.

        Args:
            scope: Validation scope ("panel" | "roi" | "full")
            chi2: Full-validation chi² value
            payload: Dict with masked_mse, best_snapshot, loss, u_matrix_checksum, etc.

        Normative Requirements:
        - chi2 MUST be variance-weighted chi² on full validation set
        - payload['best_snapshot'] MAY contain parameter snapshot at best loss
        - payload['u_matrix_checksum'] SHOULD be logged to u_matrix_lifecycle_log
        - Validation run counter incremented once per call

        Provenance:
        - ARCH-TELEMETRY-001 Phase B.1: Observer callback implementation
        - TORCH-GEOMETRY-CONVERGENCE-001: U-matrix lifecycle logging
        """
        # Increment validation run counter
        self._state.perf_validation_runs[0] += 1

        # Append full-validation chi² and loss (with iteration tuples for legacy compatibility)
        current_iter = self._state.iteration_count[0]
        self._state.chi_squared_trace_full.append((current_iter, chi2))
        loss = payload.get('loss', chi2)  # fallback: chi² is loss
        self._state.loss_trace_full.append((current_iter, loss))

        # Record masked MSE if available (with iteration tuple for legacy compatibility)
        mse = payload.get('masked_mse', 0.0)
        self._state.masked_mse_trace_full.append((current_iter, mse))

        # Update best loss tracker
        if not self._state.best_loss_full or loss < self._state.best_loss_full[-1]:
            self._state.best_loss_full.append(loss)
        else:
            self._state.best_loss_full.append(self._state.best_loss_full[-1] if self._state.best_loss_full else loss)

        # Record best chi² and iteration (tuple reassignment, not mutation)
        if chi2 < self._state.chi_squared_best[0]:
            self._state.chi_squared_best = (chi2, self._state.iteration_count[0])

        # Record best masked MSE and iteration (tuple reassignment, not mutation)
        if mse < self._state.masked_mse_best[0]:
            self._state.masked_mse_best = (mse, self._state.iteration_count[0])

        # Record best parameter snapshot if present
        if 'best_snapshot' in payload:
            self._state.best_params_snapshot = [payload['best_snapshot']]

        # Log lifecycle checksums (U-matrix, A*)
        if 'u_matrix_checksum' in payload:
            self._state.u_matrix_lifecycle_log.append(payload['u_matrix_checksum'])
        if 'a_star_checksum' in payload:
            self._state.a_star_lifecycle_log.append(payload['a_star_checksum'])

        # Record panel diagnostics if present (PERF-WARM-SIM-001)
        if 'panel_diag' in payload and self._state.panel_loss_diag is not None:
            self._state.panel_loss_diag.append(payload['panel_diag'])

    def finalize(self) -> StageResult:
        """
        Finalize telemetry collection and return typed StageResult.

        Constructs StageResult from wrapped StageATelemetryState, converting
        mutable list counters to scalar values and assembling typed telemetry.

        Returns:
            StageResult with stage="A", typed telemetry, and perf counters

        Normative Requirements:
        - Telemetry MUST include all traces accumulated during optimization
        - Perf counters MUST reflect final counts (closure evals, validations, etc.)
        - Result MUST serialize to /torch_diagnostics schema via to_legacy_dict()

        Provenance:
        - ARCH-TELEMETRY-001 Phase A.2/B.1: StageResult construction from state
        """
        # Build typed telemetry from state
        telemetry = StageATelemetry(
            iteration_count=self._state.iteration_count[0],
            loss_trace_sample=self._state.loss_trace_sample,
            loss_trace_full=self._state.loss_trace_full,
            best_loss_full=self._state.best_loss_full,
            chi_squared_trace_sample=self._state.chi_squared_trace_sample,
            chi_squared_trace_full=self._state.chi_squared_trace_full,
            chi_squared_best=self._state.chi_squared_best,
            masked_mse_trace_sample=self._state.masked_mse_trace_sample,
            masked_mse_trace_full=self._state.masked_mse_trace_full,
            masked_mse_best=self._state.masked_mse_best,
            best_params_snapshot=self._state.best_params_snapshot,
            u_matrix_lifecycle_log=self._state.u_matrix_lifecycle_log,
            a_star_lifecycle_log=self._state.a_star_lifecycle_log,
            panel_loss_diag=self._state.panel_loss_diag,
        )

        # Build perf counters from state
        perf_counters = StagePerfCounters(
            closure_evals=self._state.perf_closure_evals[0],
            validation_runs=self._state.perf_validation_runs[0],
            forward_times_ms=self._state.perf_forward_times_ms,
            variance_floor_clamped_pixels=self._state.variance_floor_clamped_pixels[0],
            variance_floor_masked_pixels=self._state.variance_floor_masked_pixels[0],
        )

        return StageResult(
            stage="A",
            telemetry=telemetry,
            perf_counters=perf_counters,
        )

    def record_step(
        self,
        iteration: int,
        loss: float,
        chi_squared: float,
        masked_mse: float,
        forward_time_ms: float = 0.0,
    ) -> None:
        """
        Convenience helper for recording per-step telemetry.

        Wraps on_step() with standard metrics dict construction.

        Args:
            iteration: Current LBFGS iteration index
            loss: Scalar loss value (variance-weighted chi²)
            chi_squared: Chi² value (should match loss)
            masked_mse: Masked MSE value
            forward_time_ms: Optional forward pass time in milliseconds

        Normative Requirements:
        - loss and chi_squared SHOULD be identical (dual metric tracking)
        - Variance floor stats updated separately via on_step metrics

        Provenance:
        - ARCH-TELEMETRY-001 Phase B.1: Convenience helper for closure integration
        """
        metrics = {
            'chi_squared': chi_squared,
            'masked_mse': masked_mse,
        }
        if forward_time_ms > 0:
            metrics['forward_time_ms'] = forward_time_ms

        self.on_step(iteration, loss, metrics)

    def record_validation(
        self,
        scope: str,
        chi2: float,
        loss: float,
        masked_mse: float,
        best_snapshot: Any = None,
    ) -> None:
        """
        Convenience helper for recording validation telemetry.

        Wraps on_validation() with standard payload dict construction.

        Args:
            scope: Validation scope ("panel" | "roi" | "full")
            chi2: Full-validation chi² value
            loss: Full-validation loss value
            masked_mse: Full-validation masked MSE
            best_snapshot: Optional parameter snapshot at best loss

        Normative Requirements:
        - chi2 and loss SHOULD be variance-weighted on full validation set
        - best_snapshot MAY be None if loss is not improving

        Provenance:
        - ARCH-TELEMETRY-001 Phase B.1: Convenience helper for closure integration
        """
        payload = {
            'loss': loss,
            'masked_mse': masked_mse,
        }
        if best_snapshot is not None:
            payload['best_snapshot'] = best_snapshot

        self.on_validation(scope, chi2, payload)

    @property
    def state(self) -> StageATelemetryState:
        """
        Access wrapped telemetry state (read-only view).

        Returns:
            StageATelemetryState instance

        Normative Requirements:
        - Callers SHOULD NOT mutate the returned state directly
        - Use observer callbacks (on_step, on_validation) for mutation

        Provenance:
        - ARCH-TELEMETRY-001 Phase B.1: State access for legacy compatibility
        """
        return self._state


class StageBTelemetryCollector:
    """
    Observer implementation for Stage B telemetry collection.

    Similar to StageATelemetryCollector but wraps StageBTelemetryState and
    omits lifecycle logging (crystal frozen in Stage B).

    Attributes:
        _state: Wrapped StageBTelemetryState dataclass (mutable lists/counters)

    Normative Requirements:
    - Same observer contract as StageATelemetryCollector
    - Includes Stage B baseline parity diagnostics per REFINE-FLOW-001

    Provenance:
    - ARCH-TELEMETRY-001 Phase A.2: Collector scaffolding
    - ARCH-TELEMETRY-001 Phase C.1: Integration with Stage B closures (future)
    """

    def __init__(self, state: StageBTelemetryState):
        """Initialize collector with wrapped StageBTelemetryState."""
        self._state = state

    def on_step(self, iteration: int, loss: float, metrics: Mapping[str, float]) -> None:
        """Record per-iteration telemetry (same logic as Stage A)."""
        self._state.iteration_count[0] = iteration
        self._state.loss_trace_sample.append(loss)
        chi2 = metrics.get('chi_squared', loss)
        mse = metrics.get('masked_mse', 0.0)
        self._state.chi_squared_trace_sample.append(chi2)
        self._state.masked_mse_trace_sample.append(mse)
        self._state.perf_closure_evals[0] += 1
        if 'forward_time_ms' in metrics:
            self._state.perf_forward_times_ms.append(metrics['forward_time_ms'])
        if 'variance_floor_clamped_pixels' in metrics:
            self._state.variance_floor_clamped_pixels[0] += int(metrics['variance_floor_clamped_pixels'])
        if 'variance_floor_masked_pixels' in metrics:
            self._state.variance_floor_masked_pixels[0] += int(metrics['variance_floor_masked_pixels'])

    def on_validation(self, scope: str, chi2: float, payload: Mapping[str, Any]) -> None:
        """Record full-validation telemetry (tuple format for Stage B parity with Stage A)."""
        self._state.perf_validation_runs[0] += 1
        current_iter = self._state.iteration_count[0]
        # Append with iteration tuples for Stage B/C full traces (parity with Stage A)
        self._state.chi_squared_trace_full.append((current_iter, chi2))
        loss = payload.get('loss', chi2)
        self._state.loss_trace_full.append((current_iter, loss))
        mse = payload.get('masked_mse', 0.0)
        self._state.masked_mse_trace_full.append((current_iter, mse))
        # Stage B/C best_loss_full is a list storing [best_value, best_iteration]
        # Initialize if empty or update if better
        # Handle both list and tuple sources by replacing the attribute entirely
        if len(self._state.best_loss_full) == 0:
            self._state.best_loss_full = [loss, current_iter]
        elif loss < self._state.best_loss_full[0]:
            self._state.best_loss_full = [loss, current_iter]
        # chi_squared_best and masked_mse_best are also lists [value, iteration]
        if chi2 < self._state.chi_squared_best[0]:
            self._state.chi_squared_best = [chi2, current_iter]
        if mse < self._state.masked_mse_best[0]:
            self._state.masked_mse_best = [mse, current_iter]
        if 'best_snapshot' in payload:
            self._state.best_params_snapshot = [payload['best_snapshot']]

    def finalize(self) -> StageResult:
        """Construct StageResult for Stage B."""
        telemetry = StageBTelemetry(
            iteration_count=self._state.iteration_count[0],
            loss_trace_sample=self._state.loss_trace_sample,
            loss_trace_full=self._state.loss_trace_full,
            best_loss_full=self._state.best_loss_full,
            chi_squared_trace_sample=self._state.chi_squared_trace_sample,
            chi_squared_trace_full=self._state.chi_squared_trace_full,
            chi_squared_best=self._state.chi_squared_best,
            masked_mse_trace_sample=self._state.masked_mse_trace_sample,
            masked_mse_trace_full=self._state.masked_mse_trace_full,
            masked_mse_best=self._state.masked_mse_best,
            best_params_snapshot=self._state.best_params_snapshot,
            stage_b_baseline_rel_diff=self._state.stage_b_baseline_rel_diff,
            stage_b_baseline_abs_diff=self._state.stage_b_baseline_abs_diff,
            stage_b_baseline_diff_path=self._state.stage_b_baseline_diff_path,
        )

        perf_counters = StagePerfCounters(
            closure_evals=self._state.perf_closure_evals[0],
            validation_runs=self._state.perf_validation_runs[0],
            forward_times_ms=self._state.perf_forward_times_ms,
            variance_floor_clamped_pixels=self._state.variance_floor_clamped_pixels[0],
            variance_floor_masked_pixels=self._state.variance_floor_masked_pixels[0],
        )

        return StageResult(stage="B", telemetry=telemetry, perf_counters=perf_counters)

    def set_baseline_parity_metrics(
        self,
        rel_diff: float,
        abs_diff: float,
        diff_path: Optional[str] = None,
    ) -> None:
        """
        Record Stage B baseline parity metrics (REFINE-FLOW-001).

        Called by _check_stage_b_baseline_parity to populate parity diagnostics
        without directly mutating telemetry state.

        Args:
            rel_diff: Relative difference (Stage B initial - Stage A canonical) / canonical
            abs_diff: Absolute difference (Stage B initial - Stage A canonical)
            diff_path: Optional path to JSON diff file emitted when parity fails

        Normative Requirements:
        - Metrics MUST be recorded for every Stage B run with canonical baseline
        - diff_path SHOULD be None when parity passes (<0.1% tolerance)

        Provenance:
        - ARCH-TELEMETRY-001 Phase C.1: Baseline parity helper for collector
        - REFINE-FLOW-001: Stage B baseline parity guard tolerance
        """
        self._state.stage_b_baseline_rel_diff = rel_diff
        self._state.stage_b_baseline_abs_diff = abs_diff
        if diff_path is not None:
            self._state.stage_b_baseline_diff_path = diff_path

    @property
    def state(self) -> StageBTelemetryState:
        """Access wrapped telemetry state (read-only view)."""
        return self._state


class StageCTelemetryCollector:
    """
    Observer implementation for Stage C telemetry collection.

    Similar to StageBTelemetryCollector with optional panel diagnostics.

    Attributes:
        _state: Wrapped StageCTelemetryState dataclass (mutable lists/counters)

    Normative Requirements:
    - Same observer contract as StageATelemetryCollector
    - Includes panel diagnostics for PERF-WARM-SIM-001 (optional)

    Provenance:
    - ARCH-TELEMETRY-001 Phase A.2: Collector scaffolding
    - ARCH-TELEMETRY-001 Phase C.1: Integration with Stage C closures (future)
    """

    def __init__(self, state: StageCTelemetryState):
        """Initialize collector with wrapped StageCTelemetryState."""
        self._state = state

    def on_step(self, iteration: int, loss: float, metrics: Mapping[str, float]) -> None:
        """Record per-iteration telemetry (same logic as Stage A)."""
        self._state.iteration_count[0] = iteration
        self._state.loss_trace_sample.append(loss)
        chi2 = metrics.get('chi_squared', loss)
        mse = metrics.get('masked_mse', 0.0)
        self._state.chi_squared_trace_sample.append(chi2)
        self._state.masked_mse_trace_sample.append(mse)
        self._state.perf_closure_evals[0] += 1
        if 'forward_time_ms' in metrics:
            self._state.perf_forward_times_ms.append(metrics['forward_time_ms'])
        if 'variance_floor_clamped_pixels' in metrics:
            self._state.variance_floor_clamped_pixels[0] += int(metrics['variance_floor_clamped_pixels'])
        if 'variance_floor_masked_pixels' in metrics:
            self._state.variance_floor_masked_pixels[0] += int(metrics['variance_floor_masked_pixels'])

    def on_validation(self, scope: str, chi2: float, payload: Mapping[str, Any]) -> None:
        """Record full-validation telemetry (tuple format for Stage C parity with Stage A/B)."""
        self._state.perf_validation_runs[0] += 1
        current_iter = self._state.iteration_count[0]
        # Append with iteration tuples for Stage C full traces (parity with Stage A/B)
        self._state.chi_squared_trace_full.append((current_iter, chi2))
        loss = payload.get('loss', chi2)
        self._state.loss_trace_full.append((current_iter, loss))
        mse = payload.get('masked_mse', 0.0)
        self._state.masked_mse_trace_full.append((current_iter, mse))
        # Stage C best_loss_full is a list, but we treat it as (best, iter) tuple stored in list[0:2]
        # Initialize if empty or update if better
        if len(self._state.best_loss_full) == 0:
            self._state.best_loss_full.extend([loss, current_iter])
        elif loss < self._state.best_loss_full[0]:
            self._state.best_loss_full[0] = loss
            self._state.best_loss_full[1] = current_iter
        if chi2 < self._state.chi_squared_best[0]:
            self._state.chi_squared_best[0] = chi2
            self._state.chi_squared_best[1] = current_iter
        if mse < self._state.masked_mse_best[0]:
            self._state.masked_mse_best[0] = mse
            self._state.masked_mse_best[1] = current_iter
        if 'best_snapshot' in payload:
            self._state.best_params_snapshot = [payload['best_snapshot']]
        # Record panel diagnostics if present (PERF-WARM-SIM-001)
        if 'panel_diag' in payload and self._state.panel_loss_diag is not None:
            self._state.panel_loss_diag.extend(payload['panel_diag'])

    def finalize(self) -> StageResult:
        """Construct StageResult for Stage C."""
        telemetry = StageCTelemetry(
            iteration_count=self._state.iteration_count[0],
            loss_trace_sample=self._state.loss_trace_sample,
            loss_trace_full=self._state.loss_trace_full,
            best_loss_full=self._state.best_loss_full,
            chi_squared_trace_sample=self._state.chi_squared_trace_sample,
            chi_squared_trace_full=self._state.chi_squared_trace_full,
            chi_squared_best=self._state.chi_squared_best,
            masked_mse_trace_sample=self._state.masked_mse_trace_sample,
            masked_mse_trace_full=self._state.masked_mse_trace_full,
            masked_mse_best=self._state.masked_mse_best,
            best_params_snapshot=self._state.best_params_snapshot,
            panel_loss_diag=self._state.panel_loss_diag,
        )

        perf_counters = StagePerfCounters(
            closure_evals=self._state.perf_closure_evals[0],
            validation_runs=self._state.perf_validation_runs[0],
            forward_times_ms=self._state.perf_forward_times_ms,
            variance_floor_clamped_pixels=self._state.variance_floor_clamped_pixels[0],
            variance_floor_masked_pixels=self._state.variance_floor_masked_pixels[0],
        )

        return StageResult(stage="C", telemetry=telemetry, perf_counters=perf_counters)

    @property
    def state(self) -> StageCTelemetryState:
        """Access wrapped telemetry state (read-only view)."""
        return self._state
