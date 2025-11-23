# Input for Ralph — Phase E Telemetry Schema Bugfix

## Summary
Fix RefinementTelemetry dataclass schema mismatch (missing `engine_protocol` and `stage_modes` fields).

## Mode
none (bugfix)

## Focus
ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase E: Orchestration Hooks & Mode Wiring) — Telemetry Schema Fix

## Branch
integration

## Mapped tests
- `pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (regression guard, MUST PASS)

## Artifacts
`plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T163000Z/`

## Do Now

**Context:** Your Phase E implementation (commit c2ec597) added `engine_protocol` and `stage_modes` fields to telemetry dicts in the engine aggregation logic, but you forgot to add these fields to the RefinementTelemetry dataclass definition. This causes a TypeError when the engine tries to reconstruct RefinementTelemetry objects.

**Error:** `TypeError: __init__() got an unexpected keyword argument 'engine_protocol'` at dbex/refinement/engine.py:139

**Root Cause:** Schema inconsistency — runtime code adds fields that dataclass doesn't define.

**Fix:** Add two fields to RefinementTelemetry dataclass and update `to_dict()` method.

### Steps (5 steps total)

1. **Read blocker analysis:**
   - `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T163000Z/phase_e_blocker_analysis.md`
   - Confirm you understand the schema mismatch (engine adds fields, dataclass doesn't define them)

2. **Add two fields to RefinementTelemetry dataclass:**
   - File: `dbex/refinement/stage.py`
   - Location: After line 157 (after `mode: Optional[str] = None`)
   - Add:
     ```python
     # ARCH-REFINE-FLOW-001 Phase E: Engine delegation telemetry
     engine_protocol: Optional[str] = None  # e.g., "A→B→C", "A-only", "A→B"
     stage_modes: Optional[Dict[str, str]] = None  # e.g., {"B": "shell", "C": "detector_offsets"}
     ```

3. **Update to_dict() method to serialize new fields:**
   - File: `dbex/refinement/stage.py`
   - Location: After line 225 (after `if self.mode is not None:` block)
   - Add:
     ```python
     # Phase E extensions
     if self.engine_protocol is not None:
         result["engine_protocol"] = self.engine_protocol
     if self.stage_modes is not None:
         result["stage_modes"] = self.stage_modes
     ```

4. **Validation:**
   - Compilation check: `python -c "from dbex.refinement.stage import RefinementTelemetry"`
   - Regression guard: `pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`
     - Expected: PASS (Stage A engine delegation with new telemetry fields)
     - Archive log: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T163000Z/pytest_stage_a_engine_bugfix.log`

5. **Commit and document:**
   - Write `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T163000Z/summary.md` with:
     - Bugfix summary (2 fields added to dataclass + to_dict())
     - Validation results (compilation + regression guard)
     - Turn Summary block (prepend to summary.md)
   - Commit: `git add -A && git commit -m "ARCH-REFINE-FLOW-001 Phase E: Fix RefinementTelemetry schema (add engine_protocol + stage_modes fields)" && git push`

## How-To Map

**Compilation check:**
```bash
python -c "from dbex.refinement.stage import RefinementTelemetry"
```

**Regression guard:**
```bash
KMP_DUPLICATE_LIB_OK=TRUE \
DBEX_SMOKE_DETECTOR_SIZE=small \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
  2>&1 | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T163000Z/pytest_stage_a_engine_bugfix.log
```

## Pitfalls To Avoid

1. **Import for Dict type:** Add `from typing import Dict` at top of `dbex/refinement/stage.py` if not present (check line ~10)
2. **Field order:** Add new fields AFTER existing Phase A4 fields (stage_type, mode) to maintain logical grouping
3. **to_dict() consistency:** Both fields are Optional, so use `if is not None` guards like existing optional fields
4. **No breaking changes:** These are purely additive fields; existing tests should pass
5. **Validation completeness:** Regression guard MUST PASS before committing (do not skip this step)

## If Blocked

If regression guard still fails with schema errors:
1. Check that ALL usages of RefinementTelemetry in engine.py and nanobrag_refinement.py pass these fields
2. Verify Dict import is present in stage.py
3. Document the exact error signature and line number in summary.md
4. Commit partial progress (dataclass changes only) and return control to Galph

## Findings Applied

- **ARCH-ENGINE-002:** Stage wrapper telemetry packaging pattern (asdict → enrich → reconstruct) applies to engine aggregation as well; ensure new fields follow same Optional pattern
- **POLICY-001:** Environment Freeze — no package installs, code-only fix
- **TESTING-003:** Test registry sync not required (no new tests, existing selector unchanged)

## Pointers

- RefinementTelemetry dataclass: `dbex/refinement/stage.py:87-227`
- Engine aggregation logic: `dbex/refinement/engine.py:120-145`
- Telemetry population: `dbex/nanobrag_refinement.py:3820-3840`
- Phase E blocker analysis: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T163000Z/phase_e_blocker_analysis.md`
- Error log: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T160000Z/pytest_stage_a_engine.log`

## Next Up (if you finish early)

**Do NOT proceed.** This is a single-field bugfix. After regression guard passes, commit and return control to Galph for Phase E continuation planning.
