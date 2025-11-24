# Ralph Input: TORCH-REFINE-004 Phase 7 Blocker Fix (Engine Telemetry Schema)

**Summary:** Fix telemetry_version schema mismatch between dbex/refinement/stage.py and dbex/nanobrag_refinement.py to unblock Phase 7 integration.

**Mode:** TDD (fix blocking test failure)

**Focus:** TORCH-REFINE-004 — Stage B Per-Reflection Mode Migration (Phase 7 Blocker Resolution)

**Branch:** integration

**Mapped tests:**
- `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` (regression guard, currently FAILS with TypeError)

**Artifacts:** `plans/active/TORCH-REFINE-004/reports/2025-11-24T091417Z/`
- `engine_schema_fix_analysis.md` (comprehensive root cause analysis with 12 sections)
- `decision.md` (4-path decision synthesis after fix validation)
- `summary.md` (Turn Summary for this loop)

---

## Do Now

**Context:** Phase 6 ASU mapping implementation (commit 19dd43e) completed successfully with all 5 unit tests PASSED. However, regression guard test_stage_b_shell_modifiers FAILED with `TypeError: __init__() got an unexpected keyword argument 'telemetry_version'` at dbex/refinement/engine.py:144.

**Root Cause (99.9% confidence):** Schema divergence between two RefinementTelemetry dataclasses:
- `dbex/nanobrag_refinement.py::RefinementTelemetry` has `telemetry_version: str = "1.0"` (line 665)
- `dbex/refinement/stage.py::RefinementTelemetry` MISSING `telemetry_version` field
- Stage B wrapper uses dbex.nanobrag_refinement.RefinementTelemetry, returns dict via asdict() which includes telemetry_version
- Engine tries to construct dbex/refinement/stage.py::RefinementTelemetry(**dict) which rejects the field

**NOT a TORCH-REFINE-004 regression** — Phase 6 code didn't touch schemas. This is an ARCH-REFACTOR-001 Phase B incomplete migration gap discovered by first Stage B engine delegation test.

### Implementation Steps (5-step protocol)

1. **Read Root Cause Analysis**
   - File: `plans/active/TORCH-REFINE-004/reports/2025-11-24T091417Z/engine_schema_fix_analysis.md`
   - Focus on "Fix Specification" section (exact code addition, placement, rationale)

2. **Add telemetry_version Field**
   - File: `dbex/refinement/stage.py`
   - Location: After line 161 (after `stage_modes` field, before `to_dict()` method definition)
   - Code to add:
     ```python
         # ARCH-REFACTOR-001 Phase B: Schema versioning for future compatibility
         telemetry_version: str = "1.0"
     ```
   - **Exact placement:** Between `stage_modes: Optional[Dict[str, str]] = None` and `def to_dict(self) -> Dict[str, Any]:`
   - **Why no to_dict() changes needed:** Method already uses asdict() fallback which automatically includes all dataclass fields

3. **Validation (3 checks)**

   A. **Compilation Check:**
   ```bash
   python -c "from dbex.refinement.stage import RefinementTelemetry; print('telemetry_version' in RefinementTelemetry.__dataclass_fields__)"
   ```
   Expected output: `True`

   B. **Regression Guard:**
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers
   ```
   Expected: PASS (no TypeError, Stage B telemetry includes telemetry_version)

   C. **Schema Parity Verification:**
   ```bash
   python -c "
   from dbex.nanobrag_refinement import RefinementTelemetry as Old
   from dbex.refinement.stage import RefinementTelemetry as New
   old_fields = set(Old.__dataclass_fields__.keys())
   new_fields = set(New.__dataclass_fields__.keys())
   missing = old_fields - new_fields
   extra = new_fields - old_fields
   print(f'Missing from new: {missing}')
   print(f'Extra in new: {extra}')
   "
   ```
   Expected: `Missing from new: set()` (no missing core fields; extra fields OK - engine delegation extensions)

4. **Decision Synthesis**
   - Write `plans/active/TORCH-REFINE-004/reports/2025-11-24T091417Z/decision.md`
   - Document which path occurred (A/B/C/D from analysis.md)
   - If Path A (PASS): Include telemetry_version value from test output
   - If not Path A: Document exact error signature and next diagnostic step

5. **Artifacts & Commit**
   - Write `plans/active/TORCH-REFINE-004/reports/2025-11-24T091417Z/summary.md` with Turn Summary (see template below)
   - Archive pytest log to artifacts directory
   - Commit message: `TORCH-REFINE-004: Fix engine telemetry_version schema (unblock Phase 7) — tests: test_stage_b_shell_modifiers`
   - **Do NOT update fix_plan.md or galph_memory.md** (supervisor will handle housekeeping)

---

## How-To Map

### Environment Setup
```bash
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
export DBEX_SMOKE_SIGMA_SOURCE=cli_override
export DBEX_SMOKE_DETECTOR_SIZE=small
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1
```

### Code Addition
- **File:** `dbex/refinement/stage.py`
- **Line:** After 161 (after `stage_modes: Optional[Dict[str, str]] = None`)
- **Exact text:**
  ```python
      # ARCH-REFACTOR-001 Phase B: Schema versioning for future compatibility
      telemetry_version: str = "1.0"

  ```
  (Note: Blank line after field before `def to_dict()` method)

### Validation Commands
```bash
# Compilation check
python -c "from dbex.refinement.stage import RefinementTelemetry; print('telemetry_version' in RefinementTelemetry.__dataclass_fields__)"

