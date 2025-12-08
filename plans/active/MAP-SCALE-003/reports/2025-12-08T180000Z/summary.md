# MAP-SCALE-003 Loop i=166 Summary (Galph Planning)

## Actor
Galph

## Date
2025-12-08T180000Z

## Mode
none (evidence collection)

## ActionType
evidence_collection

## DecisionStatus
exploring

## Focus Selection Rationale

**Portfolio Status:**
- Tier 0: All blocked or done (ARCH-GRADIENT-FLOW-001 partial, ARCH-SIM-CONSTRUCTION-001 blocked, ARCH-REFACTOR-001 blocked, others done)
- Tier 1: RUNTIME-VEC-001 just completed (i=165), SPEC-SQUARE-PARTIALITY-001 done, DB-AT-SUITE-CARE-001 Phase C complete

**Selected Focus:** MAP-SCALE-003 Phase A (CLI Refined Structure Factor Telemetry)
- **Why:** MAP-SCALE-SYNC-001 is the active roll-up (3/5 member plans complete); MAP-SCALE-003 is the next unblocked member plan with concrete Phase A tasks
- **Phase A scope:** Audit telemetry, trace refined MTZ loading path, confirm downstream consumers

## Housekeeping Completed

1. **RUNTIME-VEC-001 closure:** Updated fix_plan.md Execution Roadmap line 64 from "pending" to "done" with completion summary
2. **galph_memory.md updated:** Added Loop i=166 entry for MAP-SCALE-003 Phase A

## Problems Ledger Review

- DB-AT-028/029 entry: Already mapped to ARCH-SIM-CONSTRUCTION-001 (blocked_pending_environment)
- Template placeholder: Not a real problem
- All other entries: Resolved/checked
- **Problems ledger trigger NOT activated** — no new unchecked entries requiring incorporation

## Phase A Tasks Delegated

1. **A1: Audit current diagnostics emission**
   - Read `dbex/io/writer.py`, locate `_write_torch_outputs`
   - Document current schema under `/torch_diagnostics` group
   - Identify gap: structure-factor provenance not currently emitted
   - Output: `telemetry_audit.md`

2. **A2: Trace refined MTZ loading path**
   - Read `dbex/refine_one.py`, find `--refined-mtz` CLI flag
   - Trace: CLI → `run_nanobrag_backend` → `load_refined_mtz` → `build_structure_factor_grid`
   - Locate hook points for telemetry capture
   - Output: `mtz_loading_trace.md`

3. **A3: Confirm downstream consumers**
   - Read CLI tests and DB_AT_024 tests
   - Assess backward compatibility impact
   - Output: `downstream_consumers.md`

## Findings Applied

- **PROBE-FREEZE-001:** No new plan-local scripts
- **SCALE-003:** Reference for telemetry metadata schema design
- **SCALE-004:** Reference for refined MTZ path expectations

## ARCH Contracts

1. **ARCH-CONTRACT-TELEMETRY-001:** Torch diagnostics schema
   - Owner: `dbex/io/writer.py::_write_torch_outputs`
   - Classification: implementation validation

2. **ARCH-CONTRACT-SCALE-001:** Calibration precedence
   - Owner: `dbex/refinement/inputs.py::prepare_refinement_inputs`
   - Classification: implementation validation

## Artifacts

- `input.md` — Ralph instructions for Loop i=166
- `galph_memory.md` — Updated with Loop i=166 entry
- `docs/fix_plan.md` — RUNTIME-VEC-001 marked done

## Next Action

Ralph executes Phase A tasks (i=166), produces 3 artifacts (telemetry_audit.md, mtz_loading_trace.md, downstream_consumers.md), scopes Phase B implementation.

---

### Turn Summary

Loop i=166 (Galph): **Housekeeping + focus selection**. Marked RUNTIME-VEC-001 as **done** in fix_plan.md (Phase B/C complete i=165: correlation=1.0, sum_ratio_delta=0.0). Selected **MAP-SCALE-003 Phase A** (CLI Refined Structure Factor Telemetry) from MAP-SCALE-SYNC-001 roll-up (3/5 member plans complete, 2/5 pending). Phase A scoped: (A1) audit `_write_torch_outputs` diagnostics schema, (A2) trace refined MTZ loading path, (A3) confirm downstream consumers can access telemetry. DecisionStatus: exploring (first Phase A). Problems.md: DB-AT-028/029 already mapped to ARCH-SIM-CONSTRUCTION-001 (blocked). Applied findings: PROBE-FREEZE-001 (no new scripts), SCALE-003/004 (telemetry design refs). Next: Ralph executes Phase A tasks (i=166), produces 3 artifacts.
