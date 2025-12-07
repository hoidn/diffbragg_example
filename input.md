# Input for Ralph — Loop i=143

**Summary**: Execute DB-AT-SUITE-CARE-001 Phase B.2 centralized asset validation to unblock 5 downstream member plans.

**Mode**: none (asset validation, not test execution)

**ActionType**: implementation_ready

**DecisionStatus**: patch_ready

**InitiativeType**: harness

**Focus**: `DB-AT-SUITE-CARE-001 — Acceptance Suite Upkeep (DB-AT-002/010/020—024)`

**Branch**: integration

**Mapped tests**: none — read-only asset validation loop; format sanity checks serve as validation

**Artifacts**: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T020000Z/`

**Findings Applied (Mandatory)**:
- **TESTING-003** (Acceptance test registry maintenance): Asset validation enables TEST_SUITE_INDEX.md updates for 5 member plans (DB-AT-020/021/022/023/024). This loop confirms fixture availability as prerequisite for registry sync.
  - Code: `docs/development/TEST_SUITE_INDEX.md`
  - Adherence: Phase B.2 validates that canonical refGeom assets exist and are usable by downstream tests, unblocking registry updates.

- **DIAGNOSTICS-001** (Diagnostic artifact expectations): Asset validation report (`asset_validation.md`) follows structured artifact pattern for cross-referencing by member plans.
  - Code: `tests/dbex/test_stage_a_smoke_parity.py` (artifact writer precedent)
  - Adherence: All 4 deliverables (asset_validation.md, asset_checksums.txt, format_check_logs.txt, summary.md) emitted under timestamped reports directory.

**Pointers**:
- **Implementation Plan**: `plans/active/DB-AT-SUITE-CARE-001/implementation.md` lines 37-48 (Phase B.2 task definition)
- **Planning Notes**: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T010000Z/planning_notes.md` (detailed task breakdown)
- **Dependency Chain**: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T024500Z/dependency_chain.md` (refGeom asset consumers: DB-AT-020/021/022/023/024)
- **SPEC**: `docs/spec-db-conformance.md` §Workflow Integration Profile (acceptance criteria for 5 member plans depend on canonical fixtures)
- **ARCH**: `docs/architecture/tests_mapping.md` (fixture paths and shared dependencies)
- **TESTING_GUIDE**: `docs/TESTING_GUIDE.md` §1 (environment setup, may document asset paths)

---

## ARCH Contracts (mandatory)

**Relevant ARCH-CONTRACTs**: None directly applicable (asset validation task, not architecture change)

**Failure Classification**: N/A (this is a portfolio coordination task, not a conformance remediation)

**Rationale**: DB-AT-SUITE-CARE-001 is a harness roll-up initiative for portfolio steering. This Phase B.2 task validates shared test fixtures to unblock member plan progression. No architecture contracts are created or modified.

---

## Do Now (hard validity contract)

**Objective**: Validate canonical refGeom assets (existence, size, checksum, format) to unblock 5 downstream member plans.

**Tasks**:

1. **Locate asset paths**: Search `tests/fixtures/`, `tests/dbex/`, `docs/TESTING_GUIDE.md`, and grep test files for `refGeom.expt` references to identify canonical paths for 4 assets:
   - `refGeom.expt` (DIALS Experiment)
   - `refGeom.refl` (DIALS Reflection table)
   - `scaled.mtz` (Scaled structure factors)
   - `747_mask.pkl` (Detector trusted mask)

2. **Execute file checks**: For each asset:
   - Verify existence: `ls -lh <asset-path>`
   - Compute checksum: `sha256sum <asset-path>`
   - Record size and checksum (first 16 hex chars) in validation table

3. **Format sanity checks**: Run minimal Python commands to validate:
   - `refGeom.expt`: JSON parseable, contains `"detector"`, `"beam"`, `"crystal"` keys
   - `refGeom.refl`: DIALS reflection table loadable, has `"bbox"` column
   - `scaled.mtz`: MTZ file readable, has structure factor columns
   - `747_mask.pkl`: Pickle loadable, contains boolean mask array
   - Capture command outputs in `format_check_logs.txt`

4. **Cross-reference with member plans**: Grep `plans/active/DB-AT-020/`, `.../DB-AT-021/`, `.../DB-AT-022/`, `.../DB-AT-023/`, `.../DB-AT-024/` for asset references to confirm these are the correct shared fixtures

5. **Author asset_validation.md**: Consolidate findings into canonical report with:
   - Validation summary table (path/size/checksum/format/status for each asset)
   - Format sanity check results
   - Consumer plans cross-reference
   - Recommendations (all valid → proceed to Phase B.3/B.4; any missing → escalate)

**Implement**: None (read-only validation task, no production code changes)

**Validating pytest selector(s)**: none — format sanity checks serve as validation

**Artifacts path**: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T020000Z/`

