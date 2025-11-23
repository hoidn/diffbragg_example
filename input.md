# Phase C2: Stage B Engine Delegation (ARCH-REFINE-FLOW-001)

## Summary
Implement conditional engine delegation for Stage A→B sequence in run_nanobrag_refinement.

## Mode
none

## Focus
ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase C2: Stage B Engine Delegation)

## Branch
integration

## Mapped tests
- `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` (regression guard, small detector MUST PASS)
- `tests/dbex/test_refinement_engine.py::test_engine_executes_mock_stage` (engine contract validation)

## Artifacts
`plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T073209Z/`

## Do Now

**Objective:** Implement engine delegation for Stage A→B mode in run_nanobrag_refinement, mirroring Phase B2 pattern (commit 2872f26).

**Scope:** When `enable_stage_c=False AND enable_stage_b=True`, delegate to RefinementEngine([StageA(), StageB()]) instead of calling inline helpers. Preserve Stage C inline path temporarily (Phase D will extract Stage C).

**Implementation Steps:**

1. **Review Phase B2 completion evidence** (commit 2872f26, 2025-11-23T050432Z):
   - Read `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T050432Z/summary.md`
   - Read `dbex/nanobrag_refinement.py:2776-2824` (Stage-A-only detection + engine delegation)
   - Understand pattern: stage detection → lazy imports → engine inputs dict → engine.run() → extract telemetry → build Bragg

2. **Add Stage A→B detection logic** (in run_nanobrag_refinement after line 2777):
   ```python
   # Detect Stage A→B mode for conditional engine delegation (Phase C2)
   stage_a_b_mode = (not config.enable_stage_c and config.enable_stage_b)
   ```

3. **Implement engine delegation branch for Stage A→B** (insert after Stage-A-only delegation block, before existing inline Stage A code):
   ```python
   elif stage_a_b_mode:
       # === ENGINE DELEGATION PATH (Phase C2: A→B) ===
       from dbex.refinement.engine import RefinementEngine
       from dbex.refinement.stage_a import StageA
       from dbex.refinement.stage_b import StageB

       # Build inputs dict per StageA/StageB.run() contract
       engine_inputs = {
           'refinement_inputs': inputs,
           'detector': detector,
           'beam': beam,
           'crystal': crystal,
           'hkl_grid': hkl_grid,
           'hkl_metadata': hkl_metadata,
           'baseline_crystal': baseline_crystal,
           'baseline_detector': baseline_detector,
       }

       # Instantiate RefinementEngine with StageA → StageB sequence
       engine = RefinementEngine(stages=[StageA(), StageB()], config=config)

       # Execute engine and get telemetry dict (keyed by stage.name = "stage_a", "stage_b")
       telemetry_dict = engine.run(engine_inputs)

       # Extract Stage B telemetry (keyed by "stage_b" per StageB.name property)
       telemetry_b_raw = telemetry_dict["stage_b"]

       # Build final Bragg array using Stage B optimized shell modifiers
       device = torch.device(config.device)
       dtype = config.dtype

       # Extract Stage B shell modifiers from telemetry
       shell_modifier_params = {}
       for key in telemetry_b_raw['param_deltas']:
           if key.startswith('shell_'):
               shell_modifier_params[key] = telemetry_b_raw['param_deltas'][key]['final']

       # Rebuild modified HKL grid from shell modifiers
       # (Extract shell edges and indices from telemetry, apply modifiers to hkl_grid)
       # NOTE: This requires adding 'shell_edges' and 'shell_indices' to StageB telemetry output
       #       OR recomputing them here (parallel to Stage B inline code lines 3230-3231)

       # For now, reuse _build_final_bragg_from_stage_b_telemetry helper (to be extracted)
       bragg_full = _build_final_bragg_from_stage_b_telemetry(
           telemetry_a=telemetry_dict["stage_a"],
           telemetry_b=telemetry_b_raw,
           detector=detector,
           beam=beam,
           crystal=crystal,
           inputs=inputs,
           hkl_grid=hkl_grid,
           hkl_metadata=hkl_metadata,
           config=config,
           device=device,
           dtype=dtype
       )

       # Repackage telemetry with backward-compatible keys ("A", "B")
       telemetry_a_raw = telemetry_dict["stage_a"]
       telemetry_b = RefinementTelemetry(**{k: v for k, v in telemetry_b_raw.items() if k not in ['stage_type', 'mode']})
       telemetry_a = RefinementTelemetry(**{k: v for k, v in telemetry_a_raw.items() if k not in ['stage_type', 'mode']})

       return bragg_full, {"A": telemetry_a, "B": telemetry_b}
   ```