# Regression test (save log to artifacts)
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers > plans/active/TORCH-REFINE-004/reports/2025-11-24T091417Z/pytest_schema_fix.log 2>&1

# Schema parity check (if regression PASSES)
python -c "from dbex.nanobrag_refinement import RefinementTelemetry as Old; from dbex.refinement.stage import RefinementTelemetry as New; old=set(Old.__dataclass_fields__.keys()); new=set(New.__dataclass_fields__.keys()); print('Missing:', old-new); print('Extra:', new-old)" > plans/active/TORCH-REFINE-004/reports/2025-11-24T091417Z/schema_parity.log 2>&1
```

### Commit Pattern
```bash
git add dbex/refinement/stage.py plans/active/TORCH-REFINE-004/reports/2025-11-24T091417Z/
git commit -m "TORCH-REFINE-004: Fix engine telemetry_version schema (unblock Phase 7) — tests: test_stage_b_shell_modifiers"
git push
```

---

## Pitfalls To Avoid

1. **Placement:** Add field AFTER `stage_modes` (line 161), NOT before or after other field groups
2. **Indentation:** Match existing fields (4 spaces, NOT tabs)
3. **Default Value:** Use `"1.0"` string literal (NOT `1.0` numeric, NOT variable)
4. **Comment:** Include ARCH-REFACTOR-001 Phase B reference (documents provenance)
5. **to_dict() Changes:** Do NOT modify to_dict() method (asdict() handles new field automatically)
6. **Test Execution:** Use exact env vars from How-To Map (NANOBRAGG_DISABLE_COMPILE=1 required for CPU-only validation)
7. **Schema Parity:** If parity check reveals MORE missing fields, add ALL of them (document in decision.md)
8. **Commit Scope:** Only commit schema fix + artifacts (NO fix_plan.md, NO galph_memory.md)
9. **Decision Paths:** If NOT Path A (test failure persists), do NOT commit code changes; instead commit decision.md blocker report and return to Galph
10. **Environment Freeze:** Do not install packages or modify CUDA/torch; if import fails, record error and return to Galph

---

## If Blocked

1. **Compilation fails:** Check indentation (4 spaces), placement (after line 161), syntax (string default `"1.0"`), commit partial progress (comment only), return to Galph with error signature
2. **Test fails (different error):** Document new error signature in decision.md, classify as schema vs implementation issue, commit decision.md blocker report, return to Galph
3. **Schema parity reveals many missing fields:** Add ALL missing fields in single commit, document which fields added, update decision.md with full reconciliation, rerun ALL validation steps before committing
4. **Git push rejected:** Run `timeout 30 git pull --rebase`, resolve conflicts (keep telemetry_version addition), retry push

---

## Findings Applied (Mandatory)

**From docs/findings.md:**

- **POLICY-001 (Environment Freeze):** ✓ Code-only change, no package installs, no CUDA modifications
- **ARCH-REFACTOR-001 Phase B (Schema Versioning):** ✓ telemetry_version field pattern, default value "1.0"
- **ARCH-REFINE-FLOW-001 Phase A4 (Stage Identification):** ✓ stage_type/mode fields already in schema
- **ARCH-REFINE-FLOW-001 Phase E (Engine Delegation):** ✓ engine_protocol/stage_modes fields already in schema

**Adherence notes:**
- No findings violated by 1-line schema field addition
- Fix completes ARCH-REFACTOR-001 Phase B schema parity gap
- Validates ARCH-REFINE-FLOW-001 engine delegation contract (Stage B wrapper can return dicts matching engine dataclass)

---

## Pointers

### Spec & Architecture
- **docs/spec-db-workflow.md:33** — Engine Contract: telemetry aggregation per stage
- **docs/architecture.md** — RefinementTelemetry schema evolution (ARCH-REFACTOR-001 Phase B)

### Code References
- **dbex/nanobrag_refinement.py:665** — Source dataclass with telemetry_version field
- **dbex/refinement/stage.py:88-162** — Target dataclass MISSING telemetry_version
- **dbex/refinement/engine.py:144** — Error location (RefinementTelemetry(**dict) construction)
- **dbex/refinement/stage_b.py:94** — Stage B imports old RefinementTelemetry (includes telemetry_version)
- **dbex/refinement/stage_b.py:414** — Stage B returns asdict(telemetry_b) with telemetry_version key

### Testing & Validation
- **docs/TESTING_GUIDE.md §2.2** — Stage B smoke selector environment requirements
- **tests/dbex/test_torch_refine_smoke.py:test_stage_b_shell_modifiers** — Regression guard blocking Phase 7

### Fix Plan
- **docs/fix_plan.md:227-241** — TORCH-REFINE-004 initiative status (currently blocked on this schema issue)
- **plans/active/TORCH-REFINE-004/implementation.md:Phase 6** — Just completed (ASU infrastructure), Phase 7 blocked by schema
- **plans/active/TORCH-REFINE-004/reports/2025-11-24T130000Z/summary.md** — Phase 6 completion report (blocker identified)

---

## Next Up (Optional)

If Phase 7 blocker is resolved (test PASSES) AND you finish early AND Galph hasn't returned yet:

**Option 1:** Begin Phase 7 evidence gathering (DO NOT implement yet, just gather):
- Read `plans/active/TORCH-REFINE-004/implementation.md` Phase 7 scope
- Locate where apply_asu_modifiers should integrate (Stage B optimization closure)
- Draft 1-2 paragraph integration strategy sketch (no code changes)
- Save to `plans/active/TORCH-REFINE-004/reports/2025-11-24T091417Z/phase_7_integration_notes.md`

**Option 2:** Schema parity audit (if you're curious):
- Document ALL field differences between old/new RefinementTelemetry dataclasses
- Save to `plans/active/TORCH-REFINE-004/reports/2025-11-24T091417Z/schema_audit.md`

**Do NOT:**
- Implement Phase 7 code (wait for Galph's planning delegation)
- Update fix_plan.md or galph_memory.md (supervisor housekeeping)
- Create new tests (Phase 7 scope)

---

## Turn Summary Template

For `plans/active/TORCH-REFINE-004/reports/2025-11-24T091417Z/summary.md`:

```markdown
# Engine Telemetry Schema Fix (Phase 7 Blocker Resolution)

