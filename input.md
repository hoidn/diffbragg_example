Summary: Sample multiple calibrated mosaic domains instead of a single perfect-crystal sinc so Stage A/mapping/reconstruction simulators stop redistributing intensity into a few ROIs and recover positive DB-AT-028/029 correlations.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBEX_SMOKE_HKL_PATH=sp.proc/calibration/smoke_refined_structure_factors_small.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --geometry-mode baseline --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-21T180000Z/stage_a_baseline_probe_baseline.json
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBEX_SMOKE_HKL_PATH=sp.proc/calibration/smoke_refined_structure_factors_small.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --geometry-mode perturbed --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-21T180000Z/stage_a_baseline_probe_perturbed.json
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-21T180000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-21T180000Z/db_at_029 DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-21T180000Z/pytest_db_at_028_029.log
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-21T180000Z/

Do Now (hard validity contract):
- Implement: `dbex/refinement/config_factories.py::create_crystal_config`
  - Add a `mosaic_domains_override` gate (default None) so callers can request >1 mosaic samples; clamp overrides ≥1 and record the applied count in diagnostics alongside the existing mosaic spread metadata.
  - Thread a new `stage_a_mosaic_domains` integer through `RefinementConfig` (default ≥16 so the sinc kernel averages) and have every Stage A/mapping/reconstruction entry point that calls `create_crystal_config` (Stage A warm cache, `simulate_forward_once`, reconstruction cold path, helper scripts) pass the shared value; fall back to 1 only when config explicitly disables the feature.
  - Keep Stage A vs mapping lockstep by logging `mosaic_spread_deg` + `mosaic_domains` inside `stage_a_baseline_probe*.json`, DB-AT diagnostics (`baseline_stats.json`, `mapping_context_fixture.json`), and cold-path telemetry so the new ledger can cite the settings.
  - Rebuild the Stage A baseline probes (baseline + perturbed) and rerun DB-AT-028/029 under the commands above so this artifact set shows the effect of multi-domain sampling on ROI-level chi²/correlation.

Deterministic Parity Crisis:
- Independent Reference: DIALS reflection table `sp.proc/refGeom_small/refGeom_small.refl` stays independent of nanobrag_torch yet matches the measured ROIs (median target/reference ≈ 1.02), so it remains the contract for ROI-scale intensity.
- Transformation Ledger: `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-21T180000Z/transformation_ledger.md` captures five representative ROIs (panel 0, varying HKLs) showing Stage A/Ref ratios ranging from 7.1e-05 to 2.34e+02 while Target/Ref ≈ 1.0. Example: ROI 14 bbox [431,443,434,446] HKL (0,2,−2) has Stage A 4.08e+02 ADU vs target 2.48 ADU despite |F|² per pixel 3.91e+01. Conversely, ROI 0 HKL (−10,2,0) collapses to 1.99e-02 ADU vs reference 8.69 ADU (Stage A/Ref ≈ 2.3e-03). With Stage A vs mapping CC=0.999, the distortion is produced by the simulator’s single-domain sinc kernel, not reconstruction or telemetry.
- Boundary Bisection Step: If multi-domain sampling still leaves ROI correlations negative, enable the existing HKL stats hook with ROI identifiers inside `compare_stage_a_baseline.py` so the next loop can compare per-ROI HKL coverage (producer: `nanobrag_torch.simulator.compute_physics_for_position`, consumer: DB-AT probes) before diving into Lorentz/polarization math.

How-To Map:
- Extend `RefinementConfig` with a `stage_a_mosaic_domains` field (default 32 recommended) and wire it through `_build_stage_a_context`, `simulate_forward_once`, reconstruction’s `build_final_bragg_from_stage_a_telemetry`, and any helper that instantiates a `CrystalConfig` so every forward path samples the same mosaic grid.
- Update `create_crystal_config` to accept the override, clamp to ≥1, and keep existing stills default (1) when no override is provided—this keeps CLI/tests that expect the legacy behavior untouched.
- Persist the applied `mosaic_spread_deg` and `mosaic_domains` in `baseline_stats.json`, the baseline probe outputs, and the DB-AT diagnostics so regression triage has exact parameter values without rerunning the probe.
- Re-run the two probe commands first so you can diff ROI metrics before committing to the DB-AT run; both probes should reference the new artifact directory.
- Use the existing DB-AT env vars verbatim so the only changing variable is mosaic sampling; capture pytest stdout in the mapped log for review.

Pitfalls:
- Forgetting to pass the override into `simulate_forward_once` leaves mapping in zero-mosaic mode and instantly reintroduces the deterministic CC collapse.
- Accidentally applying the override twice (e.g., setting both `crystal_kwargs['mosaic_domains']` and manually summing intensity) will break torch autograd and spike runtimes.
- Values <1 must be clamped; letting 0 slip through will crash nanobrag_torch when it allocates rotation tensors.
- Diagnostics need to live behind existing artifact guards—do not spam production stdout with mosaic metadata.
- Keep CLI default behavior intact: only Stage A/mapping/reconstruction should request >1 domains until CLI flags exist; otherwise tests like `test_nanobrag_bridge_configs` will fail.
- Ensure reconstruction cold path and warm cache share the same domain count or DB-AT-028/029 will diverge between cache-hit and cache-miss cases.
- Do not change HKL ingestion or scale logic in this loop; the only allowed knob is the number of sampled mosaic orientations.
- Watch GPU memory: `mosaic_domains` multiplies tensor sizes; start with 16–32 and monitor runtime before pushing higher.
- Remember to update unit tests/mocks that assert on the `create_crystal_config` call signature.
- After code changes, clear stale `.pyc` if you edit files imported inside tests to avoid latent behavior.

If Blocked:
- Capture the failure (stack trace or pytest output) plus the command/env used into `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-21T180000Z/summary.md`, note it under ARCH-SIM-CONSTRUCTION-001 Attempts History in docs/fix_plan.md, log the same state in galph_memory.md, and flag whether the block requires a nanobrag_torch source patch (harness initiative) before scheduling another implementation loop.
