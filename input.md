Summary: Regenerate the missing refGeom_small assets and rerun the Stage B/C telemetry probe so we can capture real Stage A improvement traces before touching Stage A code.
Mode: Parity
Focus: ARCH-REFINE-001 — Refinement Engine Modularization & Torch IO
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py -k "test_stage_b_shell_modifiers or test_stage_c_detector_microslip" --smoke-detector-size=small
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T105500Z/
Do Now:
- Implement: plans/active/PERF-SMOKE-DETSIZE/bin/crop_refgeom_to_small.py::main — rerun the crop script with the canonical window (fast 751, slow 719, width/height 1024) so `sp.proc/refGeom_small/{refGeom_small.expt,refGeom_small.refl,refGeom_small_mask.pkl}` exist again; capture the JSON report under the new artifacts directory for reproducibility.
- Implement: plans/active/ARCH-REFINE-001/bin/capture_stage_c_stage_a_probe.py::main — after the assets land, rerun the telemetry probe (first with `--sigma-source cli_override`, optionally repeat for `metadata`) to dump Stage A/Stage C traces into the new report path; keep stdout/JSON under the artifacts directory.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-001/reports/2025-12-01T105500Z/telemetry_stage_bc_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py -k "test_stage_b_shell_modifiers or test_stage_c_detector_microslip" --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T105500Z/pytest_stage_bc_small.log
How-To Map:
1. mkdir -p sp.proc/refGeom_small && python plans/active/PERF-SMOKE-DETSIZE/bin/crop_refgeom_to_small.py --expt refGeom.expt --refl refGeom.refl --cbf lys_nitr_10_6_0001.cbf --mask 747_mask.pkl --fast-start 751 --slow-start 719 --width 1024 --height 1024 --output-root sp.proc/refGeom_small --report plans/active/ARCH-REFINE-001/reports/2025-12-01T105500Z/refGeom_small_crop_report.json --background-pad 3; verify the script emits refGeom_small.{expt,refl,mask} plus README.
2. python plans/active/ARCH-REFINE-001/bin/capture_stage_c_stage_a_probe.py --detector-size small --sigma-source cli_override --output plans/active/ARCH-REFINE-001/reports/2025-12-01T105500Z/stage_c_stage_a_probe_cli.json > plans/active/ARCH-REFINE-001/reports/2025-12-01T105500Z/stage_c_stage_a_probe_cli.log; rerun with `--sigma-source metadata` only if `sp.proc/refGeom_small/idx-0000_sigma_metadata_small.sigma_tiles.pkl` exists.
3. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py -k "test_stage_b_shell_modifiers or test_stage_c_detector_microslip" --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T105500Z/collect_stage_bc_small.log, then run the full selector command listed above, ensuring telemetry JSON/logs land in the same report directory.
Pitfalls To Avoid:
- Use the canonical crop window (fast 751–1775, slow 719–1743) so ROI metadata remains aligned; do not eyeball new bounds.
- Keep `DBEX_SMOKE_SIGMA_SOURCE` consistent between the probe and pytest run (start with cli_override) so Stage A traces match the recorded failure mode.
- Do not relax REFINE-007 gates or PHYSICS-LOSS-001 telemetry requirements—this loop is about restoring data + evidence, not weakening checks.
- Make sure `DBEX_SMOKE_TELEMETRY_PATH` points at the new timestamped directory so Stage B/C logs aren’t mixed with older attempts.
- When rerunning the probe, leave `device='cuda:0'` and `roi_sample_fraction=0.15` untouched; mismatched config will not reproduce the bug.
- Avoid modifying Stage A/B/C source files until we have fresh telemetry; this loop is evidence-only.
If Blocked:
- If the crop script fails because upstream assets (refGeom.expt, lys_nitr_10_6_0001.cbf, 747_mask.pkl) are missing, capture the stderr in plans/active/ARCH-REFINE-001/reports/2025-12-01T105500Z/crop_blocked.log, note the missing inputs in docs/fix_plan.md and galph_memory.md, and stop before touching Stage A code.
Findings Applied (Mandatory):
- REFINE-007 — Stage C detector-offset gates require Stage A telemetry improvements before validation; restoring the dataset ensures the original gate stays meaningful.
- PHYSICS-LOSS-001 — Stage B/C telemetry must include chi-squared + masked-MSE traces; the probe reuses this schema when dumping Stage A traces.
- PERF-WARM-006 — Stage B/C smokes rely on Stage A detector contexts and warmed caches from the same dataset, so the regenerated refGeom_small bundle has to match the manifest.
Pointers:
- docs/data_dependency_manifest.md:52 — Canonical paths and crop window for refGeom_small assets.
- plans/active/PERF-SMOKE-DETSIZE/bin/crop_refgeom_to_small.py:1 — Crop script CLI + workflow for regenerating the small-detector bundle.
- docs/TESTING_GUIDE.md:161 — Stage B/C smoke selector command/flags (`--smoke-detector-size`, telemetry capture expectations).
Next Up (optional): Once telemetry is captured, resume the Stage A improvement diagnosis (dbex/refinement/stage_a_impl.py::_run_stage_a_lbfgs) and re-validate Stage B/C smokes with the real traces.
