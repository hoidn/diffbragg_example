# Loop i=148 — DB-AT-021 Phase A (Mask Semantics Guard Reality Check)

## Summary
Execute DB-AT-021 Phase A reality check: validate refGeom asset availability (cross-ref DB-AT-SUITE-CARE-001 Phase B.2), reconcile mask polarity semantics across 3 spec docs, run baseline DataLoad probe (trusted_mask counts, loss_mask construction, ROI intersection), and scope Phase B test scaffold.

## Mode
none (planning/evidence — no production code edits, no test authoring this loop)

## ActionType
planning

## DecisionStatus
exploring (first Phase A for DB-AT-021; reality check + baseline metrics to ground Phase B assertions)

## InitiativeType
harness

## Focus
DB-AT-021 — Mask Semantics Guard (member plan of DB-AT-SUITE-CARE-001 roll-up)

## Branch
integration

## Mapped tests
None (Phase A is planning/evidence only; Phase B will author tests/dbex/test_mask_semantics.py)

## Artifacts
`plans/active/DB-AT-021/reports/2025-12-08T120000Z/`

## Findings Applied (Mandatory)

**MASKING-001** (Canonical mask precedence per spec-db-core.md:47):
- **Code**: `dbex/data_load.py` (trusted_mask extraction), `dbex/refinement/inputs.py` (loss_mask = (background >= 0) & trusted_mask)
- **Adherence**: Phase A validates DataLoad correctly exposes trusted_mask attribute; baseline probe confirms loss_mask construction matches spec; Phase B will author enforcement test.

**TESTING-003** (Acceptance test registry maintenance):
- **Code**: `docs/development/TEST_SUITE_INDEX.md` (status table rows for DB-AT-XXX selectors)
- **Adherence**: Phase C will update TEST_SUITE_INDEX.md with DB-AT-021 row (deferred to Phase C per Phase A/B/C pattern).

**CONFORMANCE-001** (DB-AT acceptance criteria alignment):
- **Code**: `docs/spec-db-conformance.md` (DB-AT-021 mask polarity validation criteria)
- **Adherence**: Phase A spec alignment task (A2) reconciles spec-db-conformance.md acceptance criteria with spec-db-core.md normative polarity rules.

**RUNTIME-001** (Runtime execution guardrails):
- **Code**: `docs/TESTING_GUIDE.md` (canonical environment flags for acceptance tests)
- **Adherence**: Phase B test scaffold will follow TESTING_GUIDE.md selector patterns (KMP_DUPLICATE_LIB_OK=TRUE, DBEX_SMOKE_DETECTOR_SIZE=full).

## Pointers

### SPEC
- **docs/spec-db-core.md:47-55** — Mask Polarity & Loss Mask Construction (normative)
- **docs/dials_api.md:45-62** — Reflection Table Flags Column (Flags.integrated bitmask semantics)
- **docs/spec-db-conformance.md** — DB-AT-021 acceptance criteria

### ARCH
- **docs/architecture.md:165-178** — Mask Handling Contract (trusted_mask precedence)
- **docs/architecture/module_map.md** — DataLoad module ownership

### Testing Docs
- **docs/TESTING_GUIDE.md** — Canonical selector patterns, fixture reuse
- **docs/development/TEST_SUITE_INDEX.md** — Test registry (DB-AT-021 row to be added in Phase C)

### Member Plan References
- **plans/active/DB-AT-021/implementation.md** — Phase A/B/C checklist (just authored this loop)
- **plans/active/DB-AT-SUITE-CARE-001/implementation.md** — Roll-up Phase B.4 coordination
- **plans/active/DB-AT-020/implementation.md** — Phase A precedent (reality check pattern)
- **plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T020000Z/asset_validation.md** — Centralized refGeom asset checksums (cross-ref for A1)

## ARCH Contracts (mandatory)

**ARCH-CONTRACT-DATA-LOAD-001** (DataLoad API ownership):
- **Owner module/API**: `dbex.data_load.DataLoad` (owns reflection table → trusted_mask extraction)
- **Forbidden duplicates**: Direct `.refl` file mask extraction outside DataLoad
- **Classification**: Implementation audit (Phase A verifies DataLoad correctly exposes trusted_mask attribute; no duplicates expected)

