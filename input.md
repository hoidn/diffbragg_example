Summary: Baseline probe wiring still drops the new simulator partiality hook, so we have no “applied vs expected” evidence even though the partiality ledger shows Stage A/(|F|²·F_latt²·LP) ≈ 0. Fix the probe helpers to accept the CLI flags, summarize the nanobrag_torch debug payload into JSON-friendly aggregates, and rerun the mapped probe + DB-AT selectors so the next loop can compare simulator-emitted F_latt/Lorentz/polarization values against the ledger.
Mode: Parity
ActionType: parity_localization
DecisionStatus: localized
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --geometry-mode baseline --stage-a-mosaic-domains 16 --collect-hkl-stats --collect-spot-profiles --collect-orientation-metrics --collect-physics-ledger --collect-partiality-ledger --collect-simulator-partiality-stats --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-26T150000Z/stage_a_baseline_probe_baseline.json | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-26T150000Z/stage_a_baseline_probe_baseline.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-26T150000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-26T150000Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-26T150000Z/pytest_db_at_028_029.log
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-26T150000Z/
Findings Applied: SIM-CONSTR-LORENTZ-001
ARCH Contracts (mandatory):
  - docs/spec-db-conformance.md:255-349 — Owner: Stage A + mapping forward contract (DB-AT-027/028/029). Status: still violated (architecture conformance restoration in progress).
  - docs/architecture/data_telemetry_flow.md:6-41 — Owner: RefinementEngine zero-iteration simulator and telemetry stream. Status: still violated because reconstruction + diagnostics are not providing single-source-of-truth evidence.
  - docs/architecture/calibration_scaling.md:6-20 — Owner: Calibration ladder / spot_scale threading into simulators. Status: conformance restoration; simulator physics must reflect calibrated scaling.
Do Now (hard validity contract):
1. Implement: `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py::{collect_stage_a_hkl_stats,collect_mapping_hkl_stats,main}`
   - Add explicit parameters for the CLI flags (`collect_hkl_stats`, `collect_simulator_partiality_stats`) instead of referencing a non-existent global `args`. Thread those booleans into the `debug_config` dict that `_build_stage_a_context` and `simulate_forward_once` already accept, so the simulator hook actually runs.
   - When `Simulator.partiality_stats` is present, reduce the torch tensors to JSON-safe aggregates per panel (e.g., min/median/max for `f_latt`, `lorentz_factor`, `polarization_factor`, plus a flag when values are NaN/inf). Store these summaries under `stage_a` (and `simulate_forward_once` once diagnostics expose them) so the probe emits portable evidence instead of raw tensors.
   - Keep the existing HKL stats structure intact; do not add new CLI toggles or plan-local scripts — this edit is limited to fixing the flag plumbing and serialization inside the existing probe.
2. Validate by rerunning the mapped probe command and DB-AT-028/029 selector so the new `simulator_partiality_stats` block is populated alongside the known failing metrics. Capture logs/JSON under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-26T150000Z/`.
Forbidden This Loop: no new plan-local diagnostic scripts; no additional probe flags beyond the existing `--collect-simulator-partiality-stats`; do not modify `nanobrag_torch` source until the hook evidence lands.
ARCH Conformance Remediation: n/a (ActionType≠arch_conformance).
DMI Section:
- Independent Reference: DIALS refGeom smoke target + mapping stack (dbex/vis/mapping.py:94-223) continues to produce masked means ≈87 ADU with 4,140 masked pixels (`stage_a_baseline_probe_baseline.json:39-64`).
- Transformation Ledger:
  | Field/Tensor | Expected (units/shape/axis) | Producer (file:line) | Hydration (file:line) | Consumer (file:line) | Observed Evidence | Hypothesis |
  | --- | --- | --- | --- | --- | --- | --- |
  | Mapping target masked mean | ≈87 ADU on canonical loss mask | dbex/vis/mapping.py:94-223 | stage_a_baseline_probe_baseline.json:39-64 | tests/dbex/test_stage_a_smoke_parity.py:323-402 | `target_mean_masked=87.118`, `n_masked_pixels=4140` → reference stable | Control dataset trustworthy.
  | Stage A telemetry model_mean_masked | Should match mapping masked mean | dbex/refinement/stage_a.py:437-461 | dbex/refinement/reconstruction.py:167-253 | stage_a_baseline_probe_baseline.json:47-69 | Mean matches mapping yet `chi_squared_per_pixel_initial=1.00e6` → energy redistributed | Simulator physics missing a structural term.
  | ROI Panel 0 [644:656,21:33], HKL (-7,5,-3) | Stage A/Ref≈1, Stage A/|F|²·LP≈1 | Stage A forward (stage_a.py:437-519) | compare_stage_a_baseline.py:205-389 | spot_profile_summary.md:64-106 | `StageA/Ref=3.71e-05`, `StageA/|F|²·LP=0.0000`, LP=2.61 | Missing lattice term dominates.
  | ROI Panel 0 [431:443,434:446], HKL (0,2,-2) | Stage A/|F|²·F_latt²·LP≈1 | Same as above | compare_stage_a_baseline.py:709-1012 | spot_profile_summary.md:147-154 | `StageA/|F|²·F_latt²·LP=0`, `F_latt=5233.69` | Simulator never applies F_latt weighting.
  | DB-AT-028 chi²/pixel gate | ≤1e2 per spec | Stage A telemetry → writer | tests/dbex/test_stage_a_smoke_parity.py:323-402 | db_at_028/db_at_028_metrics.json:2-63 | `chi2_per_pixel_initial=2.10e5`, `roi_cc_median_before=-0.053` | DMI persists; fix must lift simulator intensity.
- Source Trace Anchors: dbex/vis/mapping.py:94-223 (independent reference), dbex/refinement/stage_a.py:403-519 (Stage A cache), dbex/refinement/reconstruction.py:167-253 (telemetry hydration), plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py:205-389 & 1400-2478 (diagnostics), tests/dbex/test_stage_a_smoke_parity.py:323-485 (acceptance gates).
- Consumption-State Measurements: loss mask on `cuda:0` with 4,140 pixels; `target_mean_masked=87.118` & `model_mean_masked=87.118` (stage_a_baseline_probe_baseline.json:47-64); `scale_factor=1.73456512e8` (same file); DB-AT-028 telemetry recorded in `db_at_028/db_at_028_metrics.json:2-63`.
- Boundary Bisection Step: repair the baseline probe so simulator partiality stats (F_latt/Lorentz/polarization) are captured and summarized per panel — this is the final allowed probe before editing nanobrag_torch physics.
- Probe Budget: Stage A baseline script already accumulated HKL + physics + partiality ledgers; this wiring fix consumes the final instrumentation slot. After the hook evidence lands, the next loop must move to the nanobrag_torch partiality implementation plan.
How-To Map: Fix the probe helpers (single file change), rebuild/activate existing env, rerun the mapped probe and DB-AT commands, and stash artifacts/logs under the new timestamp.
Pitfalls: Forgetting to pass the CLI flags into the helper functions will keep raising `name 'args' is not defined`; dumping raw torch tensors will break JSON serialization; omitting the DB-AT rerun would violate the DMI protocol.
If Blocked: Capture the exception + stdout/stderr under the new artifact path, update docs/fix_plan.md + galph_memory.md with the blocker, and stop — do not run additional probes without supervisor guidance.
