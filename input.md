# Input for Ralph — ARCH-REFACTOR-001 Phase D.2: CLI Refactor

**Summary:** Migrate `dbex/refine_one.py::run_nanobrag_backend()` from `run_nanobrag_refinement` facade to direct `RefinementEngine` instantiation using typed contexts.

**Mode:** Parity
**InitiativeType:** architecture
**Focus:** [ARCH-REFACTOR-001] — Refinement Engine Modularization & Physics Separation (Phase D.2: CLI Refactor)
**Branch:** integration
**Mapped tests:**
- `tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata`
- `tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_runs_simulator`

**Artifacts:** `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T220000Z/`

---

## Do Now

**Implement:** `dbex/refine_one.py::run_nanobrag_backend()` (lines 505-595)

**Objective:** Replace the `run_nanobrag_refinement` facade call with direct `RefinementEngine` instantiation, following the 5-step Engine pattern documented in `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T201539Z/cli_refactor_blueprint.md`.

**Tasks:**

### 1. Import Updates (lines 505-508)

**Remove:**
```python
from dbex.nanobrag_refinement import run_nanobrag_refinement
```

**Add to existing imports:**
```python
from dbex.refinement.config import RefinementConfig  # already migrated (Phase D.1)
from dbex.refinement.context import build_job_context, build_refinement_context
from dbex.refinement.engine import RefinementEngine
from dbex.refinement.stage_a import StageA
from dbex.refinement.stage_b import StageB
from dbex.refinement.stage_c import StageC
```

**Note:** `build_job_context` is already imported at line 507; extend that import to include `build_refinement_context`.

---

### 2. Build RefinementContext (after line 543, before `try:` block at line 545)

Insert the following between the `JobContext` logging (line 543) and the `try:` block:

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
- `baseline_detector=DL.detector if enable_stage_c else None` matches PERF-WARM-SIM-001 retargeting logic.
- `extras["job_context"]` preserves existing stage access to calibration metadata and CLI args.

---

### 3. Instantiate RefinementEngine (after `refinement_context` build, before `try:` block)

Insert the following immediately after the `build_refinement_context` call:

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
- Mirrors CLI flag semantics (`--enable-stage-b`, `--enable-stage-c`).
- Stage order: A → B → C (normative per `docs/spec-db-workflow.md`).

---

### 4. Run Engine and Extract Artifacts (replace lines 547-556)

