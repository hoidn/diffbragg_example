# SPEC-INTERP-TRICUBIC-001 — Global Tricubic Interpolation Default

**Initiative Type**: spec_change
**Priority**: Tier 0 (unblocks cell parameter gradient refinement)
**Status**: in_progress
**Created**: 2025-12-08T120000Z
**Spec Owner**: docs/spec-db-core.md

## Goals

1. Make tricubic interpolation (`interpolation=True`) the canonical default across ALL stages (A, B, C)
2. Enable differentiable cell parameter gradients through the autograd path via query coordinates
3. Align spec with the physics requirement that cell parameter refinement needs smooth gradients

## Background

Investigation in ARCH-GRADIENT-FLOW-001 revealed that cell parameter gradients (e.g., `log_cell_a_delta`) show zero movement in Stage A refinement. Root cause analysis determined:

1. **Spec mandated `interpolation=False` for Stage A** (nearest-neighbor HKL lookup)
2. Nearest-neighbor lookup uses `torch.round()` which has zero gradient w.r.t. query coordinates
3. Cell parameters affect Miller indices via `h = q·a` where `q` is the scattering vector
4. Without differentiable HKL lookup, cell parameter gradients are zero by construction

**Key Evidence:**
- Stage A telemetry shows `log_cell_a_delta: {'initial': 0.0, 'final': 0.0, 'delta': 0.0}`
- nanobrag_torch's `polin3` tricubic interpolation correctly propagates gradients (verified ratio 1.0)
- Isolated nanobrag_torch simulator with `crystal.interpolate=True` shows correct gradients

## Phases Overview

- Phase A — Spec Alignment: Update normative spec documents to mandate tricubic interpolation globally
- Phase B — Implementation: Wire `interpolation=True` through Stage A forward path
- Phase C — Validation: Verify cell parameter gradients now flow and DB-AT selectors pass

## Exit Criteria

1. Spec documents (spec-db-core.md, spec-db-workflow.md, spec-db-conformance.md) mandate tricubic interpolation for all stages
2. Stage A implementation uses `interpolation=True` with ±1 haloed HKL grid
3. DB-AT-010 gradcheck passes for cell parameters (`test_gradcheck_crystal_cell_a`)
4. Stage A telemetry shows non-zero cell parameter deltas after refinement
5. Test registry synchronized: `docs/TESTING_GUIDE.md` updated with new interpolation defaults

## Compliance Matrix (Mandatory)

- [x] **Spec Constraint:** `spec-db-core.md §Interpolation Policy` — Updated to mandate tricubic globally
- [x] **Spec Constraint:** `spec-db-workflow.md §Interpolation policy (normative)` — Aligned with core spec
- [x] **Spec Constraint:** `spec-db-conformance.md §DB-AT-025` — Updated to require tricubic for all stages
- [ ] **Fix-Plan Link:** `docs/fix_plan.md — Row [ARCH-GRADIENT-FLOW-001]` — Cell gradient enablement
- [ ] **Finding/Policy ID:** To be created: INTERP-001 (Tricubic interpolation policy)

## Spec Alignment

- **Normative Spec:** docs/spec-db-core.md
- **Key Clauses:**
  - §Interpolation Policy (lines 98-102) — UPDATED
  - §Structure Factors (line 104) — Requires ±1 halo for tricubic

## Context Priming (read before edits)

- Primary docs/specs to re-read:
  - docs/spec-db-core.md §Interpolation Policy
  - docs/spec-db-workflow.md §Stage A (Geometry & Scale)
  - docs/spec-db-conformance.md §DB-AT-025
- Required findings/case law: ARCH-GRADIENT-FLOW-001 investigation evidence
- Related telemetry/attempts: Stage A telemetry showing zero cell parameter movement

---

## Phase A — Spec Alignment (COMPLETE)

### Checklist

- [x] A1: Update `docs/spec-db-core.md` §Interpolation Policy to mandate tricubic globally
- [x] A2: Update `docs/spec-db-workflow.md` §Interpolation policy to align with core
- [x] A3: Update `docs/spec-db-conformance.md` §DB-AT-025 to require tricubic for all stages
- [x] A4: Update DB-AT-028 HKL grid description

### Summary of Spec Changes Made

**spec-db-core.md (lines 98-102):**
```
OLD: Stage A SHALL use nearest-neighbor (`interpolation=False`)
NEW: All stages SHALL use tricubic (`interpolation=True`) with ±1 halo
```

