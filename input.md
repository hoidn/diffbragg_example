Summary: Patch the nanobrag_torch square-lattice sincg path so fractional HKL deltas evaluated in float64 deliver the Na·Nb·Nc boost and land an enforcement test before rerunning the Stage A baseline probe plus DB-AT-028/029.
Mode: Parity
ActionType: arch_conformance
DecisionStatus: patch_ready
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: integration
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --geometry-mode baseline --stage-a-mosaic-domains 16 --collect-hkl-stats --collect-spot-profiles --collect-orientation-metrics --collect-physics-ledger --collect-partiality-ledger --collect-simulator-partiality-stats --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-27T010000Z/stage_a_baseline_probe_baseline.json | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-27T010000Z/stage_a_baseline_probe_baseline.log
  - PYTEST_ADDOPTS= KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells --maxfail=1 | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-27T010000Z/pytest_arch_partiality.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-27T010000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-27T010000Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-27T010000Z/pytest_db_at_028_029.log
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-27T010000Z/
Findings Applied: SIM-CONSTR-LORENTZ-001 (Lorentz guard), SCALE-009 (telemetry baseline contract)
Pointers:
  - docs/spec-db-core.md:60-140 — lattice weighting + calibration contracts
  - docs/config_crosswalk.md:61-85 — N_cells threading rules
  - docs/spec-db-conformance.md:139-172 — DB-AT-028/029 acceptance gates
  - docs/architecture/calibration_scaling.md:1-90 — Stage A scaling provenance
  - docs/diagnostic_script_policy.md:1-140 — probe budget / thin-wrapper guard
ARCH Contracts (mandatory):
  - docs/spec-db-core.md:60-140 — Owner: `nanobrag_torch.simulator.compute_physics_for_position` (SQUARE branch) must emit lattice weights proportional to `(Na·Nb·Nc)^2`; failure class: implementation bug (lattice boost collapses when sincg runs in float32 near integer HKLs).
  - docs/config_crosswalk.md:61-85 — Owner: `dbex.refinement.config_factories.create_crystal_config` + `nanobrag_torch.Simulator` must honor calibrated `N_cells` for stills; failure class: implementation bug (calibrated domain counts ignored by simulator math).
  - docs/spec-db-conformance.md:139-172 — Owner: Stage A + DB-AT-028/029 acceptance gates; failure class: conformance failure (chi²/pixel ≫1e2 and median ROI corr <0.2 while independent reference stays green).
Do Now (hard validity contract):
1. **Implement the fractional-delta sincg fix** — `src/nanobrag-torch/src/nanobrag_torch/simulator.py::compute_physics_for_position` lines 295-360:
   - Compute `delta_h = (h - torch.round(h))` (and similarly for k,l) in `torch.float64`, multiply inside `sincg(torch.pi * delta_h, Na)`/… so the arguments land near zero and the ratio returns ±N when the fractional offset is tiny. Downcast the final `f_latt` product back to the simulator dtype before combining with Lorentz/polarization.
   - Leave the ROUND/GAUSS/TOPHAT branches untouched and keep device dispatch the same.
2. **Capture Environment Freeze trail** — Rebuild the editable install (`python -m pip install -e src/nanobrag-torch`), run `git status -sb`, and save both the diff and command log to `plans/active/ARCH-SIM-CONSTRUCTION-001/patches/partiality_fix.patch` + `reports/2025-12-27T010000Z/environment.md`. Tag the state as `nanobrag-partiality-2025-12-26` per CLAUDE.md.
3. **Author the enforcement test + finding** — Create `tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells` that compares simulator intensity with `N_cells=(1,1,1)` vs `(41,29,32)` (or other >1 tuple) and asserts the ratio matches `(Na·Nb·Nc)^2 ± 5%`. Record the new node in docs/TESTING_GUIDE.md after it passes, stash logs under the artifact folder, and add SIM-CONSTR-PARTIALITY-001 to docs/findings.md citing the test + rebuild tag.
4. **Validate** — Rerun the mapped Stage A baseline probe (all ledgers enabled) and DB-AT-028/029 selectors with artifacts rooted at the new timestamp, proving `median StageA/(|F|²·F_latt²·LP) → 1` and the acceptance gates pass.
Forbidden This Loop:
  - no new plan-local diagnostic scripts or CLI flags beyond those listed above
  - do not modify ROUND/GAUSS/TOPHAT lattice branches
  - no additional probes or telemetry hooks (instrumentation budget exhausted)
  - leave Stage A/mapping/reconstruction code untouched except for test updates needed by the new enforcement node
