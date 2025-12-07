# DB-AT-SUITE-CARE-001 Phase B.2 Planning Notes

**Loop**: i=142
**Date**: 2025-12-08T010000Z
**Actor**: Galph (supervisor)
**Phase**: B.2 — Centralized Asset Validation
**Action Type**: planning → implementation_ready

---

## Context

### Tier 0 Portfolio State
All Tier 0 items are done/archived/blocked:
- **ARCH-GRADIENT-FLOW-001**: blocked_pending_environment (i=140 lifecycle decision complete)
  - Blocker: nanobrag_torch DetectorConfig/simulator gradient handling (external dependency)
  - Recommended path: maintainer investigation with reproducer
- **ARCH-SIM-CONSTRUCTION-001**: blocked_pending_environment
- **ARCH-REFACTOR-001**: blocked_pending_architecture (depends on ARCH-SIM-CONSTRUCTION-001)
- All other Tier 0: done/archived

### Current Tier 1 Focus
**DB-AT-SUITE-CARE-001** (Acceptance Suite Upkeep)
- **Phase A**: ✅ Complete (i=131, 2025-12-07T024500Z)
  - Member plan audit complete
  - Dependencies mapped
  - Implementation.md authored
- **Phase B.1** (Tier-0 escalation): Delegated to ARCH-GRADIENT-FLOW-001, now blocked
- **Phase B.2** (Centralized asset validation): **SELECTED FOR THIS LOOP**
  - Status: pending
  - Blocks: 5 member plans (DB-AT-020/021/022/023/024 Phase A→B transitions)

---

## Objective (Phase B.2)

Execute centralized validation of canonical refGeom assets to unblock 5 downstream member plans that share this dependency.

### Assets to Validate
Per `plans/active/DB-AT-SUITE-CARE-001/implementation.md` lines 37-38:

1. `refGeom.expt` — DIALS Experiment (detector/beam/crystal geometry)
2. `refGeom.refl` — DIALS Reflection table (bboxes, observations, predictions)
3. `scaled.mtz` — Scaled structure factors (F_obs, I_obs, sigma)
4. `747_mask.pkl` — Detector trusted mask (DIALS format)

### Validation Contract
For each asset:
- **Existence check**: File present at expected path
- **Checksum validation**: SHA256 hash matches golden reference (if available)
- **File size**: Non-zero, within expected range (e.g., expt ~KB, refl ~MB, mtz ~KB, mask ~KB)
- **Format sanity**: Header inspection (e.g., DIALS experiment version, MTZ columns)

---

## Task Breakdown

### T1 — Locate Asset Paths
**Objective**: Identify canonical paths for refGeom assets used by DB-AT-020+ tests.

**Search locations**:
1. `tests/fixtures/` (likely home for shared test fixtures)
2. `tests/dbex/` (test-specific fixtures)
3. `docs/TESTING_GUIDE.md` (may document asset paths)
4. Grep test files for `refGeom.expt` references to infer paths

**Deliverable**: Table in `asset_validation.md` with:
```
| Asset           | Path                                  | Status   |
|-----------------|---------------------------------------|----------|
| refGeom.expt    | tests/fixtures/refGeom/refGeom.expt   | Located  |
| refGeom.refl    | tests/fixtures/refGeom/refGeom.refl   | Located  |
| scaled.mtz      | tests/fixtures/refGeom/scaled.mtz     | Located  |
| 747_mask.pkl    | tests/fixtures/refGeom/747_mask.pkl   | Located  |
```

---

### T2 — Execute File Checks
**Objective**: Validate existence, size, and checksum for each asset.

**Commands**:
```bash
# Existence + size
ls -lh <asset-path>

# Checksum (SHA256)
sha256sum <asset-path>
```

**Deliverable**: Extend table with size and checksum:
```
| Asset           | Path          | Size  | SHA256 (first 16 chars) | Status  |
|-----------------|---------------|-------|-------------------------|---------|
| refGeom.expt    | ...           | 12 KB | a3f7b9d2c8e5a1f6...     | Valid   |
| refGeom.refl    | ...           | 2.3 MB| 5c8d9e2b3f4a6c1d...     | Valid   |
| scaled.mtz      | ...           | 45 KB | 7e9f1a3c5d8b2e4f...     | Valid   |
| 747_mask.pkl    | ...           | 8 KB  | 2b4e6f8a1c3d5e7f...     | Valid   |
```

