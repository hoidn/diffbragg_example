# TORCH-REFINE-004 Phase 8 Blocker Fix — Two Bugs in Stage B Wrapper

## Summary
Fix two bugs blocking per-reflection E2E validation: (1) uppercase optimizer type causing shell regression, (2) missing stage_b_mode attribute before to_dict() serialization.

## Mode
TDD

## Focus
TORCH-REFINE-004 (Phase 8 blocker: Stage B wrapper dataclass serialization + optimizer type case)

## Branch
integration

## Mapped Tests
- `tests/dbex/test_stage_b_asu_mapping.py` (5 unit tests, must stay green)
- `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` (shell mode regression, currently FAILS with 'lbfgs' != 'LBFGS')
- `tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke` (per-reflection E2E, currently FAILS with KeyError 'shell_edges')

## Artifacts
`plans/active/TORCH-REFINE-004/reports/2025-11-24T120000Z/`

## Do Now

Ralph's Phase 8 attempt hit TWO distinct bugs. Analysis in `phase_8_blocker_analysis.md` (just written). Both are simple fixes in the Stage B wrapper.

### Bug #1: Optimizer Type Case Mismatch (Shell Regression)

**Location:** `dbex/refinement/stage_b.py:411`

**Current Code:**
```python
optimizer_type = param_values.get('optimizer_type', 'lbfgs').upper()
```

**Problem:** Uppercases to `"LBFGS"` but test expects lowercase `"lbfgs"` (line 1652 in test), and nanobrag_refinement.py stores lowercase (line 5229).

**Fix:** Remove `.upper()`
```python
optimizer_type = param_values.get('optimizer_type', 'lbfgs')  # Keep lowercase
```

### Bug #2: Missing stage_b_mode Before Serialization (Per-Reflection KeyError)

**Location:** `dbex/refinement/stage_b.py:445-490`

**Problem:** Custom attributes (`stage_b_mode`, `n_asu_unique`, `optimizer_type`, `asu_modifier_stats`) are added to `telemetry_output` dict AFTER `to_dict()` call (lines 460-480), but when engine delegates to Stage C preparation code, it receives a dict that went through to_dict() which doesn't include these fields. The Stage C code at nanobrag_refinement.py:4060-4061 tries to extract `stage_b_mode` from dict but it's not there, so `stage_b_mode` stays `None`, falls to `else` branch assuming shell mode, tries to access `shell_edges` key, KeyError!

**Root Cause:** nanobrag_refinement.py adds custom attributes directly to the dataclass object BEFORE any serialization (line 5236: `telemetry_b.stage_b_mode = "per_reflection"`), so they're included when to_dict() is called. The wrapper adds them to the dict AFTER to_dict(), which is too late.

**Fix:** Add custom attributes to `telemetry_b` dataclass object AFTER construction (line 445) but BEFORE `to_dict()` call (line 453).

**Implementation Steps:**

1. Read `phase_8_blocker_analysis.md` for full context
2. Edit `dbex/refinement/stage_b.py`:

   **Fix #1 (line 411):**
   ```python
   # Line 411: Remove .upper()
   optimizer_type = param_values.get('optimizer_type', 'lbfgs')
   ```

   **Fix #2 (after line 445, before line 453):**
   Insert this code block between RefinementTelemetry construction (line 445) and to_dict() call (line 453):

   ```python
   # Add mode-specific custom attributes to dataclass before serialization
   # (matches pattern in nanobrag_refinement.py:5226-5238)
   telemetry_b.stage_b_mode = stage_b_mode

   if stage_b_mode == "per_reflection":
       # Per-reflection mode: add ASU-specific attributes
       with torch.no_grad():
           modifiers_exp = torch.exp(log_modifiers)
           modifiers_clamped = torch.clamp(
               modifiers_exp,
               min=1.0 / self._config.stage_b_max_modifier,
               max=self._config.stage_b_max_modifier
           )

       telemetry_b.n_asu_unique = int(n_asu_unique)
       telemetry_b.optimizer_type = optimizer_type  # Already lowercase from fix #1
       telemetry_b.asu_modifier_stats = {
           "min": float(modifiers_clamped.min().item()),
           "max": float(modifiers_clamped.max().item()),
           "mean": float(modifiers_clamped.mean().item()),
           "std": float(modifiers_clamped.std().item()),
       }
   ```

   **Simplify lines 458-490:** Since attributes are now on dataclass, lines 460-480 (adding to telemetry_output dict) can be simplified:
   - Keep lines 458-461 (mode/stage_type fields) for backward compat
   - Remove redundant attribute additions since to_dict() will serialize them
   - Keep lines 485-488 (shell metadata for engine) — these are NOT custom attributes, they're engine-specific keys

   Actually, safer approach: KEEP the dict additions at lines 460-488 for now (belt-and-suspenders), just add the dataclass attributes FIRST. This ensures both paths work (direct to_dict() and dict-enhanced output).

3. Run validation protocol (4 steps):
   - **Compilation check:** `python -c "from dbex.refinement.stage_b import StageB; print('OK')"`
   - **Phase 6 unit regression:** 5 ASU tests, should stay green (no changes to helpers)
   - **Shell mode regression:** test_stage_b_shell_modifiers, should PASS now (optimizer_type lowercase)
   - **Per-reflection smoke:** test_stage_b_per_reflection_smoke, should get past KeyError (stage_b_mode in dataclass → to_dict() → dict)

4. Decision synthesis (4 paths):
   - **Path A (all PASS):** Both bugs fixed, Phase 8 complete, proceed to Phase 9
   - **Path B (per-reflection new error):** KeyError resolved but new issue (e.g., telemetry assertion, convergence), document and escalate
   - **Path C (shell FAIL):** Optimizer type fix didn't work or broke something, debug
   - **Path D (compilation/unit regression FAIL):** Syntax error or broke helpers, fix and retry

