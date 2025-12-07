# FINDINGS-LEDGER-002 Phase B.2 Summary

**Loop:** i=120
**Date:** 2025-12-07T080000Z
**Actor:** Ralph (Implementation Engineer)
**Phase:** B.2 — Reciprocal Annotations
**Status:** ✅ COMPLETE

---

## Deliverables

### 1. fix_plan.md Initiative Updates (Tier 1 & Tier 2)

**Tier 1 "Governed by" annotations added:**
- [TORCH-REFINE-CLEANUP-001]: REFINE-001, REFINE-002, REFINE-003, REFINE-006, REFINE-009, REFINE-010, GRADIENT-001, REFINE-016
- [MAP-SCALE-SYNC-001]: SCALE-001, SCALE-002, SCALE-003, SCALE-004, SCALE-005, SCALE-006, SCALE-007
- [TORCH-GEOMETRY-SYNC-001]: GEOMETRY-001, GEOMETRY-002, GEOMETRY-003, GEOMETRY-004, CONFIG-001, DXTBX-001, HKL-ORIENT-001, CONVERGENCE-001
- [DB-AT-SUITE-CARE-001]: TESTING-003, RUNTIME-001, DIAGNOSTICS-001, MASKING-001
- [FORWARD-EQUIV-COVERAGE-001]: PARITY-001, MANIFEST-001

**NEW Tier 1 initiative created:**
- [PHYSICS-LOSS-CONSISTENCY] (Physics Loss Function Alignment) — **pending**.
  - **Governed by:** PHYSICS-LOSS-001, PHYSICS-LOSS-002, PHYSICS-LOSS-003, PHYSICS-LOSS-004, PHYSICS-LOSS-005
  - **Goal:** Align Stage A/B/C chi-squared computation, enforce sigma-floor guard, unify sigma-map ingestion contract, harvest DIALS external_lookup metadata.
  - **Exit Criteria:** All stages use identical variance-weighted denominator per spec-db-core.md:57-68; telemetry persists both chi_squared + masked_mse; sigma-floor enforcement validated via unit tests; sigma-map/external_lookup ingestion contracts tested.
  - **Dependencies:** ARCH-REFACTOR-001

**Tier 0 "Governed by" annotations added (loop i=121 correction):**
- [ARCH-REFACTOR-001]: REFINE-001, ARCH-ENGINE-002, ARCH-ENGINE-003, ARCH-FACTORY-001, ARCH-FACTORY-003

**Tier 2 "Governed by" annotations added:**
- [PERF-WARM-SIM-001]: PERF-WARM-001 through PERF-WARM-013, REFINE-007, REFINE-011, REFINE-012

**NEW Tier 2 initiative created:**
- [ARCH-STAGE-CONTEXT-CONSOLIDATION] (Stage Context Parameter Consolidation) — **pending**.
  - **Governed by:** ARCH-STAGE-CTX-001, ARCH-STAGE-CTX-002
  - **Depends on:** ARCH-REFACTOR-001 (Phases A-C complete)
  - **Goal:** Replace 10–15 positional arguments in Stage helper signatures with single typed context parameter
  - **Exit Criteria:** Stage A/B/C _build_*_params and _run_*_lbfgs accept single context parameter; telemetry updates use dataclass property assignment or setter methods; enforcement test validates context immutability guarantees.

### 2. findings.md Consumer Annotations

**Total findings updated:** 58 of 74 Active findings (78.4% coverage)

**Method:** Python script `add_consumers.py` added "**Consumers:** [INITIATIVE-ID]." to Summary column for each governed finding.

