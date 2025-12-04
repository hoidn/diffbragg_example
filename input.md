Summary: Apply the stills Lorentz weighting inside nanobrag_torch so Stage A simulator outputs match the independent DIALS reflection intensities and unblock DB-AT-028/029.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBEX_SMOKE_HKL_PATH=sp.proc/calibration/smoke_refined_structure_factors_small.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --geometry-mode baseline --stage-a-mosaic-domains 16 --collect-hkl-stats --collect-spot-profiles --collect-orientation-metrics --collect-physics-ledger --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-24T150000Z/stage_a_baseline_probe_baseline.json | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-24T150000Z/stage_a_baseline_probe_baseline.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-24T150000Z/db_at_028 DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-24T150000Z/db_at_028/pytest.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-24T150000Z/db_at_029 DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-24T150000Z/db_at_029/pytest.log
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-24T150000Z/

Do Now (hard validity contract):
- Implement: `src/nanobrag-torch/src/nanobrag_torch/simulator.py::compute_physics_for_position`
  - Multiply both `intensity_pre_polar` and `intensity` by the stills Lorentz term `1/sin(2θ)` right after the phi/mosaic sum but before polarization: reuse the existing normalized incident/diffracted vectors, clamp their dot product to (-1+1e-6, 1-1e-6), take `torch.acos`, then clamp `torch.sin(two_theta)` with `torch.clamp_min(1e-6)` to avoid NaNs at grazing angles. Keep the computation batched so multisource tensors broadcast cleanly when `original_n_dims == 2`.
  - Treat this as a targeted environment-freeze bugfix: capture the diff with `git diff src/nanobrag-torch/src/nanobrag_torch/simulator.py > plans/active/ARCH-SIM-CONSTRUCTION-001/patches/lorentz_scaling.patch`, run `python -m pip install -e src/nanobrag-torch` so Python reloads the change, and log the rebuild + environment tag (e.g., `nanobrag-lorentz-2025-12-24`) in `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-24T150000Z/environment.md`.
  - Extend the nearby docstring/comment to cite `docs/spec-db-core.md §31 (Simulator produces physical intensity in photons)` and note that polarization still happens downstream so we do not double-apply it.
- Document: `docs/findings.md::SIM-CONSTR-LORENTZ-001`
  - Add a new finding referencing ARCH-SIM-CONSTRUCTION-001 that records the Lorentz patch rationale, patch file path, environment tag, rebuild command, and the validating artifacts (`stage_a_baseline_probe_baseline.json`, DB-AT-028/029 logs).
- Validate via the mapped baseline probe + DB-AT selectors so chi²/pixel initial ≤1e2 and median ROI CC ≥0.2 once the Lorentz fix lands.

Deterministic Parity Crisis:
- Independent Reference: DIALS reflection table `sp.proc/refGeom_small/refGeom_small.refl` powers the ROI intensity contract consumed by DB-AT-028/029; its target/Ref sigmoid ≈1.02 and does not share Stage A or mapping code paths (see `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-23T150000Z/db_at_028/db_at_028_metrics.json:2-53`).
- Transformation Ledger:
  | Field | Units/frame | Producer (file:line) | Consumer (file:line) | Observed evidence | Hypothesis |
  | --- | --- | --- | --- | --- | --- |
  | ROI panel 0 [644:656,21:33] HKL (-7,5,-3) StageA/ref | ADU/pixel | plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py:1512-1709 | plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-24T010000Z/spot_profile_summary.md:24-116 | Stage A/ref = 3.71e-05 and Stage A/|F|²·LP ≈ 0 (LP=2.61) even though target/ref ≈1.02, so simulator collapses high-Lorentz reflections (lines 66-106). | Missing stills Lorentz weighting suppresses low-angle intensities after |F|² is sampled. |
  | ROI panel 0 [661:673,940:952] HKL (1,-9,4) StageA/ref | ADU/pixel | same | spot_profile_summary.md:24-116 | Stage A/ref = 8.46e-02 while Stage A/|F|²·LP ≈ 0 with LP=3.01 (lines 66-105), despite correct HKL alignment. | Lorentz deficit scales with sin(2θ), so applying 1/sin(2θ) should recover these ROIs. |
  | ROI panel 0 [535:547,842:854] HKL (2,-6,2) StageA/ref | ADU/pixel | same | spot_profile_summary.md:24-116 | Stage A/ref = 1.32e-02 and Stage A/|F|²·LP ≈ 0 (LP=4.16), causing DB-AT-028 chi² ≫ spec (db_at_028_metrics.json:2-38). | Simulator omits Lorentz gain, so higher-resolution spots collapse. |
  | ROI panel 0 [257:269,37:49] HKL (-3,8,-9) StageA/ref | ADU/pixel | same | spot_profile_summary.md:24-106 | Stage A/ref = 1.46e-03 and Stage A/|F|²·LP ≈ 1e-4 with LP=2.48, even though orientation residual is only 0.196 (lines 66-105). | Physics weighting, not geometry, drives the deficit. |
  | ROI panel 0 [144:156,619:631] HKL (4,1,-6) StageA/ref | ADU/pixel | same | spot_profile_summary.md:110-116 | Stage A/ref = 2.20e+00 yet Stage A/|F|²·LP = 4.78e-02 (LP=3.56), showing simulator also over-brightens some ROIs when Lorentz >1 is missing, pushing chi² to 2.1e5. | Applying Lorentz scaling will collapse the spread so Stage A/ref ≈1. |
