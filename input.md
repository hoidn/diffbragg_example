# Input for Ralph — ARCH-TELEMETRY-001 Phase C.4

**Summary**: Remove legacy telemetry key mapping from RefinementEngine and update test assertions to use internal stage names.

**Mode**: Parity

**InitiativeType**: architecture

**Focus**: ARCH-TELEMETRY-001 — Telemetry Observer Refactor

**Branch**: integration

**Mapped tests**:
- `tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload`
- `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers`
- `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip`
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_engine_delegation_telemetry`

**Artifacts**: `plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T022931Z/`

---

## Do Now

### Background
Phase C.3.1 complete (writer consumes StageResult dataclasses). Phase C.3.2 complete (Stage B/C no longer call `to_legacy_dict()`). This loop completes Phase C.4: remove the legacy key mapping from `RefinementEngine.run()` that translates internal stage names ("stage_a", "stage_b", "stage_c") to legacy labels ("A", "B", "C") for backward compatibility with old test assertions.

### Implement

**Task 1: Remove legacy key mapping in RefinementEngine.run()**

1. **File**: `dbex/refinement/engine.py`

2. **Edit** (lines 201-215):
   - **DELETE** entire comment block + legacy_telemetry_dict construction loop (lines 201-213)
   - **REPLACE** line 215 (`return legacy_telemetry_dict`) with `return self._telemetry`

   **Before** (lines 201-215):
   ```python
   # ARCH-REFACTOR-001 Phase D.3: Map stage names to legacy labels for backward compatibility
   # Tests and downstream code expect "A"/"B"/"C" keys (not "stage_a"/"stage_b"/"stage_c")
   legacy_telemetry_dict = {}
   for stage_name, telem in self._telemetry.items():
       if stage_name == "stage_a":
           legacy_telemetry_dict["A"] = telem
       elif stage_name == "stage_b":
           legacy_telemetry_dict["B"] = telem
       elif stage_name == "stage_c":
           legacy_telemetry_dict["C"] = telem
       else:
           # Unknown stage name - pass through unchanged
           legacy_telemetry_dict[stage_name] = telem

   return legacy_telemetry_dict
   ```

   **After**:
   ```python
   # ARCH-TELEMETRY-001 Phase C.4: Return internal telemetry dict directly
   # Tests updated to use internal stage names ("stage_a", "stage_b", "stage_c")
   return self._telemetry
   ```

---

**Task 2: Update test assertions to use internal stage names**

3. **File**: `tests/dbex/test_torch_refine_smoke.py`

   **Use Edit tool with `replace_all=True` for systematic batch replacements**:

   a) Replace legacy key references with internal stage names:
      - `old_string`: `telemetry_dict["A"]`
      - `new_string`: `telemetry_dict["stage_a"]`
      - `replace_all`: True

   b) Replace legacy key existence checks:
      - `old_string`: `"A" in telemetry_dict`
      - `new_string`: `"stage_a" in telemetry_dict`
      - `replace_all`: True

   c) Repeat for Stage B:
      - `old_string`: `telemetry_dict["B"]`
      - `new_string`: `telemetry_dict["stage_b"]`
      - `replace_all`: True

   d) Repeat for Stage B existence checks:
      - `old_string`: `"B" in telemetry_dict`
      - `new_string`: `"stage_b" in telemetry_dict`
      - `replace_all`: True

   e) Repeat for Stage C:
      - `old_string`: `telemetry_dict["C"]`
      - `new_string`: `telemetry_dict["stage_c"]`
      - `replace_all`: True

   f) Repeat for Stage C existence checks:
      - `old_string`: `"C" in telemetry_dict`
      - `new_string`: `"stage_c" in telemetry_dict`
      - `replace_all`: True

4. **File**: `tests/dbex/test_stage_a_smoke_parity.py`

   **Check fixture for legacy key usage** (likely around lines 150-200):
   - If `mapping_context_fixture` or helper functions use `telemetry_dict["A"]`, apply same replacements
   - Use Edit tool with `replace_all=True` for each pattern

---

**Task 3: Validation**

5. **Run all 5 mapped test selectors** with canonical environment flags:

   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   DBEX_SMOKE_SIGMA_SOURCE=metadata \
   DBEX_SMOKE_DETECTOR_SIZE=small \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload \
     tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
     tests/dbex/test_torch_refine_smoke.py::test_stage_a_engine_delegation_telemetry \
     tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
     tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip \
     > plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T022931Z/pytest_phase_c4.log 2>&1
   ```

