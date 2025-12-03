Summary: Capture per-pixel HKL projections so we can quantify the constant offset that keeps Stage-A queries outside the structure-factor grid.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-SIM-HKL-BOUNDS-001 — Stage-A / mapping HKL alignment
Branch: integration
Mapped tests: pytest -vv tests/dbex/test_data_load_sigma_map.py
Artifacts: plans/active/ARCH-SIM-HKL-BOUNDS-001/reports/2025-12-03T152326Z/

Do Now:
- Implement: plans/active/ARCH-SIM-HKL-BOUNDS-001/bin/inspect_hkl_projection.py::main — CLI must load the canonical refGeom smoke fixture, rebuild Detector/Beam/Crystal configs via the existing bridge helpers, reproduce the `_compute_physics_for_position` scattering-vector math for the direct-beam pixel plus ±64 px offsets along slow/fast axes, and emit both `hkl_projection_metrics.json` and a Markdown summary describing fractional HKL values, rounded indices, and in-bounds status vs `crystal.hkl_metadata`.
- Implement: plans/active/ARCH-SIM-HKL-BOUNDS-001/reports/2025-12-03T152326Z/summary.md — capture the Phase B.1 observations (direct-beam offset, +/- slow/fast deltas, next hypotheses) with pointers to the JSON artifact and script CLI used.
- Validate: pytest -vv tests/dbex/test_data_load_sigma_map.py

How-To Map:
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-HKL-BOUNDS-001/bin/inspect_hkl_projection.py --detector-size small --out-dir plans/active/ARCH-SIM-HKL-BOUNDS-001/reports/2025-12-03T152326Z/
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv tests/dbex/test_data_load_sigma_map.py

Pitfalls To Avoid:
- Keep detector/beam configs canonical (DIALS convention, beam-center swap) per docs/config_crosswalk.md; do not mutate production modules.
- Use the same math as nanobrag_torch.simulator (incidence vectors, wavelength conversion, rotated `a/b/c` vectors in meters) so results match the runtime path.
- Sample pixels around the computed beam center (no hard-coded indices) to avoid drifting when calibration changes.
- Structure-factor metadata is authoritative; do not clamp HKL indices yourself—record the raw fractional values and compare against `hkl_metadata`.
- Reuse the existing DataLoad/Mapping helpers so sigma maps and calibration precedence stay aligned with spec-db-core.md.

If Blocked:
- If nanobrag_torch imports or the fixtures fail to load, log the full traceback in the artifacts directory, note the failure in `docs/fix_plan.md` Attempts History, and mark the initiative blocked pending environment investigation before issuing another implementation loop.

Findings Applied (Mandatory):
- docs/findings.md:51 (DIAG-OVERSAMPLE-001) — narrow the HKL-miss investigation to the scattering-vector projection and document offsets before altering simulator code.

Pointers:
- plans/active/ARCH-SIM-HKL-BOUNDS-001/implementation.md#phase-b
- docs/spec-db-core.md:20
- docs/spec-db-workflow.md:116
- docs/findings.md:51
