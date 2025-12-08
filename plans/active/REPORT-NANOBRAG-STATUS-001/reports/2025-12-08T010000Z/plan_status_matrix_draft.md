# Plan-vs-Status Matrix (Draft)

**Date:** 2025-12-08T010000Z
**Initiative:** REPORT-NANOBRAG-STATUS-001 Phase A
**Source:** `plans/nanobrag_integration_plan.md`, `docs/fix_plan.md`

## Integration Plan Phases (per `plans/nanobrag_integration_plan.md`)

| Phase | Description | Status | Evidence | Notes |
|-------|-------------|--------|----------|-------|
| **Phase 0** | Environment & Baseline | **Done** | `TESTING_GUIDE.md` env flags documented | Runtime flags (`KMP_DUPLICATE_LIB_OK`, etc.) established |
| **Phase 1** | Data Preparation Bridge | **Done** | `dbex/nanobrag_bridge.py`, `dbex/refinement/` | DataLoad → tensor conversion, config construction |
| **Phase 2** | PyTorch Model & Parameterization | **Done** | `dbex/torch_model.py`, `dbex/refinement/engine.py` | `NanoBraggRefinementModel`, forward pass implemented |
| **Phase 3** | Training Schedule & Loss | **Partial** | Stage A PASS; Stage B/C have regressions | Variance-weighted loss implemented; Stage C chi² drift |
| **Phase 4** | CLI Integration & Output | **Done** | `dbex.refine_one --backend nanobrag` | HDF5 output with `/torch_diagnostics` group |
| **Phase 5** | Validation & Documentation | **In Progress** | This initiative | Missing final validation report |

## Stage Refinement Status (per `docs/spec-db-workflow.md`)

| Stage | Description | Status | Evidence | Notes |
|-------|-------------|--------|----------|-------|
| **Stage A** | Crystal + scale refinement | **Done** | Loss traces in HDF5; telemetry shows convergence | 981638→979335 loss over 10 iterations |
| **Stage B** | Structure factor refinement | **Partial** | Per-reflection mode operational (`TORCH-REFINE-004`) | Shell mode fallback preserved |
| **Stage C** | Detector refinement | **Blocked** | `PERF-WARM-SIM-001` blocked | +0.067% χ² regression vs Stage A |

## Tier Status Summary (per `docs/fix_plan.md`)

### Tier 0: Refinement Architecture Finish
| Initiative | Status | Notes |
|------------|--------|-------|
| ARCH-GRADIENT-FLOW-001 | blocked_pending_upstream | Jacobian mismatch escalated to nanobrag_torch |
| ARCH-IMPL-CONFORMANCE-001 | done | Contract alignment complete |
| DIAG-NANOBRAGG-OVERSAMPLE-001 | done | Oversample diagnostics closed |
| ARCH-SIM-HKL-BOUNDS-001 | done | HKL coverage restored |
| ARCH-SIM-CONSTRUCTION-001 | blocked_pending_environment | SQUARE scaling resolved; N_cells threading pending |
| ARCH-PROBE-FREEZE-001 | done | Probe freeze policy enforced |
| ARCH-REFACTOR-001 | blocked_pending_architecture | Phase D.3 blocked |
| SPEC-SQUARE-PARTIALITY-001 | done | SQUARE lattice physics clarified |

### Tier 1: Core Physics & Stability
| Initiative | Status | Notes |
|------------|--------|-------|
| PHYSICS-LOSS-001 | done_with_environment_caveat | Variance-weighted loss parity |
| TORCH-GEOMETRY-SYNC-001 | done | Geometry convergence verified |
| RUNTIME-VEC-001 | done | Vectorization checklist enforced |
| NANOBRAG-GOLDEN-001 | done | Golden dataset captured |

### Tier 2/3: Architectural Maturity
| Initiative | Status | Notes |
|------------|--------|-------|
| ARCH-REFINE-FLOW-001 | done | Protocol Engine operational |
| TORCH-API-ALIGN-001 | done | ExperimentModel, factory unification |
| TORCH-REFINE-004 | done | Stage B per-reflection mode |
| PERF-WARM-SIM-001 | blocked | Stage C chi² regression |
| ARCH-STAGE-CONTEXT-001 | done | Stage context boundaries |

## Test Suite Status

| Category | Count | Status |
|----------|-------|--------|
| `tests/dbex/` collected | 174 | Collection OK |
| Stage A smoke | PASS | Per `TESTING_GUIDE.md` |
| Stage B smoke | PASS | Shell mode + per-reflection |
| Stage C smoke | PARTIAL | Chi² tolerance drift |
| DB-AT acceptance | MIXED | 14 PASS, 1 skip, some blocked |

## Telemetry Coverage Gap Analysis

| Field (per `docs/spec-db-core.md`) | Present in HDF5 | Notes |
|-----------------------------------|-----------------|-------|
| `refine_loss_trace_full` | Yes | Structured dtype (iteration, loss) |
| `refine_loss_trace_sample` | Yes | Per-iteration samples |
| `canonical_detector_distances_mm` | Yes | In `stage_a_refinement.h5` |
| `param_deltas` | **No** | Not captured in current telemetry |
| `optimizer_config` | **No** | Learning rate, type not persisted |
| `hkl_source` | **No** | MTZ provenance not tracked |
| `forward_time_ms` | **No** | Perf telemetry not in examined files |
| `roi_count_*` | **No** | ROI count metrics not persisted |
| `cache_mode` | **No** | Cache state not persisted |

## Open Blockers Summary

1. **ARCH-GRADIENT-FLOW-001** — Jacobian magnitude mismatch (~640×) in `nanobrag_torch` crystal computations; escalated upstream
2. **PERF-WARM-SIM-001** — Stage C panel-loss divergence causes +0.067% χ² regression
3. **ARCH-SIM-CONSTRUCTION-001** — N_cells threading and cold-path reconstruction parity pending

## Recommendations for Phase B

1. **Extract loss traces** from selected HDF5 → loss convergence table/plot
2. **Document telemetry gaps** → recommend spec additions for param_deltas, optimizer_config
3. **Cross-reference Stage C regression** → link to PERF-WARM-SIM-001 artifacts
4. **Finalize `reports/nanobrag_validation.md`** → meeting-ready summary
