# Do Now — ARCH-ENGINE-ARTIFACTS-001 Phase C.1

## Summary
Remove reconstruction helper fallback logic from `run_nanobrag_refinement` so it exclusively uses artifact channel for final Bragg arrays.

## Mode
Implementation

## InitiativeType
architecture

## Focus
ARCH-ENGINE-ARTIFACTS-001 — RefinementEngine artifact channel & final-Bragg unification

## Branch
integration

## Mapped Tests
- `tests/dbex/test_artifact_parity.py::test_stage_a_artifact_matches_helper`
- `tests/dbex/test_artifact_parity.py::test_stage_b_artifact_matches_helper_shell_mode`
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_baseline_smoke`
- `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers`

## Artifacts
`plans/active/ARCH-ENGINE-ARTIFACTS-001/reports/2025-12-02T000500Z/`

## Do Now

### Context
Exit Criteria #1 and #2 are SATISFIED:
- Artifact channel API is complete (engine.artifacts dict, StageResult protocol)
- Parity tests PASS proving Stage A/B artifacts match reconstruction helpers (max_rel=0.000e+00)

Exit Criterion #3 requires removing fallback code that calls reconstruction helpers.

Current state (dbex/nanobrag_refinement.py):
- Lines 228-241: Stage A terminal checks artifact first, falls back to `build_final_bragg_from_stage_a_telemetry`
- Lines 369-409: Stage B terminal checks artifact first, falls back to `build_final_bragg_from_stage_b_telemetry`
- Lines 507-516: Stage C terminal ONLY uses artifacts (RuntimeError if missing) ✓

The fallbacks were defensive coding for "older binaries" but are no longer needed because:
1. All code paths use RefinementEngine which unconditionally populates artifacts
2. Parity tests prove artifacts are populated correctly
3. Stage C already requires artifacts (no fallback)

### Implement

**File**: `dbex/nanobrag_refinement.py`

**Change 1: Stage A terminal path (lines 226-241)**

Replace the artifact-or-fallback pattern with artifact-only:

OLD (lines 226-241):
```python
# ARCH-STAGE-CONTEXT-001 Phase D: Build final Bragg from artifacts or telemetry fallback
# Try to read bragg_full from Stage A artifacts first (populated when Stage A is terminal)
if stage_a_artifacts is not None and hasattr(stage_a_artifacts, 'bragg_full') and stage_a_artifacts.bragg_full is not None:
    bragg_full = stage_a_artifacts.bragg_full
else:
    # Fallback: Build final Bragg using optimized parameters from telemetry
    # (for older binaries that don't populate artifact bragg_full)
    from dbex.refinement.reconstruction import build_final_bragg_from_stage_a_telemetry
    device = torch.device(config.device)
    dtype = config.dtype
    bragg_full = build_final_bragg_from_stage_a_telemetry(
        telemetry_a_enriched, detector, beam, crystal, inputs, hkl_grid,
        hkl_metadata, config, device, dtype,
        stage_a_ctx=stage_a_ctx,
        baseline_crystal=baseline_crystal,
    )
```

NEW:
```python
# ARCH-ENGINE-ARTIFACTS-001 Phase C.1: Build final Bragg from artifact channel
# Stage A unconditionally populates bragg_full in StageAArtifacts (verified by parity tests)
if stage_a_artifacts is None or not hasattr(stage_a_artifacts, 'bragg_full') or stage_a_artifacts.bragg_full is None:
    raise RuntimeError(
        "Stage A did not produce final Bragg array in artifacts. "
        "This is a bug in the Stage A wrapper."
    )
bragg_full = stage_a_artifacts.bragg_full
```

**Change 2: Stage B terminal path (lines 367-409)**

Replace the artifact-or-fallback pattern with artifact-only:

OLD (lines 367-409):
```python
# ARCH-STAGE-CONTEXT-001 Phase D: Build final Bragg from artifacts or telemetry fallback
# Try to read bragg_full from Stage B artifacts first (populated when Stage B is terminal)
if stage_b_artifacts is not None and hasattr(stage_b_artifacts, 'bragg_full') and stage_b_artifacts.bragg_full is not None:
    bragg_full = stage_b_artifacts.bragg_full
