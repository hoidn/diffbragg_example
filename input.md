Summary: Patch nanobrag_torch's square-lattice sincg path with float64 fractional deltas, add an enforcement test, and rerun the Stage A baseline probe plus DB-AT-028/029 to prove the Na·Nb·Nc boost is restored.
Mode: Parity
ActionType: arch_conformance
DecisionStatus: patch_ready
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: integration
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --geometry-mode baseline --stage-a-mosaic-domains 16 --collect-hkl-stats --collect-spot-profiles --collect-orientation-metrics --collect-physics-ledger --collect-partiality-ledger --collect-simulator-partiality-stats --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-27T120000Z/stage_a_baseline_probe_baseline.json | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-27T120000Z/stage_a_baseline_probe_baseline.log
  - PYTEST_ADDOPTS= KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells --maxfail=1 | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-27T120000Z/pytest_arch_partiality.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-27T120000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-27T120000Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-27T120000Z/pytest_db_at_028_029.log
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-27T120000Z/
Findings Applied: SIM-CONSTR-LORENTZ-001 (Lorentz guard already proven), SCALE-009 (Stage A baseline calibration + telemetry provenance), SIM-CONSTR-PARTIALITY-001 (square-lattice sincg precision requirement + enforcement expectation)
Pointers:
  - docs/spec-db-core.md:60-140 — lattice weighting + calibration contracts
  - docs/config_crosswalk.md:61-118 — `N_cells` threading rules and simulator ownership
  - docs/spec-db-conformance.md:120-210 — DB-AT-028/029 acceptance gates
  - docs/architecture/calibration_scaling.md:1-120 — Stage A scaling provenance + environment-freeze expectations
  - docs/diagnostic_script_policy.md:1-140 — thin-wrapper guard (no new probes)
ARCH Contracts (mandatory):
  - docs/spec-db-core.md:60-140 — Owner `nanobrag_torch.simulator.compute_physics_for_position` (SQUARE branch) must emit lattice weights proportional to `(Na·Nb·Nc)^2`; failure type: implementation bug (float32 sincg collapses near integer HKLs).
  - docs/config_crosswalk.md:61-118 — Owners `dbex.refinement.config_factories.create_crystal_config` + `nanobrag_torch.Simulator` must honor calibrated `N_cells` and device/dtype rules; failure type: implementation bug (calibrated domain counts ignored).
  - docs/spec-db-conformance.md:120-210 — Owners Stage A baseline probe + DB-AT-028/029 selectors; failure type: conformance failure (chi²≫1e2, ROI corr <0.2 while reference is green).
Do Now (hard validity contract):
1. Implement: `src/nanobrag-torch/src/nanobrag_torch/simulator.py::compute_physics_for_position` (SQUARE branch, lines 295-360) — compute `delta_h = (h - torch.round(h))`, `delta_k`, `delta_l` in `torch.float64`, feed those into `sincg(torch.pi * delta, N)` inside float64 math, multiply the factors before downcasting back to the simulator dtype, and leave ROUND/GAUSS/TOPHAT logic untouched so device/dtype dispatch stays canonical.
2. Capture Environment Freeze trail — Save the simulator diff to `plans/active/ARCH-SIM-CONSTRUCTION-001/patches/partiality_fix.patch`, rerun `python -m pip install -e src/nanobrag-torch`, log the rebuild/tag (`nanobrag-partiality-2025-12-27`) in `reports/2025-12-27T120000Z/environment.md`, and note the commands inside the same artifact directory.
3. Author the enforcement test + findings — Create `tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells` that compares simulator intensity with `N_cells=(1,1,1)` vs `(41,29,32)` (or another >1 tuple) and asserts the ratio matches `(Na·Nb·Nc)^2 ±5%`, update `docs/TESTING_GUIDE.md` + `docs/development/TEST_SUITE_INDEX.md` once the test passes, run/tee pytest + collect logs to the artifact directory, and add SIM-CONSTR-PARTIALITY-001 details (patch + rebuild tag + validation pointers) to `docs/findings.md`.
4. Validate — Re-run the Stage A baseline probe with every ledger flag plus DB-AT-028/029 selectors using the commands above, stash JSON/log artifacts + newly generated partiality/physics summaries under the timestamped directory, and confirm `StageA/(|F|²·F_latt²·LP)` ratios collapse toward 1 before recording chi²/ROI corr improvements.
Forbidden This Loop:
  - no new plan-local diagnostic scripts, CLI flags, or probes beyond the mapped commands
  - do not touch ROUND/GAUSS/TOPHAT lattice branches or unrelated simulator code paths
  - no edits to Stage A/mapping/reconstruction beyond the enforcement test + docs
  - no relaxation of DB-AT acceptance thresholds or telemetry guards
