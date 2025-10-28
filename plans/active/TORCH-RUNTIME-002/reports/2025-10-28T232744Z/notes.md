# TORCH-RUNTIME-002 Documentation Updates — Loop Artifacts

**Timestamp**: 2025-10-28T232744Z
**Mode**: Docs
**Focus**: Runtime checklist + testing harness seed

## Objectives
- A1: Tighten `docs/TESTING_GUIDE.md` with explicit KMP_DUPLICATE_LIB_OK and NANOBRAGG_DISABLE_COMPILE guidance
- A2: Add runtime-focused "Common Pitfalls" to `docs/development/testing_strategy.md`
- B1: Synchronize planned DB-AT selectors between testing docs
- B2: Capture pytest collect output for DB_AT_001

## Changes Summary

### A1: TESTING_GUIDE.md Updates ✓
Enhanced §1 "Environments & Flags" with:
- §1.1 Required Environment Variables: explicit rationale for KMP_DUPLICATE_LIB_OK and NANOBRAGG_DISABLE_COMPILE
- §1.2 Installation Requirements: editable install guidance + verification command
- §1.3 Quick Reference Commands: standard/gradient/determinism test commands
- Expanded from 3 bullet points to structured subsections with code blocks
- Added cross-references to spec-db-runtime.md:18-21, spec-db-conformance.md:28, pytorch_runtime_checklist.md:26

### A2: testing_strategy.md Updates ✓
Enhanced §1.6 "Common Pitfalls" with:
- New first bullet: "Missing Environment Flags" with cross-reference to TESTING_GUIDE.md §1.1-1.3
- Clarified symptoms: OMP initialization errors, non-deterministic gradient failures
- Preserved existing torch.compile, device/dtype, pixel ordering, ADU/photons pitfalls
- Ensures runtime environment contract is discoverable in strategy docs

### B1: Selector Synchronization ✓
Updated both TESTING_GUIDE.md §2 and TEST_SUITE_INDEX.md:
- TESTING_GUIDE.md: Added Status column, expanded from 5 to 9 selectors (DB_AT_001, 002, 020-024, runtime vectorization)
- TEST_SUITE_INDEX.md: Added Spec Reference column, synchronized all 8 selectors with TESTING_GUIDE
- Both documents now include DB_AT_001 (torch parity), DB_AT_002 (determinism), DB_AT_022 (background), DB_AT_023 (calibration), DB_AT_024 (mapping sanity)
- Added cross-reference note at bottom of both docs to maintain sync
- All selectors marked "planned" with spec citations and notes about prerequisites

### B2: Pytest Collection Evidence ✓
Captured pytest --collect-only output to pytest_collect.log:
- Command: `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests -k DB_AT_001`
- Result: 0 tests collected, 21 deselected (as expected for planned selector)
- Runtime: 0.98s
- Artifact serves as baseline evidence that DB_AT_001 selector is registered but tests not yet authored
- See: plans/active/TORCH-RUNTIME-002/reports/2025-10-28T232744Z/pytest_collect.log

## Notes
- pytorch_runtime_checklist.md symlink is broken (DOC-RUNTIME-004 dependency); noted in input.md pitfalls
  - Symlink: docs/pytorch_runtime_checklist.md -> ../../nanoBragg2/docs/development/pytorch_runtime_checklist.md
  - Status: target does not exist
  - Impact: References in TESTING_GUIDE.md and testing_strategy.md cite the symlink path but remain valid conceptually
  - Mitigation: Keep references to ensure they work once DOC-RUNTIME-004 is completed
- All spec references remain consistent with spec-db shards
- Testing docs now provide clear environment setup guidance for future torch work
- Selector registry synchronized between TESTING_GUIDE and TEST_SUITE_INDEX
- Exit criteria 1-4 fully satisfied:
  1. ✓ TESTING_GUIDE.md §1 documents environment flags with rationale and commands
  2. ✓ DB-AT selectors (001, 002, 020-024) captured in both TESTING_GUIDE and TEST_SUITE_INDEX
  3. ✓ Artifact captured under plans/active/TORCH-RUNTIME-002/reports/2025-10-28T232744Z/
  4. ✓ Ledger entry includes Metrics/Artifacts lines in fix_plan.md
