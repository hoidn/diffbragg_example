Summary: Replace the nanobrag bridge stubs with real nanobrag_torch config objects and harden the geometry tests so the CLI can graduate off the Gaussian placeholder.
Mode: none
Focus: NANOBRAG-BACKEND-002 — Replace CLI torch backend stub with nanobrag_torch simulator
Branch: integration
Mapped tests: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_nanobrag_bridge_configs.py
Artifacts: plans/active/NANOBRAG-BACKEND-002/reports/2025-11-04T022540Z/

Do Now (hard validity contract)
- Focus: NANOBRAG-BACKEND-002
- Implement: dbex/nanobrag_bridge.py::{DetectorConfig, BeamConfig, CrystalConfig, create_detector_config, create_beam_config, create_crystal_config} + tests/dbex/test_nanobrag_bridge_configs.py::TestDetectorConfigMapping — retire the local dataclass stubs, build real `nanobrag_torch.config` objects, and extend the tests to assert against those classes (including a new round-trip check that instantiates `nanobrag_torch.models.detector.Detector` and `Crystal`).
- Validate: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_nanobrag_bridge_configs.py | tee "$REPORT_DIR"/pytest_bridge.log
- Artifacts: plans/active/NANOBRAG-BACKEND-002/reports/2025-11-04T022540Z/

How-To Map
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. export REPORT_DIR=plans/active/NANOBRAG-BACKEND-002/reports/2025-11-04T022540Z
3. mkdir -p "$REPORT_DIR"
4. Edit dbex/nanobrag_bridge.py to replace the local dataclass definitions with thin adapters that import `nanobrag_torch.config` and return real config objects; keep the analytic XYZ inversion (GEOMETRY-002) and mask polarity guards intact.
5. Update tests/dbex/test_nanobrag_bridge_configs.py to assert against the new config classes and add a `test_detector_model_roundtrip` (or similar) that builds `nanobrag_torch.models.detector.Detector` and `nanobrag_torch.models.crystal.Crystal` using the bridge outputs to guard compatibility.
6. KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_nanobrag_bridge_configs.py | tee "$REPORT_DIR"/pytest_bridge.log

Pitfalls To Avoid
- Do not reintroduce `r3_rotation_matrix_as_x_y_z_angles`; keep the analytic inversion from GEOMETRY-002.
- Preserve True=include mask polarity; a polarity flip will break MANIFEST-001 safeguards.
- Avoid eager Simulator runs inside tests that rely on GPU-only features; keep everything CPU/device-neutral per docs/pytorch_runtime_checklist.md.
- Do not touch SCALE-002 post-sim scaling logic yet; that belongs in run_nanobrag_backend.
- Leave canonical fixtures untouched; the bridge should consume existing trusted_mask arrays without rewriting fixtures.
- Respect Environment Freeze: no pip installs or editing external packages.
- Keep new tests deterministic (seed torch/numpy if randomness is introduced).
- Ensure imports succeed without optional CUDA extras; skip tests gracefully if `nanobrag_torch` is absent and log the block in docs/fix_plan.md.
- Do not move file locations or rename existing helper functions without updating downstream imports.

If Blocked
- If `import nanobrag_torch.config` fails, capture the ImportError text in "$REPORT_DIR"/import_error.txt, mark NANOBRAG-BACKEND-002 as blocked in docs/fix_plan.md (include the signature), and stop.
- If the detector/crystal constructors reject the bridge output, save the traceback plus offending values in "$REPORT_DIR"/compatibility_fail.md and pause for supervisor guidance.

Findings Applied (Mandatory)
- GEOMETRY-002 — Maintain analytic Euler inversion when producing detector rotation angles.
- SCALE-001 — Do not rescale structure factors while constructing nanobrag_torch configs.
- SCALE-002 — Remember that √(spot_scale_override) post-sim scaling stays in run_nanobrag_backend; bridge helpers should not apply it early.
- MANIFEST-001 — Preserve trusted mask polarity so checksum guards remain valid.
- HKL-ORIENT-001 — Keep incident beam direction conventions consistent (source→sample) when instantiating beam/crystal helpers.

Pointers
- dbex/nanobrag_bridge.py:232 — Detector config hydration path that currently returns local stubs.
- tests/dbex/test_nanobrag_bridge_configs.py:1 — Existing bridge config tests to update with real nanobrag_torch classes.
- scripts/generate_simple_cubic_golden.py:565 — Reference implementation of nanobrag_torch config + simulator usage.
- docs/nanobrag_api.md:1 — Official config/dataclass contract for Detector/Beam/Crystal.
- docs/config_crosswalk.md:15 — Mapping of DIALS metadata to nanobrag_torch config fields and guards.

Next Up (optional)
- Draft helper to hydrate nanobrag_torch structure-factor grids inside dbex nanobrag bridge (Phase A2).

