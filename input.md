Summary: Promote the one-off simulator trace into a reusable script that captures the crystal/unit mismatch and records machine-readable metrics for DIAG-UNIT-001.
Mode: none
InitiativeType: diagnostics
Focus: DIAG-NANOBRAGG-OVERSAMPLE-001 — nanobrag_torch Oversample Parameter Investigation
Branch: main
Mapped tests: tests/dbex/test_nanobrag_bridge_configs.py::TestDetectorConfigMapping::test_beam_center_swap
Artifacts: plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T130945Z/

Do Now:
- Implement: plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/bin/trace_simulator_mismatch.py::main — new Tier-2 probe that loads the smoke fixtures via DataLoad/build_mapping_stage_a_context, builds a Stage A warm cache with RefinementConfig(oversample=3), toggles `trace_pixel` + `printout` on the cached simulator, captures stdout with `contextlib.redirect_stdout`, parses the TRACE_PY vectors, and writes both the raw log and `simulator_trace_metrics.json` (showing raw vs corrected h/k/l) into the artifacts directory (see phase_d_trace_plan.md).
- Implement: docs/findings.md::DIAG-UNIT-001 — append the new artifact path plus a one-line note that `trace_simulator_mismatch.py` now emits the quantified 1e10 mismatch so future loops can cite it directly.
- Validate: python plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/bin/trace_simulator_mismatch.py --detector-size small --trace-fast 0 --trace-slow 0 --device cpu --out-dir plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T130945Z/ (produces simulator_trace.log, simulator_trace_metrics.json, crystal_unit_analysis.md in the artifacts path).
- Validate: pytest -vv tests/dbex/test_nanobrag_bridge_configs.py::TestDetectorConfigMapping::test_beam_center_swap | tee plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T130945Z/pytest_detector_config.log (quick guard to ensure the diagnostics script does not drift config factory behavior).

How-To Map:
1. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_SIGMA_SOURCE=metadata KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/bin/trace_simulator_mismatch.py --detector-size small --trace-fast 0 --trace-slow 0 --device cpu --out-dir plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T130945Z/ > plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T130945Z/command.log
2. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_nanobrag_bridge_configs.py::TestDetectorConfigMapping::test_beam_center_swap | tee plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T130945Z/pytest_detector_config.log

Pitfalls To Avoid:
- Do not instantiate new simulators per ROI; reuse the Stage A cache and only mutate `trace_pixel`/`printout` so the evidence matches the warm path we validated previously.
- Keep env flags (`AUTHORITATIVE_CMDS_DOC`, `KMP_DUPLICATE_LIB_OK=TRUE`, `NANOBRAGG_DISABLE_COMPILE=1`, `DBEX_SMOKE_*`) identical to the manual run so the trace is comparable.
- Capture stdout inside the script instead of depending on shell redirection—the script must emit both the log and parsed metrics in one invocation.
- Use the canonical smoke fixtures (`sp.proc/refGeom_small/...`) declared in docs/data_dependency_manifest.md; do not point at ad-hoc files.
- Parsed metrics must compute both the raw h/k/l (≈3e-9) and the corrected values (`raw * 1e10`) so DIAG-UNIT-001 has quantitative proof of the mismatch.

If Blocked:
- If the script fails to import nanobrag_torch or DIALS assets, capture the traceback in `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T130945Z/blocker.log`, add the failure signature + repro steps to docs/fix_plan.md Attempts History, and ping Galph before attempting environment changes.
- If the TRACE_PY output schema changes (no matching regex), dump the raw log under the artifacts path and leave TODO comments for the parser; note the schema drift in docs/fix_plan.md + DIAG-UNIT-001 so we can re-plan.

Findings Applied (Mandatory):
- DIAG-OVERSAMPLE-001 (docs/findings.md:105) — keep detector/beams configs identical to Stage A warm cache and avoid altering Simulator semantics beyond diagnostics.
- DIAG-UNIT-001 (docs/findings.md:50) — this script is the codified reproduction of the unit mismatch; ensure the JSON explicitly reports the raw vs corrected dot products to satisfy the finding’s evidence requirements.

Pointers:
- docs/spec-db-core.md:12 — Units policy (Å inputs, convert to meters only for dot products) referenced when explaining the mismatch.
- docs/data_dependency_manifest.md:36 — Smoke fixture inventory for refGeom_small dataset, MTZ, mask, and sigma tiles.
- docs/findings.md:50 — DIAG-UNIT-001 finding that this script must update.
- plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/implementation.md:120 — Phase D tasks and exit criteria for the trace instrumentation.
- plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T130945Z/phase_d_trace_plan.md:1 — Detailed script requirements and validation command from this planning loop.

Next Up (optional):
- Once the metrics exist, start Phase E to patch nanobrag_torch.Crystal so real-space vectors stay in Å before dotting with scattering vectors (spec-change may be required if upstream refuses meters conversion).
