Summary: Instrument `nanobrag_torch.simulator` with an opt-in partiality debug hook so we can capture the actual `F_latt` / polarization contributions that Stage A applies, prove the lattice term is missing, and unblock the next physics fix for DB-AT-028/029.
Mode: Parity
ActionType: parity_localization
DecisionStatus: localized
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --geometry-mode baseline --stage-a-mosaic-domains 16 --collect-hkl-stats --collect-spot-profiles --collect-orientation-metrics --collect-physics-ledger --collect-partiality-ledger --collect-simulator-partiality-stats --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-26T010000Z/stage_a_baseline_probe_baseline.json | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-26T010000Z/stage_a_baseline_probe_baseline.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-26T010000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-26T010000Z/db_at_029 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-26T010000Z/pytest_db_at_028_029.log
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-26T010000Z/
Findings Applied: SIM-CONSTR-LORENTZ-001

Do Now (hard validity contract):
1. Implement: `src/nanobrag-torch/src/nanobrag_torch/simulator.py::compute_physics_for_position`
   - Add an opt-in `debug_config['collect_partiality_stats']` pathway (Environment Freeze exception) that records per-ROI `lorentz_factor`, `polarization_factor`, `partiality_factor` (F_latt²), and the raw `F_latt` triple before intensity normalization. Emit these stats via `self.hkl_stats['partiality']` alongside the existing HKL coverage telemetry so downstream probes can consume them without modifying production behavior.
2. Implement: `dbex/refinement/stage_a_utils.py::_build_stage_a_context`
   - Thread a `debug_config` dict through warm-cache simulator construction when the Stage A baseline probe requests simulator partiality stats (e.g., via a new keyword). Guard so production runs leave `debug_config=None`, but probe-mode execution can set `{'collect_hkl_stats': True, 'collect_partiality_stats': True}` to harvest the simulator evidence.
3. Implement: `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py::main`
   - Add `--collect-simulator-partiality-stats` (default off). When enabled, pass the new debug flags into both Stage A warm caches and `simulate_forward_once`, capture the returned partiality telemetry, and persist it next to the existing partiality ledger so we can compare “expected” (computed from calibration) vs “applied” (from nanobrag_torch) factors.
4. Validate with the mapped probe plus DB-AT-028/029 commands so the new simulator-level telemetry is captured, and the acceptance tests still demonstrate the deterministic failure signature under the instrumented build.
5. Artifacts path: `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-26T010000Z/` must contain the updated probe JSON/Markdown, simulator partiality stats, and pytest logs.

Forbidden This Loop:
- No new plan-local diagnostic scripts; all instrumentation must flow through `compare_stage_a_baseline.py` and the simulator debug hook.
- Do not introduce additional probe toggles beyond the partiality stats flag; probe budget for the Stage A baseline script is exhausted after this loop.

DMI Section:
- Independent Reference: DIALS reflection table `sp.proc/refGeom_small/refGeom_small.refl` (ingested via `dbex/vis/mapping.py:94-207`) provides ROI-level intensity sums and masks that remain ≈1× Stage A targets; mapping diagnostics confirm the control reference is stable.
- Transformation Ledger:
  | Field/Tensor | Expected (units/axis) | Producer (file:line) | Hydration (file:line) | Consumer (file:line) | Observed Evidence | Hypothesis |
  | --- | --- | --- | --- | --- | --- | --- |
  | `mapping_context.inputs.target` masked mean | ADU/pixel on canonical loss mask | dbex/vis/mapping.py:94-223 | compare_stage_a_baseline.py:205-289 | tests/dbex/test_stage_a_smoke_parity.py:69-152 | `target_mean_masked=87.118 ADU`, `n_masked_pixels=4140` (stage_a_baseline_probe_baseline.json:111-140) — matches DIALS reference. | Independent dataset is sound; divergence is internal to simulator. |
  | HKL amplitude grid `|F|²/pix` | amplitude-squared per ROI | dbex/nanobrag_bridge.py:856-975 | compare_stage_a_baseline.py:205-243 | stage_a_baseline_probe_baseline.json:3200-3207 | Median `|F|²/pix ÷ Ref = 1.1447`, min 0.289, max 6872 (same JSON). | HKL ingestion honors SCALE-001; mismatch lies downstream. |
  | Stage A zero-iter Bragg stack | ADU/pixel per ROI | dbex/refinement/stage_a.py:403-519 | dbex/refinement/reconstruction.py:167-253 | stage_a_baseline_probe_baseline.json:451-2908 | Median `StageA ÷ Ref = 0.0499`, ROI ratios span 3.7e-05–5.14e+02 (spot_profile_summary.md:64-116). | Simulator redistributes energy, not a simple scalar offset. |
  | Stage A vs `|F|²·LP` | dimensionless | compare_stage_a_baseline.py:514-640 | plans/.../spot_profile_summary.md:79-116 | plans/.../stage_a_baseline_probe_baseline.json:3545-3579 | Median `StageA ÷ |F|²·LP = 0.0176` (spot_profile_summary.md:83-121) despite LP factors 2.6–11.7×. | Lorentz term now present, yet 60× deficit persists, implicating lattice partiality. |
  | Stage A vs `|F|²·F_latt²·LP` | dimensionless | compare_stage_a_baseline.py:709-1012 | spot_profile_summary.md (partiality section) | plans/.../summary.md (2025-12-24T150000Z) | Median `StageA ÷ |F|²·F_latt²·LP ≈ 0` (summary.md). | Simulator likely never applies lattice term; confirm by instrumenting nanobrag_torch. |
  | DB-AT-028 initial chi²/pixel | unitless (spec ≤ 1e2) | tests/dbex/test_stage_a_smoke_parity.py:176-230 | pytest harness | plans/.../db_at_028/db_at_028_metrics.json:2-33 | `chi2_per_pixel_initial=2.10e5`, `roi_cc_median_before=-0.053`. | Acceptance gates fail deterministically; fix must lift Stage A intensity. |
