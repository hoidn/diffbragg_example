Summary: Collect comparable HKL coverage statistics from Stage A and simulate_forward_once so we know whether the missing structure factors are a Stage A issue or a data/simulator mismatch.
Mode: none
InitiativeType: diagnostics
Focus: DIAG-NANOBRAGG-OVERSAMPLE-001 — nanobrag_torch Oversample Parameter Investigation
Branch: integration
Mapped tests: pytest -k test_experiment_parity
Artifacts: plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-09T103000Z/

Do Now:
- Implement: dbex/nanobrag_bridge.py::simulate_forward_once — add an optional `debug_config` dict parameter, forward it to `create_unified_simulator`, and when `collect_hkl_stats` is set capture each simulator’s `hkl_stats` (min/max h,k,l, in/out counts) so the diagnostics dict reports HKL query coverage without altering the existing default behavior.
- Implement: plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/bin/compare_hkl_stats.py — new Tier-2 script that loads the smoke fixture, runs all Stage A warm-cache simulators and a single `simulate_forward_once` pass with `collect_hkl_stats` enabled, and writes `hkl_stats_comparison.json` plus a short `summary.md` showing grid metadata vs. observed HKL ranges/hit rates for both paths. Update `trace_simulator_mismatch.py` to rely on the `Simulator.hkl_stats` property instead of poking `_hkl_stats_enabled` so the new instrumentation is the single source of truth.
- Collect Evidence: `NANOBRAGG_DISABLE_COMPILE=1` run the comparison script (`--detector-size small`) and drop the resulting JSON + summary into the artifacts directory so we have concrete Stage A vs. mapping stats to cite in findings.
- Update Findings/Plan: If both paths miss the HKL grid, add a DIAG-OVERSAMPLE-001 follow-up in docs/findings.md and note it in the plan Attempts History; if only Stage A is out of bounds, capture that delta instead so the next initiative can target Stage A context building.
- Verify: `pytest -k test_experiment_parity` to ensure the optional debug plumbing did not break the forward helper.

How-To Map:
1. `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md`
2. `NANOBRAGG_DISABLE_COMPILE=1 python plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/bin/compare_hkl_stats.py --detector-size small --out-dir plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-09T103000Z/`
3. `KMP_DUPLICATE_LIB_OK=TRUE pytest -k test_experiment_parity -vv`

Pitfalls To Avoid:
- Keep HKL stats collection behind the `collect_hkl_stats` flag; the default simulator path must remain untouched for production runs.
- Do not call or mutate private `_hkl_stats*` fields; use the new property so we don’t destabilize torch.compile caching.
- Reuse the existing smoke fixture paths from `trace_simulator_mismatch.py` so both Stage A and mapping runs operate on identical inputs and calibration metadata.
- The comparison script should respect `NANOBRAGG_DISABLE_COMPILE=1` to keep diagnostics deterministic; record any slowdowns in the summary rather than dropping the flag.
- When editing docs/findings.md or the plan, cite the artifact path so future loops can trace the evidence quickly.

If Blocked:
- If either path crashes before emitting HKL stats, capture the partial log + stack trace in `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-09T103000Z/` and update `docs/fix_plan.md` Attempts History with the failure signature so we know whether to escalate to an environment issue or open ARCH-SIM-HKL-BOUNDS-001.

Findings Applied (Mandatory):
- DIAG-OVERSAMPLE-001 — HKL coverage instrumentation already proves 0/9.4M hits; this loop extends that evidence instead of reworking oversample plumbing again.
- DIAG-UNIT-001 — remains retracted, so avoid attributing the mismatch to unit conversions and focus on HKL coverage deltas.

Pointers:
- plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/implementation.md (Phase F checklist)
- dbex/nanobrag_bridge.py:1230 (simulate_forward_once helper to extend)
- plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/bin/trace_simulator_mismatch.py (reuse fixture-loading helpers)
- docs/findings.md:49-50 (DIAG-OVERSAMPLE-001 and DIAG-UNIT-001 entries to update once results land)

Next Up:
1. If both Stage A and simulate_forward_once miss the grid, open ARCH-SIM-HKL-BOUNDS-001 to realign HKL sources.
2. If only Stage A drifts, inspect `_build_stage_a_context` vs. mapping configs to isolate the orientation or panel slicing difference.
