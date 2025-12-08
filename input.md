# Input for Ralph (Loop i=174)

## Summary
Execute ARCH-TELEMETRY-002 Phase B — Implement telemetry surfaces enforcement test and extend supervisor policy.

## BindingForRalph
- **ActionType:** implementation_ready
- **DecisionStatus:** patch_ready
- **InitiativeType:** architecture

## SupervisorMode
TDD (author enforcement test that validates telemetry ownership contract)

## Focus
ARCH-TELEMETRY-002 — Telemetry & Probe Simplification — Phase B (Enforcement & Diagnostic Policy)

## Branch
integration

## Mapped Tests
- `pytest -v tests/architecture/test_telemetry_surfaces.py` (new test — must PASS)
- `pytest -v tests/architecture/test_probe_contracts.py` (existing — must remain green for shim delegation)

## Artifacts
`plans/active/ARCH-TELEMETRY-002/reports/2025-12-07T220000Z/`

## Findings Applied (Mandatory)
- **PROBE-FREEZE-001** (Plan-local probe policy): New test must align with existing probe contracts
  - Adherence: B3 task cross-references test_probe_contracts.py
- **ARCH-STAGE-CTX-001** (Stage context ownership): Test validates Stage collectors as primary telemetry owners
  - Adherence: Allow-list includes `telemetry_collectors.py`, `interfaces.py` as owners
- **ARCH-STAGE-CTX-002** (Telemetry dict mutations): Test flags new dict surfaces outside owner modules
  - Adherence: B1 test checks for telemetry dict creation in non-owner modules
- **DIAGNOSTICS-001** (Diagnostic artifact expectations): Artifacts follow established patterns
  - Adherence: Artifacts routed to `reports/<timestamp>/` per standard structure

## Pointers
- Implementation plan: `plans/active/ARCH-TELEMETRY-002/implementation.md` (Phase B checklist)
- Telemetry charter: `docs/architecture/telemetry.md`
- Telemetry inventory: `plans/active/ARCH-TELEMETRY-002/reports/2025-12-07T215000Z/telemetry_inventory.md`
- Probe contracts test: `tests/architecture/test_probe_contracts.py`
- Supervisor policy: `prompts/supervisor.md` (search for `diagnostic_script_policy`)
- Writer IDL: `docs/architecture/dbex/io/writer.idl.md`
- Context IDL: `docs/architecture/dbex/refinement/context.idl.md`
- Docs index: `docs/index.md` (needs telemetry charter link)

---

## ARCH Contracts (mandatory)
- **ARCH-STAGE-CTX-001/002** (Stage Context Ownership): Stage collectors own production telemetry surfaces
  - Owner: `dbex/refinement/telemetry_collectors.py`, `dbex/refinement/interfaces.py`
  - Classification: Implementation — adding enforcement test for existing ownership
- **PROBE-FREEZE-001** (Probe Policy): Plan-local scripts consume existing telemetry only
  - Owner: `prompts/supervisor.md::diagnostic_script_policy`, `tests/architecture/test_probe_contracts.py`
  - Classification: Implementation — extending enforcement with telemetry-specific rules

---

## Do Now

**Focus:** ARCH-TELEMETRY-002 Phase B — Enforcement & Diagnostic Policy

### Background
Phase A completed (loop i=173, commit 744cea60): Telemetry charter authored at `docs/architecture/telemetry.md`, inventory built, manifest extended. Minor gap: Charter not yet linked in `docs/index.md` (fix as B0).

Phase B implements enforcement artifacts per Exit Criteria 3-4.

### Phase B Tasks

#### B0 — Fix Phase A Gap: Wire Charter into Docs Index (Housekeeping)

Add telemetry charter to `docs/index.md` in the Architecture section:

```markdown
### [Telemetry Ownership Charter](architecture/telemetry.md)
Description: Canonical telemetry ownership map, expansion rules, and probe freeze policy.
Keywords: telemetry, collectors, writer, diagnostics, probe freeze
```

Output: Edit `docs/index.md`

#### B1 — Implement Telemetry Surfaces Enforcement Test

