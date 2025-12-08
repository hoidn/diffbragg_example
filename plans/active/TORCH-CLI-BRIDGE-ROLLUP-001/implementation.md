# Implementation Plan — TORCH-CLI-BRIDGE-ROLLUP-001

ID: TORCH-CLI-BRIDGE-ROLLUP-001
Title: CLI & Bridge Infrastructure Roll-up
Type: roll-up
Owner: Galph ↔ Ralph
Status: in_progress

## Goals

Consolidate and close out three related CLI/bridge initiatives:
- TORCH-BRIDGE-001: Bridge DataLoad to nanobrag_torch
- TORCH-CLI-003: Wire torch backend flag into CLI
- TORCH-CLI-004: Torch diagnostics ROI score coercion

## Dependencies

- REPORT-NANOBRAG-STATUS-001 (output schema) — **DONE** (2025-12-08T071251Z)

## Exit Criteria

Per `docs/fix_plan.md:412-416`:

1. **EC1:** CLI backend flag wiring complete per `docs/spec-db-interfaces.md`
2. **EC2:** Telemetry schema work documented in `docs/config_crosswalk.md`
3. **EC3:** Bridge responsibility split tracked per `docs/architecture.md`
4. **EC4:** Dependencies on REPORT-NANOBRAG-STATUS-001 output schema resolved

## Member Plans

| Plan ID | Title | Implementation Status | Checklist Status |
|---------|-------|----------------------|------------------|
| TORCH-BRIDGE-001 | Bridge DataLoad | Phases A-C complete | Phase D pending |
| TORCH-CLI-003 | CLI backend flag | Work complete | Checklist stale |
| TORCH-CLI-004 | ROI score coercion | Work complete | Checklist stale |

## Phases Overview

- **Phase A:** Member Plan Inventory (reality check, roadmap)
- **Phase B:** TORCH-BRIDGE-001 closeout (D1-D4)
- **Phase C:** TORCH-CLI-003 synchronization (verify + checklist)
- **Phase D:** TORCH-CLI-004 synchronization (verify + checklist)
- **Phase E:** Roll-up closure (EC verification, ledger update)

---

## Phase A — Member Plan Inventory

**Status:** Complete (2025-12-08T073000Z)
**Mode:** Docs

### Checklist
- [x] A1: Audit TORCH-BRIDGE-001 status vs implementation.md claims
- [x] A2: Audit TORCH-CLI-003 status vs implementation.md claims
- [x] A3: Audit TORCH-CLI-004 status vs implementation.md claims
- [x] A4: Compile remaining work inventory
- [x] A5: Draft roadmap for roll-up closure
- [x] A6: Update this implementation.md (replace stub)

### Artifacts
- `reports/2025-12-08T073000Z/member_plan_inventory.md`
- `reports/2025-12-08T073000Z/roadmap_draft.md`
- `reports/2025-12-08T073000Z/summary.md`

### Key Findings
1. All three member plans have implementation complete
2. Remaining work is docs/ledger synchronization only
3. No code changes required for roll-up closure
4. Estimated 2 loops to complete roll-up

---

## Phase B — TORCH-BRIDGE-001 Closeout

**Status:** Pending
**Mode:** Docs
**Estimated Loops:** 1

### Checklist
- [ ] B1: Re-run bridge + smoke pytest modules with fresh logs
- [ ] B2: Update fix_plan.md TORCH-BRIDGE-001 status → done
- [ ] B3: Update TESTING_GUIDE.md §2 and TEST_SUITE_INDEX.md
- [ ] B4: Run pytest --collect-only; save collection logs
- [ ] B5: Mark TORCH-BRIDGE-001 Phase D complete in implementation.md

### Validation Commands
```bash
export ART=plans/active/TORCH-BRIDGE-001/reports/<TIMESTAMP>
KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_nanobrag_bridge.py tests/dbex/test_nanobrag_bridge_configs.py tests/dbex/test_nanobrag_smoke.py | tee "$ART/pytest.log"
KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only tests/dbex/test_nanobrag_bridge.py tests/dbex/test_nanobrag_bridge_configs.py tests/dbex/test_nanobrag_smoke.py | tee "$ART/collect.log"
```

### Exit Criteria Addressed
- EC2: Verify `docs/config_crosswalk.md` coverage
- EC3: Verify `docs/architecture.md` bridge section

---

## Phase C — TORCH-CLI-003 Synchronization

**Status:** Pending
**Mode:** Docs
**Estimated Loops:** 0.5

### Checklist
- [ ] C1: Re-run CLI tests (15 expected)
- [ ] C2: Update TORCH-CLI-003 implementation.md Phase A (A0-A2) → checked
- [ ] C3: Update TORCH-CLI-003 implementation.md Phase B (B1-B2) → checked
- [ ] C4: Confirm fix_plan.md reflects TORCH-CLI-003 status

### Validation Commands
```bash
export ART=plans/active/TORCH-CLI-003/reports/<TIMESTAMP>
KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_refine_one_cli.py | tee "$ART/pytest_cli.log"
```

### Exit Criteria Addressed
- EC1: Verify `docs/spec-db-interfaces.md` status section

---

## Phase D — TORCH-CLI-004 Synchronization

**Status:** Pending
**Mode:** Docs
**Estimated Loops:** 0.5

### Checklist
- [ ] D1: Re-run diagnostics test (test_torch_diagnostics_metadata)
- [ ] D2: Update TORCH-CLI-004 implementation.md all phases → checked
- [ ] D3: Add fix_plan.md ledger entry or roll-up reference

### Validation Commands
```bash
export ART=plans/active/TORCH-CLI-004/reports/<TIMESTAMP>
KMP_DUPLICATE_LIB_OK=TRUE pytest -v "tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata" | tee "$ART/pytest_diag.log"
```

---

## Phase E — Roll-up Closure

**Status:** Pending
**Mode:** Docs
**Estimated Loops:** 0.5

### Checklist
- [ ] E1: Verify EC1 (CLI backend flag) with evidence
- [ ] E2: Verify EC2 (telemetry schema) with evidence
- [ ] E3: Verify EC3 (bridge responsibility) with evidence
- [ ] E4: Verify EC4 (REPORT-NANOBRAG-STATUS-001 resolved) — pre-satisfied
- [ ] E5: Update fix_plan.md TORCH-CLI-BRIDGE-ROLLUP-001 status → done
- [ ] E6: Author final closure summary

### Artifacts
- `reports/<TIMESTAMP>/closure_summary.md`
- Exit criteria evidence matrix

---

## Artifacts Index

- Reports root: `plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/reports/`
- Phase A: `reports/2025-12-08T073000Z/`
- Phase B-E: TBD

## Spec References

- `docs/spec-db-interfaces.md` (EC1)
- `docs/config_crosswalk.md` (EC2)
- `docs/architecture.md` (EC3)
