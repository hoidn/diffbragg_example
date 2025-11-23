# DBEX Test Suite Index

**Purpose**: Authoritative registry of DBEX test selectors, synchronized with `docs/TESTING_GUIDE.md` §2.

## Implementation Coverage (Active)

| Module / Area | Selector | Status | Spec Reference | Notes |
| --- | --- | --- | --- | --- |
| Bridge tensors & masks | `tests/dbex/test_nanobrag_bridge.py` | active | `docs/spec-db-core.md:20`, `docs/config_crosswalk.md:86-95` | Validates `[panel, slow, fast]` ordering, mask polarity, and background semantics. |
| Config hydration | `tests/dbex/test_nanobrag_bridge_configs.py` | active | `docs/config_crosswalk.md:15-72`, `docs/dxtbx_api.md:17-41` | Detector/beam/crystal mapping to nanobrag_torch configs; covers pixel pitch, beam center, and A* handling. |
| Smoke harness | `tests/dbex/test_nanobrag_smoke.py` | active | `docs/spec-db-workflow.md:24-29`, `docs/dials_api.md:10-28` | Single-experiment flow, stitched Bragg output, masked MSE, and basic artifact emission. |
| Stage A/B/C refinement smokes | `tests/dbex/test_torch_refine_smoke.py` | active | `docs/spec-db-workflow.md` (“Stage Smoke Dataset Policy”) | Stage A/B/C LBFGS closures with telemetry assertions; supports `--smoke-detector-size={small,full}` and enforces full-detector runs for DB-AT/workflow selectors. |
| CLI backend flag | `tests/dbex/test_refine_one_cli.py` | active | `docs/spec-db-interfaces.md:11`, `plans/active/TORCH-CLI-003/implementation.md`, `plans/active/PHYSICS-LOSS-001/implementation.md` | CLI parser validation, backend dispatch (diffbragg/nanobrag), torch path diagnostics, calibration/sigma guardrails, and HDF5 metadata checks. |
| Sigma map ingestion | `tests/dbex/test_data_load_sigma_map.py` | active | `docs/spec-db-core.md:32-68`, `docs/spec-db-workflow.md:26-31` | `load_sigma_readout_map` and `_load_external_lookup_sigma_map` behavior; enforces `[panel, slow, fast]` alignment, strict positivity, and provenance metadata. |
| Sigma metadata manifest | `tests/sp_proc/test_sigma_metadata_fixture.py` | active | `docs/spec-db-core.md:32-68`, `docs/spec-db-workflow.md:26-31` | Validates `sp.proc` sigma metadata fixtures and external_lookup embedding for Stage smokes. |
| DB-AT-026: UB Parameterization Round-Trip | `tests/dbex/test_ub_parameterization_roundtrip.py` | active | `docs/spec-db-core.md:48-68`, `docs/spec-db-workflow.md:36-50`, `docs/spec-db-runtime.md:18-28` | Validates incremental UB parameterization zero-point invariant (U(0)=U₀, B(0)=B₀, A*(0)=A*_mapping). 4 tests: orientation/cell zero-point, mapping parity, gradient flow (xfail). First added 2025-11-23. |
| ARCH-ENGINE-001: RefinementEngine TDD Nucleus | `tests/dbex/test_refinement_engine.py::test_engine_executes_mock_stage` | active | `docs/spec-db-workflow.md:32-33`, `plans/active/ARCH-REFINE-FLOW-001/implementation.md` | TDD nucleus test for Protocol-based Refinement Engine. Validates engine executes mock stage, aggregates telemetry Dict[str, RefinementTelemetry], and includes stage_type/mode fields (Phase A4 extension). 1 test collected, 1 passed. First added 2025-11-23. |

### Plan-local Visualization Drivers

TOOLING-VIS-001 defines several plan-local visualization scripts under
`plans/active/TOOLING-VIS-001/bin/` (for example,
`generate_stage_a_refgeom_roi_triptychs.py`,
`generate_stage_a_refgeom_roi_triptychs_adam.py`,
`generate_zero_iter_refined_roi_triptychs.py`,
`probe_mapping_stage_a_context_metrics.py`). These are **not** pytest
selectors and are documented in `docs/TESTING_GUIDE.md` §2.4 as
non-canonical helpers for mapping-aligned ROI diagnostics.

