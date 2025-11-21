# Input

- Summary: Re-run the Stage A/B/C full-detector smokes (CLI + metadata sigma) and sync docs/fix-plan checkpoints so PERF-SMOKE-DETSIZE exit criterion #4 can finally close.
- Mode: none
- Focus: PERF-SMOKE-DETSIZE — Introduce small-detector fixture for smoke tests
- Branch: integration
- Mapped tests:
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T093500Z/telemetry_full_cli.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T093500Z/telemetry_full_cli.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers`
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T093500Z/telemetry_full_cli.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip`
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T093500Z/telemetry_full_metadata.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T093500Z/telemetry_full_metadata.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers`
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T093500Z/telemetry_full_metadata.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip`
- Artifacts: plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T093500Z/

## Do Now
- Focus Item: PERF-SMOKE-DETSIZE
- Implement: `docs/TESTING_GUIDE.md#Stage-smoke selectors`, `docs/development/TEST_SUITE_INDEX.md`, `docs/fix_plan.md#perfs-smoke-detsize`, and `plans/active/PERF-SMOKE-DETSIZE/implementation.md::Phase D` — fold in the fresh canonical full-detector runs (CLI + metadata), update artifact pointers/gates, and mark the Phase D checklist complete once telemetry/logs are archived.
- Test: Execute the mapped Stage A/B/C selectors on the full detector for both sigma sources with `DBEX_SMOKE_TELEMETRY_PATH` pointing into the new report directory so each run records telemetry JSON alongside the pytest logs.
- Artifacts: plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T093500Z/

## How-To Map
1. `mkdir -p plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T093500Z` and `rm -f plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T093500Z/telemetry_full_cli.json plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T093500Z/telemetry_full_metadata.json` to start from a clean telemetry slate.
2. Regenerate metadata fixtures so the Stage smokes can consume `external_lookup` tiles:  
   `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md python plans/active/PHYSICS-LOSS-001/bin/embed_sigma_external_lookup.py --expt refGeom.expt --expt-idx 0 --sigma-value 3.0 --output sp.proc/idx-0000_sigma_metadata.expt --report plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T093500Z/sigma_metadata.json --manifest sp.proc/sigma_metadata_manifest.json`
3. Prove selectors still collect with the canonical knob before running the long smokes:  
   `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=full pytest --collect-only tests/dbex/test_torch_refine_smoke.py -k 'test_stage_b_shell_modifiers or test_stage_c_detector_microslip' > plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T093500Z/collect_stage_full.log`
4. Stage A (full detector, CLI sigma):  
   `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T093500Z/telemetry_full_cli.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion | tee plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T093500Z/pytest_stage_a_full_cli.log`
5. Stage B (full detector, CLI sigma): same env as step 4 targeting `::test_stage_b_shell_modifiers` and teeing to `pytest_stage_b_full_cli.log`.
6. Stage C (full detector, CLI sigma): same env as step 4 targeting `::test_stage_c_detector_microslip` and teeing to `pytest_stage_c_full_cli.log`.
7. Stage A (full detector, metadata sigma):  
   `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T093500Z/telemetry_full_metadata.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion | tee plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T093500Z/pytest_stage_a_full_metadata.log`
8. Stage B (full detector, metadata sigma): same env as step 7 targeting `::test_stage_b_shell_modifiers` and teeing to `pytest_stage_b_full_metadata.log`.
9. Stage C (full detector, metadata sigma): same env as step 7 targeting `::test_stage_c_detector_microslip` and teeing to `pytest_stage_c_full_metadata.log`.
10. Update `docs/TESTING_GUIDE.md`, `docs/development/TEST_SUITE_INDEX.md`, `docs/fix_plan.md`, and `plans/active/PERF-SMOKE-DETSIZE/implementation.md` with the new canonical telemetry/log references (chi-squared deltas, detector-offset reduction, manifest hash pointer) and summarize the run in `plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T093500Z/summary.md`.

## Pitfalls To Avoid
- `DBEX_SMOKE_DETECTOR_SIZE` must be `full` for every run or the pytest guard will skip/raise before telemetry is recorded.
- Ensure metadata fixtures exist (both `.expt` and `.sigma_tiles.pkl`) via the embed script before running the metadata smokes; otherwise the fixtures will skip.
- Always set `DBEX_SMOKE_TELEMETRY_PATH` before invoking pytest and remove any stale JSON to avoid mixing old entries with the new canonical measurements.
- Keep `KMP_DUPLICATE_LIB_OK=TRUE` and `NANOBRAGG_DISABLE_COMPILE=1` in place so Stage smokes behave deterministically per RUNTIME-001.
- Do not relax the Stage B/C assertions—use the strict gates already codified in the tests; the goal is to capture real physics improvements, not to downgrade gates.
- Capture stdout/stderr with `tee` into the artifact directory so telemetry and logs can be cross-referenced later.
- Treat the metadata embed step as destructive: re-running will overwrite `sp.proc/idx-0000_sigma_metadata.expt`; stash the generated `sigma_metadata.json` under this loop’s report directory for traceability.
- Avoid editing simulator code or test gates in this loop; the focus is evidence capture + doc/ledger sync.
- If GPU/CPU resources run out mid-test, bail, log `nvidia-smi` output (if relevant), and surface the failure before reattempting.
- Maintain `AUTHORITATIVE_CMDS_DOC` on every command so logs remain auditable.

## If Blocked
If any Stage smoke fails (e.g., Stage B returns `status=error` again), capture the full pytest log plus the partially written telemetry JSON in `plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T093500Z/blocked.log`, note which sigma source/detector size triggered it, and append a new entry to `docs/fix_plan.md` + `plans/active/PERF-SMOKE-DETSIZE/implementation.md` describing the failure signature and why Phase D remains open before pausing the initiative.

## Findings Applied (Mandatory)
- REFINE-007 — Stage C canonical smokes must show ≥80 % detector-offset reduction and ≤0.05 % χ² regression; log these metrics in telemetry and the docs table.
- REFINE-008 — Stage B canonical runs expect ≤1e-6 χ² regression and ±1 % shell modifiers; ensure telemetry/log updates cite this guard.
- REFINE-009 — Always pass the baseline detector so detector-offset telemetry references real geometry rather than zeros.
- PHYSICS-LOSS-005 — Metadata sigma fixtures (`external_lookup`) are authoritative; metadata runs should assert telemetry provenance equals `external_lookup`.
- CONFORMANCE-001 — DB-AT/workflow alignment requires forcing the full detector; document the commands/env flags accordingly.

## Pointers
- plans/active/PERF-SMOKE-DETSIZE/implementation.md:70 — Phase D checklist for canonical parity re-validation.
- docs/fix_plan.md:90 — PERF-SMOKE-DETSIZE ledger entry + attempts history.
- docs/TESTING_GUIDE.md:40 — Stage smoke selector commands, telemetry expectations, and guard rails.
- docs/development/TEST_SUITE_INDEX.md:12 — Registry row for Stage A/B/C smokes.
- tests/dbex/test_torch_refine_smoke.py:316,600,819 — Stage A/B/C selectors and telemetry helpers referenced by the reruns.

## Next Up (optional)
1. Once canonical telemetry is archived, resume PERF-WARM-SIM-001 profiling to chase real CPU speedups now that the smoke suite can run quickly on the cropped assets.

## Mapped Tests Guardrail
- `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=full pytest --collect-only tests/dbex/test_torch_refine_smoke.py -k 'test_stage_b_shell_modifiers or test_stage_c_detector_microslip' > plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T093500Z/collect_stage_full.log`