---

### T3 — Format Sanity Checks
**Objective**: Inspect headers/metadata to confirm assets are valid DIALS/MTZ files.

**Checks**:
1. **refGeom.expt**: JSON parseable, contains `"detector"`, `"beam"`, `"crystal"` keys
   ```bash
   python -c "import json; f=open('refGeom.expt'); d=json.load(f); assert 'detector' in d"
   ```

2. **refGeom.refl**: DIALS reflection table loadable, has `"bbox"` column
   ```bash
   python -c "from dials.array_family import flex; r=flex.reflection_table.from_file('refGeom.refl'); assert 'bbox' in r"
   ```

3. **scaled.mtz**: MTZ file readable, has `I_obs`, `F_obs`, `SIGI_obs` columns (typical)
   ```bash
   python -c "from iotbx import mtz; m=mtz.object(file_name='scaled.mtz'); print([c.label() for c in m.columns()])"
   ```

4. **747_mask.pkl**: Pickle loadable, contains boolean mask array
   ```bash
   python -c "import pickle; m=pickle.load(open('747_mask.pkl', 'rb')); print(type(m), m.shape if hasattr(m, 'shape') else 'non-array')"
   ```

**Deliverable**: Add "Format Check" column to table with status (Valid / Warning / Error).

---

### T4 — Cross-Reference with Member Plans
**Objective**: Confirm these assets are referenced in at least 3 of the 5 member plans.

**Search pattern**:
```bash
grep -r "refGeom.expt" plans/active/DB-AT-020/ plans/active/DB-AT-021/ plans/active/DB-AT-022/ plans/active/DB-AT-023/ plans/active/DB-AT-024/
```

**Deliverable**: Section in `asset_validation.md`:
```markdown
## Consumer Plans

| Asset           | Referenced by Plans                        |
|-----------------|--------------------------------------------|
| refGeom.expt    | DB-AT-020, DB-AT-021, DB-AT-022, DB-AT-023 |
| refGeom.refl    | DB-AT-020, DB-AT-021, DB-AT-023            |
| scaled.mtz      | DB-AT-021, DB-AT-022, DB-AT-024            |
| 747_mask.pkl    | DB-AT-020, DB-AT-021, DB-AT-023            |
```

---

### T5 — Author asset_validation.md Report
**Objective**: Consolidate findings into canonical artifact for member plans to reference.

**Structure**:
```markdown
# DB-AT-SUITE-CARE-001 Phase B.2 — Centralized Asset Validation

**Date**: 2025-12-08T...
**Loop**: i=143 (Ralph)
**Status**: Complete

## Asset Validation Summary

[Full table with path/size/checksum/format/status]

## Format Sanity Checks

[Per-asset validation results with command outputs]

## Consumer Plans

[Cross-reference table]

## Recommendations

- All 4 assets VALID → member plans can proceed to Phase B
- Asset X MISSING → escalate to fixture regeneration
- Asset Y CORRUPT → investigate and regenerate

## Cross-References

- **Fix Plan**: docs/fix_plan.md §DB-AT-SUITE-CARE-001 Phase B.2
- **Member Plans**: plans/active/DB-AT-020/, .../DB-AT-021/, .../DB-AT-022/, .../DB-AT-023/, .../DB-AT-024/
```

---

## DecisionStatus

**State**: exploring → patch_ready

**Rationale**:
- Task is well-scoped (5 subtasks, clear deliverables)
- No implementation unknowns (file checks, checksums, format validation)
- Confidence: 0.98 (standard asset validation pattern)

---

## Mapped Tests

**Primary**: None (this is asset validation, not a test execution loop)

**Regression**: None required (asset checks are read-only)

**Validation**: Format sanity checks serve as implicit validation that assets are usable by downstream tests

---

## Artifacts Deliverables

Ralph must produce (all under `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T...Z/`):

