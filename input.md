# Input for Ralph (Loop i=128)

## Summary
Plan MAP-SCALE-003 Phase A telemetry design: audit current CLI diagnostics schema, trace refined MTZ loading path, define structure-factor telemetry contract, confirm downstream consumer compatibility.

## Mode
Docs

## ActionType
planning

## DecisionStatus
exploring

## InitiativeType
spec_change

## Focus
MAP-SCALE-SYNC-001 — Calibration Ladder Synchronization (MAP-SCALE-001—005)

**Current member focus**: MAP-SCALE-003 (CLI Refined Structure Factor Telemetry) Phase A

## Branch
integration

## Mapped tests
none — planning loop (Phase A design audit, no production changes)

## Artifacts
plans/active/MAP-SCALE-003/reports/2025-12-07T150000Z/

## Findings Applied (Mandatory)
**Relevant findings**:
- **SCALE-003**: Zero-iteration helper must ingest DiffBragg-refined √spot_scale + refined |F| amplitudes (dbex/nanobrag_bridge.py:843-1106). Governs telemetry design: must surface refined vs raw MTZ provenance.
- **SCALE-004**: CLI calibration plumbing must propagate refined structure-factor path (dbex/refine_one.py, --refined-mtz flag). Governs telemetry hook points: refined MTZ loading → build_structure_factor_grid.
- **SCALE-006**: Telemetry must capture calibration metadata provenance (spot_scale, beam flux, N_cells). Governs schema: hkl_source, reflection count, mean amplitude, MTZ path fields required.
- **SCALE-007**: Silent fallback from refined to raw MTZ violates spec-db-tracing.md §2; telemetry must enforce refined-request → refined-telemetry contract. Governs Phase C deliverable (MAP-SCALE-005 enforcement).
- **TESTING-003**: Selector status transitions require pytest --collect-only confirmation. Governs artifact expectations: collect-only logs must validate telemetry test discoverability.

**No relevant findings**: None (all SCALE findings apply to calibration telemetry contract design)

## Pointers

**SPEC**:
- docs/spec-db-workflow.md:125-158 — Calibration & Unit Conventions (spot_scale, refined MTZ, sample clipping precedence)
- docs/spec-db-tracing.md:85-120 — Torch diagnostics artifact expectations (telemetry schema, provenance requirements)
- docs/config_crosswalk.md:75-95 — Structure-factor parameter mapping (refined vs raw MTZ, HKL ingestion)

**ARCH**:
- docs/architecture/calibration_scaling.md:45-78 — Calibration threading (torch_config precedence, spot_scale_override, refined MTZ path)
- docs/architecture/dbex/io/writer.idl.md:55-85 — Writer diagnostics contract (HDF5 /torch_diagnostics group schema)

**TESTING**:
- docs/TESTING_GUIDE.md:125-145 — CLI regression selectors (test_nanobrag_backend_runs_simulator, DB-AT-024 mapping)
- docs/development/TEST_SUITE_INDEX.md:85-105 — Selector registry (MAP-SCALE-002/004 completion status)

**IMPLEMENTATION**:
- plans/active/MAP-SCALE-003/implementation.md:1-39 — Phase A/B/C breakdown (telemetry design → implementation → documentation)
- plans/active/MAP-SCALE-002/implementation.md:25-36 — CLI plumbing context (--refined-mtz, load_calibration_metadata, apply_n_cells)
- plans/active/MAP-SCALE-004/implementation.md:26-34 — Zero-iteration telemetry precedent (simulate_forward_once diagnostics payload)

## ARCH Contracts (mandatory)

**Relevant ARCH-CONTRACTs**:

1. **ARCH-CONTRACT-CALIBRATION-001** (Calibration Metadata Threading)
   - **Owner module**: `dbex/io/calibration.py::load_calibration_metadata` (canonical loader)
   - **Consumer contracts**:
     - `dbex/refine_one.py::run_nanobrag_backend` (CLI backend, --torch-config ingestion)
     - `dbex/nanobrag_bridge.py::simulate_forward_once` (zero-iteration helper)
     - `dbex/refinement/config.py::RefinementConfig` (calibration_metadata field)
   - **Invariant**: Calibration metadata (spot_scale_override, beam flux, N_cells) must flow CLI → backend → simulator without silent fallback to defaults
   - **Telemetry requirement**: Provenance tracking required per spec-db-tracing.md §2 (source: calibrated vs cli_override vs default)
   - **Failure classification**: Implementation bug (telemetry schema incomplete, missing hkl_source/MTZ path fields)

