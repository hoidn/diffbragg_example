Summary: Promote the mapping dataset metrics probe into `dbex.calibration`/`dbex.tools` so calibration/HKL comparisons rely on owner APIs instead of a 670+ LOC plan script.
Mode: none
ActionType: implementation_ready
DecisionStatus: localized
InitiativeType: architecture
Focus: ARCH-PROBE-FREEZE-001 — Probe Freeze & Logging Consolidation
Branch: integration
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python -m dbex.tools.mapping_dataset_metrics --cases metadata_raw metadata_calibrated --emit-roi-artifacts --roi-count 16 --default-sigma 3.0 --device cuda:0 --out-dir plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-30T010000Z/mapping_dataset_metrics | tee plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-30T010000Z/mapping_dataset_metrics/probe.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"
Artifacts: plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-30T010000Z/
Findings Applied (Mandatory):
  - STAGEA-001 — Calibration flows must be owned by Stage A/mapping modules; migrating the dataset metrics probe prevents duplicate calibration handling.
  - SCALE-004 — HKL/refined MTZ precedence belongs in production helpers; moving case resolution into `dbex.calibration` keeps SCALE-004 enforced.
  - SCALE-005 — Sigma/calibration provenance must remain auditable via owner APIs, not plan scripts.
Pointers:
  - plans/active/ARCH-PROBE-FREEZE-001/implementation.md:41-65 — Phase B.5 now targets the mapping dataset metrics migration; follow these goals/exit criteria.
  - plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py:1-920 — Current shadow pipeline whose logic must move into the new owner modules.
  - docs/diagnostic_script_policy (prompts/supervisor.md:272-309) — Thin-wrapper rule prohibiting further expansion of plan-local probes.
  - docs/data_dependency_manifest.md:40-140 — Canonical env knobs for HKL/calibration/sigma assets that the new CLI must honor.
  - docs/TESTING_GUIDE.md:90-220 — Stage A smoke + dataset diagnostics workflow; update the references from the plan script to the new CLI.
ARCH Contracts (mandatory):
  - Diagnostic Script Policy (prompts/supervisor.md:272-309) — Owner module: `dbex.tools`; failure type: architecture conformance (shadow pipeline duplicating simulator/mapping semantics).
  - Calibration/Data Dependency Manifest (docs/data_dependency_manifest.md:40-140) — Owner: `dbex.vis.mapping` + forthcoming `dbex.calibration.config_variants`; failure type: implementation bug (dataset/env resolution duplicated outside owner modules).
  - Stage A Telemetry Ownership (docs/architecture/data_telemetry_flow.md:1-180) — Owner: `dbex.vis.mapping` / `dbex.refinement.stage_a`; failure type: implementation bug when probes bypass owner telemetry paths.
Do Now (hard validity contract)
1. Implement: `dbex/calibration/config_variants.py::materialize_calibration_variant` and helper utilities — lift the case/variant materialization logic from `compare_mapping_dataset_metrics.py`, expose reusable functions (base config loading, spot_scale override, N_cells removal, dataset path resolution mirroring `tests/conftest.py::smoke_dataset_paths`), and add minimal unit docstrings so tooling/tests can import the helpers.
2. Implement: `dbex/tools/mapping_dataset_metrics.py::main` (+ supporting functions) — move the CLI/parser, case definition, DataLoad construction, ROI correlation/scale metric computation, ROI artifact emission, and diff generation into this owner module. Provide an importable runner (e.g., `run_mapping_dataset_metrics(cases, *, default_sigma, device, emit_roi_artifacts, out_dir)`) so tests or scripts can reuse the logic without spawning a subprocess.
3. Implement: `plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py` — reduce to a compatibility shim (`from dbex.tools import mapping_dataset_metrics as tool; tool.main()`), update the module docstring to note the canonical entry point, and ensure no residual business logic remains.
4. Implement: Documentation/tests updates (at minimum `docs/TESTING_GUIDE.md` dataset diagnostics section, `plans/active/TOOLING-VIS-001/implementation.md` notes, and any docstrings or skip/help text referencing the legacy script) so operators know to run `python -m dbex.tools.mapping_dataset_metrics`. Add a short README note under `dbex/tools/` if needed to describe available tooling.
Mapped Validation (pytest):
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python -m dbex.tools.mapping_dataset_metrics --cases metadata_raw metadata_calibrated --emit-roi-artifacts --roi-count 16 --default-sigma 3.0 --device cuda:0 --out-dir plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-30T010000Z/mapping_dataset_metrics | tee plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-30T010000Z/mapping_dataset_metrics/probe.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"
Artifacts deliverables:
  - `mapping_dataset_metrics.json`, ROI PNG/NPZ bundles, and `probe.log` under `plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-30T010000Z/mapping_dataset_metrics/`.
  - Updated documentation excerpts (Testing Guide diff, plan notes) and any helper README snippets placed under the same report directory.
  - Command transcripts for the mapped validation commands plus any failure logs.
Forbidden This Loop:
  - no new plan-local diagnostic scripts or telemetry forks (all logic must live under `dbex.calibration`/`dbex.tools`).
  - do not regenerate mapping/calibration fixtures in-place; write outputs under the reserved artifacts directory.
How-To Map:
  1. Start by extracting the calibration variant helpers and dataset resolver into `dbex/calibration/config_variants.py`, adding targeted unit tests if practical.
  2. Port the CLI + computation logic into `dbex/tools/mapping_dataset_metrics.py`, ensuring it honors `DBEX_SMOKE_*` env vars, logs metrics, and can emit ROI artifacts.
  3. Replace the plan script with the shim, update docs/tests, and then run the mapped CLI command followed by the pytest collect-only run, teeing output into the reserved artifacts directory.
Pitfalls To Avoid:
  - Do not leave residual business logic inside the plan script; the shim must only delegate.
  - Keep dataset resolution identical to `tests/conftest.py::smoke_dataset_paths` so DB-AT fixtures and the new CLI stay in sync.
  - Ensure ROI artifact emission gates large tensor serialization (sampling where necessary) to avoid OOM.
  - Preserve backwards-compatible CLI flags so existing automation can switch with minimal changes.
  - Avoid touching Stage A telemetry codepaths beyond wiring in the new owner module.
If Blocked:
  - Document the blocker in `plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-30T010000Z/blockers.md`, update `docs/fix_plan.md` Attempts History, and notify Galph. If CLI runs fail due to resource constraints, rerun on CPU with smaller ROI counts but capture evidence explaining the limitation.
Doc Sync Plan (Conditional): Not required — no pytest selectors renamed; only documentation references move from the plan script to the new owner CLI.
