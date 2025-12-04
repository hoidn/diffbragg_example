Summary: Apply the missing stills Lorentz weighting inside `nanobrag_torch` and revalidate Stage A against the DB-AT-028/029 selectors.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBEX_SMOKE_HKL_PATH=sp.proc/calibration/smoke_refined_structure_factors_small.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --geometry-mode baseline --stage-a-mosaic-domains 16 --collect-hkl-stats --collect-spot-profiles --collect-orientation-metrics --collect-physics-ledger --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-24T010000Z/stage_a_baseline_probe_baseline.json | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-24T010000Z/stage_a_baseline_probe_baseline.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-24T010000Z/db_at_028 DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-24T010000Z/db_at_028/pytest.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-24T010000Z/db_at_029 DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-24T010000Z/db_at_029/pytest.log
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-24T010000Z/

Do Now (hard validity contract):
- Implement: `src/nanobrag-torch/src/nanobrag_torch/simulator.py::compute_physics_for_position`
  - After summing over phi/mosaic but before polarization, compute the stills Lorentz factor from the incident and diffracted unit vectors: `cos_two_theta = clamp(dot(-incident_beam_unit, diffracted_beam_unit), -1+1e-6, 1-1e-6)`, `two_theta = torch.acos(cos_two_theta)`, `lorentz = 1.0 / torch.clamp(torch.sin(two_theta), min=1e-6)`. Multiply both `intensity` and `intensity_pre_polar` by this tensor so the simulator returns `|F|²·F_latt²·Lorentz` (polarization still applied in the existing block). Keep the computation fully vectorized for multi-source runs and reuse the already-normalized direction tensors to avoid recomputing geometry.
  - Save the diff to `plans/active/ARCH-SIM-CONSTRUCTION-001/patches/lorentz_scaling.patch`, reinstall nanobrag_torch in editable mode if needed so Python reloads the change, and record the environment tag (e.g., `nanobragg-lorentz-2025-12-23`) plus rebuild command in `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-24T010000Z/environment.md` for reproducibility.
  - Extend the simulator change to propagate through `intensity_pre_polar` so tracing hooks remain accurate, add a short docstring comment referencing DB-AT-028 (§spec-db-core.md “Simulator produces physical intensity in photons”), and clamp the sine argument with `torch.clamp_min` to avoid NaNs near the beam axis.
- Implement: `docs/findings.md::SCALE-008/SCALE-009 follow-up entry`
  - Document the Lorentz patch under a new finding ID (e.g., `SIM-CONSTR-LORENTZ-001`) including the patch file path, environment tag, rebuild command, and how the fix restores the Stage A vs reference contract. Reference the 2025-12-24T010000Z report directory so future agents know which artifacts prove the regression is closed.

