Summary: Add a Lorentz/partiality physics ledger to the Stage A baseline probe so we can prove the DB-AT-028/029 crisis comes from missing still-intensity factors before touching nanobrag_torch.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-23T150000Z/db_at_028 DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-23T150000Z/db_at_029 DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-23T150000Z/

Do Now (hard validity contract):
- Implement: `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py::main`
  - Add a `--collect-physics-ledger` CLI flag (default False) and, when enabled, compute per-ROI still-Lorentz and polarization factors using the orientation metrics that were just added. Use the measured 2θ (degrees) to derive `two_theta_rad = np.deg2rad(two_theta_deg)`, then set `lorentz_factor = 1.0 / max(np.sin(two_theta_rad), 1e-6)` (stills approximation) and `polarization_factor = 0.5 * (1 + np.cos(two_theta_rad) ** 2)` for the unpolarized beam that DB-AT fixtures assume. Multiply the existing `amp_sq_per_pixel` value by `lorentz_factor * polarization_factor` to get `lp_weighted_expectation` and record Stage A vs LP-weighted ratios plus amp² vs LP-weighted ratios for every matched ROI.
  - Emit a `physics_alignment` block in the JSON output with: (1) global stats (median/p25/p75 Stage A ÷ (|F|²·LP), amp² ÷ reference, Pearson correlation between the LP ratios and Stage A/reference ratios); (2) resolution-binned summaries (e.g., four equal-width bins spanning the min/max resolution) containing median Stage A ÷ (|F|²·LP) so we can see whether the deficit grows with resolution; and (3) top/bottom-five ROI tables sorted by the absolute deviation of Stage A ÷ (|F|²·LP) from 1.0.
  - Update `spot_profile_summary.md` (same file used for spot/orientation evidence) with a new **Physics Alignment** section that prints the median ratio, Pearson correlation, and the top/bottom-five ROI rows with HKL, resolution, Stage A/ref, and Stage A/|F|²·LP values. Reuse the helper that already flushes orientation summaries so reviewers do not have to open the raw JSON.
  - Rerun the baseline probe with every diagnostic enabled and capture stdout:
    ```bash
    AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
    DBEX_SMOKE_SIGMA_SOURCE=cli_override \
    DBEX_SMOKE_DETECTOR_SIZE=small \
    DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json \
    DBEX_SMOKE_HKL_PATH=sp.proc/calibration/smoke_refined_structure_factors_small.mtz \
    KMP_DUPLICATE_LIB_OK=TRUE \
    NANOBRAGG_DISABLE_COMPILE=1 \
    python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py \
      --geometry-mode baseline \
      --stage-a-mosaic-domains 16 \
      --collect-hkl-stats \
      --collect-spot-profiles \
      --collect-orientation-metrics \
      --collect-physics-ledger \
      --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-23T150000Z/stage_a_baseline_probe_baseline.json \
      | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-23T150000Z/stage_a_baseline_probe_baseline.log
    ```
    After the run, append a short `python - <<'PY'` snippet that prints the new `physics_alignment` medians, resolution bins, and correlation into `spot_profile_summary.md` so the ledger has a human-readable summary.
  - Pytest: Execute the mapped DB-AT selectors above with `DBAT028_ARTIFACT_DIR` / `DBAT029_ARTIFACT_DIR` pointing at the same report directory to keep the chi²/pixel and ROI CC metrics aligned with the fresh probe evidence.
  - Artifacts: Keep the probe JSON/log, updated Markdown summary, any helper scripts, and both pytest outputs inside `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-23T150000Z/` (with `db_at_028/` and `db_at_029/` subdirectories) for ledger references.