**ARCH-CONTRACT-MASKING-001** (Mask Precedence):
- **Owner module/API**: `dbex.refinement.inputs.prepare_refinement_inputs` (owns canonical loss_mask construction per spec-db-core.md:55)
- **Forbidden duplicates**: Alternative `loss_mask` construction logic in Stage A/B/C helpers or test harness
- **Classification**: Arch conformance verification (Phase A confirms no duplicates; Phase B will author enforcement test validating canonical construction)

## Do Now (hard validity contract)

**Focus**: DB-AT-021 — Mask Semantics Guard (Phase A)

**Implement**: Planning only (no production code edits this loop)

**Validating pytest**: None (Phase A is planning/evidence; Phase B will author tests/dbex/test_mask_semantics.py)

**Artifacts path**: `plans/active/DB-AT-021/reports/2025-12-08T120000Z/`

**Initiative type**: harness

**Phase A Deliverables** (4 artifacts):

1. **asset_availability.md**:
   - Cross-reference DB-AT-SUITE-CARE-001 Phase B.2 asset validation (i=143) for refGeom.expt/refl checksums
   - Validate `747_mask.pkl` exists at repo root (file size, readability check)
   - Document skip behavior if assets missing (mirror DB-AT-020 smoke fixture guard)

2. **spec_alignment.md**:
   - Reconcile mask polarity semantics across 3 docs:
     - `docs/spec-db-core.md:47-55` (normative: trusted=True, background sentinel=-1, loss_mask construction)
     - `docs/dials_api.md:45-62` (Flags.integrated bitmask mapping to trusted_mask)
     - `docs/architecture.md:165-178` (mask precedence rules: trusted ∩ ROI ∩ background_valid)
   - Identify conflicts OR confirm alignment
   - Document ARCH-CONTRACT-MASKING-001 canonical owner (prepare_refinement_inputs)

3. **baseline_probe.md**:
   - Run lightweight DataLoad inspection (use existing `refGeom.expt`, `refGeom.refl`, `747_mask.pkl`):
     ```python
     from dbex.data_load import DataLoad
     dl = DataLoad("refGeom.expt", "refGeom.refl", "scaled.mtz", "747_mask.pkl")
     # Metrics:
     # - trusted_mask.shape (should match panel dimensions from expt)
     # - trusted_mask.dtype (should be bool)
     # - Trusted pixel counts: np.sum(dl.trusted_mask), np.sum(~dl.trusted_mask)
     # - loss_mask construction: loss_mask = (dl.background_image >= 0) & dl.trusted_mask
     # - Sample ROI intersection: Pick ROI 0, compute trusted ∩ ROI ∩ background_valid
     ```
   - Capture ≥3 metrics: trusted counts, loss_mask construction validation, sample ROI pixel count
   - Thin wrapper rule: Keep probe <100 LOC, call DataLoad API directly

4. **summary.md**:
   - Phase A completion notes (A1/A2/A3 status)
   - Key findings (asset status, spec conflicts if any, baseline metrics)
   - **Phase B scoping**: Test scaffold design (TestDB_AT_021_MaskSemantics, 3 test methods: polarity checks, loss_mask construction, precedence guards)
   - Next loop preview (Phase B implementation)

**Touched**: DB-AT-021 Phase A (A1, A2, A3)

## Forbidden This Loop

- No production code edits (`dbex/`, `tests/` implementation files)
- No test authoring (deferred to Phase B)
- No registry updates (deferred to Phase C)
- No fix_plan.md Attempts History updates until Phase A complete

## How-To Map

### Asset Availability Check (A1)
```bash
# Cross-reference B.2 validation
cat plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T020000Z/asset_validation.md

# Validate 747_mask.pkl
ls -lh 747_mask.pkl
file 747_mask.pkl

# Document in asset_availability.md
```