- Source Trace Anchors:
  - Producer: `dbex/vis/mapping.py:94-223`, `dbex/nanobrag_bridge.py:856-975` (HKL grid), `dbex/refinement/stage_a.py:403-519` (Stage A cache).
  - Hydration: `dbex/refinement/reconstruction.py:167-253` (telemetry replay), `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py:205-389,514-1012` (ledger + probes).
  - Consumer: `tests/dbex/test_stage_a_smoke_parity.py:69-230`, `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-24T150000Z/spot_profile_summary.md:20-121`, `plans/.../db_at_028/db_at_028_metrics.json:2-33`.
- Consumption-State Measurements:
  - Loss mask device `cuda:0`, dtype `float32`, 4,140 masked pixels (stage_a_baseline_probe_baseline.json:111-140).
  - `target_mean_masked = 87.118 ADU`, `model_mean_masked = 87.118 ADU` (telemetry consistency).
  - `chi_squared_per_pixel_initial = 1.004e6` in baseline probe vs `2.10e5` in DB-AT (stage_a_baseline_probe_baseline.json:133, db_at_028_metrics.json:2-33).
- Boundary Bisection Step: Instrument `nanobrag_torch.simulator` to emit the actual per-reflection `F_latt` / partiality factors (via the new debug flag) and compare them against the calibration-derived ledger; if the simulator reports ~1.0 across all ROIs, the bug is upstream (grid construction), otherwise patch `compute_physics_for_position` to apply the missing weight.
- Probe Budget: Stage A baseline probe has already consumed two instrumentation toggles (HKL stats + physics ledger); reusing it with the simulator debug hook is the final probe allowed before we must attempt a production fix.

How-To Map:
1. Rebuild the editable nanobrag_torch install (`python -m pip install -e src/nanobrag-torch`) if needed so the simulator instrumentation is active.
2. Run the mapped `compare_stage_a_baseline.py` command with `--collect-simulator-partiality-stats`; ensure the JSON contains both `partiality_alignment` (expected) and the new `simulator_partiality_stats` block referencing the debug hook output.
3. Execute the combined DB-AT-028/029 pytest selector with artifact directories pointing at the same report; verify logs mention the simulator debug hook (to confirm the instrumentation path ran) and capture the failing metrics for parity tracking.

Pitfalls:
- Forgetting to gate the new simulator debug hook behind `debug_config` will perturb production runs; ensure the default path is untouched.
- The Stage A baseline probe must only enable the debug flag when explicitly requested; accidental always-on instrumentation will slow DB-AT selectors.
- HKL stats collection already uses `debug_config`; merge the dictionaries carefully so both HKL and partiality stats can coexist.
- Writing large per-pixel payloads will explode artifact sizes—aggregate statistics per ROI/panel instead of dumping full tensors.
- Do not mutate telemetry structures while reading simulator debug output; copy into new JSON fields.
- Ensure the pip editable reinstall occurs after modifying nanobrag_torch or the old wheel will be used.
- Keep environment variables identical between the probe and DB-AT runs so artifacts remain comparable.
- Probe budget is exhausted; do not tack on additional CLI flags beyond `--collect-simulator-partiality-stats` without supervisor approval.

If Blocked:
- If `src/nanobrag-torch/.../simulator.py` cannot be edited in this environment, document the blocker in `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-26T010000Z/summary.md`, update `docs/fix_plan.md` + `galph_memory.md`, and request guidance before rerunning probes.
- If the simulator debug hook surfaces but returns empty stats, capture the raw `hkl_stats` payload, mark the loop blocked, and be prepared to promote the issue to a harness/spec-change initiative.
