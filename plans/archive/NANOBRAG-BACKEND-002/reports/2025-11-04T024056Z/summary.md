# NANOBRAG-BACKEND-002 Loop Summary (2025-11-04T024056Z)

## Focus Snapshot
- Exit criterion 1 complete (real config dataclasses in place); transitioning to Phase B simulator integration.
- `dbex.refine_one.run_nanobrag_backend` still emits `_stub_bragg_tensor`; CLI lacks hook for `spot_scale_override` (SCALE-002).
- `scripts/generate_simple_cubic_golden.py:96-178` hosts canonical `build_structure_factor_grid` logic we intend to promote into `dbex.nanobrag_bridge`.

## Evidence Reviewed
- `docs/fix_plan.md` Attempts History for NANOBRAG-BACKEND-002 (status in_progress, next actions: simulator wiring + scaling).
- `plans/active/NANOBRAG-BACKEND-002/reports/2025-11-04T031500Z/summary.md` confirming DataLoad scale probe gap.
- Source code: `dbex/refine_one.py:135-220`, `dbex/nanobrag_bridge.py:1-220`, `scripts/generate_simple_cubic_golden.py:96-178`, `tests/dbex/test_refine_one_cli.py:80-200`.
- Knowledge base findings: GEOMETRY-002, SCALE-001, SCALE-002, HKL-ORIENT-001, CONFIG-002/003, MODEL-001.

## Proposed Implementation Focus (for Ralph)
1. Promote structure-factor hydration helper into `dbex.nanobrag_bridge` (reusable by CLI) while honoring SCALE-001 (no pre-scale) and HKL-ORIENT-001 (incident direction sign).
2. Extend CLI parser (`dbex/refine_one.py::create_parser`) with optional `--spot-scale-override`, thread through DataLoad + backend call.
3. Replace `_stub_bragg_tensor` usage with real `nanobrag_torch.Simulator` loop in `run_nanobrag_backend`; apply √(spot_scale_override) to simulator output prior to `_write_torch_outputs`.
4. Add targeted pytest coverage in `tests/dbex/test_refine_one_cli.py` that patches `nanobrag_torch.Simulator` to capture call args, verifies structure-factor tensor + scaling flow, and inspects `_write_torch_outputs` inputs.
5. Run `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_refine_one_cli.py -k nanobrag_backend` (plus collect-only guard if selector renamed) with artifacts stored under this timestamp.

## Risks & Mitigations
- **Import availability:** Respect Environment Freeze; if `nanobrag_torch` import fails, mark loop blocked and log signature per fix plan.
- **Device neutrality:** Simulator should default to CPU; guard tests with `torch.device('cpu')` to avoid GPU-only regressions (docs/pytorch_runtime_checklist.md:26).
- **Scaling correctness:** Enforce SCALE-002 by applying √(spot_scale_override) after simulation only; ensure tests assert this behavior explicitly.
- **Geometry fidelity:** Preserve GEOMETRY-002 analytic Euler inversion outputs when constructing DetectorConfig → Simulator.

## Artifact Plan
- Store pytest logs, patched simulator call traces, and any T1 analysis outputs under `plans/active/NANOBRAG-BACKEND-002/reports/2025-11-04T024056Z/`.