5. Archive artifacts: pytest logs with timestamps
6. Write `summary.md` with Turn Summary
7. Commit: `git add -A && git commit -m "TORCH-REFINE-004 Phase 8: Fix wrapper bugs (optimizer case + stage_b_mode serialization) — tests: <result>"`
8. Push: `git push`

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
  > plans/active/TORCH-REFINE-004/reports/2025-11-24T120000Z/pytest_phase6_regression.log 2>&1
```

### Shell Mode Regression (was FAILING with 'lbfgs' != 'LBFGS')
```bash
cd /home/ollie/Documents/diffbragg_example
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers -vv \
  > plans/active/TORCH-REFINE-004/reports/2025-11-24T120000Z/pytest_shell_regression.log 2>&1
```

### Per-Reflection Smoke (was FAILING with KeyError 'shell_edges')
```bash
cd /home/ollie/Documents/diffbragg_example
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke -vv \
  > plans/active/TORCH-REFINE-004/reports/2025-11-24T120000Z/pytest_per_reflection_smoke.log 2>&1
```

## Pitfalls To Avoid

1. **Serialization order:** Custom attributes MUST be added to dataclass BEFORE to_dict() call (between lines 445-453), not after
2. **Attribute vs dict key:** Use `telemetry_b.stage_b_mode = ...` (object attribute), not `telemetry_b['stage_b_mode'] = ...` (dict key) — dataclass is not a dict
3. **Optimizer case:** Keep lowercase throughout (`"lbfgs"` or `"adam"`), do NOT uppercase
4. **Backward compat:** Keep existing dict additions at lines 460-488 even after adding dataclass attributes (belt-and-suspenders for any code paths that bypass to_dict())
5. **torch.no_grad():** Modifier stats computation must be inside `with torch.no_grad():` context (line 465-473 pattern already exists)
6. **Shell mode unchanged:** Shell mode code path (lines 481-488) should be untouched except removing .upper() from optimizer_type
7. **Environment freeze:** No new packages, only fix existing Stage B wrapper code

## If Blocked

**If per-reflection test still hits KeyError after fix:**
1. Verify `telemetry_b.stage_b_mode` attribute is set BEFORE line 453
2. Add debug print: `print(f"DEBUG: telemetry_b attributes: {dir(telemetry_b)}")` before to_dict()
3. Check if to_dict() includes custom attributes in output: `print(f"DEBUG: to_dict keys: {telemetry_b.to_dict().keys()}")`
4. If to_dict() doesn't include custom attrs, check RefinementTelemetry dataclass definition — does it use `@dataclass` with `asdict()` fallback?
5. Document findings in `dataclass_serialization_investigation.md`

**If shell test still fails with case mismatch:**
1. Verify line 411 doesn't have `.upper()`
2. Check if optimizer_type is modified anywhere else in wrapper (grep for `optimizer_type.*upper`)
3. Check nanobrag_refinement.py line 5183 — does it also uppercase? (No, it uses `.upper()` for display in telemetry.optimizer field, but custom attribute at line 5229 stays lowercase)

**If new error emerges (Path B):**
1. Capture full traceback in `new_error_<type>.log`
2. Classify: telemetry schema / optimizer divergence / assertion failure
3. Write brief analysis: "Path B — <error type>, <one-sentence description>"
4. Return to Galph with all artifacts

## Findings Applied

- **REFINE-001/002/005:** LBFGS warm-start, acceptance gate, halo mandatory
- **SCALE-001/002:** Unscaled structure factors, global post-sim factor
- **PHYSICS-LOSS-001:** Variance-weighted loss function
- **POLICY-001:** Environment Freeze (code-only fixes)
- **ARCH-ENGINE-002:** Lazy torch imports
- **ARCH-REFINE-FLOW-001:** Engine delegation pattern (dataclass → to_dict() → engine → Stage C)
- **spec-db-workflow.md:59:** Per-reflection SHALL be default
- **spec-db-workflow.md:107:** Optimizer flexibility (LBFGS/Adam)

## Pointers

- **Bug analysis:** `plans/active/TORCH-REFINE-004/reports/2025-11-24T120000Z/phase_8_blocker_analysis.md` (comprehensive root cause)
- **Fix locations:** `dbex/refinement/stage_b.py:411` (optimizer case), `dbex/refinement/stage_b.py:446-452` (custom attributes before to_dict())
- **Telemetry pattern reference:** `dbex/nanobrag_refinement.py:5226-5238` (custom attributes on dataclass)
- **Stage C extraction logic:** `dbex/nanobrag_refinement.py:4058-4080` (where KeyError happens)
- **Test expectations:** `tests/dbex/test_torch_refine_smoke.py:1652` (lowercase optimizer), `tests/dbex/test_torch_refine_smoke.py:1640-1657` (per-reflection telemetry fields)
- **Previous attempt:** `plans/active/TORCH-REFINE-004/reports/2025-11-24T115000Z/` (Ralph's first try, both bugs present)
- **Implementation plan:** `plans/active/TORCH-REFINE-004/implementation.md:160-180` (Phase 8 spec)

## Next Up

**If Path A (all tests PASS):**
- Galph assesses Phase 8 ✓ COMPLETE
- Plans Phase 9 (documentation: test registry sync, finding REFINE-006)
- Evaluates TORCH-REFINE-004 initiative closure (4 exit criteria check)

**If Path B (new error):**
- Ralph captures error signature + full traceback
- Galph triages: bug vs spec gap vs env issue
- Max 2 retry cycles before sub-initiative escalation

**If Path C/D (fix didn't work):**
- Ralph debugs specific failure (syntax/logic/test)
- Max 1 retry cycle before escalating to Galph
