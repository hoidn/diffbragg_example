"""
Stage artifacts for typed refinement outputs (ARCH-STAGE-CONTEXT-001 Phase B).

Defines artifact dataclasses that stages return alongside telemetry, allowing
the engine and downstream consumers (writer, tests) to access stage outputs
(warm contexts, shell metadata, final Bragg tensors) without scraping private caches.

Per docs/spec-db-workflow.md:33 and ARCH-STAGE-CONTEXT-001:
- Stage A returns warm context (StageAContext payload + schema version)
- Stage B returns shell/ASU metadata + baseline parity diagnostics
- Stage C returns final Bragg tensor

Key Design Points:
- Artifacts are typed and versioned to support evolution
- Engine caches artifacts per stage name (no stage-specific branches)
- Writer/tests fetch artifacts via a single artifacts map
- Telemetry remains separate (RefinementTelemetry schema unchanged)
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class StageAArtifacts:
    """
    Stage A artifacts: warm context payload for downstream stage reuse.

    Per ARCH-STAGE-CONTEXT-001 Phase B.1:
    - Carries StageAContext (simulator+cache snapshot) for Stage B/C warm starts
    - Includes schema version for future compatibility
    - Replaces engine._stage_a_ctx_cache private attribute

    Attributes:
        stage_a_ctx: StageAContext instance (warm simulator cache)
        context_schema_version: Schema version marker (e.g., "v1")

    Normative Requirements:
    - Device/dtype must remain consistent with RefinementSharedContext
    - Warm cache tensors must not be modified after creation
    """
    stage_a_ctx: Any  # StageAContext (avoid circular import)
    context_schema_version: str = "v1"


@dataclass
class StageBArtifacts:
    """
    Stage B artifacts: shell metadata, parity diagnostics, ASU stats.

    Per ARCH-STAGE-CONTEXT-001 Phase B.1 + REFINE-FLOW-001:
    - Shell edges/indices/count for final Bragg reconstruction
    - Baseline parity stats (rel/abs diff, diff payload path)
    - Per-reflection ASU statistics when applicable
    - Replaces engine._stage_b_shell_edges, _stage_b_shell_indices, etc.

    Attributes:
        shell_edges: Shell boundary array (resolution bins)
        shell_indices: Per-HKL shell assignment indices
        n_shells: Number of resolution shells
        stage_b_baseline_rel_diff: REFINE-FLOW-001 parity metric (optional)
        stage_b_baseline_abs_diff: REFINE-FLOW-001 parity metric (optional)
        stage_b_baseline_diff_path: Path to parity diff JSON (optional)
        stage_b_mode: Stage B mode ("shell_modifiers" | "per_reflection")
        n_asu_unique: ASU count for per-reflection mode (optional)
        optimizer_type: Optimizer used (optional)
        asu_modifier_stats: Per-reflection ASU statistics (optional)

    Normative Requirements:
    - Shell metadata must be numpy arrays (CPU-resident)
    - Baseline parity fields required when Stage B baseline guard fires
    """
    shell_edges: Any  # numpy array
    shell_indices: Any  # numpy array
    n_shells: int
    stage_b_baseline_rel_diff: Optional[float] = None
    stage_b_baseline_abs_diff: Optional[float] = None
    stage_b_baseline_diff_path: Optional[str] = None
    stage_b_mode: Optional[str] = None
    n_asu_unique: Optional[int] = None
    optimizer_type: Optional[str] = None
    asu_modifier_stats: Optional[Dict[str, Any]] = None


@dataclass
class StageCArtifacts:
    """
    Stage C artifacts: final Bragg tensor.

    Per ARCH-STAGE-CONTEXT-001 Phase B.1:
    - Carries final [panel, slow, fast] Bragg tensor after detector refinement
    - Replaces engine._stage_c_bragg_full private attribute

    Attributes:
        bragg_full: Final Bragg volume (numpy array, [panel, slow, fast])

    Normative Requirements:
    - Must be numpy array (CPU-resident for HDF5 writer)
    - Shape must match detector geometry [n_panels, slow_pixels, fast_pixels]
    """
    bragg_full: Any  # numpy array [panel, slow, fast]