DMI Section:
- **Independent Reference:** `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-26T150000Z/stage_a_baseline_probe_baseline.json` (mapping ROI masked mean `target_mean_masked=87.118` ADU, `n_masked_pixels=4140`) remains stable — reference stays green.
- **Transformation Ledger:**
  | Field/Tensor | Expected (units) | Producer | Hydration | Consumer | Observed Evidence | Hypothesis |
  | --- | --- | --- | --- | --- | --- | --- |
  | Mapping ROI masked mean | ≈87 ADU | dbex/vis/mapping.py:94-223 | stage_a_baseline_probe_baseline.json:39-69 | tests/dbex/test_stage_a_smoke_parity.py:323-402 | `target_mean_masked=87.118` | Reference stable |
  | Stage A/|F|² ratio | ≈1 | dbex/refinement/stage_a.py:403-519 | spot_profile_summary.md:81-120 | DB-AT-028 telemetry | `median StageA/|F|²=0.0714` | Simulator missing lattice boost |
  | Stage A/|F|²·LP ratio | ≈1 | same | same | spot_profile_summary.md | `median StageA/(|F|²·LP)=0.0176` | Polarization/Lorentz fixed |
  | Stage A/|F|²·F_latt²·LP ratio | ≈1 | stage_a baseline + partiality ledger | spot_profile_summary.md:120-168 | DB-AT-028 metrics | `median=0`, many ROIs ≤1e-4 | Lattice factor collapses |
  | Simulator hook `f_latt` | ≈Na·Nb·Nc≈38,048 | nanobrag_torch/simulator.py:295-360 | stage_a_baseline_probe_baseline.json:25-37 | compare_stage_a_baseline.py instrumentation | panel 0 median `f_latt=1.3e-4`, `f_latt_sq≈1` | sincg underflows near integer HKLs |
- **Source Trace Anchors:** dbex/refinement/stage_a.py:403-519; dbex/refinement/reconstruction.py:167-253; plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py:205-389 & 709-1012; tests/dbex/test_stage_a_smoke_parity.py:323-485; src/nanobrag-torch/src/nanobrag_torch/simulator.py:295-523.
- **Consumption-State Measurements:** Stage A baseline probe + simulator stats show `scale_factor=1.73456512e8`, hook median `f_latt=1.2957e-4`, DB-AT-028 `chi2_per_pixel_initial=2.0979e5`, `roi_cc_median_before=-0.053`.
- **Boundary Bisection Step:** Patch the SQUARE sincg path with float64 fractional deltas, then rerun the baseline probe + DB-AT selectors to verify `Stage A/(|F|²·F_latt²·LP)` medians approach 1 before chasing downstream effects.
- **Probe Budget:** Exhausted — diagnostics must stay within existing hooks and mapped commands (per ARCH-PROBE-FREEZE-001).
How-To Map:
  1. Modify `compute_physics_for_position` (SQUARE branch only) per Do Now Step 1, run `python -m pip install -e src/nanobrag-torch`, and capture both the `git diff src/nanobrag-torch` and rebuild command log into `plans/active/ARCH-SIM-CONSTRUCTION-001/patches/partiality_fix.patch` + `reports/2025-12-27T120000Z/environment.md`.
  2. Implement `tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells`, run the targeted pytest command (tee log to the artifacts directory), and follow up with `pytest --collect-only tests/architecture/test_nanobrag_partiality.py > plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-27T120000Z/collect_arch_partiality.log` once the test passes.
  3. Execute the mapped Stage A baseline probe command (all ledger flags enabled) so `stage_a_baseline_probe_baseline.{json,log}` and `spot_profile_summary.md` inside the artifacts directory record the restored `f_latt` medians and ratio bins.
  4. Re-run DB-AT-028/029 selectors with the specified env vars (`DBAT028_ARTIFACT_DIR`, `DBAT029_ARTIFACT_DIR`), saving pytest logs + metrics JSON files, and confirm chi²/pixel initial ≤1e2 and ROI correlation ≥0.2 once the lattice fix lands.
  5. Update `docs/TESTING_GUIDE.md`, `docs/development/TEST_SUITE_INDEX.md`, and `docs/findings.md` with the new architecture test + SIM-CONSTR-PARTIALITY-001 evidence referencing the patch + artifact paths.
Pitfalls To Avoid:
  - Forgetting to upcast fractional HKL deltas to float64 before calling `sincg`, which leaves the Na·Nb·Nc boost broken.
  - Touching ROUND/GAUSS/TOPHAT or unrelated simulator code paths (violates narrow scope + probe freeze).
  - Skipping the editable reinstall/tag and patch file required by the Environment Freeze exception.
  - Relaxing DB-AT-028/029 acceptance gates instead of fixing simulator physics.
  - Adding new plan-local probes or CLI toggles beyond the mapped commands (ARCH-PROBE-FREEZE-001 guard).
  - Neglecting to update docs/test registries or findings after the enforcement test lands.
  - Omitting the new architecture test from the mapped pytest suite or failing to capture collect-only output.
If Blocked:
  - Capture the failing command/log inside `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-27T120000Z/`, update `docs/fix_plan.md` + `galph_memory.md` with the blocker, and stop — do not add new probes or broaden scope without supervisor approval.
Doc Sync Plan:
  - After the enforcement test passes, run `pytest --collect-only tests/architecture/test_nanobrag_partiality.py > plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-27T120000Z/collect_arch_partiality.log`, then update `docs/TESTING_GUIDE.md` and `docs/development/TEST_SUITE_INDEX.md` with the selector name, command, and artifact references once code/tests succeed.
