# Maintenance Check — Loop i=217

**Date:** 2025-12-09T030000Z
**Focus:** DB-AT-SUITE-CARE-001 (Maintenance Mode)
**Branch:** integration

---

## Inbox/Outbox Audit

### nanoBragg Outbox (`~/Documents/nanoBragg/outbox/`)

| File | Date | Status | Summary |
|------|------|--------|---------|
| `dbex-gradient-blockers-fix-report.md` | Dec 7 18:31 | **PROCESSED** | wavelength/fluence/distance gradients FIXED in nanobrag_torch. 17/17 tests passing. |
| `square-lattice-partiality-response.md` | Dec 7 19:55 | **PROCESSED** | SQUARE scaling clarified. Peak ∝ N², integrated ∝ N. Already captured in SPEC-SQUARE-PARTIALITY-001 (done). |

### DBEX Inbox (`./inbox/`)

| File | Date | Status | Summary |
|------|------|--------|---------|
| `nanobrag_torch_cell_gradient_response_2025_12_08.md` | Dec 8 13:15 | **ACTIONABLE** | Cell gradients work in nanobrag_torch (6/6 tests PASS). Issue is in DBEX integration layer. Provides 3 debugging hypotheses. |
| `nanobrag_torch_response_2025_12_08.md` | Dec 7 18:38 | **PROCESSED** | SQUARE lattice response (duplicate of outbox response) |
| `from_nanobragg.md` | Dec 7 18:22 | **PROCESSED** | Historical communication |

### nanoBragg Inbox (`~/Documents/nanoBragg/inbox/`) — Outstanding Requests

| File | Priority | Status | Summary |
|------|----------|--------|---------|
| `mosaic_gradient_bug_2025_12_08.md` | HIGH | **AWAITING RESPONSE** | `mosaic_spread_deg > 0` breaks gradient magnitude. Blocks mosaicity refinement. |
| `chunked_interpolation_request_2025_12_09.md` | MEDIUM | **AWAITING RESPONSE** | Tricubic interpolation memory issue. Blocks PERF-GPU-MEM-001. |

---

## Key Finding: ARCH-GRADIENT-FLOW-001 Partially Actionable

The cell gradient response (`nanobrag_torch_cell_gradient_response_2025_12_08.md`) confirms:

1. **nanobrag_torch cell param gradients work correctly** (6/6 gradcheck tests PASS)
2. **Issue is in DBEX integration layer**, not upstream
3. **Three debugging hypotheses provided:**
   - Hypothesis 1: Double unit conversion (Å→m applied twice)
   - Hypothesis 2: Scalar extraction (.item()/.detach()) breaking gradient graph
   - Hypothesis 3: Fluence mismatch

**Loop i=209 already performed Phase B.7:**
- Pure-PyTorch B-matrix implemented
- Removed `.detach()` from A* extraction
- **Graph connectivity RESTORED** (analytical gradients non-zero: 7.04e7 cell_a, 4.64e7 cell_gamma)
- **Magnitude mismatch remains** (843× cell_a, 19,352× cell_gamma)

**Conclusion:** ARCH-GRADIENT-FLOW-001 is NOT fully blocked — DBEX-side magnitude investigation can proceed. The mosaic bug is a **separate** blocker that only affects `mosaic_spread_deg > 0` scenarios.

---

## Recommended Next Actions

1. **ARCH-GRADIENT-FLOW-001 Phase B.8:** Continue DBEX integration layer investigation
   - Focus on unit conversion audit in `config_factories.py`
   - Create minimal reproduction bypassing DBEX factories (as suggested by upstream)
   - Compare fluence values with upstream tests (they use `fluence=1e28`)

2. **Separate the two gradient blockers:**
   - Cell param magnitude → DBEX-side fix (actionable now)
   - Mosaic gradient → upstream fix (awaiting response)

---

## Portfolio Status Update

| Initiative | Previous Status | Updated Status | Rationale |
|------------|-----------------|----------------|-----------|
| ARCH-GRADIENT-FLOW-001 | blocked_pending_upstream | **in_progress** (Phase B.8) | DBEX-side magnitude investigation actionable |
| PERF-GPU-MEM-001 | blocked_pending_upstream | blocked_pending_upstream | No change (chunked interp request pending) |
| DB-AT-SUITE-CARE-001 | blocked (maintenance) | **in_progress** | Parent unblocked via ARCH-GRADIENT-FLOW-001 |

---

## Artifacts

- This maintenance check: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-09T030000Z/maintenance_check.md`
