Summary: Instrument the simulator's partiality debug hook so we can capture Δh/Δk/Δl + per-axis sincg distributions from a real Stage A run before attempting another lattice patch.
Mode: Parity
ActionType: parity_localization
DecisionStatus: localized
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: integration
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --geometry-mode baseline --stage-a-mosaic-domains 16 --collect-hkl-stats --collect-spot-profiles --collect-orientation-metrics --collect-physics-ledger --collect-partiality-ledger --collect-simulator-partiality-stats --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-27T180000Z/stage_a_baseline_probe_baseline.json | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-27T180000Z/stage_a_baseline_probe_baseline.log
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-27T180000Z/
Findings Applied (Mandatory): SIM-CONSTR-PARTIALITY-001 (square lattice sincg precision guard), SIM-CONSTR-LORENTZ-001 (Lorentz telemetry proof), SCALE-009 (Stage A baseline calibration + telemetry provenance)
Pointers:
  - docs/spec-db-core.md:60-140 — lattice weighting requirements + calibration threading
  - docs/config_crosswalk.md:61-118 — ownership of N_cells / apply_calibration_n_cells flags
  - docs/spec-db-conformance.md:120-210 — DB-AT-028/029 acceptance metrics driving this initiative
  - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-27T120000Z/summary.md — latest failed sincg patch and residual evidence gaps
ARCH Contracts (mandatory):
  - docs/spec-db-core.md:60-140 — Owner `nanobrag_torch.simulator.compute_physics_for_position` (SQUARE branch); failure class: implementation bug (lattice weighting collapses).
  - docs/config_crosswalk.md:61-118 — Owners `dbex.refinement.config_factories` + `nanobrag_torch.Simulator` must honor calibrated N_cells / apply_calibration_n_cells; failure class: implementation bug (calibrated domain counts ignored).
  - docs/spec-db-conformance.md:120-210 — Owners Stage A baseline probe + DB-AT-028/029 selectors; failure class: conformance failure (chi²≫1e2, ROI corr<0.2 despite reference parity).
Do Now (hard validity contract)
1. Implement: `src/nanobrag-torch/src/nanobrag_torch/simulator.py::compute_physics_for_position` (SQUARE branch, partiality hook) — when `debug_config.get('collect_partiality_stats')` is true, extend the per-panel stats dict to include percentiles (min/1e-4/median/0.999/max) for `delta_h`, `delta_k`, `delta_l` (fractional HKLs prior to rounding) and for the individual sincg factors (`F_latt_a`, `_b`, `_c`) before the product. Keep the hook opt-in (no new CLI scripts) and respect existing device/dtype guards.
2. Update the Stage A baseline probe consumer: `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py` should plumb the new stats through `_serialize_partiality_stats_to_json` and render a markdown section summarizing fractional-delta distributions and per-axis sincg behavior. Avoid new CLI flags; reuse the existing `--collect-simulator-partiality-stats` switch.
3. Rerun the mapped baseline probe command (baseline geometry, all ledger flags) and archive JSON, logs, and the refreshed `spot_profile_summary.md` under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-27T180000Z/` so we have decision-carrying evidence on whether ROIs actually sit near integer HKLs.
Forbidden This Loop:
  - no further simulator physics changes (do not attempt another sincg patch yet)
  - no new plan-local diagnostic scripts or CLI flags (stick to the existing debug hook)
  - do not rerun DB-AT-028/029 until instrumentation proves where the lattice collapse occurs
DMI Section:
- **Independent Reference:** `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-26T150000Z/stage_a_baseline_probe_baseline.json` (mapping masked mean 87.118 ADU, chi² green) remains authoritative.
- **Transformation Ledger:**
  | Field/Tensor | Expected (units) | Producer | Hydration | Consumer | Observed Evidence | Hypothesis |
  | --- | --- | --- | --- | --- | --- | --- |
  | Mapping ROI masked mean | ≈87 ADU | dbex/vis/mapping.py | Stage A baseline probe JSON | DB-AT-028 harness | `target_mean_masked=87.118` | Reference stable |
  | Stage A/|F|² ratio | ≈1 | dbex/refinement/stage_a.py | spot_profile_summary.md | DB-AT-028 telemetry | `median StageA/|F|²=0.0714` | Missing lattice boost |
  | Stage A/|F|²·LP ratio | ≈1 | same | same | same | `median=0.0176` | Lorentz fixed, lattice collapsed |
  | Stage A/|F|²·F_latt²·LP ratio | ≈1 | stage_a baseline + partiality ledger | same | DB-AT-028 metrics | `median=0` | SQUARE sincg path never returns Na·Nb·Nc |
  | Simulator hook `f_latt` | ≈Na·Nb·Nc≈38k | nanobrag_torch/simulator.py | stage_a_baseline_probe_baseline.json | compare_stage_a_baseline.py | panel 0 median `f_latt=1.3e-4`, `f_latt_sq≈1` | Need stats on Δh/Δk/Δl vs sincg factors |
- **Source Trace Anchors:** dbex/refinement/stage_a.py:403-519; dbex/refinement/reconstruction.py:167-253; plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py:709-1050; tests/architecture/test_nanobrag_partiality.py:27-120; src/nanobrag-torch/src/nanobrag_torch/simulator.py:295-360.
- **Consumption-State Measurements:** Baseline probe + simulator hook show `scale_factor=1.735e8`, `chi2_per_pixel_initial≈1.0e6`, and `f_latt` medians ≈1.3e-4 while reference stays ≈1 — deterministic DMI persists.
- **Boundary Bisection Step:** Capture Δh/Δk/Δl + per-axis sincg distributions from the real Stage A path to confirm whether sincg sees near-integer arguments before touching simulator physics again.
- **Probe Budget:** Plan-local probe budget exhausted; instrumentation must live in production code/hook and reuse the existing baseline probe command.
How-To Map:
  1. Edit `src/nanobrag-torch/src/nanobrag_torch/simulator.py` to enrich the `collect_partiality_stats` payload with the requested percentiles for Δh/Δk/Δl and `F_latt_a/b/c`; keep tensors on-device and downcast to CPU only when serializing aggregates.
  2. Update `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py` so `_serialize_partiality_stats_to_json` and `spot_profile_summary.md` integrate the new stats (tables or bullet summaries) without introducing new CLI flags.
  3. Run the mapped baseline probe command from repo root; stash `stage_a_baseline_probe_baseline.{json,log}`, the refreshed `spot_profile_summary.md`, and any console summaries inside `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-27T180000Z/`.
Pitfalls To Avoid:
  - Do not re-attempt the sincg float64 patch or any other simulator physics change until the fractional-delta evidence exists.
  - Keep the debug hook opt-in; default runs must see zero overhead.
  - Avoid introducing new plan-local scripts or CLI switches (ARCH-PROBE-FREEZE-001).
  - Don’t skip the probe run—without artifacts under the new timestamp the docs ledger is incomplete.
  - Watch for accidental tensor/device conversions when summarizing stats; keep reductions cheap.
If Blocked:
  - Capture the failing command/log in the artifacts directory, annotate `docs/fix_plan.md` + `galph_memory.md` with the blocker, and halt. Do not broaden scope to new probes or tests without supervisor approval.
Doc Sync Plan (Conditional): none — no new pytest selectors in this loop.
