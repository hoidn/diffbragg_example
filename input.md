# TORCH-REFINE-004 Phase 8 Blocker Fix — Stage B Wrapper Mode Isolation

## Summary
Fix KeyError 'shell_indices' in Stage B wrapper by adding mode-aware param extraction.

## Mode
TDD

## Focus
TORCH-REFINE-004 (Phase 8 blocker: Stage B wrapper must extract mode-specific keys from param_values dict)

## Branch
integration

## Mapped Tests
- `tests/dbex/test_stage_b_asu_mapping.py` (5 unit tests, regression guard)
- `tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke` (E2E per-reflection validation)
- `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` (shell mode regression)

## Artifacts
`plans/active/TORCH-REFINE-004/reports/2025-11-24T115000Z/` (create new timestamp directory)

## Do Now

**Root Cause:** Stage B wrapper (`dbex/refinement/stage_b.py:343`) unconditionally extracts `shell_indices` from `param_values` dict, but per-reflection mode doesn't populate this key — it populates `asu_indices`, `n_asu_unique`, `log_modifiers` instead (per `dbex/nanobrag_refinement.py:2662-2673` mode branching).

**Fix Specification:**
1. **Extract mode from param_values:** Line ~342 should read `stage_b_mode = param_values['stage_b_mode']` (key exists per line 2646)
2. **Mode-aware key extraction:** Lines ~343-360 should branch on `stage_b_mode`:
   - If `"per_reflection"`: extract `asu_indices`, `n_asu_unique`, `log_modifiers` (lines 2664-2666)
   - If `"shell"`: extract `shell_indices`, `shell_edges`, `shell_modifier_raw` (lines 2670-2672)
3. **Update telemetry assembly:** Lines ~350-422 already have mode-aware telemetry at lines ~410-422 in wrapper; verify these lines handle both modes correctly

**Implementation Steps:**
1. Read Ralph's Phase 8 blocker artifacts: `plans/active/TORCH-REFINE-004/reports/2025-11-24T095000Z/pytest_per_reflection_smoke_retry3.log` (KeyError at line 343)
2. Read Phase 7 mode branching implementation: `dbex/nanobrag_refinement.py:2662-2673` (_build_stage_b_params return dict)
3. Read Stage B wrapper current param extraction: `dbex/refinement/stage_b.py:240-425`
4. Implement fix in `dbex/refinement/stage_b.py`:
   - After line 341 (before current line 343 `shell_indices = ...`): insert `stage_b_mode = param_values['stage_b_mode']`
   - Replace lines 343-350 with mode-aware conditional extraction:
```python
# Extract mode-specific parameters
stage_b_mode = param_values['stage_b_mode']

if stage_b_mode == "per_reflection":
    # Per-reflection mode: extract ASU parameters
    asu_indices = param_values['asu_indices']
    log_modifiers = param_values['log_modifiers']
    n_asu_unique = param_values['n_asu_unique']
    shell_indices = None  # Not used in per-reflection mode
    shell_edges = None
else:  # shell mode
    # Shell mode: extract shell parameters
    shell_indices = param_values['shell_indices']
    shell_edges = param_values['shell_edges']
    shell_modifier_raw = param_values['shell_modifier_raw']
    asu_indices = None  # Not used in shell mode
    n_asu_unique = 0
```
   - Review lines ~280-300: check _build_stage_b_lbfgs_closure call — does it need shell_indices explicitly or can it extract from param_values itself?
   - Review lines ~340-422: verify telemetry assembly handles both modes (look for existing `if stage_b_mode == "per_reflection"` branches)
5. Run validation protocol (4 steps):
   - Compilation: `python -c "from dbex.refinement.stage_b import StageB"`
   - Phase 6 unit regression: 5 ASU mapping tests (1.04s baseline per commit 19dd43e)
   - Shell mode regression: test_stage_b_shell_modifiers (13.66s baseline per commit aebdddd)
   - Per-reflection smoke: test_stage_b_per_reflection_smoke (should get past KeyError, may hit new issues)
6. Decision synthesis (4 paths):
   - **Path A (per-reflection smoke PASS):** Blocker resolved, Phase 8 complete, proceed to Phase 9
   - **Path B (per-reflection smoke new error):** KeyError resolved but new issue, document blocker type, escalate to Galph
   - **Path C (shell regression FAIL):** Mode isolation broke shell path, rollback and debug
   - **Path D (compilation error):** Fix syntax, revalidate
7. Archive artifacts: save all pytest logs with descriptive filenames + timestamps
8. Write `summary.md` with Turn Summary per galph_prompt end_of_loop_hygiene template
9. Commit: `git add -A && git commit -m "TORCH-REFINE-004 Phase 8: Fix Stage B wrapper mode isolation (KeyError shell_indices) — tests: <Path A|B|C|D result>"`
10. Push: `git push`

**Decision Tree Criteria:**
- Path A: All 4 validation tests PASS + per-reflection smoke shows n_asu_unique ~34K per Phase 8 assessment
- Path B: Per-reflection test gets past line 343 but FAILs with different error (e.g., telemetry schema, optimizer divergence, etc.)
- Path C: Shell mode regression FAILs (was PASSING at commit aebdddd)
- Path D: Python import/syntax error during compilation check

## How-To Map

### Compilation Check
```bash
python -c "from dbex.refinement.stage_b import StageB; print('StageB import OK')"
```

### Phase 6 Unit Regression (5 tests, <2s)
```bash
cd /home/ollie/Documents/diffbragg_example
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest tests/dbex/test_stage_b_asu_mapping.py -v \
  > plans/active/TORCH-REFINE-004/reports/2025-11-24T115000Z/pytest_phase6_regression.log 2>&1
```

