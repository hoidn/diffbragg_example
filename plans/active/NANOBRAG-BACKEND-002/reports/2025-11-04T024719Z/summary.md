# NANOBRAG-BACKEND-002 Loop Summary (2025-11-04T024719Z)

## Focus Snapshot
- Phase B (simulator integration) still outstanding: `run_nanobrag_backend` uses `_stub_bragg_tensor` and CLI lacks a way to pass the diffBragg `spot_scale_override` guard (SCALE-002).
- Structure-factor hydration lives only in `scripts/generate_simple_cubic_golden.py`; the CLI has no reusable helper to construct HKL grids for the simulator (SCALE-001).
- Parity harness blocks until the torch backend emits real simulator output with √scale applied and persists deterministic artifacts.

## Evidence Reviewed
- `docs/fix_plan.md` §NANOBRAG-BACKEND-002 (status in_progress, exit criteria 2-4 open).
- Working plan `plans/active/NANOBRAG-BACKEND-002/implementation.md` (Phase B checklist B1-B3 pending).
- Prior reports: 2025-11-04T024056Z (Do Now draft) and 2025-11-04T031500Z (DataLoad scale probe).
- Source: `dbex/refine_one.py` (CLI + backend stub), `dbex/nanobrag_bridge.py` (config helpers/RefinementInputs), `scripts/generate_simple_cubic_golden.py:96-180,560-640` (canonical structure-factor grid + simulator wiring example).
- Specs/docs: `docs/nanobrag_api.md` (Simulator/Detector contract), `docs/config_crosswalk.md` (detector/beam/crystal mapping), `docs/spec-db-core.md` (HKL, ROI semantics), `docs/pytorch_runtime_checklist.md` (device/dtype guardrails), `docs/forward_equivalence.md` (DB_AT_001 parity expectations).
- Knowledge base findings: GEOMETRY-002, SCALE-001, SCALE-002, HKL-ORIENT-001, CONFIG-002/003, MODEL-001.

## Recommended Implementation Focus (hand-off to Ralph)
1. **Promote structure-factor helper:** Port `build_structure_factor_grid` into `dbex.nanobrag_bridge` (torch-agnostic wrapper returning `(grid, metadata)`), consuming `DataLoad.F.indices()/data()` while honoring SCALE-001 and HKL metadata logging.
2. **CLI plumbing:** Extend `create_parser` to accept `--spot-scale-override` (float, default `None` → derive from `DataLoad` metadata later). Thread through to `run_nanobrag_backend` with compatibility defaults and update help text accordingly.
3. **Simulator wiring in `run_nanobrag_backend`:**
   - Import `nanobrag_torch` components (`Simulator`, models.detector.Detector, models.crystal.Crystal) lazily with `pytest.importorskip` pattern for tests.
   - Instantiate beam/detector/crystal configs via bridge helpers per panel; hydrate HKL grid via new helper; set `crystal_model.hkl_data/metadata`.
   - Run simulator per panel on CPU (`torch.device('cpu')`), apply √(spot_scale_override) post-sim (SCALE-002), stitch into `[panel, slow, fast]` array aligned with existing ROI layout.
   - Preserve existing diagnostics + `_write_torch_outputs` interface.
4. **Targeted regression test:** Add `tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_uses_simulator` (name TBD) that patches `nanobrag_torch.Simulator.run`, captures call args (HKL grid, detector/crystal configs, √scale application), and asserts `_write_torch_outputs` receives simulator output—ensuring SCALE-001/002 + GEOMETRY-002 guard rails.
5. **Pytest command:** `KMP_DUPLICATE_LIB_OK=TRUE AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -v tests/dbex/test_refine_one_cli.py -k nanobrag_backend` (collect-only first if selector renamed/new).

## Risks & Mitigations
- **Environment Freeze:** Treat missing `nanobrag_torch` imports as blockers; capture error signature in `docs/fix_plan.md` if encountered.
- **Device neutrality:** Force CPU execution in tests (`torch.device('cpu')`) to avoid GPU dependence; assert outputs are moved to NumPy before serialization.
- **Scaling correctness:** Explicitly log √scale and guard against double application. Tests should fail if simulator output bypasses the scaling multiply.
- **HKL coverage:** Ensure grid metadata stored for diagnostics; mismatch in index ranges should raise early with actionable errors.

## Artifact Plan
- Store updated pytest log(s), patched-call transcript, and any supporting analysis under `plans/active/NANOBRAG-BACKEND-002/reports/2025-11-04T024719Z/` once implementation completes.
