# Dependency Chain Analysis (DB-AT-SUITE-CARE-001 Phase A)

**Date**: 2025-12-07T024500Z
**Scope**: Inter-initiative dependencies and critical path for 7 DB-AT acceptance test initiatives

## Dependency Graph

```
External Dependencies:
  ├─ FORWARD-EQUIV-002 artifacts → DB-AT-002 (determinism baselines)
  └─ Canonical refGeom assets (shared)
      ├─ refGeom.expt
      ├─ refGeom.refl
      ├─ scaled.mtz
      └─ 747_mask.pkl

Shared Implementation Dependencies:
  ├─ dbex.data_load.DataLoad → DB-AT-020, 021, 022, 023, 024
  ├─ dbex.nanobrag_bridge.prepare_refinement_inputs → DB-AT-021, 022, 023, 024
  ├─ dbex.nanobrag_bridge (torch helpers) → DB-AT-010
  └─ dbex.refine_one CLI/backend → DB-AT-023, 024

Logical Sequencing (Phase B):
  DB-AT-002 (standalone: determinism env + fixtures)
  DB-AT-010 (standalone: gradcheck; BLOCKED on Phase D regression fix)

  Workflow Integration Cluster (parallel Phase A; sequential Phase B recommended):
    DB-AT-020 (bbox/ROI ingestion)
      ↓ (informs but not blocking)
    DB-AT-021 (mask polarity/shape) ────┐
      ↓                                  ├─→ DB-AT-022 (sentinel guard)
    DB-AT-023 (ADU/photon calibration) ─┘
      ↓ (helper extraction shared context)
    DB-AT-024 (mapping consistency)
```

## Critical Path Analysis

### Tier 0 (Blocking All)
- **DB-AT-010 Phase D regression fix** (gradcheck `crystal_cell_a` failure)
  - **Impact**: Blocks Gradient-Safe conformance profile certification
  - **Blocker type**: Hard gate violation (gradcheck is normative)
  - **Estimated effort**: 1-2 loops (audit TorchCrystal override path, patch `.item()` coercion, re-run gradcheck with eps=1e-6/atol=1e-5/rtol=0.05, update ledger)
  - **Escalation status**: Documented in DB-AT-010/reports/2025-11-04T232350Z/summary.md; requires immediate attention before portfolio closure

### Tier 1 (External Dependencies)
- **FORWARD-EQUIV-002 artifacts availability** (DB-AT-002 dependency)
  - **Location**: `tests/fixtures/golden_data/simple_cubic/` with manifest checksum `2d1f8d67…8567aee`
  - **Status**: Unchecked (DB-AT-002 Phase A1 task)
  - **Blocker type**: Soft (can proceed with Phase A verification; Phase B blocked if missing)
  - **Mitigation**: DB-AT-002 Phase A1 confirms existence; if missing, escalate to FORWARD-EQUIV-002 owner or generate new golden suite