### Shell Mode Regression (was PASSING at commit aebdddd, must not regress)
```bash
cd /home/ollie/Documents/diffbragg_example
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers -vv \
  > plans/active/TORCH-REFINE-004/reports/2025-11-24T115000Z/pytest_shell_regression.log 2>&1
```

### Per-Reflection Smoke (currently FAILs at line 343 KeyError 'shell_indices')
```bash
cd /home/ollie/Documents/diffbragg_example
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke -vv \
  > plans/active/TORCH-REFINE-004/reports/2025-11-24T115000Z/pytest_per_reflection_smoke.log 2>&1
```

## Pitfalls To Avoid

1. **Mode isolation:** Wrapper MUST NOT extract shell-mode keys when `stage_b_mode == "per_reflection"` and vice versa
2. **Helper function compatibility:** `_build_stage_b_lbfgs_closure` (line ~290 in wrapper) may already extract mode-specific keys from param_values internally — check if explicit shell_indices parameter is needed or if it reads from param_values dict
3. **Telemetry assembly:** Wrapper lines ~340-422 likely already have mode-aware telemetry branches (check for existing `if param_values['stage_b_mode'] == "per_reflection"` logic)
4. **Backward compatibility:** Shell mode test must continue to PASS — do not change shell-mode code paths, only add per-reflection branch
5. **Environment freeze:** Use existing cctbx/torch/pytest only; no new package installs
6. **Null safety:** When mode is per-reflection, shell_indices/shell_edges can be None; when mode is shell, asu_indices can be None — ensure downstream code (if any) checks for None before using
7. **ASU indices dtype:** `asu_indices` is `torch.long` (line 2482), not float32

## If Blocked

**If _build_stage_b_lbfgs_closure requires explicit shell_indices parameter:**
1. Grep closure signature: `grep -A30 "^def _build_stage_b_lbfgs_closure" dbex/nanobrag_refinement.py`
2. Document exact signature in `blocker_analysis.md` (save to reports directory)
3. If closure expects shell_indices as parameter (not from param_values), update call at line ~290 to pass mode-specific keys
4. Rerun validation protocol
5. If changes break shell mode, log error and return to Galph

**If per-reflection test FAILs with new error after KeyError fix:**
1. Capture full traceback in `new_error.log`
2. Classify: telemetry schema issue / optimizer divergence / ASU mapping failure / tensor shape mismatch
3. Write brief analysis: "Path B — new error <TYPE>, requires Galph assessment"
4. Return control to Galph with all artifacts

**If wrapper telemetry assembly needs mode-aware updates:**
1. Check lines ~340-422 for existing per-reflection telemetry logic
2. Review nanobrag_refinement.py:5196-5203 for telemetry pattern (custom attributes)
3. Ensure wrapper mirrors this pattern (dynamic attribute assignment)
4. Revalidate

## Findings Applied

- **REFINE-001/002/005:** LBFGS scale warm-start, acceptance gate, halo-padded HKL grid mandatory
- **SCALE-001/002:** Unscaled structure factors, global post-simulation factor
- **PHYSICS-LOSS-001:** Variance-weighted loss function
- **POLICY-001:** Environment Freeze (no pip installs, dbex-only changes)
- **ARCH-ENGINE-002:** Lazy torch imports preserved
- **spec-db-workflow.md:59:** Per-reflection SHALL be default (Phase 8 objective)
- **spec-db-workflow.md:60:** Shell mode fallback permitted
- **spec-db-workflow.md:61:** Tricubic + halo mandatory
- **spec-db-workflow.md:107:** Optimizer flexibility (LBFGS/Adam per parameter count gate)

## Pointers

- **Error traceback:** `plans/active/TORCH-REFINE-004/reports/2025-11-24T095000Z/pytest_per_reflection_smoke_retry3.log:343-346` (KeyError 'shell_indices' at stage_b.py:245 [old line numbering])
- **Phase 7 mode dict keys:** `dbex/nanobrag_refinement.py:2662-2673` (per_reflection vs shell update() calls)
- **Stage B wrapper param extraction:** `dbex/refinement/stage_b.py:240-425` (run() method)
- **Closure function signature:** `dbex/nanobrag_refinement.py:2678-2700` (_build_stage_b_lbfgs_closure)
- **Per-reflection telemetry pattern:** `dbex/nanobrag_refinement.py:5196-5203` (custom attributes: n_asu_unique, optimizer_type, asu_modifier_stats)
- **Phase 8 assessment:** `plans/active/TORCH-REFINE-004/reports/2025-11-24T095000Z/phase_8_assessment.md` (comprehensive planning, Option A minimal fix)
- **Implementation plan Phase 8:** `plans/active/TORCH-REFINE-004/implementation.md:160-180`
- **Fix plan exit criteria:** `docs/fix_plan.md:231-235`

## Next Up

**If Path A (all tests PASS):**
- Galph assesses Phase 8 completion (blocker resolved, per-reflection E2E validated)
- Plans Phase 9 (documentation: test registry sync with pytest --collect-only, REFINE-006 finding for per-reflection/ASU patterns)
- Considers TORCH-REFINE-004 initiative closure if all 4 exit criteria met

**If Path B (new error after KeyError fix):**
- Ralph documents new error type + full traceback
- Galph triages: implementation bug vs spec gap vs environmental issue
- Max 2 retry cycles before escalating to new sub-initiative

**If Path C (shell regression):**
- Ralph bisects mode isolation logic, verifies shell-mode code paths unchanged
- Galph reviews mode branching correctness
