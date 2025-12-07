# Input for Ralph — Loop i=133

**Summary**: DB-AT-SUITE-CARE-001 Phase B.1+B.2 — Verify DB-AT-010 status & execute centralized asset validation

**Mode**: none

**ActionType**: implementation_ready

**DecisionStatus**: patch_ready

**InitiativeType**: harness

**Focus**: [DB-AT-SUITE-CARE-001] — Acceptance Suite Upkeep (DB-AT-002/010/020—024)

**Branch**: integration

**Mapped tests**:
- `env KMP_DUPLICATE_LIB_OK=TRUE DBAT010_ARTIFACT_DIR=plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T084500Z/db_at_010_verification NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests -k DB_AT_010 --smoke-detector-size=full`
- Asset validation (no pytest; ls checks + checksum validation)

**Artifacts**: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T084500Z/`

**Findings Applied (Mandatory)**:
- **TESTING-003** — Phase B asset validation confirms canonical refGeom presence before member plans advance to Phase A/B transition
- **RUNTIME-001** — DB-AT-010 requires `NANOBRAGG_DISABLE_COMPILE=1` + `--smoke-detector-size=full` per workflow spec
- **DIAGNOSTICS-001** — Centralized asset validation emits structured artifact (file existence checks + checksums + file sizes)

**ARCH Contracts (mandatory)**:
1. **ARCH-CONTRACT-TESTING-001** (Test registry synchronization)
   - **Owner**: `docs/development/TEST_SUITE_INDEX.md`
   - **Failure**: member_plan_status_audit.md classified DB-AT-010 as "blocked" but tests pass with correct flags

**Do Now**:

Execute Phase B.1 (DB-AT-010 status verification) and Phase B.2 (centralized asset validation) for DB-AT-SUITE-CARE-001.

**Context**: Loop i=131 delivered Phase A audit classifying DB-AT-010 as "blocked" per 2025-11-04T232350Z regression report, but 2025-11-05T000200Z verification shows all tests PASSING. Need fresh verification with canonical flags.

**B.1 — DB-AT-010 Status Verification**

```bash
mkdir -p plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T084500Z/db_at_010_verification

env KMP_DUPLICATE_LIB_OK=TRUE \
    DBAT010_ARTIFACT_DIR=plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T084500Z/db_at_010_verification \
    NANOBRAGG_DISABLE_COMPILE=1 \
    pytest -v tests -k DB_AT_010 --smoke-detector-size=full \
    > plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T084500Z/pytest_db_at_010_verification.log 2>&1

echo $? > plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T084500Z/db_at_010_exit_code.txt
```

Then create `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T084500Z/db_at_010_status_verification.md` documenting:
- Test execution (command, exit code, tests collected/passed/failed)
- Status update (PASSING vs BLOCKED)
- Resolution (update member_plan_status_audit.md classification if tests pass)

**B.2 — Centralized Asset Validation**

Check workspace root for 4 canonical refGeom assets (refGeom.expt, refGeom.refl, scaled.mtz, 747_mask.pkl):

```bash
echo "=== Canonical refGeom Asset Availability Check ===" > plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T084500Z/asset_validation.md
echo "**Date**: 2025-12-07T084500Z" >> plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T084500Z/asset_validation.md
echo "" >> plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T084500Z/asset_validation.md

for asset in refGeom.expt refGeom.refl scaled.mtz 747_mask.pkl; do
  if [ -f "$asset" ]; then
    size=$(stat -c%s "$asset" 2>/dev/null || stat -f%z "$asset" 2>/dev/null)
    checksum=$(sha256sum "$asset" 2>/dev/null | awk '{print $1}' || shasum -a 256 "$asset" 2>/dev/null | awk '{print $1}')
    echo "### \`$asset\`: ✅ FOUND" >> plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T084500Z/asset_validation.md
    echo "- Location: \`$(pwd)/$asset\`" >> plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T084500Z/asset_validation.md
    echo "- Size: $size bytes" >> plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T084500Z/asset_validation.md
    echo "- SHA256: \`$checksum\`" >> plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T084500Z/asset_validation.md
    echo "" >> plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T084500Z/asset_validation.md
  else
    echo "### \`$asset\`: ❌ NOT FOUND" >> plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T084500Z/asset_validation.md
    echo "" >> plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T084500Z/asset_validation.md
  fi
done

echo "---" >> plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T084500Z/asset_validation.md
echo "**Validation completed by**: Ralph (Loop i=133)" >> plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T084500Z/asset_validation.md
```

**Summary Report**

Create `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T084500Z/summary.md` documenting:
- Phase B.1 complete (DB-AT-010 status: PASSING/BLOCKED)
- Phase B.2 complete (X/4 assets found)
- Next steps (Phase B advancement ready vs escalation required)

**Validation**:
- DB-AT-010 pytest completes (exit code 0 = PASS)
- 4 asset checks complete (existence + checksums)
- 3 markdown reports exist

**Forbidden This Loop**:
- No member plan Phase A/B tasks (defer to B.4-B.5)
- No production code changes
- No new tests or selector extensions
- No asset provisioning (document missing files only)

**Pitfalls**:
1. Missing `--smoke-detector-size=full` causes UsageError not test failure
2. Update member_plan_status_audit.md if DB-AT-010 passes
3. Check both workspace root AND tests/fixtures/ for assets
4. Portable checksum: `sha256sum` (Linux) OR `shasum -a 256` (macOS)

**If Blocked**:
- DB-AT-010 fails: Document signature, mark B.1 blocked, escalate to Phase D loop
- Assets missing: Document gaps, complete B.2 with mitigation options