2. **ARCH-CONTRACT-WRITER-001** (Torch Diagnostics Persistence)
   - **Owner module**: `dbex/io/writer.py::_write_torch_outputs` (HDF5 /torch_diagnostics group)
   - **Consumer contracts**:
     - `tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata` (regression test)
     - `tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping` (acceptance test)
     - `dbex/look.py` (visualization, reads HDF5 artifacts)
   - **Invariant**: Diagnostics group must persist all calibration/telemetry metadata fields without breaking backward compatibility
   - **Schema extension**: hkl_source, hkl_n_reflections, hkl_mean_amplitude, hkl_path fields (Phase B deliverable)
   - **Failure classification**: Implementation bug (schema incomplete, Phase A must define fields)

3. **ARCH-CONTRACT-STRUCTURE-FACTORS-001** (Refined MTZ Ingestion)
   - **Owner module**: `dbex/nanobrag_bridge.py::load_refined_mtz` (refined structure-factor loader)
   - **Consumer contracts**:
     - `dbex/nanobrag_bridge.py::build_structure_factor_grid` (HKL grid builder, consumes refined amplitudes)
     - `dbex/refine_one.py::run_nanobrag_backend` (CLI backend, --refined-mtz path)
     - `dbex/nanobrag_bridge.py::simulate_forward_once` (zero-iteration helper, delegates to grid builder)
   - **Invariant**: Refined MTZ path must flow --refined-mtz → load_refined_mtz → build_structure_factor_grid → simulator without silent fallback to raw amplitudes
   - **Telemetry requirement**: hkl_source must distinguish "refined" vs "raw" per SCALE-007
   - **Failure classification**: Implementation bug (telemetry hook points not identified, Phase A must trace call chain)

## Do Now

**Phase A planning deliverables** (MAP-SCALE-003 implementation.md lines 21-24):

1. **Audit current diagnostics schema** (`dbex/io/writer.py::_write_torch_outputs`):
   - Read `dbex/io/writer.py` lines covering `_write_torch_outputs` function
   - List existing `/torch_diagnostics` HDF5 attributes (e.g., masked_mse, loss_mask_coverage, backend)
   - Identify schema extension points for structure-factor telemetry (hkl_source, hkl_n_reflections, hkl_mean_amplitude, hkl_path)
   - Document findings in `plans/active/MAP-SCALE-003/reports/2025-12-07T150000Z/schema_audit.md`

2. **Trace refined MTZ loading path**:
   - Read `dbex/refine_one.py` to locate `--refined-mtz` CLI argument handling
   - Read `dbex/nanobrag_bridge.py` to trace:
     - `load_refined_mtz` invocation site (where refined MTZ path is consumed)
     - `build_structure_factor_grid` call site (where refined amplitudes enter HKL grid)
     - Return value flow to `simulate_forward_once` (where diagnostics payload is constructed)
   - Identify hook points for telemetry computation (post `load_refined_mtz`, pre simulator invocation)
   - Document call chain with file:line anchors in `plans/active/MAP-SCALE-003/reports/2025-12-07T150000Z/mtz_flow_trace.md`

3. **Define telemetry metadata schema**:
   - Design metadata dictionary with 4 required fields:
     - `hkl_source`: str ("refined" | "raw") — distinguishes refined MTZ vs raw amplitudes
     - `hkl_n_reflections`: int — reflection count from HKL grid
     - `hkl_mean_amplitude`: float — mean |F| amplitude for diagnostics
     - `hkl_path`: str — absolute path to MTZ file (or empty string if default)
   - Specify fallback behavior when refined MTZ absent (hkl_source="raw", hkl_path="")
   - Document schema + rationale in `plans/active/MAP-SCALE-003/reports/2025-12-07T150000Z/telemetry_schema.md`

4. **Confirm downstream consumer compatibility**:
   - Read `tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata` to understand existing assertion patterns
   - Read `tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke` to identify telemetry access points
   - Verify HDF5 schema extension (new attrs under `/torch_diagnostics`) won't break existing artifact parsers
   - Document compatibility analysis in `plans/active/MAP-SCALE-003/reports/2025-12-07T150000Z/consumer_compatibility.md`

5. **Synthesize planning report**:
   - Consolidate findings from steps 1-4 into `plans/active/MAP-SCALE-003/reports/2025-12-07T150000Z/planning_notes.md`
   - Include:
     - Schema audit summary (existing fields + proposed extensions)
     - MTZ flow trace diagram (file:line anchors for hook points)
     - Telemetry metadata schema (4 required fields + fallback rules)
     - Consumer compatibility assessment (regression/acceptance test impact)
     - Next action recommendation (Phase B implementation readiness)