else:
    # Fallback: Build final Bragg using optimized parameters from telemetry
    # (for older binaries that don't populate artifact bragg_full)
    from dbex.refinement.reconstruction import build_final_bragg_from_stage_b_telemetry
    # Create a dict version of telemetry_b with shell metadata for the helper
    from dataclasses import asdict
    telemetry_b_dict = asdict(telemetry_b_raw)
    if shell_edges is not None:
        telemetry_b_dict['shell_edges'] = shell_edges
    if shell_indices is not None:
        telemetry_b_dict['shell_indices'] = shell_indices
    if n_shells is not None:
        telemetry_b_dict['n_shells'] = n_shells
    # Add custom attributes back to dict (Phase 8 fix #2)
    if stage_b_mode is not None:
        telemetry_b_dict['stage_b_mode'] = stage_b_mode
    if n_asu_unique is not None:
        telemetry_b_dict['n_asu_unique'] = n_asu_unique
    if optimizer_type is not None:
        telemetry_b_dict['optimizer_type'] = optimizer_type
    if asu_modifier_stats is not None:
        telemetry_b_dict['asu_modifier_stats'] = asu_modifier_stats

    bragg_full = build_final_bragg_from_stage_b_telemetry(
        telemetry_a=telemetry_a_raw,
        telemetry_b=telemetry_b_dict,
        detector=detector,
        beam=beam,
        crystal=crystal,
        baseline_crystal=baseline_crystal,
        inputs=inputs,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        config=config,
        device=final_device,  # Use CPU device if CPU fallback is active
        dtype=dtype,
        use_stage_b_cpu_fallback=use_stage_b_cpu_fallback,
        stage_a_ctx=stage_b_eval_stage_a_ctx,  # Use CPU-cloned context when fallback active
    )
```

NEW:
```python
# ARCH-ENGINE-ARTIFACTS-001 Phase C.1: Build final Bragg from artifact channel
# Stage B unconditionally populates bragg_full in StageBartifacts (verified by parity tests)
if stage_b_artifacts is None or not hasattr(stage_b_artifacts, 'bragg_full') or stage_b_artifacts.bragg_full is None:
    raise RuntimeError(
        "Stage B did not produce final Bragg array in artifacts. "
        "This is a bug in the Stage B wrapper."
    )
bragg_full = stage_b_artifacts.bragg_full
```

### Validate

Run all mapped tests to ensure no regressions:

```bash
# Parity tests (prove artifact channel correctness)
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=metadata \
DBEX_SMOKE_DETECTOR_SIZE=full \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_artifact_parity.py --tb=short

# Stage A smoke (prove Stage A terminal still works)
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=metadata \
DBEX_SMOKE_DETECTOR_SIZE=full \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_baseline_smoke --tb=short