4. **Extract `_build_final_bragg_from_stage_b_telemetry` helper** (lines 3309-3374):
   - Signature: `_build_final_bragg_from_stage_b_telemetry(telemetry_a, telemetry_b, detector, beam, crystal, inputs, hkl_grid, hkl_metadata, config, device, dtype) -> np.ndarray`
   - Mirrors `_build_final_bragg_from_stage_a_telemetry` (lines 1890-2084)
   - Input: Stage A + Stage B telemetry dicts
   - Output: Final Bragg array with Stage B shell modifiers applied
   - Extract frozen Stage A params from telemetry_a, shell modifiers from telemetry_b
   - Rebuild modified HKL grid, generate Bragg panels with warm cache if enabled

5. **Add shell metadata to StageB telemetry output** (dbex/refinement/stage_b.py):
   - After line 401 (before return telemetry_output), add:
     ```python
     telemetry_output["shell_edges"] = shell_edges.cpu().tolist()
     telemetry_output["shell_indices"] = shell_indices.cpu().tolist()
     telemetry_output["n_shells"] = config.stage_b_n_shells
     ```
   - Required for engine path to rebuild modified HKL grid without recomputing shell binning

6. **Wrap existing inline Stage A code in else block** (pure indentation change):
   - Lines 2825-3152 (existing Stage A inline code) → indent by 4 spaces
   - Preserve all existing logic (params, optimizer, LBFGS closure, telemetry assembly)
   - No functional changes to inline path

7. **Compilation check**:
   ```bash
   python -c "from dbex.nanobrag_refinement import run_nanobrag_refinement; print('OK')" 2>&1 | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T073209Z/compilation_check.log
   ```

8. **Regression guard** (MANDATORY):
   ```bash
   KMP_DUPLICATE_LIB_OK=TRUE pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers -xvs 2>&1 | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T073209Z/pytest_stage_b_shell_modifiers.log
   ```
   MUST PASS (engine delegation path active for Stage A→B mode).

9. **Engine contract test**:
   ```bash
   pytest tests/dbex/test_refinement_engine.py::test_engine_executes_mock_stage -xvs 2>&1 | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T073209Z/pytest_engine_contract.log
   ```

10. **Update implementation.md** (mark Phase C2 complete if tests PASS):
    - Update `plans/active/ARCH-REFINE-FLOW-001/implementation.md` Phase C section with Phase C2 completion timestamp + commit hash
    - Note: Stage A→B engine delegation path validated via test_stage_b_shell_modifiers regression guard

11. **Write summary.md** (turn summary per galph_prompt end_of_loop_hygiene):
    - Create `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T073209Z/summary.md`
    - 3-5 sentences: what shipped, main problem + resolution, next step
    - Append same block to existing summary.md (prepend above earlier notes)

12. **Commit**:
    ```bash
    git add -A
    git commit -m "$(cat <<'EOF'
    RALPH: ARCH-REFINE-FLOW-001 Phase C2 — Stage B engine delegation

    Implemented conditional engine delegation for Stage A→B mode (enable_stage_c=False AND enable_stage_b=True).
    Extracted _build_final_bragg_from_stage_b_telemetry helper (~65 lines).
    Added shell metadata (shell_edges, shell_indices, n_shells) to StageB telemetry output for engine path.
    Wrapped existing inline Stage A code in else block (pure indentation, no logic changes).

    Tests:
    - test_stage_b_shell_modifiers: PASSED (engine delegation path active)
    - test_engine_executes_mock_stage: PASSED (engine contract validated)

    🤖 Generated with [Claude Code](https://claude.com/claude-code)

    Co-Authored-By: Claude <noreply@anthropic.com>
    EOF
    )"
    git push
    ```

## How-To Map

### Environment
```bash
export KMP_DUPLICATE_LIB_OK=TRUE
cd /home/ollie/Documents/diffbragg_example
```