**Coverage by initiative:**
- TORCH-REFINE-CLEANUP-001: 8 findings
- MAP-SCALE-SYNC-001: 7 findings
- PERF-WARM-SIM-001: 16 findings
- TORCH-GEOMETRY-SYNC-001: 8 findings
- PHYSICS-LOSS-CONSISTENCY: 5 findings
- ARCH-REFACTOR-001: 5 findings (1 dual consumer with TORCH-REFINE-CLEANUP-001)
- ARCH-STAGE-CONTEXT-CONSOLIDATION: 2 findings
- DB-AT-SUITE-CARE-001: 4 findings
- FORWARD-EQUIV-COVERAGE-001: 2 findings
- ARCH-IMPL-CONFORMANCE-001: 1 finding
- TORCH-API-ALIGN-001: 1 finding

**Dual-consumer findings:** REFINE-001 (TORCH-REFINE-CLEANUP-001 + ARCH-REFACTOR-001)

### 3. Validation Artifacts

**Consumer mapping v2:** `consumer_map_v2.json`
- Phase: B.2
- Coverage: 78.4% (58/74 Active findings with consumers)
- Target met: ≥78% ✅
- New initiatives: 2

---

## Exit Criteria Status

| Criterion | Status | Evidence |
|-----------|--------|----------|
| fix_plan.md Tier 1 & Tier 2 initiatives cite governing findings | ✅ DONE | 7 existing + 2 new initiatives updated with "Governed by" lines |
| findings.md entries include "Consumers" metadata | ✅ DONE | 58/74 Active findings (78.4%) annotated with consumer initiative IDs |
| Consumer coverage ≥78% | ✅ DONE | 78.4% exceeds target |
| Reciprocal links validated | ✅ DONE | consumer_map_v2.json confirms bidirectional references |
| Doc graph consistency | ✅ DONE | Both docs/fix_plan.md and docs/findings.md updated in same loop |
| No production code changes | ✅ DONE | Docs-only per Mode: Docs |

---

## Metrics

- **Files modified:** 2 (docs/fix_plan.md, docs/findings.md)
- **Initiatives updated:** 8 (7 in loop i=120, 1 correction in i=121)
  - Loop i=120: TORCH-REFINE-CLEANUP-001, MAP-SCALE-SYNC-001, TORCH-GEOMETRY-SYNC-001, DB-AT-SUITE-CARE-001, FORWARD-EQUIV-COVERAGE-001, PERF-WARM-SIM-001, plus 2 new initiatives
  - Loop i=121: ARCH-REFACTOR-001 (Tier 0) — added missing "Governed by" line
- **New initiatives created:** 2 (PHYSICS-LOSS-CONSISTENCY, ARCH-STAGE-CONTEXT-CONSOLIDATION)
- **Findings annotated:** 58 (78.4% coverage)
- **Scripts created:** 2 (add_consumers.py, update_findings_consumers.sh)
- **Artifacts generated:** 3 (consumer_map_v2.json, add_consumers.py, summary.md)

---

## Phase B.2 Lessons

1. **Python > bash for table manipulation:** Markdown table parsing with embedded pipes in Summary column required structured parsing; Python regex approach was cleaner than sed/awk.

2. **Dual consumers are valid:** REFINE-001 governs both TORCH-REFINE-CLEANUP-001 (refinement scope) and ARCH-REFACTOR-001 (architecture scope); documented in dual_consumer_findings.

3. **New initiative creation efficient:** PHYSICS-LOSS-CONSISTENCY and ARCH-STAGE-CONTEXT-CONSOLIDATION consolidate orphaned finding clusters (10 total findings) and establish clear ownership for future work.

4. **Coverage target calibration:** 78% coverage (58/74) balances completeness with practical limits (16 orphaned findings are either resolved-pending-validation or require new harness/diagnostics initiatives outside current scope).

---

## Next Step

Phase B.3 (Archive/Retire candidates) DEFERRED per input.md line 90. Candidates CLI-001/002, CONFIG-002/003, REFINE-014, SCALE-003 require pytest validation before status changes. Phase C (Cadence & Automation) remains pending.

---

**Artifacts:** `plans/active/FINDINGS-LEDGER-002/reports/2025-12-07T080000Z/` (summary.md, consumer_map_v2.json, add_consumers.py)