DMI Section:
- **Independent Reference:** DIALS mapping ROI baseline (plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-26T150000Z/stage_a_baseline_probe_baseline.json) still reports `target_mean_masked=87.118` ADU with `n_masked_pixels=4140`.
- **Transformation Ledger:**
  | Field/Tensor | Expected (units) | Producer | Hydration | Consumer | Observed Evidence | Hypothesis |
  | --- | --- | --- | --- | --- | --- | --- |
  | Mapping ROI masked mean | ≈87 ADU | dbex/vis/mapping.py:94-223 | stage_a_baseline_probe_baseline.json:39-69 | tests/dbex/test_stage_a_smoke_parity.py:323-402 | `target_mean_masked=87.118` | Reference stable |
  | Stage A/|F|² ratio | ≈1 | dbex/refinement/stage_a.py:403-519 | spot_profile_summary.md:81-120 | DB-AT-028 telemetry | `median StageA/|F|²=0.0714` | Simulator misses lattice weight |
  | Stage A/|F|²·LP ratio | ≈1 | same | same | spot_profile_summary.md | `median StageA/(|F|²·LP)=0.0176` | Still Lorentz already fixed |
  | Stage A/|F|²·F_latt²·LP ratio | ≈1 | same + partiality ledger | spot_profile_summary.md:120-168 | DB-AT-028 | `median=0.0`, many ROIs ≤1e-4 | Lattice boost collapses |
  | Simulator hook `f_latt` | ≈Na·Nb·Nc≈38,048 | nanobrag_torch/simulator.py:295-360 | stage_a_baseline_probe_baseline.json:25-37 | compare_stage_a_baseline.py instrumentation | panel 0 median `f_latt=1.3e-4`, `f_latt_sq≈1` | sincg underflows near integer HKLs |
- **Source Trace Anchors:** dbex/refinement/stage_a.py:403-519, dbex/refinement/reconstruction.py:167-253, plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py:205-389 & 709-1012, tests/dbex/test_stage_a_smoke_parity.py:323-485, src/nanobrag-torch/src/nanobrag_torch/simulator.py:295-523.
- **Consumption-State Measurements:** Stage A baseline probe + simulator stats show `scale_factor=1.73456512e8`, hook median `f_latt=1.2957e-4`, DB-AT-028 `chi2_per_pixel_initial=2.0979e5`, `roi_cc_median_before=-0.053`.
- **Boundary Bisection Step:** Patch the SQUARE sincg path, then re-run the baseline probe + DB-AT selectors to verify `Stage A/(|F|²·F_latt²·LP)` converges to ~1 before chasing downstream effects.
- **Probe Budget:** Final instrumentation hook already in place; no new probes allowed until this fix lands.
How-To Map:
  1. Apply the simulator edit, run `python -m pip install -e src/nanobrag-torch` (log command + timestamp), and save `git diff src/nanobrag-torch` to `patches/partiality_fix.patch`.
  2. Execute the mapped Stage A baseline probe command (tee logs + JSON into the artifact directory). Confirm `simulator_partiality_stats.stage_a` now reports `f_latt` medians ≈Na·Nb·Nc and `StageA/(|F|²·F_latt²·LP)` ratios ≈1 in `spot_profile_summary.md`.
  3. Run the new architecture test under `pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells` (tee log + collect-only output) and update docs/TESTING_GUIDE.md selectors once it passes.
  4. Re-run DB-AT-028/029 with artifact dirs pointed at the new timestamp; stash metrics + pytest logs.
Pitfalls To Avoid:
  - forgetting to upcast deltas to float64 before calling `sincg`
  - mutating ROUND/GAUSS/TOPHAT branches (only fix SQUARE)
  - omitting the Environment Freeze rebuild/tag + patch file
  - lowering DB-AT acceptance thresholds instead of fixing physics
  - adding new plan-local probes or CLI toggles (violates probe-freeze guard)
  - skipping the architecture test or docs/findings updates
  - running DB-AT selectors without `AUTHORITATIVE_CMDS_DOC` + required env vars
If Blocked:
  - Capture failing command output (probe, pytest, or rebuild) under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-27T010000Z/`, update docs/fix_plan.md + galph_memory.md with the blocker reason, and stop. Do not add new probes; escalate to supervisor if simulator edit cannot proceed under Environment Freeze rules.
Doc Sync Plan:
  - After `tests/architecture/test_nanobrag_partiality.py` lands, run `pytest --collect-only tests/architecture/test_nanobrag_partiality.py > plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-27T010000Z/collect_arch_partiality.log` and update `docs/TESTING_GUIDE.md` / `docs/development/TEST_SUITE_INDEX.md` with the new selector + artifact path once the code passes.
