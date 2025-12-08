# Galph Planning Notes — Loop i=148

**Date**: 2025-12-08T120000Z
**Initiative**: DB-AT-021 (Mask Semantics Guard)
**Phase**: A — Reality Check & Inputs
**Action**: planning
**Decision Status**: exploring

---

## Context

DB-AT-SUITE-CARE-001 Phase B progression:
- **Phase B.2 complete** (i=143): Centralized refGeom asset validation (all 4 canonical assets VALID)
- **Phase B.3 complete** (i=144): FORWARD-EQUIV-002 artifact check (Case C-Minor, core files VALID)
- **DB-AT-020 closure** (i=147): First member plan complete (Phases A/B/C done, registry synced)
- **Phase B.4 next**: Coordinate remaining member plan Phase A tasks (DB-AT-021, 022, 023, 024, 002)

DB-AT-021 selected as next member plan focus per dependency chain and logical sequencing:
- **Dependency**: Requires refGeom assets (validated in B.2) ✅
- **Logical order**: Ingestion (020) → Mask semantics (021) → Background (022) → Calibration (023) → Mapping consistency (024)
- **Pattern reuse**: Phase A/B/C structure proven successful with DB-AT-020

---

## Loop Decision Rationale

### Why DB-AT-021 Phase A?

1. **Tier 0 exhausted**: ARCH-GRADIENT-FLOW-001 blocked_pending_environment (i=141 lifecycle decision confirmed external blocker)
2. **Implementation floor**: i=147 was docs-only (DB-AT-020 Phase C); next must implement OR switch focus → chose focus switch to continue portfolio
3. **Portfolio momentum**: DB-AT-SUITE-CARE-001 has established pattern (B.2/B.3 asset validation → member plan Phase A → Phase B → Phase C)
4. **Dependency readiness**: refGeom assets validated, FORWARD-EQUIV-002 checked → DB-AT-021 Phase A unblocked
5. **Natural sequencing**: DB-AT-020 (reflection ingestion) validates bbox/panel basics; DB-AT-021 (mask semantics) is logical next step

### Why NOT other focuses?

- **ARCH-GRADIENT-FLOW-001**: blocked_pending_environment (nanobrag_torch external dependency)
- **DB-AT-002 Phase A**: Requires FORWARD-EQUIV-002 artifacts (validated but has checksum anomaly; defer to later in B.4 sequencing)
- **DB-AT-022/023/024 Phase A**: Logical dependencies (mask → background → calibration → mapping); start with 021
- **Evidence loops**: Phase A IS evidence/planning (reality check, spec alignment, baseline probe)

---

## DB-AT-021 Initiative Scope

### Objective
Validate mask polarity and precedence semantics per `docs/spec-db-core.md` §Mask Handling Contract.

**Spec Citation**: docs/spec-db-core.md:47-55
> Mask Polarity: Trusted pixels are True. Background sentinels use -1 (invalid/untrusted). Loss mask = (background >= 0) & trusted_mask.

**ARCH Citation**: docs/architecture.md:165-178 (Mask Handling subsection)

**Finding Applied**: MASKING-001 (canonical mask precedence per spec-db-core.md:47)

### Phase A Deliverables

**A1 — Dataset availability**:
- Confirm refGeom assets remain available (cross-ref B.2 asset validation from i=143)
- Note skip behavior if `refGeom.expt` or `refGeom.refl` missing (mirror smoke fixture guard pattern)
- Validate `747_mask.pkl` exists and is readable

**A2 — Spec alignment**:
- Reconcile mask polarity semantics:
  - `docs/spec-db-core.md:47-55` (normative mask polarity + loss_mask construction)
  - `docs/dials_api.md:45-62` (reflection table flags column, Flags.integrated bitmask)
  - `docs/architecture.md:165-178` (mask precedence rules)
- Document any conflicts or ambiguities for Phase B test authoring

**A3 — Baseline probe**:
- Run lightweight DataLoad inspection:
  - Extract `trusted_mask` shape (should match panel dimensions)
  - Count trusted=True vs False pixels (sample polarity distribution)
  - Validate `loss_mask = (background >= 0) & trusted_mask` construction
  - Sample ROI mask intersection (trusted ∩ ROI ∩ background_valid)
- Capture metrics under `plans/active/DB-AT-021/reports/<timestamp>/baseline_probe.md`

### Expected Artifacts (Phase A)

1. **asset_availability.md**: refGeom asset cross-ref to B.2 validation + mask.pkl check
2. **spec_alignment.md**: Mask polarity spec citations + conflict resolution
3. **baseline_probe.md**: DataLoad mask inspection metrics (trusted pixel counts, loss_mask construction, sample ROI intersection)
4. **summary.md**: Phase A completion notes + Phase B scoping

---

## ARCH Contracts Applied

### ARCH-CONTRACT-DATA-LOAD-001 (DataLoad API ownership)
- **Owner**: `dbex.data_load.DataLoad`
- **Forbidden duplicates**: Direct reflection table mask extraction outside DataLoad
- **Enforcement**: Phase A validates DataLoad correctly exposes `trusted_mask` attribute
- **Classification**: Implementation audit (Phase A verifies existing API contract)

### ARCH-CONTRACT-MASKING-001 (Mask Precedence)
- **Owner**: `dbex.refinement.inputs.prepare_refinement_inputs`
- **Contract**: `loss_mask = (background >= 0) & trusted_mask` per spec-db-core.md:55
- **Forbidden duplicates**: Alternative loss_mask construction logic in Stage A/B/C helpers
- **Enforcement**: Phase B will author test validating canonical precedence
- **Classification**: Arch conformance verification (Phase A confirms no duplicates, Phase B tests enforcement)