**Validation**: None (planning loop, no pytest execution required)

**Artifact destinations**:
- `plans/active/MAP-SCALE-003/reports/2025-12-07T150000Z/schema_audit.md`
- `plans/active/MAP-SCALE-003/reports/2025-12-07T150000Z/mtz_flow_trace.md`
- `plans/active/MAP-SCALE-003/reports/2025-12-07T150000Z/telemetry_schema.md`
- `plans/active/MAP-SCALE-003/reports/2025-12-07T150000Z/consumer_compatibility.md`
- `plans/active/MAP-SCALE-003/reports/2025-12-07T150000Z/planning_notes.md`

## Forbidden This Loop
- No production code changes (planning only)
- No pytest execution (Docs mode, no tests mapped)
- No new probes or instrumentation (schema audit via code reading only)

## How-To Map

**Not applicable** (Docs mode — no test execution or production changes)

**Artifact capture**:
```bash
# Ralph should create reports directory manually:
mkdir -p plans/active/MAP-SCALE-003/reports/2025-12-07T150000Z/

# Write planning artifacts as specified in Do Now steps 1-5
# (schema_audit.md, mtz_flow_trace.md, telemetry_schema.md, consumer_compatibility.md, planning_notes.md)
```

## Pitfalls To Avoid

1. **Type discipline**: This is a planning loop (ActionType=planning, Mode=Docs). Do not attempt implementation edits to dbex/io/writer.py or dbex/nanobrag_bridge.py. Code reading only.

2. **Parity-first**: MAP-SCALE-003 telemetry contract must align with MAP-SCALE-004 precedent (simulate_forward_once diagnostics payload). Review MAP-SCALE-004 implementation.md Phase A/B for schema consistency.

3. **No stacking**: This is Phase A planning. Do not skip to Phase B implementation without completing all 5 Do Now deliverables (schema audit, MTZ trace, telemetry schema, consumer compatibility, planning notes).

4. **Evidence→Action contract**: Planning notes must end with concrete Phase B next action (file::function to edit, pytest selector to validate). If uncertain, mark blocked and escalate to Galph.

5. **Findings paydown**: SCALE-003/004/006/007 findings govern telemetry design. All 4 must be cited in planning notes with implementation guidance.

6. **ARCH conformance**: Telemetry schema must conform to ARCH-CONTRACT-WRITER-001 (HDF5 /torch_diagnostics group). Do not introduce conflicting persistence patterns.

7. **Scriptization policy**: If analysis requires trace capture, use existing production code paths (no new plan-local probes). Code reading via Read tool is sufficient for Phase A.

8. **Environment freeze**: No package installs, no env modifications. All planning work stays in docs/reports artifacts.

9. **Doc sync plan**: None required (planning loop, no tests added/renamed).

10. **Loop discipline**: This is the first planning loop for MAP-SCALE-SYNC-001. Next loop must either delegate Phase B implementation OR switch focus if blocked. Maximum 2 consecutive planning loops per focus.

## If Blocked

**Blocking scenarios**:
1. **Schema extension conflicts**: If existing `/torch_diagnostics` attrs cannot accommodate 4 new fields without breaking backward compatibility, mark Phase A blocked and document conflict in planning_notes.md. Escalate to Galph for spec_change scoping (HDF5 schema versioning).

2. **MTZ flow trace incomplete**: If `load_refined_mtz` → `build_structure_factor_grid` call chain cannot be traced (missing functions, unclear delegation), mark Phase A blocked and document gap in mtz_flow_trace.md. Escalate to Galph for architecture audit (ARCH-CONTRACT-STRUCTURE-FACTORS-001 violation).

3. **Consumer incompatibility**: If regression tests (test_torch_diagnostics_metadata, DB-AT-024) require breaking changes to access new telemetry fields, mark Phase A blocked and document impact in consumer_compatibility.md. Escalate to Galph for harness initiative (test refactor scoping).

**Resolution**:
- Record block in `plans/active/MAP-SCALE-003/reports/2025-12-07T150000Z/planning_notes.md`
- Update galph_memory.md with block details + escalation reason
- Next loop: Galph selects alternative Tier 1 focus (DB-AT-SUITE-CARE-001) OR scopes unblock initiative (spec_change/harness)

## Doc Sync Plan
**Not applicable** (planning loop, no tests added/renamed)
