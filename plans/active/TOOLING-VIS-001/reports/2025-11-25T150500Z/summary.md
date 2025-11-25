### Turn Summary
Fixed sigma-source routing so cli_map metadata tiles flow correctly through _select_sigma_readout and mapping diagnostics emit distinguishable cli_map provenance strings.
Both mapping_context_fixture.json files now show sigma_provenance="cli_map (args.sigma_map)" instead of "cli_override (default scalar)" with calibration_path present.
DB-AT-028/029 pytest run completed with expected failures (chi²/pixel violations still present but unrelated to sigma routing fix); artifacts persisted per CONFORMANCE-001 Hard Gate.
Next: Investigate chi²/pixel and ROI correlation failures (likely calibration payload construction bugs per Phase D.D diagnosis) now that metadata sigma tiles correctly flow through mapping forward pass.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T150500Z/ (mapping_cpu_gpu_metadata/probe.log, pytest_db_at_028_029.log, db_at_028/mapping_context_fixture.json, db_at_029/mapping_context_fixture.json)

### Turn Summary (Prior — Supervisor Planning)
Queued the sigma-source routing fix so `_select_sigma_readout` finally consumes the metadata cli_map tiles and the mapping diagnostics report the right provenance.
Captured the blocker evidence from the last DB-AT-028/029 run, updated docs/fix_plan.md with the new plan, and rewrote input.md with the exact implementation + validation steps for Ralph.
Next: implement the helper/telemetry edit, rerun the mapping probe plus DB-AT-028/029 under the metadata env, and confirm both mapping_context fixtures show the metadata sigma source.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T150500Z/ (input.md, summary.md)
