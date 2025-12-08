# Member Plan Inventory — TORCH-CLI-BRIDGE-ROLLUP-001 Phase A

**Generated:** 2025-12-08T073000Z
**Focus:** Phase A Member Plan Reality Check

---

## 1. Member Plan Status Table

| Plan ID | Title | Claimed Status | Actual Status | Remaining Phases | Est. Loops |
|---------|-------|----------------|---------------|------------------|------------|
| TORCH-BRIDGE-001 | Bridge DataLoad to nanobrag_torch | in_progress | Phase A-C complete | D (closeout) | 1 |
| TORCH-CLI-003 | Wire torch backend flag into CLI | in_progress | **Work complete** (checklist stale) | Checklist sync | 0.5 |
| TORCH-CLI-004 | Torch diagnostics ROI score coercion | pending | **Work complete** (ledger stale) | Ledger sync | 0.5 |

**Total Remaining Task Count:** 6 checklist items across 3 plans

---

## 2. Detailed Member Plan Audits

### 2.1 TORCH-BRIDGE-001 (Bridge DataLoad to nanobrag_torch)

**Implementation Plan:** `plans/active/TORCH-BRIDGE-001/implementation.md`
**Claimed Status:** in_progress
**Actual Status:** Phases A-C genuinely complete; Phase D pending

#### Phase Status Breakdown

| Phase | Description | Status | Completed Date | Artifacts |
|-------|-------------|--------|----------------|-----------|
| A | Scaffolding & I/O | COMPLETE | 2025-10-28T222910Z | `reports/2025-10-28T222910Z/` |
| B | Config Hydration | COMPLETE | 2025-10-28T224846Z | `reports/2025-10-28T224846Z/` |
| C | Smoke Harness | COMPLETE | 2025-10-28T231200Z | `reports/2025-10-28T230500Z/` |
| D | Closeout | PENDING | — | — |

#### Phase D Remaining Tasks (D1-D4)
- [ ] D1: Re-run bridge + smoke pytest modules; capture fresh log + metrics
- [ ] D2: Update ledgers/docs for wrap-up (fix_plan status → done)
- [ ] D3: Update `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md`
- [ ] D4: Run `pytest --collect-only` for bridge/config/smoke; save logs

**Test Collection Evidence:**
```
28 tests collected:
- test_nanobrag_bridge.py: 5 tests
- test_nanobrag_bridge_configs.py: 20 tests
- test_nanobrag_smoke.py: 3 tests
```

**Note:** B1.1 (CUSTOM override) is an optional/exploratory item marked as NOT complete, but this does not block closeout.

**Assessment:** Phase D is docs/ledger closeout only — no code changes required. Estimated 1 loop.

---

### 2.2 TORCH-CLI-003 (Wire torch backend flag into CLI)

**Implementation Plan:** `plans/active/TORCH-CLI-003/implementation.md`
**Claimed Status:** in_progress
**Actual Status:** Exit criteria satisfied (per 2025-10-29 summary); checklist outdated

#### Reality Check

The Phase C completion summary (`reports/2025-10-29T003751Z/summary.md`) states:
> "Status: Complete (all exit criteria satisfied)"

**Exit Criteria Status (per summary):**
1. ✅ `dbex.refine_one` accepts `--backend {diffbragg,nanobrag}` with default `diffbragg`
2. ✅ Torch branch emits `Bragg` tensor and diagnostics matching legacy layout
3. ✅ `docs/index.md` entry reflects backend flag
4. ✅ Entry validated by running torch CLI smoke
5. ✅ Test registry synchronized

**Test Collection Evidence:**
```
15 tests collected in test_refine_one_cli.py:
- Parser tests (2): test_parser_has_backend_flag, test_parser_rejects_invalid_backend
- Dispatch tests (2): test_main_dispatches_to_diffbragg/nanobrag_backend
- Integration tests (9): calibration, sigma, MTZ, diagnostics
- Diagnostics tests (2): test_torch_diagnostics_metadata variants
```

#### Checklist Inconsistency

The `implementation.md` shows:
- Phase A (A0-A2): UNCHECKED
- Phase B (B1-B2): UNCHECKED
- Phase C (C1-C3): CHECKED

This is inconsistent — if C1-C3 (registry sync) are complete, A and B must have been done first. The checklist was not updated retroactively.

