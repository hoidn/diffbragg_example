# Input for Ralph (Loop i=173)

## Summary
Execute ARCH-TELEMETRY-002 Phase A — Author telemetry ownership charter and build telemetry inventory.

## BindingForRalph
- **ActionType:** planning
- **DecisionStatus:** exploring
- **InitiativeType:** architecture

## SupervisorMode
Docs (architectural documentation + inventory)

## Focus
ARCH-TELEMETRY-002 — Telemetry & Probe Simplification — Phase A (Charter & Inventory)

## Branch
integration

## Mapped Tests
- `pytest -v tests/architecture/test_probe_contracts.py` (PROBE-FREEZE-001 enforcement, must remain green)
- No new tests authored this loop (Phase A is docs/inventory)

## Artifacts
`plans/active/ARCH-TELEMETRY-002/reports/2025-12-07T215000Z/`

## Findings Applied (Mandatory)
- **PROBE-FREEZE-001** (Plan-local probe policy): Telemetry charter must align with existing probe freeze constraints
  - Adherence: Phase A explicitly defers semantics to Spec-DB and existing IDLs; no new production schemas
- **ARCH-STAGE-CTX-001** (Stage context ownership): Charter must recognize Stage collectors as primary telemetry owners
  - Adherence: A1 task names Stage collectors (StageATelemetry, StageBTelemetry, StageCTelemetry) as production owners
- **ARCH-STAGE-CTX-002** (Telemetry dict mutations): Charter must address typed setter methods over dict mutations
  - Adherence: Inventory (A2) will catalog which surfaces still use dict patterns vs typed dataclasses
- **DIAGNOSTICS-001** (Diagnostic artifact expectations): Artifacts must follow established patterns
  - Adherence: Artifacts routed to `reports/<timestamp>/` per standard structure

## Pointers
- Implementation plan: `plans/active/ARCH-TELEMETRY-002/implementation.md`
- Spec-DB core (telemetry refs): `docs/spec-db-core.md` §Objective Function, §Variance Model
- Spec-DB workflow (telemetry pipeline): `docs/spec-db-workflow.md` §Calibration & Unit Conventions
- Data telemetry flow doc: `docs/architecture/data_telemetry_flow.md`
- Stage collector impl: `dbex/refinement/telemetry_collectors.py`
- Writer IDL: `docs/architecture/dbex/io/writer.idl.md`
- Context IDL: `docs/architecture/dbex/refinement/context.idl.md`
- Data dependency manifest: `docs/data_dependency_manifest.md`

---

## ARCH Contracts (mandatory)
- **ARCH-STAGE-CTX-001/002** (Stage Context Ownership): Stage collectors own production telemetry surfaces
  - Owner: `dbex/refinement/telemetry_collectors.py`
  - Classification: N/A (charter aligns with existing ownership, not changing it)
- **PROBE-FREEZE-001** (Probe Policy): Plan-local scripts consume existing telemetry, don't create new production schemas
  - Owner: `prompts/supervisor.md::diagnostic_script_policy`, `tests/architecture/test_probe_contracts.py`
  - Classification: N/A (charter documents existing constraints)

---

## Do Now

**Focus:** ARCH-TELEMETRY-002 Phase A — Charter & Inventory

### Background
With Tier 0 exhausted and DB-AT-SUITE-CARE-001 Phase D.1 complete, this loop advances architectural hygiene by establishing telemetry ownership documentation. ARCH-TELEMETRY-002 dependencies are met:
- ARCH-PROBE-FREEZE-001: done (enforcement test exists)
- ARCH-TELEMETRY-001: archived (observer refactor complete)
- ARCH-STAGE-CONTEXT-001: done (typed contexts)

### Phase A Tasks

#### A0 — Nucleus / Contract Spike

Sketch initial telemetry ownership map by auditing key files:

