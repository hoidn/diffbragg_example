# Planning Notes — Loop i=170 (Galph)

**Focus**: ARCH-GRADIENT-FLOW-001 Phase B.5 (DBEX-layer gradient audit)
**Timestamp**: 2025-12-08T220000Z

## Portfolio Analysis

### Tier 0 Status
| Initiative | Status | Actionable |
|------------|--------|------------|
| ARCH-GRADIENT-FLOW-001 | partial | YES — Phase B.5 scoped |
| ARCH-IMPL-CONFORMANCE-001 | done | No |
| DIAG-NANOBRAGG-OVERSAMPLE-001 | done | No |
| ARCH-SIM-HKL-BOUNDS-001 | done | No |
| ARCH-SIM-CONSTRUCTION-001 | blocked_pending_environment | No |
| ARCH-PROBE-FREEZE-001 | done | No |
| ARCH-REFACTOR-001 | blocked_pending_architecture | No |
| PORTFOLIO-STATUS | done | No |

### Focus Selection Rationale
Per Agent Rule: "Prioritize initiatives in lower-numbered tiers. Within a tier, follow dependency chains. Do not start a Tier N+1 item if a Tier N item is unblocked."

ARCH-GRADIENT-FLOW-001 is `partial` (not blocked) — actionable work exists:
- nanobrag_torch layer: FIXED (enforcement tests 5/5 PASS)
- DBEX layer: NOT FIXED (DB-AT-010 still 5/5 FAIL)

Therefore, continue ARCH-GRADIENT-FLOW-001 rather than moving to Tier 1.

## Prior Work Summary

### Phase A (Complete, i=138)
- Call graph trace: 7 levels documented
- Suspect audit: 4 modules, 13 matches, 0 production UNSAFE patterns
- Test harness gradient breaks: test_gradients.py:383 (detector), :496 (beam)

### Phase B (Partial, i=153)
- B1: Upstream fix integration (nanobrag_torch gradient-preserving patterns)
- B2: Detector property conversion (post-creation override support)
- B3: Enforcement tests (5/5 PASS in tests/architecture/test_gradient_contracts.py)
- B4: Documentation (GRADIENT-002 finding, TEST_SUITE_INDEX.md)

### Phase B.5 (New — DBEX Layer)
Root cause has shifted from nanobrag_torch to DBEX layer. The code path:
```
simulate_forward_torch (forward.py:73)
  → create_crystal_config (config_factories.py:278) [WITHOUT crystal_overrides]
  → crystal_config.cell_* = override values (forward.py:205-225)
  → create_unified_simulator (helpers.py:83)
  → TorchCrystal construction (inside helpers.py)
```

**Hypothesis**: Gradient may be lost when:
1. CrystalConfig coerces tensor values to scalar on assignment, OR
2. create_unified_simulator extracts .item() from config values, OR
3. TorchCrystal constructor doesn't preserve tensor gradients

## Phase B.5 Task Design

### B.5.1 — Diagnostic Gradcheck
Run single test with verbose output to capture exact failure traceback.
- Input: test_db_at_010_gradcheck_crystal_cell_a
- Output: gradcheck_verbose.log

### B.5.2 — Tensor Flow Audit
Trace tensor from test → forward.py → config_factories.py → helpers.py
- Search patterns: .item(), .detach(), float(), np.array()
- Critical check: CrystalConfig field assignment behavior

### B.5.3 — Hypothesis Document
- Tensor flow trace with file:line annotations
- Suspect patterns identified
- Hypothesis with confidence score
- Proposed fix (if localized)

### B.5.4 — Summary
Turn summary for archive.

## Non-Negotiables Applied

- **Evidence→Action contract**: Loop ends with hypothesis + next production edit
- **Probe saturation**: No new diagnostic scripts (use grep/read only)
- **PROBE-FREEZE-001**: Any ad-hoc code must stay <400 LOC
- **Type discipline**: architecture (not bugfix)

## Dwell Tracking

- ARCH-GRADIENT-FLOW-001: dwell=0 for Phase B.5 (first DBEX-layer loop)
- Prior dwell: dwell=1 for Phase B partial completion review (i=157)
- Budget: ≤2 evidence loops allowed before implementation or switch

## ARCH/SPEC References Consulted

- docs/spec-db-conformance.md §Gradient-Safe Profile (DB-AT-010 acceptance)
- docs/findings.md::GRADIENT-001, GRADIENT-002
- plans/active/ARCH-GRADIENT-FLOW-001/implementation.md
- plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T060000Z/summary.md