Create `tests/architecture/test_telemetry_surfaces.py` that:

1. **Validates owner allow-list**: Only chartered owner modules may define long-lived telemetry dict surfaces
2. **Scans production modules**: Walk `dbex/` (excluding tests, plans, archive, scripts)
3. **Detects new dict surfaces**: Flag dict literals or `dict()` returned from public functions in non-owner modules
4. **Maintains allow-list**: Small exception list for existing surfaces (bridge diagnostics, mapping helpers)

**Test structure:**
```python
"""
Telemetry surfaces enforcement test.

ARCH-TELEMETRY-002 Exit Criterion 3: Prevents new long-lived telemetry dict
surfaces in dbex/ outside owner allow-list.

Owner allow-list (from docs/architecture/telemetry.md §2):
- dbex/refinement/interfaces.py (Stage*Telemetry dataclasses)
- dbex/refinement/telemetry_collectors.py (Stage*TelemetryCollector)
- dbex/io/writer.py (/torch_diagnostics HDF5 schema)

Secondary owners (diagnostics, not full enforcement):
- dbex/refinement/telemetry_baseline.py (baseline metrics)
- dbex/refinement/artifacts.py (stage artifacts)
"""

TELEMETRY_OWNER_MODULES = {
    "dbex/refinement/interfaces.py",
    "dbex/refinement/telemetry_collectors.py",
    "dbex/io/writer.py",
}

SECONDARY_OWNER_MODULES = {
    "dbex/refinement/telemetry_baseline.py",
    "dbex/refinement/artifacts.py",
    "dbex/vis/mapping.py",
}
```

**Test functions:**
- `test_telemetry_owners_exist()` — Verify owner modules exist
- `test_no_unchartered_telemetry_exports()` — Scan for new telemetry dict exports in non-owner modules (may need AST walk or grep-based heuristic)

Output: `tests/architecture/test_telemetry_surfaces.py`

#### B2 — Extend Supervisor Diagnostic Policy

Update `prompts/supervisor.md` `<diagnostic_script_policy>` section to include telemetry charter compliance:

Add to existing rules:
```xml
<telemetry_charter_compliance>
  - New production telemetry fields MUST follow expansion rules in docs/architecture/telemetry.md §5:
    (1) Spec update if new semantics, (2) IDL definition, (3) Dataclass update, (4) Collector wiring,
    (5) Writer support if HDF5, (6) Enforcement test coverage.
  - Plan-local scripts may read existing telemetry surfaces but MUST NOT define new production schemas.
  - Dict-based telemetry in dbex/ outside owner modules (§2 of charter) is forbidden without charter amendment.
</telemetry_charter_compliance>
```

Output: Edit `prompts/supervisor.md`

#### B3 — Align Probe Contracts Test

Update `tests/architecture/test_probe_contracts.py` docstring or comments to reference telemetry charter:

At top of file or in relevant test docstrings, add:
```python
# Cross-reference: docs/architecture/telemetry.md (telemetry ownership charter)
# Cross-reference: tests/architecture/test_telemetry_surfaces.py (telemetry dict guard)
```

Output: Edit `tests/architecture/test_probe_contracts.py` (minimal — add cross-reference only)

#### B4 — Summary

Create `reports/2025-12-07T220000Z/summary.md` with:
1. Phase B task completion status (B0, B1, B2, B3)
2. Test results (new test + existing probe contracts)
3. Phase C scope preview (cleanup/closure)

---

## How-To Map

```bash
# Set environment
cd /home/ollie/Documents/diffbragg_example
export ARTIFACT_DIR=plans/active/ARCH-TELEMETRY-002/reports/2025-12-07T220000Z

# B0: Wire charter into docs/index.md
# Use Edit tool to add entry in Architecture section

# B1: Create enforcement test
# Use Write tool to create tests/architecture/test_telemetry_surfaces.py
# Then validate:
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1
pytest -v tests/architecture/test_telemetry_surfaces.py --maxfail=1

# B2: Update supervisor policy
# Use Edit tool to add telemetry_charter_compliance to diagnostic_script_policy

# B3: Add cross-reference to probe contracts
# Use Edit tool to add cross-reference comment

# B4: Write summary
# Use Write tool to create summary.md

# Final validation: Run both architecture tests
pytest -v tests/architecture/test_telemetry_surfaces.py tests/architecture/test_probe_contracts.py::test_probe_shims_delegate_to_owner_clis
```

