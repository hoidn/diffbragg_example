### Turn Summary
Prepared a ready-for-implementation plan so Stage A engine delegation consumes the mapping-adjusted baseline and records telemetry in DB-AT-029 artifacts.
Root cause is that `_build_stage_a_params` and `dbex/refinement/stage_a.py` never propagate `calibration_adjusted_for_n_cells`, so the engine path keeps doubling the spot scale even after mapping fixes it; the new Do Now covers helper/state/telemetry wiring plus the smoke selectors.
Next: Ralph implements the shared helper updates, runs the DB-AT-028/029 pytest pair, and reports whether `log_scale_baseline_source="mapping_global_scale_hint"` with the expected chi² failures still archived.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-26T020500Z/ (input.md, fix_plan updates)
