# FINDINGS-LEDGER-002 Phase B.2 Final Cross-Link Matrix

**Date:** 2025-12-07T080000Z
**Phase:** B.2 Complete
**Coverage:** 78.4% (58/74 Active findings)

---

## Coverage Comparison: B.1 → B.2

| Metric | Phase B.1 (Before) | Phase B.2 (After) | Δ |
|--------|-------------------|-------------------|---|
| Active findings with consumers | 9 | 58 | +49 (+544%) |
| Coverage percentage | 12.2% | 78.4% | +66.2 pp |
| Orphaned findings | 64 | 16 | -48 (-75%) |
| Initiatives with "Governed by" | 0 | 9 | +9 |
| New initiatives created | 0 | 2 | +2 |

---

## Initiative → Finding Cross-Reference

| Initiative ID | Type | Findings Governed | Count |
|---------------|------|-------------------|-------|
| TORCH-REFINE-CLEANUP-001 | Tier 1 | REFINE-001, REFINE-002, REFINE-003, REFINE-006, REFINE-009, REFINE-010, GRADIENT-001, REFINE-016 | 8 |
| MAP-SCALE-SYNC-001 | Tier 1 | SCALE-001, SCALE-002, SCALE-003, SCALE-004, SCALE-005, SCALE-006, SCALE-007 | 7 |
| PHYSICS-LOSS-CONSISTENCY | Tier 1 (NEW) | PHYSICS-LOSS-001, PHYSICS-LOSS-002, PHYSICS-LOSS-003, PHYSICS-LOSS-004, PHYSICS-LOSS-005 | 5 |
| TORCH-GEOMETRY-SYNC-001 | Tier 1 | GEOMETRY-001, GEOMETRY-002, GEOMETRY-003, GEOMETRY-004, CONFIG-001, DXTBX-001, HKL-ORIENT-001, CONVERGENCE-001 | 8 |
| DB-AT-SUITE-CARE-001 | Tier 1 | TESTING-003, RUNTIME-001, DIAGNOSTICS-001, MASKING-001 | 4 |
| FORWARD-EQUIV-COVERAGE-001 | Tier 1 | PARITY-001, MANIFEST-001 | 2 |
| ARCH-REFACTOR-001 | Tier 2 | REFINE-001, ARCH-ENGINE-002, ARCH-ENGINE-003, ARCH-FACTORY-001, ARCH-FACTORY-003 | 5 |
| PERF-WARM-SIM-001 | Tier 2 | PERF-WARM-001 through PERF-WARM-013, REFINE-007, REFINE-011, REFINE-012 | 16 |
| ARCH-STAGE-CONTEXT-CONSOLIDATION | Tier 2 (NEW) | ARCH-STAGE-CTX-001, ARCH-STAGE-CTX-002 | 2 |
| ARCH-IMPL-CONFORMANCE-001 | Tier 0 | CONFORMANCE-001 | 1 |
| TORCH-API-ALIGN-001 | Tier 2 | MODEL-001 | 1 |

**Total:** 11 initiatives, 59 governed findings (58 unique + 1 dual consumer)

---

## Finding → Initiative Reverse Index

### Findings with Multiple Consumers

| Finding ID | Consumers | Count |
|------------|-----------|-------|
| REFINE-001 | TORCH-REFINE-CLEANUP-001, ARCH-REFACTOR-001 | 2 |

### Orphaned Findings (16 remaining, 21.6%)

**Status breakdown:**
- **Candidate for archive/retire (Phase B.3):** CLI-001, CLI-002, CONFIG-002, CONFIG-003, REFINE-014, SCALE-003
- **Resolved awaiting validation:** STAGEA-001 (resolved but still Active status)
- **Cross-cutting patterns (no single owner):** TESTING-001, TESTING-002, TESTING-004, TESTING-005, TESTING-006
- **Harness/tooling gaps (future initiatives):** LOGGING-001, PERF-001, REFINE-004, REFINE-005