1. **Stage collectors** (`dbex/refinement/telemetry_collectors.py`):
   - List exported dataclasses (StageATelemetry, StageBTelemetry, StageCTelemetry, StageResult, StagePerfCounters)
   - Note what attributes each owns

2. **Writer** (`dbex/io/writer.py`):
   - List `/torch_diagnostics` attributes emitted
   - Cross-reference with `docs/architecture/dbex/io/writer.idl.md`

3. **Mapping diagnostics** (`dbex/vis/mapping.py` if exists, or `dbex/refinement/helpers.py`):
   - Identify mapping metrics surfaces (mapping_metrics.json pattern)

4. **Baseline helpers** (search for `baseline` in dbex/):
   - Identify baseline metrics surfaces

Output: `reports/2025-12-07T215000Z/ownership_spike.md`

#### A1 — Author Telemetry Charter

Create `docs/architecture/telemetry.md` with:

1. **Purpose Statement**: Clarify telemetry ownership and expansion rules
2. **Primary Owners**:
   - Stage collectors (StageATelemetry, StageBTelemetry, StageCTelemetry)
   - Writer (`/torch_diagnostics` schema)
   - CLI telemetry bundle
3. **Secondary/Diagnostic Owners**:
   - Bridge/mapping helpers
   - Baseline metrics helpers
4. **Semantics Deferral**: Explicitly state that Spec-DB and IDLs are normative for semantics
5. **Expansion Rules**: New production telemetry must go through:
   - Charter update
   - IDL definition
   - Enforcement test coverage

Output: `docs/architecture/telemetry.md`

#### A2 — Build Telemetry Inventory

Create inventory covering:

| Surface | Owner Module | Fields/Attributes | Consumers (tests/plans) |
|---------|--------------|-------------------|------------------------|
| `/torch_diagnostics` | `dbex/io/writer.py` | (list from writer) | (grep test files) |
| StageATelemetry | `telemetry_collectors.py` | (list fields) | (grep test files) |
| ... | ... | ... | ... |

Sources to audit:
1. `dbex/io/writer.py` — search for `diagnostics_group` and attribute assignments
2. `dbex/refinement/telemetry_collectors.py` — list dataclass fields
3. `dbex/vis/mapping.py` or related — mapping metrics
4. grep for `baseline` in dbex/ — baseline metrics

Output: `reports/2025-12-07T215000Z/telemetry_inventory.md`

#### A3 — Extend Data Dependency Manifest

Add "Telemetry" section to `docs/data_dependency_manifest.md`:
- Point to owner modules
- List canonical artifacts (mapping_metrics.json, baseline metrics JSON)
- Cross-reference telemetry charter

Output: Edit `docs/data_dependency_manifest.md`

#### A4 — Summary

Create `reports/2025-12-07T215000Z/summary.md` with:
1. Charter location and status
2. Inventory findings (surface count, owner modules)
3. Manifest update status
4. Phase B scope preview (enforcement test, supervisor policy)

---

## How-To Map

```bash
# Set environment
cd /home/ollie/Documents/diffbragg_example
export ARTIFACT_DIR=plans/active/ARCH-TELEMETRY-002/reports/2025-12-07T215000Z

# A0: Audit key files for ownership spike
grep -n "class Stage.*Telemetry" dbex/refinement/telemetry_collectors.py
grep -n "diagnostics_group" dbex/io/writer.py
grep -rn "mapping_metrics" dbex/
grep -rn "baseline" dbex/ --include="*.py" | grep -v test | head -30

# A1: Create telemetry charter via Write tool

# A2: Build inventory by examining:
# - dbex/io/writer.py (torch_diagnostics attributes)
# - dbex/refinement/telemetry_collectors.py (dataclass fields)
# - dbex/vis/mapping.py (if exists)

# A3: Edit docs/data_dependency_manifest.md via Edit tool

# A4: Write summary.md via Write tool

# Validation: Ensure probe contracts still pass
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1
pytest -v tests/architecture/test_probe_contracts.py --maxfail=1
```

