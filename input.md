# Input — Loop i=190 (Ralph)

## Summary
Verify TORCH-REFINE-003 status: run Stage C microslip test to determine if implementation is complete; update checkboxes if PASS.

## Focus
TORCH-REFINE-003 — Stage C Detector Microslip (Scope Verification)

## Branch
integration

## Mapped Tests
- `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip` (primary — expect PASS if implementation complete)
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (regression guard)

## Artifacts
`plans/active/TORCH-REFINE-003/reports/2025-12-08T104000Z/`

---

## Do Now

**Focus:** TORCH-REFINE-003 — Scope Verification

**Implement:** `plans/active/TORCH-REFINE-003/implementation.md` Phase 0-4 checkbox sync (if test passes)

**Validating selector:** `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip`

**Artifacts path:** `plans/active/TORCH-REFINE-003/reports/2025-12-08T104000Z/`

### Background

The TORCH-REFINE-CLEANUP-001 Phase A member plan audit (i=186) classified TORCH-REFINE-003 as "blocked" because:
1. It depended on TORCH-REFINE-002D (Stage A gate restoration) — **NOW RESOLVED** (002D confirmed done, November 2025)
2. It depended on TORCH-REFINE-002E (gradient flow) — **NOT a hard blocker** (Stage C uses detector offsets, not crystal gradients)

**DISCOVERY (i=189 Galph)**: The test `test_stage_c_detector_microslip` already exists and collects (1 test). The implementation.md checkboxes are ALL unchecked, but the test code is present. This suggests the implementation work may be complete with only checklist hygiene remaining.

### Tasks

| ID | Task | Deliverable |
|----|------|-------------|
| V1 | Run collect-only for Stage C test | `collect_stage_c.log` confirming 1 test collected |
| V2 | Run Stage C test | `pytest_stage_c.log` with PASS/FAIL status |
| V3 | If PASS: Update implementation.md | Mark all applicable Phase 0-4 checkboxes complete |
| V4 | If PASS: Update fix_plan.md | Add Attempts History entry, update status |
| V5 | If FAIL: Document failure | Capture failure mode, identify remaining work |
| V6 | Author summary.md | Turn Summary block for this loop |

---

## How-To Map

### V1: Collect-only
```bash
KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only \
  tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip \
  2>&1 | tee plans/active/TORCH-REFINE-003/reports/2025-12-08T104000Z/collect_stage_c.log
```

### V2: Run Stage C test
```bash
mkdir -p plans/active/TORCH-REFINE-003/reports/2025-12-08T104000Z

KMP_DUPLICATE_LIB_OK=TRUE \
  DBEX_SMOKE_DETECTOR_SIZE=small \
  pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip \
  --maxfail=1 \
  2>&1 | tee plans/active/TORCH-REFINE-003/reports/2025-12-08T104000Z/pytest_stage_c.log
```

**Expected outcomes:**
- **PASS**: Implementation complete; proceed with V3-V4 (checkbox sync + ledger update)
- **FAIL with OOM**: Environment resource limit (same as i=188 smoke tests); document as environment caveat, not code issue
- **FAIL with assertion error**: Identify which exit criterion fails; scope remaining work

### V3: Implementation.md updates (if PASS)
Review test code and mark checkboxes in `plans/active/TORCH-REFINE-003/implementation.md`:
- Phase 0 (P0.1-P0.2): Baseline reality check — VERIFY test exercises deterministic detector offsets
- Phase 1 (P1.1-P1.3): Config plumbing — VERIFY `RefinementConfig` has Stage C toggles, per-panel distance params exist
- Phase 2 (P2.1-P2.3): LBFGS integration — VERIFY Stage C runs post-Stage A with detector distance optimization
- Phase 3 (P3.1-P3.3): Telemetry — VERIFY Stage C telemetry emitted with per-panel deltas
- Phase 4 (P4.1-P4.3): Validation — VERIFY test asserts improvement + telemetry completeness

### V4: fix_plan.md updates (if PASS)
Add Attempts History entry under TORCH-REFINE-CLEANUP-001 detailed section (~line 404):
```
  * 2025-12-08T104000Z (Loop i=190, Ralph) — **TORCH-REFINE-003 scope verification**: Ran test_stage_c_detector_microslip (PASS/FAIL). Implementation status: (complete if PASS / partial if FAIL). Updated implementation.md checkboxes. Artifacts: plans/active/TORCH-REFINE-003/reports/2025-12-08T104000Z/
```

---

## Pitfalls To Avoid

1. **DO** use `DBEX_SMOKE_DETECTOR_SIZE=small` for faster execution (full-detector requires more GPU memory)
2. **DO** capture test output to log file in artifacts directory
3. **DO NOT** modify production code — this is scope verification only
4. **DO NOT** modify test files — test already exists
5. **DO** verify test actually exercises Stage C (not just Stage A) by checking for `StageC` usage in test code
6. **Environment Freeze:** If OOM occurs, document it as environment caveat (not code regression) per i=188 precedent
7. **DO** check that Stage A also passes (regression guard) if time permits

---

## If Blocked

1. If test fails with OOM: Document in summary.md as `environment_resource_limit`, not a code failure
2. If test fails with assertion: Capture the specific failure, identify which exit criterion is unmet, scope the fix
3. If test fails with import error: Document the missing dependency and mark as environment blocker

---

## Findings Applied

- **TESTING-003**: Use canonical pytest selectors from TESTING_GUIDE.md
- **PROBE-FREEZE-001**: No new probe scripts — use existing test infrastructure
- **REFINE-007**: Stage C strict gates key off telemetry (≥80% offset reduction, ≤0.05% chi² regression)
- **REFINE-009**: Stage C must seed detector distance offsets from known geometry for telemetry accuracy

---

## Pointers

- TORCH-REFINE-003 implementation.md: `plans/active/TORCH-REFINE-003/implementation.md:18-37` (Phase checklist)
- Test code: `tests/dbex/test_torch_refine_smoke.py:1044-1364` (test_stage_c_detector_microslip)
- Prior Stage C summary: `plans/active/TORCH-REFINE-003/reports/2025-11-05T090201Z/stage_c_improvement_probe.json` (if exists)
- REFINE-007 finding: `docs/findings.md:67` (Stage C gate calibration)
- REFINE-009 finding: `docs/findings.md:71` (baseline detector seeding)

---

## Next Up (optional)

If Stage C test passes and time permits:
1. Run Stage A regression guard: `pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`
2. If both pass: Consider marking TORCH-REFINE-003 as `done` in fix_plan.md