**Date:** 2025-11-24T091417Z
**Mode:** TDD (blocking test fix)
**Outcome:** [PASS/FAIL - fill after validation]

## Summary
Fixed telemetry_version schema mismatch between dbex/refinement/stage.py (engine dataclass) and dbex/nanobrag_refinement.py (Stage B source dataclass). Added single field to engine RefinementTelemetry dataclass, restoring schema parity and unblocking Phase 7 optimization loop integration.

## Changes
- `dbex/refinement/stage.py` (+2 lines): Added `telemetry_version: str = "1.0"` field after line 161

## Validation Results
- Compilation check: [PASS/FAIL]
- Regression guard (test_stage_b_shell_modifiers): [PASS/FAIL - include runtime]
- Schema parity check: [document missing/extra fields]

## Root Cause
Schema divergence from ARCH-REFACTOR-001 Phase B (added telemetry_version to dbex.nanobrag_refinement) and ARCH-REFINE-FLOW-001 Phase A (created dbex.refinement.stage without field parity). Stage B wrapper uses old dataclass, engine uses new dataclass, mismatch discovered on first Stage B engine delegation test.

## Next Steps
[If PASS]: Phase 7 integration ready (apply_asu_modifiers, dynamic optimizer selection)
[If FAIL]: Document new error signature, escalate to supervisor

## Artifacts
- pytest_schema_fix.log — Regression test output
- schema_parity.log — Field difference audit
- decision.md — Path outcome (A/B/C/D)

---

Last updated: 2025-11-24T091417Z
```

---

## Doc Sync Plan

**Conditional:** NOT required for this loop (no new tests authored, only schema fix)

**Rationale:** test_stage_b_shell_modifiers already exists in TESTING_GUIDE.md and TEST_SUITE_INDEX.md. Schema fix unblocks existing test, doesn't add new selectors.

**Next Loop:** If Phase 7 integration adds new tests (e.g., test_stage_b_asu_integration), THEN run `pytest --collect-only` and update registries.

---

## Mapped Tests Guardrail

**Active Selector:** `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers`

**Collection Check:**
```bash
pytest --collect-only -q tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers
```
Expected: `1 test collected` (selector exists and is active)

**Status:** Test exists but currently FAILS (TypeError). This loop's goal is to make it PASS.

**Hard Gate Compliance:** If test still collects 0 after any refactoring, downgrade to "Planned" in TESTING_GUIDE.md OR add missing test. Current status: test exists, selector valid, no gate violation.

---

**End of Input**