6. **Capture results**:
   - Save pytest log to artifacts directory (already done via redirect above)
   - Verify all 5 tests PASSED
   - Report any failures with error signatures

---

## How-To Map

| Step | Command / Action |
|------|------------------|
| 1. Remove engine mapping | Edit `dbex/refinement/engine.py` lines 201-215 per Task 1 |
| 2a. Update test_torch_refine_smoke.py | Edit with `replace_all=True` for 6 patterns per Task 2.3 |
| 2b. Update test_stage_a_smoke_parity.py | Edit with `replace_all=True` if legacy keys found per Task 2.4 |
| 3. Run validation suite | Execute bash command from Task 3 (pytest with 5 selectors, redirect to log) |
| 4. Verify results | Check pytest log for all PASSED; report failures if any |

---

## Pitfalls To Avoid

1. **DO NOT** modify `dbex/refinement/interfaces.py` or `telemetry_collectors.py` — this loop only touches engine.py and test files
2. **DO NOT** change telemetry field names or schema — only update dict key strings from legacy labels to internal stage names
3. **DO NOT** skip `replace_all=True` — use batch replacement to ensure all assertions are updated consistently
4. **DO** verify test file changes with Read tool after edits to confirm all legacy keys replaced
5. **DO** preserve canonical environment flags when running pytest (DBEX_SMOKE_SIGMA_SOURCE=metadata, DBEX_SMOKE_DETECTOR_SIZE=small, etc.)
6. **DO** use small detector size for smoke tests to stay within runtime budget (already in command above)

---

## If Blocked

If tests fail after key name updates:
1. Capture full pytest log output with `-s` flag to see assertion error messages
2. Check if any test files outside `test_torch_refine_smoke.py` and `test_stage_a_smoke_parity.py` use legacy keys
3. Search for remaining legacy key references: `rg 'telemetry_dict\["[ABC]"\]' tests/dbex`
4. Update Attempts History in `docs/fix_plan.md` with failure signature and blocked status
5. Report findings to Galph in summary

---

## Findings Applied (Mandatory)

- **ARCH-STAGE-CTX-001**: Typed contexts own telemetry; RefinementEngine returns internal telemetry dict directly
- **ARCH-STAGE-CTX-002**: Ban telemetry dict mutation; stages emit observer callbacks into typed collectors
- **ARCH-TELEMETRY-001 Phase C.3.1**: Writer consumes StageResult dataclasses (telemetry/perf counters accessed via typed fields)
- **ARCH-TELEMETRY-001 Phase C.3.2**: Stage B/C no longer call `to_legacy_dict()`; direct field access proven green

---

## Pointers

- **Spec**: docs/spec-db-workflow.md §§Calibration & Pipeline telemetry (no schema changes required)
- **Architecture**: plans/active/ARCH-TELEMETRY-001/implementation.md (Phase C.4 checklist, line ~90)
- **Fix Plan**: docs/fix_plan.md row [ARCH-TELEMETRY-001] (Attempts History, line ~169)
- **Planning**: plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T022931Z/planning_notes.md (this loop)
- **Testing Guide**: docs/TESTING_GUIDE.md §2 (canonical env flags for smoke tests)
- **Prior Artifacts**: plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T021140Z/ (Phase C.3.2 completion, writer migration)

---

## Next Up (optional)

If all tests PASS and you finish early:
- Mark ARCH-TELEMETRY-001 Phase C.4 complete in implementation plan
- No additional work planned; initiative ready for supervisor sign-off after this loop
