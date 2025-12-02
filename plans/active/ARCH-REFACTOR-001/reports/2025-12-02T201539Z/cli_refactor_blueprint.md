# Phase D.2: CLI Refactor Blueprint — refine_one.py Migration to RefinementEngine

**Initiative:** ARCH-REFACTOR-001 Phase D.2
**Date:** 2025-12-02T201539Z
**Status:** Planning

## Objective

Migrate `dbex/refine_one.py::run_nanobrag_backend()` from calling `run_nanobrag_refinement()` facade to directly instantiating and running `RefinementEngine` with typed contexts.

## Current State (Facade Pattern)

**File:** `dbex/refine_one.py`
**Function:** `run_nanobrag_backend()` (lines ~277-600)
**Call site:** Line 546

### Current Pattern (lines 505-555)

```python
from dbex.nanobrag_refinement import run_nanobrag_refinement, RefinementConfig
from dbex.refinement.context import build_job_context

# Configure refinement
refine_config = RefinementConfig(
    device=str(device),
    dtype=torch.float32,
    sigma_floor_value=sigma_floor_value,
    sigma_readout_provenance=sigma_provenance,
    sigma_readout_reference_value=sigma_reference_target_units,
    enable_stage_b=args.enable_stage_b,
    enable_stage_c=args.enable_stage_c,
    calibration_metadata=calibration_metadata,
)

# Build JobContext
job_context = build_job_context(
    cli_args=args,
    dataload=DL,
    calibration_metadata=calibration_metadata,
    sigma_provenance=sigma_provenance,
    sigma_reference_value=sigma_reference_target_units,
    refinement_config=refine_config,
    hkl_metadata=hkl_metadata,
    asu_map=asu_map,
    spot_scale_override=spot_scale,
    hkl_source=hkl_source,
    hkl_path=hkl_path,
)

# Call facade
Bragg_refined, refine_telemetry_dict, engine_artifacts = run_nanobrag_refinement(
    inputs=inputs,
    detector=DL.detector,
    beam=DL.beam,
    crystal=DL.crystal,
    hkl_grid=hkl_grid,
    hkl_metadata=hkl_metadata,
    config=refine_config,
    job_context=job_context
)
```

**Problem:** `run_nanobrag_refinement()` is a monolithic facade (~656 lines) wrapping Stage A/B/C logic.
**Goal:** Replace with direct RefinementEngine instantiation using typed contexts.

## Target State (Engine Pattern)

### Required Imports (lines 505-515)

**Remove:**
```python
from dbex.nanobrag_refinement import run_nanobrag_refinement, RefinementConfig
```

**Add:**
```python
from dbex.refinement.config import RefinementConfig
from dbex.refinement.engine import RefinementEngine
from dbex.refinement.stage_a import StageA
from dbex.refinement.stage_b import StageB
from dbex.refinement.stage_c import StageC
from dbex.refinement.inputs import prepare_refinement_inputs
from dbex.refinement.context import build_refinement_context, build_job_context
```

**Note:** `prepare_refinement_inputs` is already imported earlier (line ~200) for building `inputs` before refinement.
         Only context builders need to be added.

### Target Pattern (lines 514-580)

