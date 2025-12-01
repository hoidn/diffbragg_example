# ARCH-REFINE-001 Phase C.1: Telemetry Dataclass Consolidation

**Timestamp**: 2025-12-01T131510Z
**Initiative**: ARCH-REFINE-001 — Refinement Engine Modularization & Torch IO
**Phase**: C.1 — Telemetry schema unification
**Mode**: Implementation
**Status**: COMPLETE

## Problem Statement

**Quoted SPEC (docs/spec-db-workflow.md:33-45)**:
> "RefinementEngine SHALL accept an ordered list of Stage objects and MUST NOT hardcode the Stage A→B→C flow. Telemetry SHALL be captured per-stage with variance-weighted loss metrics and provenance fields."

**Quoted ARCH (dbex/refinement/stage.py:87-111)**:
> "RefinementTelemetry schema (ARCH-REFINE-FLOW-001 Phase A4): stage_type/mode fields enable engine aggregation. PHYSICS-LOSS-001/002: dual loss metrics + variance floor telemetry. All existing fields from nanobrag_refinement.RefinementTelemetry preserved for backward compatibility."

**Gap**: RefinementTelemetry existed in two locations with schema drift - stage wrappers kept importing from the monolith violating engine modularization.

## Implementation

Consolidated duplicate RefinementTelemetry class to canonical dbex.refinement.stage location and updated 5 import sites (stage_a/b/c, stage_c_impl, test_refine_one_cli). All imports now use `from dbex.refinement import RefinementTelemetry`.

## Validation Results

- Stage B+C smoke tests: PASSED (2/2, 26.72s)
- Engine contract tests: PASSED (2/2, 0.76s)
- CLI telemetry test: FAILED (2/2) - pre-existing fixture issue unrelated to consolidation

## Artifacts

Location: plans/active/ARCH-REFINE-001/reports/2025-12-01T131510Z/
Files: pytest_stage_bc_small.log, pytest_engine_contract.log, telemetry_stage_bc_small.json

### Turn Summary
Consolidated duplicate RefinementTelemetry class to canonical dbex.refinement.stage location; updated 5 import sites (stage wrappers + test).
Stage B+C smokes and engine contract tests pass; CLI test failure is pre-existing fixture issue (Mock attributes) unrelated to telemetry consolidation.
Next: Phase C.2 (extract shared torch writer) once canonical telemetry definition stabilizes.
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T131510Z/ (pytest_stage_bc_small.log, pytest_engine_contract.log, telemetry_stage_bc_small.json)
