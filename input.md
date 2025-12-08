# Input for Ralph (Loop i=166)

## Summary
Execute MAP-SCALE-003 Phase A (Telemetry Design) — audit current diagnostics emission, trace refined MTZ loading path, and confirm downstream consumers can access structure-factor telemetry.

## BindingForRalph
- **ActionType:** evidence_collection
- **DecisionStatus:** exploring
- **InitiativeType:** spec_change

## SupervisorMode
none (evidence collection / research)

## Focus
MAP-SCALE-003 — CLI Refined Structure Factor Telemetry (Phase A)

## Branch
integration

## Mapped Tests
- `pytest --collect-only tests/dbex/test_refine_one_cli.py` (inventory existing CLI tests)
- `pytest -v tests/dbex/test_mapping_consistency.py::test_DB_AT_024*` (downstream consumer validation)

## Artifacts
`plans/active/MAP-SCALE-003/reports/2025-12-08T180000Z/`

## Findings Applied (Mandatory)
- **PROBE-FREEZE-001** — No new plan-local scripts; evidence collection only via file reads and existing tests
- **SCALE-003** (structure factor provenance) — Reference for telemetry metadata schema design
- **SCALE-004** (calibration precedence) — Reference for refined MTZ path expectations

## Pointers
- Plan: `plans/active/MAP-SCALE-003/implementation.md` — Phase A checklist
- Roll-up: `plans/active/MAP-SCALE-SYNC-001/implementation.md` — Parent initiative context
- Fix-plan row: `docs/fix_plan.md` Tier 1 — [MAP-SCALE-SYNC-001]
- Spec refs:
  - `docs/spec-db-workflow.md` §4 — Calibration & structure-factor workflow
  - `docs/config_crosswalk.md` §2 — Structure-factor and calibration parameter mapping
  - `docs/spec-db-tracing.md` §2 — Torch diagnostics expectations

## ARCH Contracts (mandatory)
1. **ARCH-CONTRACT-TELEMETRY-001**: Torch diagnostics schema
   - Owner: `dbex/io/writer.py::_write_torch_outputs`
   - Classification: implementation validation (telemetry audit)
2. **ARCH-CONTRACT-SCALE-001**: Calibration precedence
   - Owner: `dbex/refinement/inputs.py::prepare_refinement_inputs`
   - Classification: implementation validation (refined MTZ path trace)

---

## Do Now

**Focus:** MAP-SCALE-003 Phase A (Telemetry Design)

### Execute Phase A tasks from `plans/active/MAP-SCALE-003/implementation.md`:

#### A1: Audit current diagnostics emission
1. **Read `dbex/io/writer.py`** and locate `_write_torch_outputs` function
2. **Document current schema**: List all attributes/datasets written under `/torch_diagnostics` group
3. **Identify gap**: Structure-factor provenance (hkl_source, reflection count, mean amplitude, MTZ path) is NOT currently emitted
4. **Output**: `telemetry_audit.md` with:
   - Current diagnostics schema (attribute list with types)
   - Missing fields for structure-factor provenance
   - Proposed schema additions (hkl_source, reflection_count, mean_amplitude, mtz_path)

#### A2: Trace refined MTZ loading path
1. **Read `dbex/refine_one.py`** — find `--refined-mtz` CLI flag handling
2. **Trace call chain**:
   - CLI → `run_nanobrag_backend` → `load_refined_mtz` → `build_structure_factor_grid`
   - Identify where structure-factor amplitudes are computed/consumed
3. **Locate hook points**: Where can telemetry be captured?
   - Post `load_refined_mtz` (MTZ path, reflection count)
   - Pre/post `build_structure_factor_grid` (mean amplitude, hkl_source)
4. **Output**: `mtz_loading_trace.md` with:
   - Call chain diagram (file:line → file:line → ...)
   - Proposed hook points with code citations
   - Any existing telemetry captured in this path

#### A3: Confirm downstream consumers
1. **Read `tests/dbex/test_refine_one_cli.py`** — identify tests that exercise `--refined-mtz` path
2. **Read `tests/dbex/test_mapping_consistency.py`** — check if DB_AT_024 accesses structure-factor telemetry
3. **Assess impact**: Will adding telemetry break existing artifact schemas?
4. **Output**: `downstream_consumers.md` with:
   - List of tests that exercise refined MTZ path
   - Existing artifact assertions (what schema do tests expect?)
   - Risk assessment: backward compatibility impact

---

## How-To Map

```bash
# Set environment
cd /home/ollie/Documents/diffbragg_example

# A1: Read writer module
# Use Read tool to examine dbex/io/writer.py

# A2: Trace refined MTZ path
# Use Read tool to examine:
# - dbex/refine_one.py (CLI entry point)
# - dbex/nanobrag_bridge.py or dbex/refinement/inputs.py (MTZ loading)

# A3: Check downstream consumers
# Use Read tool to examine:
# - tests/dbex/test_refine_one_cli.py
# - tests/dbex/test_mapping_consistency.py

# Optional: Verify tests collect
pytest --collect-only tests/dbex/test_refine_one_cli.py 2>&1 | head -30
pytest --collect-only tests/dbex/test_mapping_consistency.py 2>&1 | head -30
```

## Pitfalls To Avoid
1. **Do not modify production code** — Phase A is evidence collection only
2. **Do not create new probe scripts** — PROBE-FREEZE-001 applies
3. **Do not run full test suite** — collect-only for inventory, no execution needed
4. **Use Read tool, not grep** — for precise file examination
5. **Cite file:line** — all code references must include line numbers

## Forbidden This Loop
- No production code changes (evidence-only loop)
- No new plan-local scripts (per PROBE-FREEZE-001)
- No test execution beyond collect-only (Phase A is research)

## If Blocked
If refined MTZ path does not exist or telemetry hook points are unclear:
- Document the gap in summary.md
- Record as "Phase A incomplete — refined MTZ path not implemented or undocumented"
- Mark MAP-SCALE-003 as `blocked_pending_implementation`
- Do NOT attempt to implement missing functionality in this loop

---

## Exit Criteria Validation (for Phase A)

| Criterion | Expected | Validation |
|-----------|----------|------------|
| Telemetry audit complete | `telemetry_audit.md` exists | File in artifacts dir |
| MTZ loading trace complete | `mtz_loading_trace.md` exists | File in artifacts dir |
| Downstream consumers assessed | `downstream_consumers.md` exists | File in artifacts dir |
| Summary authored | `summary.md` exists | File in artifacts dir |
| No production code changed | git status clean | Verify no staged changes |

---

## Output Artifacts Expected

1. `plans/active/MAP-SCALE-003/reports/2025-12-08T180000Z/telemetry_audit.md`
2. `plans/active/MAP-SCALE-003/reports/2025-12-08T180000Z/mtz_loading_trace.md`
3. `plans/active/MAP-SCALE-003/reports/2025-12-08T180000Z/downstream_consumers.md`
4. `plans/active/MAP-SCALE-003/reports/2025-12-08T180000Z/summary.md`