```python
# 1. Configure refinement (UNCHANGED)
refine_config = RefinementConfig(
    device=str(device),
    dtype=torch.float32,
    sigma_floor_value=sigma_floor_value,
    sigma_readout_provenance=sigma_provenance,
    sigma_readout_reference_value=sigma_reference_target_units,
    enable_stage_b=args.enable_stage_b,
    enable_stage_c=args.enable_stage_c,
    calibration_metadata=calibration_metadata,
)

# 2. Build JobContext (UNCHANGED)
job_context = build_job_context(
    cli_args=args,
    dataload=DL,
    calibration_metadata=calibration_metadata,
    sigma_provenance=sigma_provenance,
    sigma_reference_value=sigma_reference_target_units,
    refinement_config=refine_config,
    hkl_metadata=hkl_metadata,
    asu_map=asu_map,
    spot_scale_override=spot_scale,
    hkl_source=hkl_source,
    hkl_path=hkl_path,
)

# 3. Build RefinementContext (NEW)
refinement_context = build_refinement_context(
    refinement_inputs=inputs,  # RefinementInputs prepared earlier (line ~490)
    detector=DL.detector,
    beam=DL.beam,
    crystal=DL.crystal,
    hkl_grid=hkl_grid,
    hkl_metadata=hkl_metadata,
    baseline_crystal=None,  # No perturbed geometry in CLI path (unlike test_stage_a_expansion)
    baseline_detector=DL.detector if refine_config.enable_stage_c else None,  # Stage C requires baseline
    asu_map=asu_map,  # Pre-computed ASU mapping from CLI prep (line ~474)
    hkl_indices_grid=None,  # Optional; not used in CLI path
    halo_mask=None,  # Optional; not used in CLI path
    extras={"job_context": job_context},  # Thread JobContext for stage access
)

# 4. Instantiate RefinementEngine (NEW)
stages = [StageA()]  # Always run Stage A
if refine_config.enable_stage_b:
    stages.append(StageB())
if refine_config.enable_stage_c:
    stages.append(StageC())

engine = RefinementEngine(stages=stages, config=refine_config)

# 5. Run refinement (NEW)
# Engine.run() expects dict with 'context' key per ARCH-REFINE-001 Phase B.1
engine_inputs = {"context": refinement_context}
refine_telemetry_dict = engine.run(engine_inputs)

# 6. Extract artifacts (NEW)
# RefinementEngine stores artifacts in engine._artifacts after run()
# Engine artifacts format: {"stage_a": StageAArtifacts, "stage_b": StageBArtifacts, ...}
engine_artifacts = engine._artifacts

# 7. Extract final Bragg (NEW)
# Stage A always runs; final Bragg is in StageAArtifacts.bragg_full (terminal artifact)
# If Stage B/C ran, their artifacts override; otherwise use Stage A
if "stage_c" in engine_artifacts:
    final_stage_artifacts = engine_artifacts["stage_c"]
    Bragg_refined = final_stage_artifacts.bragg_full  # Stage C terminal Bragg
elif "stage_b" in engine_artifacts:
    final_stage_artifacts = engine_artifacts["stage_b"]
    Bragg_refined = final_stage_artifacts.bragg_full  # Stage B terminal Bragg
else:
    final_stage_artifacts = engine_artifacts["stage_a"]
    Bragg_refined = final_stage_artifacts.bragg_full  # Stage A terminal Bragg

# 8. Extract Stage A telemetry (UNCHANGED downstream)
# refine_telemetry_dict is already Dict[str, RefinementTelemetry] keyed by stage ("A", "B", "C")
# Existing code at lines 558-595 already handles multi-stage telemetry extraction
refine_telemetry = refine_telemetry_dict["A"]  # Stage A telemetry (always present)
```

## Detailed Change Mapping

### Section 1: Import Updates (lines 505-515)

**Before:**
```python
    from dbex.nanobrag_refinement import run_nanobrag_refinement, RefinementConfig
    from dbex.refinement.context import build_job_context
```

**After:**
```python
    from dbex.refinement.config import RefinementConfig
    from dbex.refinement.engine import RefinementEngine
    from dbex.refinement.stage_a import StageA
    from dbex.refinement.stage_b import StageB
    from dbex.refinement.stage_c import StageC
    from dbex.refinement.context import build_refinement_context, build_job_context
```

**Rationale:** Import Engine and Stages directly; RefinementConfig moved to canonical module.

### Section 2: Context Building (NEW, after JobContext construction)

**Insert after line 542 (after `job_context = build_job_context(...)`):**

```python
    # Build typed RefinementContext for Engine
    refinement_context = build_refinement_context(
        refinement_inputs=inputs,
        detector=DL.detector,
        beam=DL.beam,
        crystal=DL.crystal,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        baseline_crystal=None,  # CLI path uses actual geometry (no perturbation)
        baseline_detector=DL.detector if refine_config.enable_stage_c else None,
        asu_map=asu_map,
        hkl_indices_grid=None,
        halo_mask=None,
        extras={"job_context": job_context},
    )
    print(f"[nanobrag backend] RefinementContext built (baseline_detector={'present' if refinement_context.baseline_detector else 'None'})")
```

**Rationale:** `build_refinement_context` encapsulates all geometry/HKL state into typed container.

### Section 3: Engine Instantiation (NEW, replace facade call)

**Remove lines 544-555 (facade call block):**
```python
    try:
        # ARCH-STAGE-CONTEXT-001 Phase B.4: run_nanobrag_refinement now returns artifacts
        Bragg_refined, refine_telemetry_dict, engine_artifacts = run_nanobrag_refinement(
            inputs=inputs,
            detector=DL.detector,
            beam=DL.beam,
            crystal=DL.crystal,
            hkl_grid=hkl_grid,
            hkl_metadata=hkl_metadata,
            config=refine_config,
            job_context=job_context
        )
```