### Spec Alignment (A2)
```bash
# Read 3 spec sections
cat docs/spec-db-core.md | sed -n '47,55p'  # Mask polarity normative
cat docs/dials_api.md | sed -n '45,62p'     # Flags.integrated bitmask
cat docs/architecture.md | sed -n '165,178p' # Mask precedence

# Reconcile in spec_alignment.md
```

### Baseline Probe (A3)
```python
# Thin wrapper probe script (save as plans/active/DB-AT-021/reports/2025-12-08T120000Z/baseline_probe.py)
import numpy as np
from dbex.data_load import DataLoad

# Load canonical assets
dl = DataLoad("refGeom.expt", "refGeom.refl", "scaled.mtz", "747_mask.pkl")

# Metrics
metrics = {
    "trusted_mask_shape": dl.trusted_mask.shape,
    "trusted_mask_dtype": dl.trusted_mask.dtype,
    "trusted_pixel_count": int(np.sum(dl.trusted_mask)),
    "untrusted_pixel_count": int(np.sum(~dl.trusted_mask)),
    "loss_mask_construction_formula": "(background >= 0) & trusted_mask",
    "loss_mask_pixel_count": int(np.sum((dl.background_image >= 0) & dl.trusted_mask)),
    "sample_roi_index": 0,
    "sample_roi_trusted_pixels": int(np.sum(dl.trusted_mask[dl.pids[0],
                                                             dl.roi_bboxes[0,1]:dl.roi_bboxes[0,3],
                                                             dl.roi_bboxes[0,0]:dl.roi_bboxes[0,2]]))
}

# Write to baseline_probe.md
with open("plans/active/DB-AT-021/reports/2025-12-08T120000Z/baseline_probe.md", "w") as f:
    f.write("# DB-AT-021 Phase A Baseline Probe\n\n")
    for k, v in metrics.items():
        f.write(f"- **{k}**: {v}\n")
```

Run probe:
```bash
cd /home/ollie/Documents/diffbragg_example
python plans/active/DB-AT-021/reports/2025-12-08T120000Z/baseline_probe.py
```

## Pitfalls To Avoid

1. **Type discipline**: Do not author tests in Phase A (harness type, planning phase) — defer to Phase B
2. **Spec conflicts**: If mask polarity semantics conflict between spec-db-core.md and dials_api.md, prioritize spec-db-core.md (normative) and document DIALS mapping notes
3. **Shadow pipeline guard**: Keep baseline probe <100 LOC; call DataLoad API directly; do not re-implement mask extraction logic
4. **Fixture sharing**: Note in summary.md that `refgeom_dataload` fixture can be reused from test_reflection_ingestion.py (or extract to conftest.py if shared across 3+ member plans)
5. **Asset cross-ref**: Use DB-AT-SUITE-CARE-001 Phase B.2 checksums (i=143) for refGeom.expt/refl; do not recompute
6. **Skip guard**: Document that Phase B tests must skip when assets missing (mirror DB-AT-020 pattern)
7. **No fix_plan updates**: Phase A Attempts History appended in Phase C only (after full member plan closure)
8. **PROBE-FREEZE-001**: Baseline probe must be thin wrapper (<100 LOC); if it exceeds, switch to manual inspection + notes in baseline_probe.md

## If Blocked

**Asset unavailable**:
- Cross-check DB-AT-SUITE-CARE-001 Phase B.2 validation (i=143) — assets were VALID 5 loops ago
- If missing, mark DB-AT-021 blocked_pending_asset_regeneration and escalate to DB-AT-SUITE-CARE-001 coordination

**Spec conflicts**:
- Prioritize spec-db-core.md (normative)
- Document conflict in spec_alignment.md with hypothesis for resolution
- Flag for supervisor review in summary.md

**Probe failures**:
- If DataLoad raises errors, capture error signature in baseline_probe.md
- Mark Phase A blocked_pending_dataload_fix and escalate to ARCH-CONTRACT-DATA-LOAD-001 conformance review

## Doc Sync Plan (Conditional)

Not applicable (Phase A does not modify tests; registry updates deferred to Phase C).

---

**Input authored**: 2025-12-08T120000Z (Loop i=148, Galph)
**Next loop actor**: Ralph (executes Phase A tasks, produces 4 artifacts, scopes Phase B)