**Deliverables** (all under artifacts path):
1. `asset_validation.md` — Primary report (validation table, format checks, consumer cross-refs)
2. `asset_checksums.txt` — Raw SHA256 output for all 4 assets
3. `format_check_logs.txt` — Output from Python format sanity check commands
4. `summary.md` — Loop summary with validation outcome and next action recommendation

**Initiative type consistency**: ✅ harness (portfolio coordination task per DB-AT-SUITE-CARE-001 charter)

---

## Forbidden This Loop

- **No new probes**: This is asset validation, not debugging; use existing file tools and Python imports only
- **No plan-local diagnostic scripts**: Use inline Python commands via `python -c "..."` for format checks
- **No production code changes**: Read-only validation task
- **No test file modifications**: Member plans will consume asset_validation.md as reference artifact

---

## How-To Map

### Asset Location Discovery
```bash
# Search for refGeom.expt references in test files
grep -r "refGeom.expt" tests/

# Search for fixture path documentation
grep -r "refGeom" docs/TESTING_GUIDE.md

# List candidate fixture directories
find tests/ -type d -name "fixtures" -o -name "refGeom"
```

### Asset Validation Commands
```bash
# For each asset, run:
ls -lh <asset-path>
sha256sum <asset-path> | tee -a asset_checksums.txt
```

### Format Sanity Check Examples
```bash
# refGeom.expt (DIALS Experiment JSON)
python -c "import json; f=open('<path>/refGeom.expt'); d=json.load(f); assert 'detector' in d; assert 'beam' in d; assert 'crystal' in d; print('VALID: contains detector/beam/crystal keys')"

# refGeom.refl (DIALS Reflection table)
python -c "from dials.array_family import flex; r=flex.reflection_table.from_file('<path>/refGeom.refl'); assert 'bbox' in r; print(f'VALID: {len(r)} reflections, bbox column present')"

# scaled.mtz (MTZ structure factors)
python -c "from iotbx import mtz; m=mtz.object(file_name='<path>/scaled.mtz'); cols=[c.label() for c in m.columns()]; print(f'VALID: columns={cols}')"

# 747_mask.pkl (Detector mask)
python -c "import pickle; m=pickle.load(open('<path>/747_mask.pkl', 'rb')); print(f'VALID: type={type(m).__name__}, shape={m.shape if hasattr(m, \"shape\") else \"non-array\"}')"
```

### Artifact Assembly
```bash
# Create timestamped report directory
mkdir -p plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T020000Z

# Write validation table to asset_validation.md
# (Use Edit tool or Write tool to assemble markdown report)

# Write summary.md with outcome
# (Include validation status, next phase recommendation)
```

---

## Pitfalls To Avoid

1. **Asset path assumptions**: Do NOT assume paths without searching; grep test files and docs to locate actual fixture locations
2. **Checksum baseline**: If no golden checksums exist, that's OK — record current checksums as baseline for future regression detection
3. **Format check dependencies**: If DIALS or iotbx imports fail (unlikely), note in format_check_logs.txt and defer to member plan Phase A reality checks
4. **Consumer plan grep scope**: Search all 5 member plan directories (DB-AT-020 through DB-AT-024) to confirm asset usage
5. **Type discipline**: This is harness (portfolio coordination), not bugfix or feature — do not change production code
6. **Artifact emission**: All 4 deliverables must land under timestamped reports directory for cross-referencing
7. **No test execution**: Do NOT run pytest this loop (format checks are Python imports, not test suite runs)
8. **Summary.md clarity**: Must include clear next action (Phase B.3/B.4 if assets valid, escalation if missing/corrupt)

---

## If Blocked

**If assets not found**:
- Record in `asset_validation.md` with status=MISSING
- Recommend escalation to fixture regeneration or maintainer inquiry
- Update `summary.md` with blocker status and next steps

**If format checks fail due to import errors**:
- Note in `format_check_logs.txt` with error message
- Assess whether this is environment issue (unlikely) or corrupt asset
- Recommend investigation in next loop or defer to member plan Phase A

**If checksums unavailable (no golden reference)**:
- Record current checksums in `asset_checksums.txt`
- Mark as "BASELINE RECORDED" in validation table
- Proceed with validation (absence of golden checksums is not a blocker)

---

## Doc Sync Plan

**Not required this loop** — this is asset validation, not test authoring.

Future Phase C (portfolio-wide registry sync) will update TEST_SUITE_INDEX.md based on member plan Phase C completion. This Phase B.2 task validates prerequisites only.

---

**Issued by**: Galph (supervisor)
**Loop**: i=142 → i=143
**Next milestone**: Phase B.3 (FORWARD-EQUIV-002 artifact check) OR Phase B.4 (member plan Phase A coordination) after asset validation complete
