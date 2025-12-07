# Input for Ralph — Loop i=144

**Summary**: Execute DB-AT-SUITE-CARE-001 Phase B.3 FORWARD-EQUIV-002 artifact check to validate external dependency for DB-AT-002.

**Mode**: none (evidence collection, external dependency validation)

**ActionType**: evidence_collection

**DecisionStatus**: patch_ready

**InitiativeType**: harness

**Focus**: `DB-AT-SUITE-CARE-001 — Acceptance Suite Upkeep (DB-AT-002/010/020—024)`

**Branch**: integration

**Mapped tests**: none — evidence-only (asset existence check, no pytest execution)

**Artifacts**: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T030000Z/`

**Findings Applied (Mandatory)**:
- **MANIFEST-001** (Canonical manifest emission): Generator must verify `.npy` payloads exist before writing checksums; otherwise DB_AT_001 falls back to synthetic tensors. This loop validates manifest + payload co-location.
  - Code: `scripts/generate_simple_cubic_golden.py:620-717`
  - Adherence: Phase B.3 checks manifest.json and cross-references `.npy` file paths to ensure no foreign paths per MANIFEST-001.

- **DIAGNOSTICS-001** (Diagnostic artifact expectations): FORWARD-EQUIV-002 check report follows structured artifact pattern.
  - Code: `docs/spec-db-tracing.md`, `dbex/refine_one.py:80-95`
  - Adherence: All 4 deliverables emitted under timestamped reports directory.

**Pointers**:
- **Implementation Plan**: `plans/active/DB-AT-SUITE-CARE-001/implementation.md` lines 38-39 (Phase B.3 task definition)
- **Dependency Chain**: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T024500Z/dependency_chain.md` (DB-AT-002 depends on FORWARD-EQUIV-002 artifacts)
- **Member Plan**: `plans/active/DB-AT-002/implementation.md` (Phase A1 depends on this check)
- **FORWARD-EQUIV-002 Plan**: `plans/active/FORWARD-EQUIV-002/implementation.md` (escalation target if missing)
- **SPEC**: `docs/spec-db-conformance.md` §DB-AT-002 (canonical tensors + metrics baselines)
- **Testing Strategy**: `docs/development/testing_strategy.md` §2.1 (Golden dataset maintenance)

---

## ARCH Contracts (mandatory)

**No ARCH-CONTRACT enforcement this loop** — Evidence collection only; no architecture boundaries touched.

**Reference for context**:
- **MANIFEST-001** (finding, not ARCH-CONTRACT): Canonical manifest generation must verify `.npy` payloads exist before writing checksums
  - **Owner**: `scripts/generate_simple_cubic_golden.py`
  - **Classification**: Implementation correctness (not conformance failure; generator tool issue if manifest broken)

---

## Do Now (hard validity contract)

**Objective**: Validate `tests/fixtures/golden_data/simple_cubic/` artifact availability for DB-AT-002 Phase A1 prerequisite.

**Implement**: **No production code changes** — Evidence collection only.

**Tasks**:

1. **Check directory existence**: Verify `tests/fixtures/golden_data/simple_cubic/` exists via `ls` command. Capture output to `ls_golden_data.txt`.

2. **Manifest verification**: Check if `tests/fixtures/golden_data/simple_cubic/manifest.json` exists. If exists:
   - Load manifest and extract expected checksum (should be `2d1f8d67…8567aee` per implementation.md:38)
   - Verify `.npy` tensor payloads exist in same directory (no foreign paths per MANIFEST-001)
   - Compute actual SHA256 checksum of manifest file
   - Record comparison in `manifest_verification.txt`

3. **Tensor inventory**: List all `.npy` files in the directory. Note file sizes and timestamps. Append to `ls_golden_data.txt`.

4. **Status classification**:
   - **Case A (all valid)**: Manifest exists, checksum matches expected value, all referenced `.npy` files co-located → DB-AT-002 Phase A1 unblocked
   - **Case B (manifest missing)**: Directory exists but no manifest → Escalate to FORWARD-EQUIV-002 owner; DB-AT-002 Phase A1 blocked
   - **Case C (manifest broken)**: Manifest exists but checksum mismatch or foreign paths → Escalate to FORWARD-EQUIV-002 owner; recommend regeneration
   - **Case D (directory missing)**: No `tests/fixtures/golden_data/simple_cubic/` → CRITICAL escalation; FORWARD-EQUIV-002 must regenerate golden suite

