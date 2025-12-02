# Phase D.2 Planning Notes — CLI Refactor (refine_one.py)

**Initiative:** ARCH-REFACTOR-001 Phase D.2
**Loop:** 2025-12-02T220000Z
**Galph Action:** Planning (servicing problems.md ledger directive "PRIORITIZE ARCH-REFACTOR-001 ASAP")
**Focus:** Migrate `dbex/refine_one.py::run_nanobrag_backend()` from `run_nanobrag_refinement` facade to direct `RefinementEngine` instantiation.

---

## Context

- **Problems.md guard triggered:** Last two galph_memory entries (2025-12-02T201539Z, 2025-12-02T210000Z) don't mention problems.md ledger.
- **Ledger directive:** "PRIORITIZE ARCH-REFACTOR-001 ASAP" remains active.
- **Phase C status:** Complete (all `*_impl.py` deleted, Exit Criterion #1 satisfied).
- **Phase D.1 status:** Complete (RefinementConfig extracted to `dbex/refinement/config.py`, commit 43a70eae).
- **Phase D.2 status:** Not started. CLI blueprint delivered in 2025-12-02T201539Z planning artifacts (`cli_refactor_blueprint.md`).

---

## Scope Analysis

### Current State (refine_one.py lines 505-595)

**Facade call site:** Line 547
**Pattern:**
1. Import `run_nanobrag_refinement` from facade (line 506)
2. Build `RefinementConfig` (lines 515-524)
3. Build `JobContext` via `build_job_context()` (lines 529-541)
4. Call facade with 8 arguments (lines 547-556):
   - `inputs` (RefinementInputs)
   - `detector`, `beam`, `crystal` (dxtbx objects)
   - `hkl_grid`, `hkl_metadata` (structure factors + metadata)
   - `config` (RefinementConfig)
   - `job_context` (JobContext)
5. Extract outputs (lines 547, 559-595):
   - `Bragg_refined` (final forward model array)
   - `refine_telemetry_dict` (dict of RefinementTelemetry per stage)
   - `engine_artifacts` (stage-specific artifacts)
6. Extract `stage_results` from telemetry (lines 563-566, ARCH-TELEMETRY-001 Phase C.2)
7. Compute refined MSE and log status (lines 569-595)

**Imports:**
- `dbex.refinement.config.RefinementConfig` — already migrated (Phase D.1)
- `dbex.nanobrag_refinement.run_nanobrag_refinement` — facade to be removed

### Target State (Engine pattern)

**Required new imports:**
- `dbex.refinement.engine.RefinementEngine`
- `dbex.refinement.stage_a.StageA`
- `dbex.refinement.stage_b.StageB`
- `dbex.refinement.stage_c.StageC`
- `dbex.refinement.context.build_refinement_context` (already imports `build_job_context`)

**Pattern:**
1. Build `RefinementContext` via `build_refinement_context()` helper (NEW)
   - Consumes: `inputs`, `detector`, `beam`, `crystal`, `hkl_grid`, `hkl_metadata`, `baseline_crystal`, `baseline_detector`, `asu_map`, `hkl_indices_grid`, `halo_mask`, `extras`
   - Note: `baseline_detector` required if Stage C enabled (per PERF-WARM-SIM-001 retargeting logic)
   - Note: Thread `job_context` via `extras` dict for stage access
2. Instantiate stage list based on `refine_config.enable_stage_*` flags (NEW)
3. Instantiate `RefinementEngine(stages=stages, config=refine_config)` (NEW)
4. Call `engine.run({"context": refinement_context})` (NEW)
   - Per ARCH-REFACTOR-001 Exit Criterion #4, engine accepts dict with 'context' key
5. Extract outputs from engine (NEW):
   - `refine_telemetry_dict` returned directly by `engine.run()`
   - `Bragg_refined` from final stage artifact (precedence: C > B > A)
   - `engine_artifacts` from `engine._artifacts` (private attribute, documented pattern)

**Validation selectors (from implementation.md D.2):**
- `tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata`
- `tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_runs_simulator`

---

## Implementation Strategy

### Step 1: Import Updates (lines 505-508)

**Remove:**
```python
from dbex.nanobrag_refinement import run_nanobrag_refinement
```

**Add:**
```python
from dbex.refinement.engine import RefinementEngine
from dbex.refinement.stage_a import StageA
from dbex.refinement.stage_b import StageB
from dbex.refinement.stage_c import StageC
from dbex.refinement.context import build_refinement_context  # add to existing build_job_context import
```

### Step 2: Build RefinementContext (after line 543, before try block)

```python
# Build RefinementContext (ARCH-REFACTOR-001 Phase D.2)
# Wraps all refinement inputs in typed context for Engine consumption
refinement_context = build_refinement_context(
    refinement_inputs=inputs,  # RefinementInputs prepared at line ~490
    detector=DL.detector,
    beam=DL.beam,
    crystal=DL.crystal,
    hkl_grid=hkl_grid,
    hkl_metadata=hkl_metadata,
    baseline_crystal=None,  # CLI path has no perturbed geometry (unlike test_stage_a_expansion)
    baseline_detector=DL.detector if refine_config.enable_stage_c else None,  # Stage C retargeting requires baseline
    asu_map=asu_map,  # Pre-computed ASU mapping from CLI prep (line ~474)
    hkl_indices_grid=None,  # Optional; not used in CLI path
    halo_mask=None,  # Optional; not used in CLI path
    extras={"job_context": job_context},  # Thread JobContext for stage access to CLI args/calibration
)
```

**Rationale:**
- `baseline_detector=DL.detector if enable_stage_c else None` matches PERF-WARM-SIM-001 retargeting logic
- `extras["job_context"]` preserves existing stage access to calibration metadata and CLI args
- All other fields match facade signature

### Step 3: Instantiate Engine (after refinement_context build, before try block)

```python
# Instantiate RefinementEngine with stage list (ARCH-REFACTOR-001 Phase D.2)
stages = [StageA()]  # Always run Stage A
if refine_config.enable_stage_b:
    stages.append(StageB())
if refine_config.enable_stage_c:
    stages.append(StageC())

engine = RefinementEngine(stages=stages, config=refine_config)
```

**Rationale:**
- Mirrors CLI flag semantics (`--enable-stage-b`, `--enable-stage-c`)
- Stage order: A → B → C (normative per spec-db-workflow.md)

### Step 4: Run Engine (replace facade call lines 547-556)

**Replace:**
```python
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

**With:**
```python
# Run refinement via RefinementEngine (ARCH-REFACTOR-001 Phase D.2)
# Engine.run() expects dict with 'context' key per Exit Criterion #4
engine_inputs = {"context": refinement_context}
refine_telemetry_dict = engine.run(engine_inputs)

# Extract final Bragg from terminal stage artifact (precedence: C > B > A)
# RefinementEngine stores artifacts in engine._artifacts (private, documented pattern)
if refine_config.enable_stage_c and "C" in engine._artifacts:
    Bragg_refined = engine._artifacts["C"].bragg_full
elif refine_config.enable_stage_b and "B" in engine._artifacts:
    Bragg_refined = engine._artifacts["B"].bragg_full
else:
    Bragg_refined = engine._artifacts["A"].bragg_full

# Extract engine_artifacts for downstream writer/diagnostics (ARCH-STAGE-CONTEXT-001 Phase B.4)
engine_artifacts = engine._artifacts
```

**Rationale:**
- Engine returns `refine_telemetry_dict` directly (dict of {label: RefinementTelemetry})
- Final Bragg array extracted from terminal stage artifact (C > B > A precedence matches facade semantics)
- `engine._artifacts` provides stage-specific artifacts (ARCH-STAGE-CONTEXT-001)

### Step 5: Preserve Downstream Logic (lines 558-595)

**No changes needed:**
- Stage A telemetry extraction (line 559)
- `stage_results` extraction from telemetry (lines 563-566, ARCH-TELEMETRY-001 Phase C.2)
- Refined MSE computation (lines 569-570)
- Logging (lines 572-584)
- Exception handling fallback (lines 590-595)

All downstream logic consumes `refine_telemetry_dict` and `engine_artifacts`, which Engine provides in the same format as the facade.

---

## Validation Plan

### Mapped Tests (from implementation.md D.2)
1. `tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata`
   - Validates HDF5 `/torch_diagnostics` attributes after refinement
   - Expected: same attributes as facade path (masked_mse, loss_mask_coverage, n_rois, target_shape, backend)

2. `tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_runs_simulator`
   - Validates CLI smoke test with minimal fixture
   - Expected: refinement completes without errors, telemetry present

### Environment Flags (from TESTING_GUIDE.md)
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv \
  tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata \
  tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_runs_simulator \
  | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-02T220000Z/pytest_cli_refactor.log
```

### Expected Outcomes
- Both tests PASS
- HDF5 schema unchanged (backward compatible)
- Telemetry structure preserved (stage_results extraction works)
- No import errors
- No behavioral regression vs facade path

---

## Risks & Mitigations

### Risk 1: `engine._artifacts` attribute access
**Issue:** RefinementEngine stores artifacts in private `_artifacts` dict; direct attribute access may be brittle.
**Mitigation:** This is documented pattern in CLI blueprint and test migration plan. Engine contract guarantees `_artifacts` availability after `run()`. If this proves fragile, can add public accessor in follow-up.

### Risk 2: `baseline_detector` requirement for Stage C
**Issue:** If Stage C is enabled but `baseline_detector=None`, retargeting logic may fail.
**Mitigation:** Explicitly set `baseline_detector=DL.detector if enable_stage_c else None` per PERF-WARM-SIM-001 semantics. Validation selector `test_stage_c_detector_microslip` will catch regressions.

### Risk 3: `job_context` threading via `extras` dict
**Issue:** Stages expect `job_context` for calibration metadata access; if not threaded, stages may fail.
**Mitigation:** Thread via `extras={"job_context": job_context}` per RefinementContext contract. Validation selectors will catch missing context.

### Risk 4: Telemetry structure assumptions
**Issue:** Downstream code expects `refine_telemetry_dict` keys "A", "B", "C" and `engine_artifacts` dict.
**Mitigation:** Engine returns exactly this structure (validated in `test_refinement_engine.py`). CLI code unchanged except facade replacement.

---

## Findings Applied

- **ARCH-ENGINE-002:** RefinementEngine is canonical seam; stages consume typed contexts only.
- **ARCH-STAGE-CTX-001:** Stages receive RefinementContext/RefinementSharedContext, not ad-hoc dicts.
- **ARCH-TELEMETRY-001 Phase C.2:** StageResult extraction from telemetry preserved.
- **GRADIENT-004:** Device/dtype neutrality maintained (engine config.device/dtype passed to stages).
- **PERF-WARM-SIM-001:** Stage C baseline detector requirement honored.

---

## Next Steps

1. **Ralph implementation (Phase D.2):**
   - Apply import updates (Step 1)
   - Add `build_refinement_context` call (Step 2)
   - Add stage list + engine instantiation (Step 3)
   - Replace facade call with `engine.run()` + artifact extraction (Step 4)
   - Validate with 2 mapped CLI tests

2. **Subsequent loops (Phase D.3-D.5):**
   - D.3: Migrate test harness files (6 test functions + 1 tooling function)
   - D.4: Fix legacy physics.loss imports (4 inline imports in test_physics_loss_current.py)
   - D.5: Delete facade after comprehensive verification (12-step checklist)

---

## Artifacts Reserved

- **Directory:** `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T220000Z/`
- **Files:**
  - `planning_notes.md` (this file)
  - `pytest_cli_refactor.log` (Ralph's validation output)
  - `summary.md` (loop summary, will be written by Galph at end-of-loop)