Deterministic Parity Crisis:
- Independent Reference: DIALS reflection table `sp.proc/refGeom_small/refGeom_small.refl` remains the authoritative intensity source. It is independent of Stage A/mapping and reports target/ref median ≈1.02, so it still defines the acceptance contract.
- Transformation Ledger:
  | Field | Units/frame | Producer (file:line) | Consumer (file:line) | Observed evidence | Hypothesis |
  | --- | --- | --- | --- | --- | --- |
  | ROI panel 0 [644:656,21:33] HKL (-7,5,-3) Stage A/ref ratio | ADU/pixel | plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py:1494-1605 | plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-23T010000Z/spot_profile_summary.md:48-75 | Stage A predicts 7.12e-05× the DIALS reference while |Δhkl|=0.2473 and resolution=2.68 Å | Geometry is close, so the deficit reflects missing still-intensity factors (Lorentz/partiality) rather than ROI placement. |
  | ROI panel 0 [257:269,37:49] HKL (-3,8,-9) Stage A/ref ratio | ADU/pixel | same producer | same consumer | Stage A/ref=2.94e-03 with |Δhkl|=0.1958 despite resolution=2.56 Å | Even moderate misalignment (<0.2) gives 300× deficit ⇒ need physics normalization ledger. |
  | ROI panel 0 [535:547,842:854] HKL (2,-6,2) Stage A/ref ratio | ADU/pixel | same producer | same consumer | Stage A/ref=1.68e-02 at |Δhkl|=0.2094 and resolution=4.14 Å | Indicates ratio drift scales with resolution, consistent with missing Lorentz/partiality. |
  | ROI panel 0 [661:673,940:952] HKL (1,-9,4) Stage A/ref ratio | ADU/pixel | same producer | same consumer | Stage A/ref=1.46e-01 while |Δhkl|=0.2330 and resolution=3.06 Å | The deficit shrinks but never reaches 1.0 even when |Δhkl| is similar, pointing to physics-based scaling differences rather than geometry. |
  | ROI panel 0 [350:362,877:889] HKL (4,-5,-1) Stage A/ref ratio | ADU/pixel | same producer | same consumer | Stage A/ref=3.10e+00 with |Δhkl|=0.1945 (same magnitude as deficits) | Simulator also overshoots when the ROI captures nearly all energy, matching the hypothesis that missing Lorentz/polarization applies non-uniform scaling that spikes certain reflections. |
- Boundary Bisection Step: Add the Lorentz/partiality physics ledger so we can compare Stage A vs `|F|²·LP` in resolution bins; if Stage A matches the LP expectation, the issue lies upstream (HKL ingestion), otherwise we pivot to implementing the missing LP factors inside nanobrag_torch.

How-To Map:
- Edit the probe script, add the new CLI flag, and keep the JSON/Markdown schema changes close to the existing spot/orientation sections so reviewers can diff easily.
- Run the baseline probe command above once (geometry-mode baseline only) and keep the stdout log in the report root; avoid extra perturbed runs per stop-and-read rule.
- After the probe finishes, run a small helper to pretty-print the `physics_alignment` block into `spot_profile_summary.md`:
  ```bash
  python - <<'PY'
  import json, pprint
  data = json.load(open('plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-23T150000Z/stage_a_baseline_probe_baseline.json'))
  pprint.pp(data['physics_alignment'])
  PY >> plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-23T150000Z/spot_profile_summary.md
  ```
- Run the two pytest selectors with the artifact dirs pointing at the same timestamp so chi²/pixel and ROI CC metrics line up with the new ledger.

Pitfalls:
- `np.sin(two_theta_rad)` goes to zero near the beam axis; clamp with an epsilon before inverting to avoid infinities in the Lorentz factor.
- Only compute the physics ledger when both orientation metrics and HKL amplitudes exist; skip (and log) ROIs that lack either to prevent NaNs from polluting the medians.
- Keep all angular math in radians—orientation metrics store degrees, so convert exactly once to avoid mixing units.
- Ensure the resolution-binning logic covers the whole range (inclusive) and note the bin edges in the JSON for reproducibility.
- Update both the JSON payload and `spot_profile_summary.md`; dropping either will force another loop because the ledger has to be human-readable.
- Preserve previous keys in the JSON so downstream tooling doesn’t break; append the new block instead of restructuring existing sections.
- Do not rerun perturbed geometry or additional toggles; the deterministic parity signature is already stable, so extra runs violate the stop-and-read guard.
- Keep the scripts under the same timestamp; littering multiple directories makes ledger citations harder.
- Watch for floating-point overflow when multiplying |F|² by large Lorentz factors—cast to float64 for the intermediate computation before storing float32 in the JSON.

If Blocked:
- If the probe crashes (e.g., detector geometry missing or Lorentz factor blows up), capture the traceback under the report directory, update docs/fix_plan Attempts History plus galph_memory with the failure, and stop—do not hack nanobrag_torch. A missing orientation metric should be logged and treated as evidence for a follow-up harness loop.
- If pytest cannot run (asset missing), stash the partial probe artifacts, record the block in docs/fix_plan and the report summary, and request supervisor guidance before attempting alternative datasets or harness/spec-type work.