1. **asset_validation.md** — Primary deliverable (validation table, format checks, consumer cross-refs)
2. **asset_checksums.txt** — Raw SHA256 output for all 4 assets
3. **format_check_logs.txt** — Output from Python sanity check commands
4. **summary.md** — Loop summary with validation outcome (all valid / escalation needed)

---

## Next Loop Decision Tree

### If all 4 assets VALID
- **Next**: Phase B.3 (FORWARD-EQUIV-002 artifact check) OR Phase B.4 (member plan Phase A coordination)
- **Rationale**: Asset validation complete, proceed to next portfolio coordination task

### If 1+ assets MISSING/CORRUPT
- **Next**: Escalate to fixture regeneration initiative (create harness item or defer to maintainer)
- **Rationale**: Cannot unblock member plans without valid fixtures

### If checksums unavailable (no golden reference)
- **Next**: Record current checksums as baseline, proceed to Phase B.3
- **Rationale**: Absence of golden checksums is not a blocker if assets are format-valid

---

## Type Discipline

**Initiative Type**: harness (roll-up coordination)
**Action Type**: planning (this loop) → implementation_ready (next loop)
**Mode**: none (asset validation, not test execution)

**Conformance**:
- Not changing spec (no spec_change required)
- Not changing architecture (no ARCH-CONTRACT work)
- Purely portfolio coordination task per DB-AT-SUITE-CARE-001 charter

---

## ARCH/SPEC Alignment

### Relevant SPEC Sections
- **docs/spec-db-conformance.md** §Workflow Integration Profile — DB-AT-020/021/022/023/024 acceptance criteria depend on canonical fixtures
- **docs/TESTING_GUIDE.md** §1 — Environment Setup & Canonical Assets (if documented)

### Relevant ARCH Sections
- **docs/architecture/tests_mapping.md** — Fixture paths and shared dependencies
- **plans/active/DB-AT-SUITE-CARE-001/implementation.md** lines 106-107 — Canonical refGeom assets dependency

### Findings Applied
- **TESTING-003**: Asset validation enables TEST_SUITE_INDEX.md updates for 5 member plans
- **DIAGNOSTICS-001**: Artifact emission pattern (asset_validation.md serves as cross-referenced evidence)

---

## Risks & Mitigations

### Risk 1: Assets not found
**Likelihood**: Low (member plans authored recently, likely used working fixtures)
**Impact**: High (blocks 5 member plans)
**Mitigation**: Grep test files to locate actual paths; escalate to fixture regeneration if truly missing

### Risk 2: Checksums unavailable (no golden reference)
**Likelihood**: Medium (refGeom may be ad-hoc fixture, not versioned golden suite)
**Impact**: Low (checksums optional for validation, format checks sufficient)
**Mitigation**: Record current checksums as baseline for future regression detection

### Risk 3: Format checks require environment dependencies (DIALS, iotbx)
**Likelihood**: Low (these should be available in current environment)
**Impact**: Medium (cannot validate format, only size/existence)
**Mitigation**: Environment freeze allows reads; if import fails, defer format check to member plan Phase A reality check

---

## Loop Budget

**Estimated loops**: 1 (this is a read-only validation task, no implementation complexity)

**Dwell tracking**:
- Focus: DB-AT-SUITE-CARE-001
- Selector: Phase B.2
- Signature: centralized_asset_validation
- Dwell: 0 (first loop for this selector)

---

## Galph Notes

- **Portfolio steering rationale**: Tier 0 exhausted (all blocked/done/archived), DB-AT-SUITE-CARE-001 Phase B.2 is highest-priority unblocked Tier 1 task
- **Dependency unblocking**: This task unblocks 5 member plans (DB-AT-020/021/022/023/024) Phase A→B transitions
- **Dominant-hypothesis lock**: Not applicable (planning loop, not implementation)
- **Implementation floor**: Not applicable (next loop is first implementation for this selector)
- **Findings paydown**: TESTING-003 and DIAGNOSTICS-001 applied via artifact pattern

---

**Planning notes authored**: 2025-12-08T010000Z (Loop i=142, Galph)
**Next loop (i=143)**: Phase B.2 implementation (Ralph executes asset validation, produces 4 artifacts)