---

## Forbidden This Loop
- **No telemetry schema changes** — Enforcement test validates existing ownership, doesn't modify production telemetry
- **No new probes** — Phase B is enforcement/policy; probes deferred to Phase C cleanup
- **No dict removal yet** — Cleanup is Phase C; Phase B establishes guards

## Pitfalls To Avoid
1. **Don't over-engineer AST analysis** — Simple heuristic (grep for dict patterns, check module path) is sufficient for MVP
2. **Don't duplicate charter content in test** — Reference charter, don't copy rules into test assertions
3. **Keep allow-list minimal** — Only document existing surfaces; reject temptation to pre-allow hypotheticals
4. **Test must be deterministic** — If using file scanning, sort paths for stable output
5. **Don't break existing tests** — Probe contracts shim test must remain green

## If Blocked
If owner module scanning is too complex for a single loop:
1. Author a minimal enforcement test that validates owner modules exist and are documented
2. Document the gap in `reports/2025-12-07T220000Z/gaps.md`
3. Defer full AST scanning to Phase C or a harness initiative
4. Still complete B0, B2, B3 (docs/policy updates)

---

## Exit Criteria Validation

| Criterion | Expected | Validation |
|-----------|----------|------------|
| B0 complete | Charter linked in docs/index.md | Grep for `architecture/telemetry` in index |
| B1 complete | Enforcement test exists + passes | `pytest tests/architecture/test_telemetry_surfaces.py` |
| B2 complete | Supervisor policy extended | Grep for `telemetry_charter_compliance` in supervisor.md |
| B3 complete | Probe contracts cross-ref added | Grep for telemetry charter reference in test |
| B4 complete | Summary exists | `reports/.../summary.md` |
| Existing tests green | No regression | `test_probe_shims_delegate_to_owner_clis` PASS |

---

## Output Artifacts Expected

1. `docs/index.md` (edited — telemetry charter entry added)
2. `tests/architecture/test_telemetry_surfaces.py` (new file)
3. `prompts/supervisor.md` (edited — telemetry_charter_compliance added)
4. `tests/architecture/test_probe_contracts.py` (edited — cross-reference added)
5. `plans/active/ARCH-TELEMETRY-002/reports/2025-12-07T220000Z/summary.md`

---

## Context: Phase A Completion

### Deliverables Produced (i=173, commit 744cea60)
- `docs/architecture/telemetry.md` — Telemetry ownership charter with §1-9
- `reports/2025-12-07T215000Z/ownership_spike.md` — Initial owner mapping
- `reports/2025-12-07T215000Z/telemetry_inventory.md` — Surface catalog (13+ HDF5 attrs, 20+ per-stage, 4 secondary)
- `docs/data_dependency_manifest.md` — Telemetry section added

### Key Findings from Inventory
- **5 primary dataclasses** in interfaces.py
- **3 collectors** in telemetry_collectors.py
- **1 HDF5 schema owner** in writer.py
- **No mapping_metrics.json** pattern — mapping telemetry embedded in calibration dicts
- **Baseline metrics opt-in** via config flag

### Exit Criteria Progress (5 total)
1. Charter exists ✅ (minor: needs index link — B0)
2. Inventory exists ✅ (in manifest + reports)
3. Enforcement test — **Phase B** (B1)
4. Supervisor policy updated — **Phase B** (B2)
5. Tests pass under guards — **Phase C** (validation sweep)

---

## Implement Target
`tests/architecture/test_telemetry_surfaces.py::test_telemetry_owners_exist` + `test_no_unchartered_telemetry_exports`

## Validating Pytest Selectors
```bash
pytest -v tests/architecture/test_telemetry_surfaces.py tests/architecture/test_probe_contracts.py::test_probe_shims_delegate_to_owner_clis
```
