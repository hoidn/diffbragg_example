Summary: Replace the CLI nanobrag backend stub with the real nanobrag_torch simulator (structure-factor hydration + √scale) and lock in targeted pytest coverage.
Mode: none
Focus: NANOBRAG-BACKEND-002 — Replace CLI torch backend stub with nanobrag_torch simulator
Branch: integration
Mapped tests: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_refine_one_cli.py -k nanobrag_backend
Artifacts: plans/active/NANOBRAG-BACKEND-002/reports/2025-11-04T031500Z/

Do Now (hard validity contract)
- Focus: NANOBRAG-BACKEND-002
- Implement: dbex/refine_one.py::{create_parser, run_nanobrag_backend} + dbex/nanobrag_bridge.py::build_structure_factor_grid + tests/dbex/test_refine_one_cli.py::TestNanobragBackend — accept an optional spot-scale override, hydrate nanobrag_torch Simulator per panel using real configs, and add regression tests that guard simulator invocation plus √(spot_scale_override) scaling.
- Validate: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_refine_one_cli.py -k nanobrag_backend | tee "$REPORT_DIR"/pytest_nanobrag_backend.log
- Artifacts: plans/active/NANOBRAG-BACKEND-002/reports/2025-11-04T031500Z/

How-To Map
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. export REPORT_DIR=plans/active/NANOBRAG-BACKEND-002/reports/2025-11-04T031500Z
3. mkdir -p "$REPORT_DIR"
4. Port the canonical HKL grid builder from scripts/generate_simple_cubic_golden.py:565 into dbex/nanobrag_bridge.py::build_structure_factor_grid (torch device-neutral, SCALE-001 compliant) and expose metadata needed by the backend.
5. Update dbex/refine_one.py::{create_parser, run_nanobrag_backend} to wire optional --spot-scale-override (default 1), instantiate nanobrag_torch Crystal/Detector/Simulator on CPU, run per-panel simulation, apply √(spot_scale_override), and reuse _write_torch_outputs; drop the Gaussian stub.
6. Extend tests/dbex/test_refine_one_cli.py::TestNanobragBackend with deterministic patches for Simulator/bridge helpers to assert structure-factor hydration, scaling, and output hand-off; skip via pytest.importorskip when nanobrag_torch is unavailable.
7. KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_refine_one_cli.py -k nanobrag_backend | tee "$REPORT_DIR"/pytest_nanobrag_backend.log

Pitfalls To Avoid
- Keep GEOMETRY-002 analytic Euler inversion; do not revert to scitbx angle helpers.
- Structure factors must stay unscaled before the simulator (SCALE-001); apply only the post-sim √scale (SCALE-002).
- Default the simulator device to CPU; ensure tests patch heavy classes so they remain device-neutral.
- Respect Environment Freeze: no pip installs or edits to external packages/modules.
- Preserve `_write_torch_outputs` contract (ROI scoring + diagnostics) and reuse existing artifact layout.
- Ensure tests use deterministic tensors and seeded randomness if needed; avoid GPU-only assertions.
- If `nanobrag_torch` import fails, short-circuit with pytest.skip and record the blocker per Fix Plan instructions.
- Guard mask polarity (MANIFEST-001) and incident beam conventions (HKL-ORIENT-001) when constructing configs.

If Blocked
- Capture the exact ImportError or runtime exception in "$REPORT_DIR"/nanobrag_backend_blocker.md, update docs/fix_plan.md Attempts with the signature, and halt further edits pending supervisor guidance.

Findings Applied (Mandatory)
- GEOMETRY-002 — Maintain analytic detector Euler inversion when filling DetectorConfig.
- SCALE-001 — Do not pre-scale structure factors while hydrating the HKL grid.
- SCALE-002 — Apply √(spot_scale_override) post-simulation to align with DiffBragg intensity units.
- MANIFEST-001 — Keep trusted mask polarity True=include throughout the bridge/backend.
- HKL-ORIENT-001 — Preserve incident beam orientation when feeding nanobrag_torch Crystal/Detector models.
- CONFIG-002 / CONFIG-003 — Continue using DetectorConvention enum values and tuple polarization axes.
- MODEL-001 — Ensure configs still instantiate nanobrag_torch Detector/Crystal models without regression.
- RUNTIME-001 — Set KMP_DUPLICATE_LIB_OK=TRUE before running torch-based tests.

Pointers
- dbex/refine_one.py:135 — Current nanobrag backend stub to replace with real simulator wiring.
- scripts/generate_simple_cubic_golden.py:565 — Reference HKL grid + simulator loop with √scale.
- docs/nanobrag_api.md:1 — Official simulator/config contract.
- docs/config_crosswalk.md:60 — Geometry/beam/crystal mapping + SCALE guardrails.
- tests/dbex/test_refine_one_cli.py:89 — Existing backend tests to extend for simulator coverage.
- docs/TESTING_GUIDE.md:74 — Parity harness runtime flags and logging expectations.

Next Up (optional)
- Refresh DB_AT_001 parity selector to consume the nanobrag backend once simulator wiring passes tests.