### Phase B2 Review
```bash
# Read Phase B2 completion evidence
cat plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T050432Z/summary.md

# Review Stage-A-only delegation pattern (commit 2872f26)
git show 2872f26:dbex/nanobrag_refinement.py | sed -n '2776,2824p'
```

### Implementation Sequence
1. Add stage_a_b_mode detection (after line 2777)
2. Extract _build_final_bragg_from_stage_b_telemetry helper (before run_nanobrag_refinement)
3. Implement engine delegation elif branch (after stage_a_only_mode block)
4. Add shell metadata to StageB telemetry (dbex/refinement/stage_b.py:401)
5. Indent existing inline Stage A code (lines 2825-3152) inside else block

### Validation Commands
```bash
# Compilation check
python -c "from dbex.nanobrag_refinement import run_nanobrag_refinement; print('OK')" 2>&1 | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T073209Z/compilation_check.log

# Regression guard (MANDATORY — MUST PASS)
KMP_DUPLICATE_LIB_OK=TRUE pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers -xvs 2>&1 | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T073209Z/pytest_stage_b_shell_modifiers.log

# Engine contract test
pytest tests/dbex/test_refinement_engine.py::test_engine_executes_mock_stage -xvs 2>&1 | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T073209Z/pytest_engine_contract.log
```

### Telemetry Comparison (Optional Debug)
```python
# T0 probe: Compare Stage B telemetry structure between inline and engine paths
# (Embed in summary.md, no separate file)
import json
with open('plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T230000Z/pytest_stage_b_shell_modifiers.log') as f:
    baseline_log = f.read()
# Extract telemetry JSON from test output (if available)
# Compare keys/values with new engine path output
```

## Pitfalls To Avoid

1. **Device/dtype neutrality**: Use `config.device` and `config.dtype` consistently; no hardcoded `"cuda"` or `torch.float32`.
2. **Protected Assets**: Do NOT modify `tests/` or `docs/` during implementation (only after tests pass).
3. **Lazy imports**: Import `RefinementEngine`, `StageA`, `StageB` inside the delegation branch to avoid circular imports at module load time.
4. **Telemetry repackaging**: Engine returns dict keyed by `stage.name` ("stage_a", "stage_b"), but run_nanobrag_refinement must return dict keyed by uppercase ("A", "B") for backward compatibility.
5. **Shell metadata**: StageB telemetry MUST include `shell_edges`, `shell_indices`, `n_shells` for engine path to rebuild modified HKL grid.
6. **Indentation hygiene**: When wrapping inline code in else block, verify all lines are consistently indented (use spaces, not tabs; follow existing style).
7. **Helper extraction scope**: `_build_final_bragg_from_stage_b_telemetry` should mirror `_build_final_bragg_from_stage_a_telemetry` pattern (lines 1890-2084). Extract ONLY the Bragg regeneration logic (lines 3309-3374), NOT the shell modifier application or telemetry assembly (those stay in StageB.run()).
8. **Regression guard requirement**: test_stage_b_shell_modifiers MUST PASS before marking Phase C2 complete. If it fails, debug the engine delegation path (telemetry keys, shell modifier application, HKL grid rebuild).
9. **Environment Freeze**: Do not install/upgrade packages. If an import fails, mark blocked in galph_memory.md with the error signature.
10. **Right-sized scriptization**: T0 probes (≤120 chars, stdlib-only) embed in summary.md. T1 one-offs (≤25 lines, first use) embed in summary.md. T2 reused scripts (referenced in Do Now, run >1x, or decision-carrying) live at `plans/active/<initiative>/bin/<slug>.py` or `scripts/tools/<area>/<slug>.py`.

## If Blocked

**Scenario 1: Helper extraction breaks Stage B inline path**
- Revert helper extraction, verify inline path still works via test_stage_b_shell_modifiers
- Re-extract with narrower scope (ONLY Bragg regeneration, no telemetry assembly)
- Log error signature + revert hash in `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T073209Z/blocker.md`

**Scenario 2: Engine delegation path fails regression guard**
- Run inline path test first to confirm baseline still passes: `KMP_DUPLICATE_LIB_OK=TRUE pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers -xvs -k "not engine"`
- Compare telemetry dicts (inline vs engine) via T0 probe
- Check shell metadata presence in StageB telemetry output (shell_edges, shell_indices, n_shells)
- Verify telemetry repackaging (stage.name → uppercase keys)
- Log failure mode + telemetry diff in blocker.md