**Replace with (NEW lines 544-575):**
```python
    try:
        # ARCH-REFACTOR-001 Phase D.2: Direct RefinementEngine usage (no facade)
        # Instantiate stages based on config flags
        stages = [StageA()]
        if refine_config.enable_stage_b:
            stages.append(StageB())
        if refine_config.enable_stage_c:
            stages.append(StageC())

        # Instantiate and run Engine
        engine = RefinementEngine(stages=stages, config=refine_config)
        engine_inputs = {"context": refinement_context}
        refine_telemetry_dict = engine.run(engine_inputs)

        # Extract artifacts from Engine
        # Engine stores artifacts in engine._artifacts: {"stage_a": StageAArtifacts, ...}
        engine_artifacts = engine._artifacts

        # Extract final Bragg from terminal stage
        # Stage C > Stage B > Stage A (last stage wins)
        if "stage_c" in engine_artifacts:
            Bragg_refined = engine_artifacts["stage_c"].bragg_full
        elif "stage_b" in engine_artifacts:
            Bragg_refined = engine_artifacts["stage_b"].bragg_full
        else:
            Bragg_refined = engine_artifacts["stage_a"].bragg_full
```

**Rationale:**
- Engine pattern: instantiate stages, configure engine, run with typed context
- Artifacts extraction: Engine exposes `_artifacts` dict after `run()`
- Final Bragg: Terminal stage's `bragg_full` field (last stage wins)

### Section 4: Telemetry Extraction (UNCHANGED, lines 557-595)

**No changes required.** Existing code already handles multi-stage telemetry:
- Line 558: `refine_telemetry = refine_telemetry_dict["A"]` (Stage A always present)
- Lines 562-565: Build `stage_results` dict from telemetry (already Engine-compatible)
- Lines 576-595: Log Stage B/C telemetry if present

**Validation:** Ensure telemetry dict keys remain "A", "B", "C" (Stage labels).

## Context Builder Contracts

### build_job_context (ALREADY USED, line 528)

**Signature (dbex/refinement/context.py:297):**
```python
def build_job_context(
    cli_args,
    dataload,
    calibration_metadata: Optional[Dict[str, Any]],
    sigma_provenance: str,
    sigma_reference_value: float,
    refinement_config: RefinementConfig,
    hkl_metadata: Dict[str, Any],
    asu_map: Optional[torch.Tensor],
    spot_scale_override: float,
    hkl_source: str,
    hkl_path: Optional[str],
) -> JobContext
```

**Already correct in CLI.** No changes needed.

### build_refinement_context (NEW CALL, insert after line 542)

**Signature (dbex/refinement/context.py:91):**
```python
def build_refinement_context(
    refinement_inputs: RefinementInputs,
    detector,  # dxtbx Detector
    beam,  # dxtbx Beam
    crystal,  # dxtbx Crystal
    hkl_grid: torch.Tensor,
    hkl_metadata: Dict[str, Any],
    baseline_crystal=None,  # Optional baseline for misset extraction
    baseline_detector=None,  # Optional baseline for Stage C offsets
    asu_map: Optional[torch.Tensor] = None,
    hkl_indices_grid: Optional[np.ndarray] = None,
    halo_mask: Optional[np.ndarray] = None,
    extras: Optional[Dict[str, Any]] = None,
) -> RefinementContext
```