- Boundary Bisection Step: If Lorentz scaling fails to fix the ratios, capture the per-reflection partiality + polarization components inside `compute_physics_for_position` (next flag in `compare_stage_a_baseline.py`) to decide whether partiality kernels or polarization ordering need edits before touching the simulator again.

How-To Map:
1. Confirm the editable simulator path: `python - <<'PY'\nimport nanobrag_torch, pathlib\nprint(pathlib.Path(nanobrag_torch.__file__).resolve())\nPY` (expect it under `src/nanobrag-torch`).
2. Apply the Lorentz patch in `src/nanobrag-torch/src/nanobrag_torch/simulator.py`, then rebuild locally: `python -m pip install -e src/nanobrag-torch` (document command + env tag in `environment.md`).
3. Capture the diff for Environment Freeze compliance: `git diff src/nanobrag-torch/src/nanobrag_torch/simulator.py > plans/active/ARCH-SIM-CONSTRUCTION-001/patches/lorentz_scaling.patch`.
4. Re-run the baseline probe command above (baseline geometry, all collection flags) and stash both the JSON and log under the new report directory.
5. Re-run DB-AT-028 and DB-AT-029 with `DBAT028_ARTIFACT_DIR`/`DBAT029_ARTIFACT_DIR` pointing at the same timestamp so chi²/pixel + ROI CC metrics cite the patched simulator.
6. Update `docs/findings.md` with the new SIM-CONSTR-LORENTZ-001 entry summarizing the fix, patch path, rebuild command, and validation artifacts.

Pitfalls:
- Keep the Lorentz tensor shape-aligned when batching ROIs/panels; missing `unsqueeze` calls will silently broadcast across HKL samples.
- Do not double-apply Lorentz when polarization is toggled off; guard so the new factor always precedes the existing polarization branch.
- Writing outside `src/nanobrag-torch` without recording a patch violates the Environment Freeze exception—always save the diff + env tag.
- Touch only the mapped probe + DB-AT selectors; additional toggles break the “stop-and-read before expensive matrices” rule.
- Rebuild nanobrag_torch after patching or Python will cache the stale kernel, leading to a false-negative validation.
- Clamp `sin(2θ)` aggressively; low-angle reflections from panel 0 have |cos(2θ)|≈1, so missing the clamp will cause inf/NaN cascades.
- Ensure the findings entry clearly references the plan report + patch so future loops do not redo the same targeted fix.
- Respect the probe-saturation guard: no new instrumentation before attempting this production fix.

If Blocked:
- If the editable nanobrag_torch tree is missing, stop, log the blocker in `docs/fix_plan.md` + `galph_memory.md`, and request maintainer guidance before attempting a different package path.
- If Lorentz scaling destabilizes the kernel (NaNs/Infs), capture the failing outputs, stash logs under the report directory, and halt—next loop can consider spec_change vs additional clamps.
