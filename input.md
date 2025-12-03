Summary: Instrument nanobrag_torch for HKL coverage stats so we can replace the retracted DIAG-UNIT finding with quantitative evidence.
Mode: none
InitiativeType: diagnostics
Focus: DIAG-NANOBRAGG-OVERSAMPLE-001 — nanobrag_torch Oversample Parameter Investigation
Branch: main
Mapped tests: pytest -k test_experiment_parity
Artifacts: plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-08T210000Z/

Do Now:
- Implement: Extend `src/nanobrag-torch/src/nanobrag_torch/simulator.py` so `compute_physics_for_position` accepts optional `hkl_metadata` + `debug_stats`. When `debug_config['collect_hkl_stats']` is set on the Simulator, aggregate min/max h,k,l and in-bounds/out-of-bounds counts (using metadata bounds) into `self._hkl_stats`, and expose the results via a read-only `hkl_stats` property. Reset the stats dict at the start of each `run()` call.
- Implement: Update `dbex/refinement/helpers.py::create_unified_simulator` to accept a `debug_config` parameter and pass it to the Simulator constructor so diagnostics scripts can enable HKL stats without manual post-init mutation.
- Implement: Refresh `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/bin/trace_simulator_mismatch.py` to set `NANOBRAGG_DISABLE_COMPILE=1`, request `collect_hkl_stats` via the factory, and emit the new `hkl_stats.json` (dumping the simulator’s stats dict) alongside the existing trace artifacts.
- Collect Evidence: Re-run the smoke fixture with the updated script so the new artifacts (trace log, metrics JSON, HKL stats JSON) land in `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-08T210000Z/` and cite them in the DIAG-UNIT retraction thread.
- Verify: Run `pytest -k test_experiment_parity` to ensure the helper + Simulator instrumentation did not regress the parity shim.

How-To Map:
1. `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md`
2. `NANOBRAGG_DISABLE_COMPILE=1 python plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/bin/trace_simulator_mismatch.py --detector-size small --trace-fast 0 --trace-slow 0 --out-dir plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-08T210000Z/`
3. `pytest -k test_experiment_parity`

Pitfalls To Avoid:
- Do not leave HKL stats enabled by default; guard everything behind the `collect_hkl_stats` flag and keep the `debug_stats` path out of the compiled hot loop unless the flag is set.
- Reset the stats dict at the beginning of each `run()` call so repeated runs don’t accumulate stale counts.
- Keep the new script outputs in the requested artifacts directory; do not overwrite the older 2025-12-03T130945Z evidence.
- Remember to set `NANOBRAGG_DISABLE_COMPILE=1` when running the script so Python-side aggregation isn’t optimized away.
- Updating `create_unified_simulator` touches multiple call sites—default the new parameter to `None` so existing callers keep working without edits.

If Blocked:
- If HKL stats show zero total queries or another unexpected invariant, capture the raw `hkl_stats.json`, note the failure signature in `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-08T210000Z/summary.md`, and ping Galph so we can reassess whether the simulator is skipping the physics kernel altogether.

Findings Applied:
- DIAG-OVERSAMPLE-001 — keep the oversample threading fixes intact while adding instrumentation.
- DIAG-UNIT-001 — marked as Retracted; this work replaces the incorrect unit-mismatch assumption with HKL coverage stats.

Pointers:
- plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/implementation.md (Phase E checklist)
- docs/findings.md (DIAG-UNIT-001 retraction note)
- src/nanobrag-torch/src/nanobrag_torch/simulator.py (physics kernel & new HKL stats path)
- plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/bin/trace_simulator_mismatch.py (diagnostic script to update)

Next Up:
1. After small-detector stats, repeat the run with `--detector-size full` to see whether HKL coverage changes across detector crops.