5. **Write primary report**: Author `forward_equiv_002_check.md` with:
   - Validation outcome (Case A/B/C/D)
   - Manifest checksum comparison (if applicable)
   - Tensor inventory (file count, sizes, timestamps)
   - Recommendations: proceed to Phase B.4 (if Case A) OR escalate to FORWARD-EQUIV-002 owner (if Case B/C/D)
   - Cross-references: DB-AT-002 implementation.md Phase A1, FORWARD-EQUIV-002 implementation.md

6. **Write summary.md**: Loop summary with validation outcome, artifacts list, and next milestone readiness assessment.

**Validating pytest selector(s)**: none — evidence-only

**Artifacts path**: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T030000Z/`

**Deliverables** (all under artifacts path):
1. `forward_equiv_002_check.md` — Primary validation report
2. `ls_golden_data.txt` — Directory listing
3. `manifest_verification.txt` — SHA256 manifest check output (if manifest exists)
4. `summary.md` — Loop summary

**Initiative type consistency**: ✅ harness (external dependency validation per DB-AT-SUITE-CARE-001 charter)

---

## Forbidden This Loop

- **No new probes**: Evidence collection via shell commands only (`ls`, `sha256sum`, Python one-liner for manifest load)
- **Do not extend plan-local diagnostic scripts**: Use shell commands directly per PROBE-FREEZE-001
- **No production code changes**: Evidence collection only; no changes to `dbex/`, `tests/dbex/`, or fixture generation scripts
- **Do not modify test files**: DB-AT-002 member plan owns test authoring in future Phase B loops

---

## How-To Map

### Commands

**Directory existence check**:
```bash
mkdir -p plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T030000Z
ls -lah tests/fixtures/golden_data/simple_cubic/ > plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T030000Z/ls_golden_data.txt 2>&1
```

**Manifest verification** (conditional on manifest existence):
```bash
if [ -f tests/fixtures/golden_data/simple_cubic/manifest.json ]; then
  echo "Manifest exists" > plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T030000Z/manifest_verification.txt
  sha256sum tests/fixtures/golden_data/simple_cubic/manifest.json >> plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T030000Z/manifest_verification.txt
  python3 -c "import json; manifest = json.load(open('tests/fixtures/golden_data/simple_cubic/manifest.json')); print('Manifest keys:', list(manifest.keys())); [print(f'{k}: {v}') for k,v in manifest.items() if 'path' in str(v).lower()]" >> plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T030000Z/manifest_verification.txt 2>&1
else
  echo "Manifest NOT FOUND" > plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T030000Z/manifest_verification.txt
fi
```

**No pytest this loop** — Evidence collection only.

---

## Pitfalls To Avoid

1. **No production edits by Galph** — Evidence collection only; Ralph executes shell commands and writes reports
2. **Type discipline** — This is harness initiative; stay in scope (asset validation). Do not implement DB-AT-002 test logic
3. **Evidence→Action contract** — Must recommend concrete next action: proceed to Phase B.4 (if assets valid) OR escalate to FORWARD-EQUIV-002 owner (if broken/missing)
4. **Scriptization policy** — Use shell commands directly (`ls`, `sha256sum`, Python one-liner). No plan-local `.py` scripts per PROBE-FREEZE-001
5. **Parity-first interpretation** — Not applicable (no parity comparison this loop)
6. **No stacking on a cliff** — Not applicable (no prior cliff detected)
7. **Findings paydown** — Applied MANIFEST-001 (manifest validation protocol)
8. **Implementation floor** — This is NOT a docs-only loop (evidence collection with concrete shell commands). Next loop may be implementation (Phase B.4) or continued evidence depending on outcome

---

## If Blocked

**Case B/C/D (manifest missing/broken/directory missing)**:
- Mark DB-AT-SUITE-CARE-001 Phase B.3 **blocked_pending_forward_equiv_002**
- Cross-link to FORWARD-EQUIV-002 owner plan in `forward_equiv_002_check.md`
- Recommend regenerating golden suite via `scripts/generate_simple_cubic_golden.py` (if FORWARD-EQUIV-002 plan provides such script)
- Update `docs/fix_plan.md` Attempts History with blocker classification and cross-ref
- Switch focus to alternative Phase B task (e.g., Phase B.4 for DB-AT-020/021/023/024 which do NOT depend on FORWARD-EQUIV-002)

**Case A (all valid)**:
- Proceed to Phase B.4 (member plan Phase A coordination) in next loop
- No blocker; DB-AT-002 Phase A1 prerequisite satisfied

---

## Doc Sync Plan (Conditional)
**Not applicable this loop** — No tests added/renamed; evidence collection only.

---

**Issued by**: Galph (supervisor)
**Loop**: i=143 → i=144
**Next milestone**: Phase B.4 (member plan Phase A coordination) if Case A; escalation to FORWARD-EQUIV-002 owner if Case B/C/D