# Stage B smoke (prove Stage B terminal still works)
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=metadata \
DBEX_SMOKE_DETECTOR_SIZE=full \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --tb=short
```

Save test logs to artifacts directory.

### Expected Outcome
- All 4 mapped tests PASS
- Code size reduced by ~50 lines (fallback logic removed)
- No behavioral changes (artifacts already populated, fallbacks were never exercised)
- Simpler, more maintainable code (single artifact-only path)

## How-To Map

**Read the file first**:
```bash
# Understand current structure
cat dbex/nanobrag_refinement.py | grep -n -A 20 "Stage A terminal"
cat dbex/nanobrag_refinement.py | grep -n -A 50 "Stage B terminal"
```

**Make edits**:
Use Edit tool to replace both fallback blocks as specified above.

**Run tests**:
Execute the four pytest commands from Validate section, redirecting output to:
- `plans/active/ARCH-ENGINE-ARTIFACTS-001/reports/2025-12-02T000500Z/pytest_parity.log`
- `plans/active/ARCH-ENGINE-ARTIFACTS-001/reports/2025-12-02T000500Z/pytest_stage_a_smoke.log`
- `plans/active/ARCH-ENGINE-ARTIFACTS-001/reports/2025-12-02T000500Z/pytest_stage_b_smoke.log`

**Verify no imports left behind**:
After edits, check that reconstruction helper imports are removed (they should be in the deleted fallback blocks):
```bash
grep -n "build_final_bragg_from_stage" dbex/nanobrag_refinement.py
# Expected: No matches (or only in comments)
```

## Pitfalls To Avoid

1. **Do NOT remove reconstruction helpers from `dbex/refinement/reconstruction.py`** — They are still used by parity tests and potentially other tools. Only remove the fallback CALLS in nanobrag_refinement.py.

2. **Do NOT change Stage C logic** — It already follows the artifact-only pattern (lines 507-516). Only modify Stage A and Stage B terminal paths.

3. **Do NOT modify artifact population logic** — The Stage wrappers already populate artifacts correctly (proven by parity tests). This is purely removing unused fallback code.

4. **Device/dtype neutrality**: No device/dtype code is being changed (fallbacks are deleted wholesale), so no risk here.

5. **Environment Freeze**: No package installs needed, purely code refactoring.

6. **Initiative type boundary**: This is architecture work (removing dead code, simplifying orchestration). Do NOT change acceptance criteria or specs.

## If Blocked

If any test FAILS:
1. Capture full pytest output with `--tb=long` to artifacts directory
2. Check if the failure is due to missing artifacts or a different root cause
3. If artifacts are missing, record in Attempts History and escalate to Galph (this would indicate a bug in Stage wrappers)
4. Do NOT revert to fallback logic — fix the underlying artifact population bug instead

## Findings Applied

**Relevant findings** from `docs/findings.md`:
- ARCH-ENGINE-003: Telemetry enrichment must stay in active engine path (artifact channel is the active path)
- POLICY-001: Environment Freeze (no package changes, code-only refactor)
- REFINE-FLOW-001: Stage B baseline parity (validated by parity tests)

**Adherence**:
- ARCH-ENGINE-003: ✓ Using artifact channel (not telemetry fallback)
- POLICY-001: ✓ No environment changes
- REFINE-FLOW-001: ✓ Parity tests validate correctness

## Pointers

**Spec references**:
- `docs/spec-db-workflow.md:33` — Engine must own orchestration and expose artifacts
- `docs/spec-db-workflow.md:41` — Stage contract + outputs
- `docs/spec-db-core.md:85-90` — HKL/Bragg tensor contracts

**Architecture docs**:
- `docs/architecture/live_backend.md` — Current backend implementation (will need update in Phase C.3)
- `docs/architecture/dbex/refinement/context.idl.md` — RefinementContext contracts

**Implementation artifacts**:
- `plans/active/ARCH-ENGINE-ARTIFACTS-001/implementation.md` — Phase C checklist
- `plans/active/ARCH-ENGINE-ARTIFACTS-001/reports/2025-12-02T000500Z/planning_notes.md` — This loop's analysis

**Test registry**:
- `docs/TESTING_GUIDE.md:§2` — Authoritative test commands
- `docs/development/TEST_SUITE_INDEX.md` — Test selector status

## Next Up

After Phase C.1 completes successfully:
- Phase C.2: (Optional) Remove unused reconstruction helper imports from nanobrag_refinement.py module-level imports (if any remain)
- Phase C.3: Update documentation to reflect artifact-only orchestration flow

## Doc Sync Plan

No new tests added/renamed this loop, so no test registry updates needed.
Existing parity tests already documented in TEST_SUITE_INDEX.md.

## Mapped Tests Guardrail

All 4 mapped selectors collect successfully (verified during planning loop):
- ✓ `test_artifact_parity.py::test_stage_a_artifact_matches_helper` (collects 1)
- ✓ `test_artifact_parity.py::test_stage_b_artifact_matches_helper_shell_mode` (collects 1)
- ✓ `test_torch_refine_smoke.py::test_stage_a_baseline_smoke` (exists, will verify collection)
- ✓ `test_torch_refine_smoke.py::test_stage_b_shell_modifiers` (exists, will verify collection)

If any selector collects 0 after code changes, DO NOT mark phase complete — debug and fix.