Deterministic Parity Crisis:
- Independent Reference: The DIALS reflection table `sp.proc/refGeom_small/refGeom_small.refl` (independent of Stage A/mapping) supplies the ROI intensities used by DB-AT-028/029; its target/ref median ≈1.02 anchors the acceptance contract while Stage A outputs diverge (`plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-23T150000Z/db_at_028/db_at_028_metrics.json`).
- Transformation Ledger:
  | Field | Units/frame | Producer (file:line) | Consumer (file:line) | Observed evidence | Hypothesis |
  | --- | --- | --- | --- | --- | --- |
  | ROI panel 0 [644:656,21:33] HKL (-7,5,-3) Stage A/ref ratio | ADU/pixel | plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py:492-574 | plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-23T150000Z/spot_profile_summary.md:64 | Stage A/ref = 7.12e-05 while Stage A/|F|²·LP = 1.0e-04 with LP factor 2.61. Geometry is fine (|Δhkl|=0.2473), so the ≈10⁴ deficit tracks the missing Lorentz boost. | Apply Lorentz weighting inside the simulator so low-angle reflections no longer collapse relative to the DIALS reference. |
  | ROI panel 0 [661:673,940:952] HKL (1,-9,4) Stage A/ref ratio | ADU/pixel | same | spot_profile_summary.md:66-105 | Stage A/ref = 1.46e-01 but Stage A/|F|²·LP = 1.0e-04 despite LP factor 3.01. Orientation metrics show |Δhkl|=0.233. | The per-ROI deficit scales with sin(2θ); adding the Lorentz term should bring this ratio toward 1. |
  | ROI panel 0 [535:547,842:854] HKL (2,-6,2) Stage A/ref ratio | ADU/pixel | same | spot_profile_summary.md:68-105 | Stage A/ref = 1.68e-02 and Stage A/|F|²·LP = 1.0e-04; LP factor 4.16 amplifies the miss at higher 2θ. | Missing Lorentz weighting suppresses Bragg response as resolution increases, matching the deterministic parity crisis signature. |
  | ROI panel 0 [257:269,37:49] HKL (-3,8,-9) Stage A/ref ratio | ADU/pixel | same | spot_profile_summary.md:69-106 | Stage A/ref = 2.94e-03 with Stage A/|F|²·LP = 2.0e-04, LP factor 2.48. Reference target/ref ≈1 so simulator physics (not data) causes the ≈500× gap. | Lorentz fix should normalize these mid-resolution reflections without touching geometry. |
  | ROI panel 0 [431:443,434:446] HKL (0,2,-2) high-intensity ROI | ADU/pixel | same | spot_profile_summary.md:110-116 | Stage A/ref = 2.34e+02 yet Stage A/|F|²·LP = 8.92e-01 (LP factor 11.70). Over-bright low-angle ROI matches expectation once Lorentz is included, so the fix should also cap these spikes. | Lorentz scaling will reduce the variance across ROIs and collapse Stage A/ref toward 1 uniformly. |
- Boundary Bisection Step: Patch `compute_physics_for_position` to multiply intensities by the stills Lorentz factor before polarization, then regenerate the physics ledger and DB-AT selectors; if ratios remain off, pivot to verifying partiality/mosaic dependence in `Crystal.get_structure_factor`.

How-To Map:
- Determine the active `nanobrag_torch` install path via `python - <<'PY'` (`import nanobrag_torch, pathlib; print(pathlib.Path(nanobrag_torch.__file__).resolve())`) so the patch targets the correct source tree.
- Edit the simulator file, run `python -m pip install -e /path/to/src/nanobrag-torch` (or equivalent) to refresh the module, and store the diff in `plans/active/ARCH-SIM-CONSTRUCTION-001/patches/lorentz_scaling.patch` for reproducibility.
- Re-run the baseline probe command with all collection flags enabled; keep stdout + JSON in the new report directory and append the updated physics summary to `spot_profile_summary.md`.
- Execute the mapped DB-AT selectors with `DBAT028_ARTIFACT_DIR`/`DBAT029_ARTIFACT_DIR` pointing at the same timestamp so chi²/pixel and ROI CC metrics cite the patched simulator.

Pitfalls:
- Clamp the dot product before `torch.acos` and the sine denominator to avoid NaNs at grazing angles.
- Ensure the Lorentz tensor matches the intensity shape for both single- and multi-source paths; broadcast carefully when `original_n_dims == 2`.
- Update `intensity_pre_polar` alongside `intensity` so trace hooks remain valid.
- Keep polarization logic untouched—only Lorentz is missing, and double-applying polarization would break DB-AT-027.
- Remember to capture and publish the patch file + environment tag per Environment Freeze; undocumented local edits are non-compliant.
- Run only the mapped tests; extra toggle hunts violate the stop-and-read guard since the parity signature is already deterministic.
- If the editable install path differs from this repo, note it explicitly in environment.md so future loops know where the patch lives.
- DB-AT tests write artifacts into their directories; ensure the env vars point at the new timestamp so evidence stays synchronized.

If Blocked:
- If the simulator file cannot be edited (e.g., package path missing), capture the failure, add the blocker to `docs/fix_plan.md` + `galph_memory.md`, and request guidance before attempting alternative datasets.
- If applying the Lorentz factor causes numerical blow-ups, keep the partial artifacts, log the NaNs/Infs in the report, and stop—the next loop can reassess whether the formula needs a spec-change or simulator-side clamp.