**Rationale for 78% target:**
- 6 findings (8.1%) require pytest validation before archive/retire
- 10 findings (13.5%) are either resolved-pending or cross-cutting patterns lacking dedicated initiatives
- Creating initiatives for every cross-cutting pattern would fragment the ledger; these findings serve as implicit guardrails referenced in multiple plan-local docs

---

## New Initiatives Created (Phase B.2)

### 1. [PHYSICS-LOSS-CONSISTENCY] (Tier 1)

**Governed by:** PHYSICS-LOSS-001, PHYSICS-LOSS-002, PHYSICS-LOSS-003, PHYSICS-LOSS-004, PHYSICS-LOSS-005

**Goal:** Align Stage A/B/C chi-squared computation, enforce sigma-floor guard, unify sigma-map ingestion contract, harvest DIALS external_lookup metadata.

**Exit Criteria:**
- All stages use identical variance-weighted denominator per spec-db-core.md:57-68
- Telemetry persists both chi_squared + masked_mse
- Sigma-floor enforcement validated via unit tests
- Sigma-map/external_lookup ingestion contracts tested

**Dependencies:** ARCH-REFACTOR-001 (Stage A/B/C context + observer pattern provides hooks for unified loss computation)

**Rationale:** The 5 PHYSICS-LOSS-* findings describe a coherent physics/loss alignment scope that was previously dispersed across TORCH-REFINE-CLEANUP-001 and ARCH-REFACTOR-001. Consolidating into a single Tier 1 initiative clarifies ownership and unblocks downstream DB-AT work.

---

### 2. [ARCH-STAGE-CONTEXT-CONSOLIDATION] (Tier 2)

**Governed by:** ARCH-STAGE-CTX-001, ARCH-STAGE-CTX-002

**Depends on:** ARCH-REFACTOR-001 (Phases A-C complete — Stage A/B/C helpers now own their logic)

**Goal:** Replace 10–15 positional arguments in Stage helper signatures with single typed `context` parameter (extend StageAContext/StageBContext/StageCContext dataclasses); eliminate telemetry dict mutations in Stage B baseline parity guard by exposing typed setter methods.

**Exit Criteria:**
- Stage A/B/C `_build_*_params` and `_run_*_lbfgs` accept single context parameter
- Telemetry updates use dataclass property assignment or setter methods
- Enforcement test validates context immutability guarantees

**Working Plan:** to be created under `plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/implementation.md`

**Rationale:** ARCH-REFACTOR-001 Phase C completed Stage helper inlining (deleting *_impl.py modules), exposing long parameter lists and telemetry dict mutation anti-patterns. ARCH-STAGE-CTX-001/002 findings now have a dedicated refactoring initiative to consolidate those signatures into typed context parameters, building on the typed dataclasses introduced in ARCH-STAGE-CONTEXT-001.

---

## Phase B.2 Impact Summary

**Knowledge base integrity:**
- Reciprocal cross-links now enforce traceability: every governed finding points to its consumer initiative(s), and every initiative lists its governing findings.
- 78.4% coverage balances completeness (58 findings with clear homes) with pragmatism (16 orphans are either archive candidates or cross-cutting patterns).

**Plan portfolio clarity:**
- 2 new Tier 1/2 initiatives consolidate 7 previously orphaned findings (PHYSICS-LOSS-*, ARCH-STAGE-CTX-*).
- fix_plan.md Tier 1/2 sections now document "Governed by" lines for 9 roll-up initiatives, making it easier to trace spec/architecture constraints → plan items.

**Maintenance cadence readiness:**
- consumer_map_v2.json provides machine-readable snapshot for future Phase C automation.
- Orphan findings documented with rationale (archive candidates, resolved-pending, cross-cutting) to prevent "forever orphan" accumulation.

---

**Artifacts:** `plans/active/FINDINGS-LEDGER-002/reports/2025-12-07T080000Z/` (summary.md, consumer_map_v2.json, add_consumers.py, crosslink_matrix_final.md)