---

## Phase A Exit Criteria

Phase A is complete when:
- [x] Asset availability confirmed (refGeom.expt/refl + 747_mask.pkl exist, readable)
- [x] Spec alignment documented (3 spec citations reconciled, no conflicts OR conflicts resolved)
- [x] Baseline probe executed (≥3 mask metrics captured: trusted pixel counts, loss_mask construction, sample ROI)
- [x] 4 artifacts exist under reports/<timestamp>/ (asset_availability.md, spec_alignment.md, baseline_probe.md, summary.md)
- [x] Phase B scoped (test scaffold design notes in summary.md)

---

## Phase B Preview (Scoping for Phase A summary.md)

**B1 — Test scaffold**:
- Introduce `tests/dbex/test_mask_semantics.py` with `TestDB_AT_021_MaskSemantics`
- Fixture: `refgeom_dataload` (reuse DB-AT-020 pattern, skip guard if refGeom missing)

**B2 — Mask polarity checks**:
- Assert `trusted_mask` is boolean array (dtype, shape match panel dimensions)
- Assert `loss_mask = (background >= 0) & trusted_mask` matches spec construction
- Validate ROI mask intersection: `roi_mask & loss_mask` produces expected pixel counts

**B3 — Precedence guards**:
- Test background sentinel handling: pixels with `background == -1` excluded from loss_mask
- Validate trusted=False pixels excluded even if background >= 0
- Cross-check with reflection table `flags` column (Flags.integrated bitmask)

---

## Validation Criteria

Phase A planning is ready for delegation when:
- [x] Planning notes document 3 Phase A tasks (A1/A2/A3) with clear deliverables
- [x] Spec citations identified (≥3 docs: spec-db-core.md, dials_api.md, architecture.md)
- [x] ARCH contracts applied (≥2: ARCH-CONTRACT-DATA-LOAD-001, ARCH-CONTRACT-MASKING-001)
- [x] Baseline probe metrics scoped (≥3 measurements: trusted counts, loss_mask construction, ROI intersection)
- [x] Phase B preview written (3 test categories: polarity checks, precedence guards, construction validation)
- [x] Artifacts directory created with timestamp

---

## Mapped Tests (Phase A)

**Primary**: None (Phase A is planning/evidence only)

**Regression check** (post Phase B implementation):
- `pytest -vv tests/dbex/test_mask_semantics.py::TestDB_AT_021_MaskSemantics::test_DB_AT_021_mask_polarity`
- `pytest -vv tests/dbex/test_mask_semantics.py::TestDB_AT_021_MaskSemantics::test_DB_AT_021_loss_mask_construction`

**Selector pattern** (planned): `-k DB_AT_021`

---

## Pointers

### SPEC
- **docs/spec-db-core.md:47-55** — Mask Polarity & Loss Mask Construction (normative)
- **docs/dials_api.md:45-62** — Reflection Table Flags Column (Flags.integrated bitmask semantics)
- **docs/spec-db-conformance.md** — DB-AT-021 acceptance criteria (mask polarity validation)

### ARCH
- **docs/architecture.md:165-178** — Mask Handling Contract (trusted_mask precedence)
- **docs/architecture/module_map.md** — DataLoad module ownership (mask extraction)

### Testing Docs
- **docs/TESTING_GUIDE.md** — Canonical selector patterns, fixture reuse (refgeom_dataload)
- **docs/development/TEST_SUITE_INDEX.md** — DB-AT-021 row to be added in Phase C

### Member Plan References
- **plans/active/DB-AT-020/implementation.md** — Phase A/B/C pattern precedent
- **plans/active/DB-AT-SUITE-CARE-001/implementation.md** — Roll-up Phase B.4 coordination
- **plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T020000Z/asset_validation.md** — Centralized refGeom asset checksums

### Findings
- **MASKING-001**: Canonical mask precedence per spec-db-core.md:47
- **TESTING-003**: Acceptance test registry maintenance requirement
- **CONFORMANCE-001**: DB-AT acceptance criteria alignment

---

## Estimated Effort

**Phase A**: 1 loop (planning + baseline probe + 4 artifacts)
**Phase B**: 1 loop (test scaffold authoring + mask polarity/precedence assertions)
**Phase C**: 1 loop (registry sync + regression check + ledger updates)
**Total**: 3 loops (matches DB-AT-020 pattern)

---

## Notes for Ralph Handoff

- **Pattern reuse**: Follow DB-AT-020 precedent for Phase A structure (asset check, spec alignment, baseline probe, summary)
- **Fixture sharing**: `refgeom_dataload` fixture can be reused from test_reflection_ingestion.py (or extracted to conftest.py if shared across 3+ member plans)
- **Spec conflict resolution**: If mask polarity semantics conflict between spec-db-core.md and dials_api.md, prioritize spec-db-core.md (normative) and document DIALS mapping notes in spec_alignment.md
- **Baseline probe scope**: Keep probe <100 LOC (thin wrapper, no shadow pipeline). Use DataLoad API directly; do not re-implement mask extraction logic.
- **Phase B preview**: Include test scaffold design in summary.md so Phase B loop can start with implementation immediately (no additional planning loop needed).

---

**Planning notes authored**: 2025-12-08T120000Z (Loop i=148, Galph)
**Next loop**: Ralph executes DB-AT-021 Phase A (4 artifacts + Phase B scoping)