---

## Forbidden This Loop
- **No new production code** — Phase A is docs/inventory
- **No new test authoring** — Phase B handles enforcement test
- **No telemetry schema changes** — Inventory-only; cleanup is Phase C

## Pitfalls To Avoid
1. **Don't duplicate IDL content** — Charter should reference IDLs, not copy them
2. **Don't invent new ownership** — Document existing conventions, don't redesign
3. **Don't over-engineer inventory** — Simple markdown table is sufficient
4. **Keep charter concise** — 1-2 page max; point to specs/IDLs for details
5. **Apply PROBE-FREEZE-001** — No new plan-local scripts for this audit; use grep/read tools

## If Blocked
If critical modules are missing or ownership is unclear:
1. Document the gap in `reports/2025-12-07T215000Z/gaps.md`
2. Flag in summary.md as "Phase A incomplete — ownership unclear for X"
3. Proceed to Phase B with partial inventory; gaps become cleanup items for Phase C

---

## Exit Criteria Validation

| Criterion | Expected | Validation |
|-----------|----------|------------|
| A0 complete | Ownership spike exists | `reports/.../ownership_spike.md` |
| A1 complete | Charter exists | `docs/architecture/telemetry.md` |
| A2 complete | Inventory exists | `reports/.../telemetry_inventory.md` |
| A3 complete | Manifest updated | Telemetry section in `docs/data_dependency_manifest.md` |
| A4 complete | Summary exists | `reports/.../summary.md` |
| Probe contracts green | No regression | `pytest tests/architecture/test_probe_contracts.py` PASS |

---

## Output Artifacts Expected

1. `plans/active/ARCH-TELEMETRY-002/reports/2025-12-07T215000Z/ownership_spike.md`
2. `docs/architecture/telemetry.md`
3. `plans/active/ARCH-TELEMETRY-002/reports/2025-12-07T215000Z/telemetry_inventory.md`
4. `docs/data_dependency_manifest.md` (edited — Telemetry section added)
5. `plans/active/ARCH-TELEMETRY-002/reports/2025-12-07T215000Z/summary.md`

---

## Context: Portfolio Status

### Tier 0 (Exhausted)
- ARCH-GRADIENT-FLOW-001: **blocked_pending_upstream** (Jacobian mismatch in nanobrag_torch crystal gradient)
- ARCH-SIM-CONSTRUCTION-001: **blocked_pending_environment**
- ARCH-REFACTOR-001: **blocked_pending_architecture**
- Others: done/archived

### Tier 1
- DB-AT-SUITE-CARE-001: **in_progress** (Phase D.1 complete 2025-12-07T213000Z; D.2-D.5 maintenance deferred)
- MAP-SCALE-SYNC-001: **done**
- TORCH-GEOMETRY-SYNC-001: **done**
- PHYSICS-LOSS-001: **done_with_environment_caveat**
- SPEC-SQUARE-PARTIALITY-001: **done**
- RUNTIME-VEC-001: **done**
- Others: pending with dependencies

### Tier 3 (Selected)
- ARCH-TELEMETRY-002: **pending** → **in_progress** (Phase A this loop)

### Why This Focus
With Tier 0 exhausted and no Tier 1 implementation work unblocked, ARCH-TELEMETRY-002 provides:
1. Dependencies met (ARCH-PROBE-FREEZE-001 done, ARCH-TELEMETRY-001 archived)
2. Concrete Phase A/B/C structure with implementation in Phase B
3. Advances architectural hygiene ahead of future telemetry changes
4. Low risk — docs/inventory work unlikely to regress tests

---

## Implement Target
N/A — This is planning (docs + inventory). Phase B will introduce `tests/architecture/test_telemetry_surfaces.py`.

## Validating Pytest Selector
`pytest -v tests/architecture/test_probe_contracts.py` (must remain green — no regressions from docs work)