**Replace:**
```python
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
- Engine returns `refine_telemetry_dict` directly (dict of {label: RefinementTelemetry}).
- Final Bragg array extracted from terminal stage artifact (C > B > A precedence matches facade semantics).
- `engine._artifacts` provides stage-specific artifacts (ARCH-STAGE-CONTEXT-001).

---

### 5. Preserve Downstream Logic (no changes needed)

**Lines 558-595** remain unchanged:
- Stage A telemetry extraction (line 559)
- `stage_results` extraction from telemetry (lines 563-566, ARCH-TELEMETRY-001 Phase C.2)
- Refined MSE computation (lines 569-570)
- Logging (lines 572-584)
- Exception handling fallback (lines 590-595)

All downstream logic consumes `refine_telemetry_dict` and `engine_artifacts`, which Engine provides in the same format as the facade.

---

## How-To Map

### Validation Commands

Run the 2 mapped CLI selectors to validate the refactor:

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

**Expected outcomes:**
- Both tests PASS
- HDF5 `/torch_diagnostics` attributes unchanged (backward compatible)
- Telemetry structure preserved (stage_results extraction works)
- No import errors
- No behavioral regression vs facade path

---

## Pitfalls To Avoid

1. **Import Order:** Do not import `run_nanobrag_refinement` after removing the facade import. Ensure `build_refinement_context` is added to the existing `build_job_context` import line.

2. **RefinementContext Baseline Detector:** Stage C requires `baseline_detector` for retargeting logic (PERF-WARM-SIM-001). Always set `baseline_detector=DL.detector if enable_stage_c else None`.

3. **JobContext Threading:** Stages expect `job_context` for calibration metadata access. Always thread via `extras={"job_context": job_context}`.

4. **Engine Artifact Access:** `engine._artifacts` is a private attribute but documented pattern (per CLI blueprint). Do NOT attempt to add a public accessor in this loop; that can be a follow-up refactor.

5. **Terminal Stage Precedence:** Bragg extraction must follow C > B > A precedence to match facade semantics. Check `enable_stage_c` first, then `enable_stage_b`, then default to A.

6. **Telemetry Structure:** Do NOT change downstream code (lines 558-595). Engine returns `refine_telemetry_dict` in the same format as facade (dict of {label: RefinementTelemetry}).

7. **Exception Handling:** The `try/except` block (lines 545-595) must remain unchanged. Only the facade call inside the `try` block is replaced.

8. **Device/Dtype Neutrality (GRADIENT-004):** Engine receives `config.device` and `config.dtype` from `refine_config`, which is already built correctly (lines 515-524). Do NOT add device/dtype overrides in Engine instantiation.

9. **Backward Compatibility:** RefinementConfig is still available via `dbex.nanobrag_refinement` re-export (Phase D.1 backward-compat layer). Import from `dbex.refinement.config` for clarity.

10. **No Test Changes:** This loop only touches `dbex/refine_one.py`. Do NOT modify test files or other consumers yet (those are Phase D.3).

---

## If Blocked

If any of the following occur:

1. **Import errors:** Verify `dbex/refinement/context.py` exports `build_refinement_context` and `build_job_context`. If missing, check git history for Phase D.1 changes.

2. **Engine runtime errors:** Check that `RefinementEngine.run()` accepts dict with 'context' key (ARCH-REFACTOR-001 Exit Criterion #4). If signature mismatch, consult `dbex/refinement/engine.py` and `test_refinement_engine.py`.

3. **Artifact extraction errors:** Verify `engine._artifacts` is populated after `engine.run()`. If empty, check Stage A/B/C `run()` methods store artifacts via `self._artifacts[label] = ...`.

4. **Telemetry structure errors:** Verify `engine.run()` returns dict of {label: RefinementTelemetry}. If format mismatch, consult `test_refinement_engine.py::test_engine_returns_telemetry_dict`.

5. **Test failures:**
   - Log the failure signature in `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T220000Z/pytest_cli_refactor.log`.
   - Update `docs/fix_plan.md` Attempts History with the blocker (e.g., "blocked — engine artifact mismatch, needs [new-initiative-id]").
   - Mark ARCH-REFACTOR-001 Phase D.2 as `blocked` and notify Galph.

---

## Findings Applied (Mandatory)

**From `docs/findings.md`:**

- **ARCH-ENGINE-002:** RefinementEngine is canonical seam; stages consume typed contexts only. (Applied: Engine instantiation + RefinementContext build)

- **ARCH-STAGE-CTX-001:** Stages receive RefinementContext/RefinementSharedContext, not ad-hoc dicts. (Applied: `build_refinement_context` replaces facade's exploded arguments)

- **ARCH-TELEMETRY-001 Phase C.2:** StageResult extraction from telemetry preserved. (Applied: lines 563-566 unchanged, `stage_results` dict builds correctly)

- **GRADIENT-004:** Device/dtype neutrality maintained. (Applied: `refine_config.device`/`dtype` passed to Engine, no overrides)

- **PERF-WARM-SIM-001:** Stage C baseline detector requirement honored. (Applied: `baseline_detector=DL.detector if enable_stage_c else None`)

**No additional findings flagged for this initiative.**

---

## Pointers

**Specs:**
- `docs/spec-db-workflow.md §§30-41` — RefinementEngine protocol architecture
- `docs/architecture/dbex/refinement/context.idl.md` — RefinementContext contract

**Architecture:**
- `plans/active/ARCH-REFACTOR-001/implementation.md` — Phase D checklist (D.1 ✓, D.2 in progress)
- `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T201539Z/cli_refactor_blueprint.md` — Detailed CLI refactor pattern (reference implementation)
- `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T220000Z/planning_notes.md` — This loop's planning notes

**Testing:**
- `docs/TESTING_GUIDE.md §2` — Canonical environment flags and CLI selectors
- `docs/development/TEST_SUITE_INDEX.md` — Test registry (update if new tests added)

**Fix Plan:**
- `docs/fix_plan.md` — Row [ARCH-REFACTOR-001] (lines 52-86, Attempts History includes Phase D.1 complete + D.2 planning)

**Code:**
- `dbex/refine_one.py:505-595` — Current facade call site (target for refactor)
- `dbex/refinement/config.py:1-135` — RefinementConfig dataclass (Phase D.1 extraction)
- `dbex/refinement/context.py:91-XXX` — `build_refinement_context` helper
- `dbex/refinement/engine.py` — RefinementEngine class
- `dbex/refinement/stage_a.py`, `stage_b.py`, `stage_c.py` — Stage implementations

---

## Next Up (optional)

If you finish early and all 2 CLI tests pass:

1. **Commit your work:**
   ```bash
   git add dbex/refine_one.py
   git commit -m "ARCH-REFACTOR-001 Phase D.2: Migrate CLI to RefinementEngine (tests: 2/2 pass)"
   ```

2. **Update implementation.md:** Mark Phase D.2 complete in the checklist at `plans/active/ARCH-REFACTOR-001/implementation.md` line 369.

3. **Do NOT proceed to Phase D.3:** Test migrations require separate planning and validation. Wait for Galph's next loop to scope D.3.

---

## Doc Sync Plan (Conditional)

**Not applicable for this loop:** No new tests are added. CLI selectors already exist in `docs/TESTING_GUIDE.md` and `docs/development/TEST_SUITE_INDEX.md`.

---

## Mapped Tests Guardrail

Both mapped selectors collect > 0 tests:
- `test_torch_diagnostics_metadata` — validates HDF5 `/torch_diagnostics` attributes
- `test_nanobrag_backend_runs_simulator` — CLI smoke test with minimal fixture

If either selector collects 0 tests after your changes, treat this as a blocker and mark Phase D.2 `blocked`.

---

**End of Do Now.**

Ralph, please execute Tasks 1-5 in order, validate with the 2 CLI selectors, and log all outputs to the artifacts directory. If blocked, update `docs/fix_plan.md` and notify Galph. If successful, commit your work and mark Phase D.2 complete in `implementation.md`.