**Scenario 3: Circular import at module load time**
- Move imports inside delegation branch (lazy imports)
- Verify compilation check passes after moving imports
- Log import error + traceback in blocker.md

**Fallback**: If blocked after 3 attempts, write comprehensive blocker.md with error signatures, attempted fixes, and proposed escalation path. Update galph_memory.md with `next_action=switch_focus` and mark ARCH-REFINE-FLOW-001 Phase C2 blocked in docs/fix_plan.md Attempts History.

## Findings Applied (Mandatory)

**Relevant Finding IDs from docs/findings.md:**
- **REFINE-005** (Stage B halo/interpolation): StageB telemetry includes shell_edges/shell_indices for engine path to rebuild modified HKL grid. Adherence: Shell metadata added to telemetry output.
- **REFINE-008** (Stage B improvement gates): Engine delegation path preserves improvement gate logic (handled by _run_stage_b_lbfgs helper called by StageB.run()). Adherence: No gate changes, helpers unchanged.
- **POLICY-001** (Environment Freeze): No package installs/upgrades. Adherence: Implementation uses only existing dependencies.
- **CONFIG-001** (Detector metadata contracts): Detector/beam/crystal configs flow through RefinementEngine inputs dict. Adherence: Engine inputs dict includes all required metadata.
- **SCALE-001/002/003/007** (Scale handling): Stage A frozen log_scale flows through StageB telemetry. Adherence: StageB extracts log_scale_final from stage_a_telemetry['param_deltas']['log_scale']['final'].

No other findings relevant to Phase C2 engine delegation.

## Pointers

### Spec/Arch/Testing Docs
- **Spec DB Workflow §7** (Refinement Protocol Architecture): `docs/spec-db-workflow.md:31-34` (Stage contract)
- **ARCH-REFINE-FLOW-001 Plan**: `plans/active/ARCH-REFINE-FLOW-001/implementation.md:179-212` (Phase C checklist)
- **Testing Guide §2**: `docs/TESTING_GUIDE.md` (selector registry)
- **Test Suite Index**: `docs/development/TEST_SUITE_INDEX.md` (active selectors)

### Fix Plan Entries
- **ARCH-REFINE-FLOW-001**: `docs/fix_plan.md:181-211` (current status, dependencies, exit criteria)
- **Phase B2 Completion**: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T050432Z/summary.md` (Stage-A-only delegation pattern)
- **Phase C1b Completion**: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T230000Z/summary.md` (StageB wrapper implementation)

### Code Anchors
- **Stage-A-only delegation**: `dbex/nanobrag_refinement.py:2776-2824`
- **Stage B inline code**: `dbex/nanobrag_refinement.py:3153-3453`
- **StageB class**: `dbex/refinement/stage_b.py:22-405`
- **RefinementEngine**: `dbex/refinement/engine.py`
- **_build_final_bragg_from_stage_a_telemetry**: `dbex/nanobrag_refinement.py:1890-2084`

## Next Up (optional)

If Phase C2 completes early and all tests pass:
- **Phase C3**: Run full Stage B smoke suite (small + full detector) and capture telemetry JSON verifying engine path maintains numeric parity with inline path.
- **Phase C4**: Execute DB-AT-024 (mapping consistency) in collect-only + pytest modes to validate Stage B engine path doesn't break gradient flows.

Do NOT proceed to Phase C3 without explicit Galph approval. Mark Phase C2 complete and commit artifacts.

## Doc Sync Plan (Conditional)

NOT REQUIRED for Phase C2 (no new tests authored, only refactoring existing code path). If tests were added/renamed, would:
1. Run `pytest --collect-only tests/dbex/test_torch_refine_smoke.py tests/dbex/test_refinement_engine.py` and archive logs
2. Update `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` AFTER tests pass
3. Note selector changes in Phase C2 completion summary

## Mapped Tests Guardrail

Both mapped selectors collect >0 tests (verified via `pytest --collect-only`):
- `test_stage_b_shell_modifiers`: 1 test (Active)
- `test_engine_executes_mock_stage`: 1 test (Active)

No downgrade required. Both selectors MUST PASS for Phase C2 completion.