- **Canonical refGeom assets availability** (shared by DB-AT-020/021/022/023/024)
  - **Files**: `refGeom.expt`, `refGeom.refl`, `scaled.mtz`, `747_mask.pkl`
  - **Status**: Unchecked (each plan's Phase A1 verifies independently)
  - **Blocker type**: Soft (Phase A can document gaps; Phase B blocked if assets missing)
  - **Mitigation**: Centralize asset validation in roll-up Phase B loop; if missing, coordinate with data provisioning or use alternative dataset

### Tier 2 (Workflow Integration Cluster Sequencing)
- **DB-AT-020 (Reflection Ingestion) → DB-AT-021/022** (logical but not hard dependency)
  - **Reason**: bbox/ROI semantics inform mask and sentinel coverage expectations
  - **Recommendation**: Execute DB-AT-020 Phase B first; results provide baseline for 021/022 Phase A probes
  - **Parallel option**: All 3 can run Phase A concurrently (asset checks independent); sequence only Phase B implementation

- **DB-AT-021 (Mask) + DB-AT-023 (Calibration) → DB-AT-022 (Sentinel)** (soft dependency)
  - **Reason**: DB-AT-022 sentinel guard validates `background_image` semantics downstream of mask polarity and calibration representation; `prepare_refinement_inputs` is the consumption site
  - **Recommendation**: Complete 021 and 023 Phase B before 022 Phase B; ensures `prepare_refinement_inputs` signature stable
  - **Parallel option**: Phase A for all 3 can run concurrently

- **DB-AT-024 (Mapping) helper extraction informs DB-AT-023 (Calibration)** (code-sharing opportunity)
  - **Reason**: DB-AT-024 Phase B1 extracts `simulate_forward_once` helper returning `(bragg, target_adu, target_photons, ...)` without HDF5; this helper should handle ADU/photon representation cleanly, providing reference for 023's photon conversion path
  - **Recommendation**: Execute 024 Phase B1 (helper extraction) before or in parallel with 023 Phase B1 (CLI arg + conversion wiring); coordinate to avoid duplicate photon-conversion logic
  - **Risk**: If 024 and 023 implement conversion independently, may diverge; centralize in `prepare_refinement_inputs` and have both tests consume it

### Tier 3 (Independent / Parallel)
- **DB-AT-002 (Determinism)**: No inbound dependencies after FORWARD-EQUIV-002 artifact check; can run all phases independently
- **DB-AT-010 (Gradcheck)**: Phase D unblocking is independent of other plans (requires only TorchCrystal bridge audit)

## External Dependency Details

### FORWARD-EQUIV-002 Artifacts
- **Required by**: DB-AT-002 Phase A1
- **Artifact type**: Canonical tensors + metrics baselines for determinism parity
- **Location**: `tests/fixtures/golden_data/simple_cubic/` with manifest checksum `2d1f8d67…8567aee`
- **Validation task**: DB-AT-002 Phase A1 must confirm existence and checksum; if missing, escalate to FORWARD-EQUIV-002 owner or regenerate golden suite
- **Risk**: If FORWARD-EQUIV-002 was a historical plan and artifacts were not committed, DB-AT-002 must either wait for regeneration or use alternative determinism baseline (e.g., self-parity with different seeds)

### Canonical refGeom Assets
- **Required by**: DB-AT-020, 021, 022, 023, 024 (5 plans share this dependency)
- **Files**:
  - `refGeom.expt` (DIALS experiment model: detector, beam, crystal geometry)
  - `refGeom.refl` (DIALS reflection table: bbox, panel IDs, miller indices)
  - `scaled.mtz` (structure factor amplitudes: H, K, L, F, SIGF)
  - `747_mask.pkl` (trusted pixel mask: [panel, slow, fast] boolean array)
- **Current location**: Not specified in member plan docs (likely workspace root or `tests/fixtures/`; each Phase A1 must confirm)
- **Validation task**: Each plan Phase A1 includes asset availability check (`ls -lh` snapshot in reports); recommend centralizing into roll-up Phase B artifact
- **Risk**: If assets missing or misplaced, all 5 plans block at Phase A/B transition; mitigation is to provision assets or create synthetic minimal dataset for smoke tests

### SPEC/ARCH Normative Dependencies
- **spec-db-core.md**: Defines mask polarity (021), bbox exclusivity (020), background sentinel semantics (022), HKL interpolation (024/025)
- **spec-db-workflow.md**: Defines calibration policy (023), Stage A/B/C flow (024/027/028/029)
- **spec-db-conformance.md**: Acceptance criteria and thresholds for all DB-AT selectors
- **dials_api.md**, **config_crosswalk.md**: DIALS data model mappings (bbox, panel ordering, beam center conventions) for 020/021
- **testing_strategy.md §2.7**: Determinism thresholds (same-seed corr ≥0.9999999, diff-seed corr ≤0.7, ≥50% differing pixels) for DB-AT-002
- **TESTING_GUIDE.md**: Canonical selector patterns, environment flags (`KMP_DUPLICATE_LIB_OK=TRUE`, `NANOBRAGG_DISABLE_COMPILE=1`), artifact expectations

All member plans reference these docs in their implementation.md Pointers sections; roll-up Phase B must ensure no contradictions between member plan expectations and SPEC/ARCH.

## Priority Ordering Recommendation

### Immediate (Loop i=131+1)
1. **DB-AT-010 Phase D** (unblock Gradient-Safe profile; Tier 0)
2. **Centralized asset validation** (create shared artifact for refGeom availability check; unblocks 5 plans' Phase A→B transition)

### Short-term (Loops i=131+2 to i=131+4)
3. **DB-AT-002 Phase A** (FORWARD-EQUIV-002 artifact check + env rehearsal + metric spec alignment)
4. **DB-AT-020/021/023/024 Phase A** (parallel: asset checks + baseline probes; 4 loops or 1 batched loop)

### Medium-term (Loops i=131+5 to i=131+9)
5. **DB-AT-020 Phase B** (bbox/ROI test authoring; 1 loop)
6. **DB-AT-024 Phase B1** (helper extraction; 1 loop) + **DB-AT-023 Phase B1** (CLI arg + conversion; parallel or sequential)
7. **DB-AT-021 Phase B** (mask polarity test authoring; 1 loop)
8. **DB-AT-022 Phase B** (sentinel guard test authoring; 1 loop)
9. **DB-AT-002 Phase B** (determinism harness authoring; 1 loop)

### Long-term (Loops i=131+10 to i=131+12)
10. **All plans Phase C** (docs/registry sync; can batch into 1-2 loops after Phase B completion)

### Alternative: Batched Phase B Test Authoring Sprint
If supervisor prioritizes portfolio velocity, execute Phase A for all pending plans (002, 020, 021, 022, 023) in parallel, then batch Phase B test authoring into a single focused loop per plan or even a multi-plan loop if tests are structurally similar (e.g., 020/021/022 all validate DataLoad/bridge contracts and can share fixture patterns).

## Risk Register

| Risk ID | Description | Impact | Mitigation |
|---------|-------------|--------|------------|
| DEP-001 | FORWARD-EQUIV-002 artifacts missing or checksum mismatch | DB-AT-002 blocked at Phase A/B transition | Escalate to FORWARD-EQUIV-002 owner; if unavailable, regenerate golden suite or use self-parity baseline |
| DEP-002 | Canonical refGeom assets missing or incomplete | 5 plans (020/021/022/023/024) blocked at Phase A/B transition | Centralize asset provisioning; create synthetic minimal dataset if production assets unavailable |
| DEP-003 | DB-AT-010 Phase D regression not fixed | Gradient-Safe conformance profile cannot be certified; portfolio closure blocked | Escalate as Tier-0 priority; allocate dedicated loop(s) for TorchCrystal bridge audit and gradcheck fix |
| DEP-004 | Divergent photon-conversion implementations in DB-AT-023 and DB-AT-024 | Code duplication, maintenance burden, potential semantic drift between calibration and mapping paths | Coordinate 023/024 Phase B implementations; centralize photon conversion in `prepare_refinement_inputs`; cross-validate with shared test fixture |
| DEP-005 | `prepare_refinement_inputs` signature instability during parallel Phase B work | DB-AT-021, 022, 023, 024 all modify or extend `prepare_refinement_inputs`; concurrent edits risk merge conflicts and semantic drift | Sequence Phase B implementations (020 → 021 → 023/024 || 022) or batch into single loop with coordinated signature extension |
| DEP-006 | TEST_SUITE_INDEX.md registry drift during multi-plan Phase C | 7 plans update registry concurrently; merge conflicts and stale status entries | Defer all Phase C registry sync to a single batched loop after all Phase B implementations land; use fix_plan.md Attempts History as source of truth during Phase B |

## Next Steps

1. Review dependency graph with supervisor to confirm priority ordering
2. Execute Tier-0 unblocking (DB-AT-010 Phase D) before advancing other plans
3. Execute centralized asset validation artifact to derisk Phase A→B transitions
4. Sequence or parallelize Phase A/B work based on resource availability and code-change coordination needs

---

**Dependency analysis completed**: 2025-12-07T024500Z
**Next artifact**: exit_criteria.md