**spec-db-workflow.md (lines 52-59):**
```
OLD: Stage A: interpolation=False is canonical
     Stage B/C: interpolation=True REQUIRED
NEW: All stages: interpolation=True REQUIRED with ±1 halo
```

**spec-db-conformance.md:**
- DB-AT-025: Updated to apply tricubic requirement to all stages
- DB-AT-028: Removed nearest-neighbor language from HKL grid description

### Notes & Risks

- **Risk:** Existing tests may assume nearest-neighbor for Stage A and fail
- **Mitigation:** Phase B will update implementation; Phase C validates all DB-AT selectors

---

## Phase B — Implementation (COMPLETE 2025-12-08T130000Z)

### Checklist

- [x] B1: Change config default `enable_hkl_interpolation: bool = True` in `config.py:42`
- [x] B2: HKL grid construction already includes ±1 halo (verified: Stage A smoke shows 99.79% hit rate)
- [x] B3: Stage A path honors interpolation flag via `RefinementConfig.enable_hkl_interpolation` (default now True)
- [x] B4: Update test files with legacy comments for explicit `False` settings (3 locations in `test_stage_a_smoke_parity.py`)

### Files Modified

1. `dbex/refinement/config.py:37-42` — Changed default, updated comments
2. `tests/dbex/test_stage_a_smoke_parity.py:201-202,266,745` — Added legacy comments

### Validation Results (2025-12-08T130000Z)

- **Partiality tests:** 2/2 PASS
- **Stage A smoke:** Tricubic interpolation working correctly (HKL hit rate 99.79%); OOM during reconstruction is environment resource constraint, not code regression

### Notes & Risks

- **Risk:** Performance regression from tricubic vs nearest-neighbor (4×4×4 neighborhood vs single lookup)
- **Mitigation:** Tricubic is already used for Stage B/C; overhead is acceptable for gradient accuracy
- **Environment constraint:** Stage A smoke test hits CUDA OOM during reconstruction; this is a known environment limitation (documented in TORCH-REFINE-CLEANUP-001)

---

## Phase C — Validation

### Checklist

- [ ] C1: Run DB-AT-010 gradcheck for cell parameters — expect PASS
- [ ] C2: Run Stage A smoke test — verify non-zero cell parameter deltas in telemetry
- [ ] C3: Run full DB-AT suite — all selectors should pass
- [ ] C4: Update docs/TESTING_GUIDE.md with new interpolation default
- [ ] C5: Create finding INTERP-001 in docs/findings.md

### Notes & Risks

- **Risk:** Other DB-AT selectors may have hard-coded nearest-neighbor expectations
- **Mitigation:** Search for `interpolat` patterns in test files and update

---

## Artifacts Index

- Reports root: `plans/active/SPEC-INTERP-TRICUBIC-001/reports/`
- Spec diffs: `2025-12-08T120000Z/spec_changes.md`

---

## Related Plans to Update

The following plans reference interpolation policy and may need updates:

1. **ARCH-GRADIENT-FLOW-001** — Cell gradient investigation (this initiative provides the spec fix)
2. **TORCH-REFINE-002D** — Stage A refinement (implementation must honor new spec)
3. **TOOLING-VIS-001** — Visualization (may reference Stage A interpolation)
4. **ARCH-REFINE-001** — Refinement architecture (interpolation policy references)

---

## Rationale

**Why tricubic is required for cell gradients:**

1. Cell parameters (a, b, c, α, β, γ) affect where Bragg peaks appear on the detector
2. Peak position depends on Miller indices: `h = q·a` (dot product of scattering vector with lattice vector)
3. Structure factor lookup: `F(h, k, l)` where h, k, l are continuous values
4. **Nearest-neighbor:** `F_nearest = F[round(h), round(k), round(l)]` — `round()` has zero gradient
5. **Tricubic:** `F_tricubic = polin3(F_grid, h, k, l)` — smooth interpolation, non-zero gradient w.r.t. h, k, l
6. Therefore: `dI/d(cell_a)` requires tricubic to propagate gradients through `d(h,k,l)/d(cell_a)`

**Why the spec originally mandated nearest-neighbor:**

Legacy DiffBragg used nearest-neighbor (`interpolate=0`) for Stage A. The spec was written to match this behavior for parity. However, this blocks autograd-based cell refinement, which was not a concern for the original finite-difference approach.

**Why changing the spec is the right fix:**

The spec error is: mandating `interpolation=False` while also expecting cell parameters to be trainable via autograd. These requirements are mutually exclusive. Since autograd cell refinement is the goal, the interpolation policy must change.