**CLI-specific values:**
- `refinement_inputs`: Already prepared (line ~490, `inputs = prepare_refinement_inputs(...)`)
- `detector`, `beam`, `crystal`: From `DL` (DataLoad object)
- `hkl_grid`, `hkl_metadata`: Already prepared (lines ~455-470)
- `baseline_crystal`: `None` (CLI uses actual geometry; tests use perturbed)
- `baseline_detector`: `DL.detector` if Stage C enabled, else `None`
- `asu_map`: Pre-computed (line ~474, `asu_map = build_structure_factor_grid(...)`)
- `hkl_indices_grid`: `None` (CLI doesn't pre-compute Miller indices grid)
- `halo_mask`: `None` (CLI doesn't pre-compute halo mask)
- `extras`: `{"job_context": job_context}` (thread JobContext for stage access)

## Artifact Extraction Contract

### Engine Artifacts Format

**Source:** `RefinementEngine._artifacts` (populated by `engine.run()`)
**Type:** `Dict[str, Any]` keyed by stage label (e.g., `"stage_a"`, `"stage_b"`, `"stage_c"`)

**Contents:**
- `"stage_a"`: `StageAArtifacts` dataclass (from `dbex/refinement/stage_a.py`)
  * `bragg_full: np.ndarray` — Full-detector Bragg intensities (terminal)
  * `stage_a_context: StageAContext` — Stage A runtime context
  * Additional Stage A metadata

- `"stage_b"`: `StageBArtifacts` dataclass (from `dbex/refinement/stage_b.py`, if enabled)
  * `bragg_full: np.ndarray` — Full-detector Bragg intensities (terminal, with shell modifiers)
  * `shell_modifiers: torch.Tensor` — Per-shell or per-reflection modifiers
  * Additional Stage B metadata

- `"stage_c"`: `StageCContextArtifacts` dataclass (from `dbex/refinement/stage_c.py`, if enabled)
  * `bragg_full: np.ndarray` — Full-detector Bragg intensities (terminal, with detector offsets)
  * `panel_distance_deltas: np.ndarray` — Per-panel distance offsets
  * Additional Stage C metadata

**Terminal Bragg Precedence:**
1. If Stage C ran: use `engine_artifacts["stage_c"].bragg_full`
2. Else if Stage B ran: use `engine_artifacts["stage_b"].bragg_full`
3. Else: use `engine_artifacts["stage_a"].bragg_full`

**Current CLI code (lines 557-573):** Already expects `engine_artifacts` dict; no changes needed downstream.

## Validation Strategy

### Unit Tests (Staged)

**Phase D.2 Validation (CLI-only):**
1. **CLI smoke test (small detector):**
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata \
     | tee plans/active/ARCH-REFACTOR-001/reports/<timestamp>/pytest_cli_diagnostics.log
   ```

2. **CLI backend smoke test (simulator invocation):**
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_runs_simulator \
     | tee plans/active/ARCH-REFACTOR-001/reports/<timestamp>/pytest_cli_backend.log
   ```

**Gate:** Both tests PASSED, no ImportError, HDF5 output structure preserved.

### Integration Tests (Phase D.3)

**After test harness migration (Phase D.3):**
- Run all 6 Stage A/B/C smoke tests (test_torch_refine_smoke.py)
- Validate telemetry dict keys, artifact structure, final Bragg consistency

### Regression Guard

**Compare outputs before/after:**
1. Run CLI with facade (before D.2): capture HDF5 output + telemetry JSON
2. Run CLI with Engine (after D.2): capture HDF5 output + telemetry JSON
3. Compare:
   - Final Bragg intensities (should match within 1e-6)
   - Telemetry dict keys ("A", "B", "C" labels preserved)
   - HDF5 `/torch_diagnostics` group structure (backward compatible)

**Tool:** `h5diff` or custom Python script comparing datasets/attrs

## Risk Assessment

**Risk Level:** MEDIUM

**Risks:**
1. **Artifact extraction mismatch:** Engine artifacts format differs from facade return
   - Mitigation: Engine already exposes `_artifacts` dict; CLI code already expects this
2. **Telemetry key mismatch:** Engine uses different stage labels
   - Mitigation: Engine uses "A"/"B"/"C" labels (validated in test_refinement_engine.py)
3. **Downstream HDF5 breakage:** Writer expects different telemetry structure
   - Mitigation: Telemetry dict format unchanged (same RefinementTelemetry dataclass)

**Rollback criteria:**
- If CLI smoke tests fail → revert D.2 changes, reassess Engine contract

## Dependencies & Sequencing

**Blocks:**
- Phase D.3 (Test Harness Migration) — requires CLI pattern as reference
- Phase D.5 (Facade Deletion) — requires CLI migrated away from facade

**Blocked by:**
- Phase D.1 (Config Migration) — requires `dbex.refinement.config` to exist

**Can run in parallel with:**
- None (D.2 is critical path for production entry point)

## Implementation Checklist

Phase D.2 is **complete** when:
1. ✅ Import section updated (lines 505-515): RefinementEngine + Stages imported
2. ✅ `build_refinement_context()` call added (after line 542)
3. ✅ Facade call removed (lines 544-555)
4. ✅ Engine instantiation + run() added (lines 544-575, new)
5. ✅ Artifact extraction logic updated (Bragg from terminal stage)
6. ✅ Telemetry extraction unchanged (lines 557-595)
7. ✅ CLI smoke tests PASSED (2 selectors)
8. ✅ No ImportError when running `python -m dbex.refine_one --help`
9. ✅ HDF5 output structure preserved (backward compatible)
10. ✅ Artifacts logged under D.2 implementation reports directory

**Sign-off:** Mark implementation.md Phase D.2 checklist item complete; proceed to D.3 (Test Harness Migration).
