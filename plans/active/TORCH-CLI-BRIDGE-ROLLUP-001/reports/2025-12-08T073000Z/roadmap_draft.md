# Roll-up Roadmap — TORCH-CLI-BRIDGE-ROLLUP-001

**Generated:** 2025-12-08T073000Z
**Status:** Draft (pending supervisor approval)

---

## Overview

This roadmap sequences the closeout of the TORCH-CLI-BRIDGE-ROLLUP-001 roll-up initiative, which consolidates three member plans:
- TORCH-BRIDGE-001 (Bridge DataLoad to nanobrag_torch)
- TORCH-CLI-003 (Wire torch backend flag into CLI)
- TORCH-CLI-004 (Torch diagnostics ROI score coercion)

**Key Insight:** All implementation work is complete. Remaining work is verification runs and documentation/ledger synchronization.

---

## Phased Approach

### Phase A: Member Plan Inventory (THIS LOOP)
**Status:** Complete
**Mode:** Docs
**Deliverables:**
- [x] `member_plan_inventory.md` — Reality check and status table
- [x] `roadmap_draft.md` — This document
- [x] Updated `implementation.md` — Replace stub with real plan

---

### Phase B: TORCH-BRIDGE-001 Closeout
**Estimated Loops:** 1
**Mode:** Docs (verification + ledger)
**Scope:** Execute Phase D (D1-D4) of TORCH-BRIDGE-001

#### Tasks
| ID | Task | Exit Criteria |
|----|------|---------------|
| D1 | Re-run bridge + smoke pytest modules | Fresh pytest.log with all tests passing |
| D2 | Update ledgers/docs for wrap-up | fix_plan.md status → done |
| D3 | Update TESTING_GUIDE.md §2 + TEST_SUITE_INDEX.md | Bridge/config/smoke selectors documented |
| D4 | Run pytest --collect-only; save logs | Collection logs under reports path |

**Commands:**
```bash
export ART=plans/active/TORCH-BRIDGE-001/reports/<NEW_TIMESTAMP>
mkdir -p "$ART"

# D1: Verification run
KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_nanobrag_bridge.py tests/dbex/test_nanobrag_bridge_configs.py tests/dbex/test_nanobrag_smoke.py | tee "$ART/pytest.log"

# D4: Collection check
KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only tests/dbex/test_nanobrag_bridge.py tests/dbex/test_nanobrag_bridge_configs.py tests/dbex/test_nanobrag_smoke.py | tee "$ART/collect.log"
```

**Exit Criterion Mapping:**
- EC2: Telemetry schema documented → Verify `docs/config_crosswalk.md` coverage
- EC3: Bridge responsibility split → Verify `docs/architecture.md` coverage

---

### Phase C: TORCH-CLI-003 Synchronization
**Estimated Loops:** 0.5 (can combine with Phase B if time permits)
**Mode:** Docs
**Scope:** Update stale checklist and verify tests

#### Tasks
| ID | Task | Exit Criteria |
|----|------|---------------|
| C.1 | Re-run CLI tests | 15/15 tests passing |
| C.2 | Update implementation.md | Phase A (A0-A2) and Phase B (B1-B2) checked |
| C.3 | Update fix_plan.md | Status reflects completion |

**Commands:**
```bash
export ART=plans/active/TORCH-CLI-003/reports/<NEW_TIMESTAMP>
mkdir -p "$ART"

# C.1: Verification run
KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_refine_one_cli.py | tee "$ART/pytest_cli.log"
```

**Exit Criterion Mapping:**
- EC1: CLI backend flag wiring → Verify per `docs/spec-db-interfaces.md`

---

### Phase D: TORCH-CLI-004 Synchronization
**Estimated Loops:** 0.5 (can combine with Phase C)
**Mode:** Docs
**Scope:** Update stale checklist and verify targeted test

#### Tasks
| ID | Task | Exit Criteria |
|----|------|---------------|
| D.1 | Re-run diagnostics test | test_torch_diagnostics_metadata passes |
| D.2 | Update implementation.md | All phases (A, B, C) checked |
| D.3 | Update fix_plan.md | Status explicitly tracked or roll-up ref added |

**Commands:**
```bash
export ART=plans/active/TORCH-CLI-004/reports/<NEW_TIMESTAMP>
mkdir -p "$ART"

# D.1: Verification run
KMP_DUPLICATE_LIB_OK=TRUE pytest -v "tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata" | tee "$ART/pytest_diag.log"
```

---

### Phase E: Roll-up Closure
**Estimated Loops:** 0.5
**Mode:** Docs
**Scope:** Final verification and ledger update

#### Tasks
| ID | Task | Exit Criteria |
|----|------|---------------|
| E.1 | Verify all 4 exit criteria (EC1-EC4) | Documented evidence for each |
| E.2 | Update fix_plan.md TORCH-CLI-BRIDGE-ROLLUP-001 status → done | Status change committed |
| E.3 | Archive member plan report pointers | Cross-references in roll-up reports |
| E.4 | Author closure summary | summary.md with metrics |

---

## Exit Criteria Verification Matrix

| Exit Criterion | Responsible Phase | Verification Method |
|----------------|-------------------|---------------------|
| EC1: CLI backend flag wiring | Phase C | `docs/spec-db-interfaces.md` status section |
| EC2: Telemetry schema documented | Phase B | `docs/config_crosswalk.md` bridge entries |
| EC3: Bridge responsibility split | Phase B | `docs/architecture.md` bridge section |
| EC4: REPORT-NANOBRAG-STATUS-001 resolved | Already done | REPORT-NANOBRAG-STATUS-001 is done (2025-12-08) |

---

## Recommended Sequencing

```
Phase A (this loop)    Phase B          Phase C         Phase D         Phase E
Member Inventory   →   BRIDGE-001   →   CLI-003     →   CLI-004     →   Roll-up
    │                  closeout         sync            sync            closure
    │                     │               │               │               │
    └─ DONE ─────────────┴───────────────┴───────────────┴───────────────┘
                         1 loop          0.5 loop       0.5 loop       0.5 loop
                                                                    ═══════════
                                                          Total: 2.5 loops
```

**Optimization:** Phases C and D can be combined into a single loop since both are quick verification + checklist updates.

**Realistic Estimate:** 2 loops total (Phase B = 1, Phases C+D = 0.5, Phase E = 0.5)

---

## Blockers and Risks

| Risk | Mitigation |
|------|------------|
| Tests may have regressed since Oct/Nov 2025 | Run fresh verification before marking done |
| Documentation may not reflect code | Review docs during each phase |
| fix_plan.md line numbers may have shifted | Search for section headers, not line numbers |

**No blocking dependencies:** REPORT-NANOBRAG-STATUS-001 is already done.

---

## Success Metrics

- All 28 bridge/config/smoke tests passing
- All 15 CLI tests passing
- All 3 member plan implementation.md checklists complete
- Roll-up status → done in fix_plan.md
- EC1-EC4 documented as satisfied

---

**Next Step:** Update `plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/implementation.md` with this phased approach.