**Remaining Work:**
- [ ] Update Phase A checklist items to checked (A0-A2)
- [ ] Update Phase B checklist items to checked (B1-B2)
- [ ] Verify tests still pass with fresh run

**Assessment:** Implementation work is done; only checklist sync required. Estimated 0.5 loops.

---

### 2.3 TORCH-CLI-004 (Torch diagnostics ROI score coercion)

**Implementation Plan:** `plans/active/TORCH-CLI-004/implementation.md`
**Claimed Status:** (implicit) pending
**Actual Status:** Implementation complete (per 2025-11-04 summary); ledger not updated

#### Reality Check

The completion summary (`reports/2025-11-04T222435Z/summary.md`) documents:
- Score coercion implemented in `dbex/refine_one.py:414-424`
- Empty collection guard added at `dbex/refine_one.py:448-456`
- Test assertions added to `tests/dbex/test_refine_one_cli.py`

**Test Results (from summary):**
- Targeted: `test_torch_diagnostics_metadata` — PASSED
- Full suite: 67 passed, 2 failed (pre-existing), 3 skipped

**Next Actions Listed (not completed):**
1. Mark TORCH-CLI-004 as `done` in `docs/fix_plan.md`
2. No new findings warranted
3. Consider archiving artifacts

#### Checklist Status

All phases (A1-A3, B1-B3, C1-C3) show UNCHECKED in `implementation.md`, but summary documents completed work.

**Remaining Work:**
- [ ] Update implementation.md Phase A, B, C checklists
- [ ] Update `docs/fix_plan.md` status (currently not explicitly tracked)
- [ ] Verify targeted test still passes

**Assessment:** Implementation work is done; only ledger sync required. Estimated 0.5 loops.

---

## 3. Dependency Graph

```
REPORT-NANOBRAG-STATUS-001 (DONE - 2025-12-08T071251Z)
        │
        ▼
TORCH-CLI-BRIDGE-ROLLUP-001
        │
        ├── TORCH-BRIDGE-001 (Phase D pending)
        │       ├── No internal dependencies
        │       └── Provides: bridge helpers, config mapping, smoke harness
        │
        ├── TORCH-CLI-003 (Checklist sync pending)
        │       ├── Depends on: TORCH-BRIDGE-001 (bridge helpers)
        │       └── Provides: --backend CLI flag, dispatch logic
        │
        └── TORCH-CLI-004 (Ledger sync pending)
                ├── Depends on: TORCH-CLI-003 (diagnostics path)
                └── Provides: ROI score coercion, empty guard
```

**Critical Path:** TORCH-BRIDGE-001 Phase D → TORCH-CLI-003 sync → TORCH-CLI-004 sync

---

## 4. Exit Criteria Mapping (Roll-up)

Per `docs/fix_plan.md:412-416`:

| Exit Criterion | Responsible Plan | Status |
|----------------|------------------|--------|
| EC1: CLI backend flag wiring complete per `docs/spec-db-interfaces.md` | TORCH-CLI-003 | Code done; needs verification |
| EC2: Telemetry schema work documented in `docs/config_crosswalk.md` | TORCH-BRIDGE-001 | Phase B done; check docs |
| EC3: Bridge responsibility split tracked per `docs/architecture.md` | TORCH-BRIDGE-001 | Phase D docs pending |
| EC4: Dependencies on REPORT-NANOBRAG-STATUS-001 resolved | All | SATISFIED (dependency done) |

---

## 5. Summary Statistics

- **Total Member Plans:** 3
- **Plans with Code Complete:** 3 (100%)
- **Plans with Checklist Complete:** 0 (0%)
- **Remaining Checklist Items:** 6 (D1-D4 + CLI-003 sync + CLI-004 sync)
- **Estimated Total Loops to Close:** 2 loops
- **Blocker Dependencies:** None (REPORT-NANOBRAG-STATUS-001 is done)

---

## 6. Key Findings

1. **Checklist Drift:** All three member plans have work completed but checklists/ledgers not updated. This is a documentation debt, not implementation debt.

2. **No Code Changes Required:** All remaining work is docs/ledger sync (Mode: Docs).

3. **Quick Win Path:** TORCH-BRIDGE-001 Phase D is the most structured closeout — D1-D4 are well-defined verification steps.

4. **Risk:** The test suite state should be verified with fresh runs before marking done, as summaries are from October-November 2025.

---

**Next Step:** Draft roadmap for roll-up closure (Phase A3).
