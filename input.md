Summary: Apply the refined mosaic spread from `refGeom_small.expt` to every CrystalConfig so Stage A/mapping simulators use the same blur as the DB-AT references instead of the hard-coded perfect-crystal kernel that creates the 200× ROI spikes in the transformation ledger.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBEX_SMOKE_HKL_PATH=sp.proc/calibration/smoke_refined_structure_factors_small.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --geometry-mode baseline --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-21T010000Z/stage_a_baseline_probe_baseline.json
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBEX_SMOKE_HKL_PATH=sp.proc/calibration/smoke_refined_structure_factors_small.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --geometry-mode perturbed --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-21T010000Z/stage_a_baseline_probe_perturbed.json
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-21T010000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-21T010000Z/db_at_029 DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-21T010000Z/pytest_db_at_028_029.log
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-21T010000Z/

Do Now (hard validity contract):
- Implement: `dbex/refinement/config_factories.py::create_crystal_config`
  - Inspect `experiment.crystal.to_dict()` for `ML_half_mosaicity_deg` / `ML_domain_size_ang` whenever stills configs are built (Stage A, mapping, reconstruction). If a positive half-mosaic value exists, translate it to the simulator’s `mosaic_spread_deg` (use the same degrees that DiffBragg reports; no more hard-coded zero) and carry it through every `CrystalConfig` you instantiate.
  - When calibration metadata omits explicit `N_cells`, fall back to `ML_domain_size_ang` by dividing by each unit-cell edge and rounding to the nearest positive integer so we do not drop the calibrated lattice width when only the experiment provides it.
  - Thread the populated mosaic spread into Stage A/mapping/reconstruction contexts without changing CLI semantics, and extend the existing diagnostics (`baseline_stats.json`, mapping diagnostics) to echo the applied mosaic so the supervisor report can cite the value that went into nanobrag_torch.
  - Re-run the baseline + perturbed probes and DB-AT-028/029 commands above so this loop’s artifact directory contains refreshed ROI diagnostics (expect ROI CC ≫0 once the blur matches the data) and the acceptance selectors exercising the same code path.

Deterministic Parity Crisis:
- Independent Reference: The DIALS reflection table (`sp.proc/refGeom_small/refGeom_small.refl`) is independent of nanobrag_torch yet matches the observed target pixels (median target/reference ratio ≈ 1.02), so it remains the authoritative ROI-level contract.
- Transformation Ledger:

  | Field | Units / Frame / Order | Producer (file:line) | Consumer (file:line) | Observed evidence | Hypothesis |
  | --- | --- | --- | --- | --- | --- |
  | Masked mean baseline (`telemetry.target_mean_masked`, `model_mean_masked`, `chi²/pixel`) | ADU/pixel under detector loss mask | `dbex/refinement/stage_a.py:403-520` | `tests/dbex/test_stage_a_smoke_parity.py:335-515` | `stage_a_baseline_probe_baseline.json` shows `target=model=87.118 ADU` while `chi²/pixel=9.8e5`. | Scalar calibration is correct; deterministic failure is spatial redistribution before DB-AT gates. |
  | ROI 0 Panel 0 `[897:909,17:29]`, HKL (−10,2,0) | ADU/pixel | `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py:611-747` | `tests/dbex/test_stage_a_smoke_parity.py:398-515` | Reflection 8.69 ADU vs Stage A 0.0199 ADU (`stagea_vs_ref_ratio=2.3×10⁻³`). | Zero-mosaic simulator dumps almost no energy into this ROI even though reference + HKL amplitude agree. |
  | ROI 2 Panel 0 `[257:269,37:49]`, HKL (−3,8,−9) | ADU/pixel | same | same | Reflection 83.10 ADU vs Stage A 0.244 ADU (`stagea_vs_amp_sq_ratio=4.8×10⁻⁴`). | Bright reflections still lose 99.95 % of intensity, matching a kernel that is far sharper than the measured crystal. |
  | ROI 14 Panel 0 `[431:443,434:446]`, HKL (0,2,−2) | ADU/pixel | same | same | Stage A mean = 407.7 ADU vs target 2.48 ADU (`stagea_vs_ref_ratio=234`). | Perfect-crystal sinc spikes overfill a handful of ROIs while starving the rest. |
  | ROI 21 Panel 0 `[787:799,694:706]`, HKL (−2,−6,5) | ADU/pixel | same | same | Stage A mean = 11.80 ADU vs target 192.9 ADU (≈0.061×). | Median deficit (~16×) echoes the reflection-table ratio and will drop once the calibrated mosaic blur is honored. |

- Boundary Bisection Step: If the mosaic injection still leaves ROI correlations negative, next boundary is to tap nanobrag_torch’s `Simulator._hkl_stats` per ROI (adding ROI-ID tags to the existing HKL telemetry) so we can prove whether the sampled HKLs align with each ROI’s reflection before diving into Lorentz/polarization math.

How-To Map:
- Keep the smoke fixture settings identical to prior probes (env vars above) so the only delta is mosaic plumbing; this isolates the kernel change when comparing JSON artifacts.
- Fetch experiment metadata once per call site (`crystal_dict = crystal.to_dict()`), guard missing keys, and log the applied mosaic spread/domain size inside the diagnostics block to keep ledger citations grounded.
- When deriving fallback `N_cells` from `ML_domain_size_ang`, divide by each axis length separately (a,b,c) so anisotropic crystals remain supported; round to at least 1 to avoid zero-cell edge cases.
- After updating `create_crystal_config`, run the two probe commands before DB-AT so the new ROI stats are captured even if pytest fails; stash stdout/stderr under the artifact directory for reuse in the ledger.
- Use `python -m dbex.refine_one ...` only if you need manual spot checks; all validation for this loop must flow through the mapped probe + pytest commands to keep artifacts consistent.

Pitfalls:
- Forgetting to propagate the mosaic spread into mapping/reconstruction leaves Stage A fixed but DB-AT harness still cold-pathing with the zero-mosaic helper; double-check both code paths hit the updated factory.
- Do not double-apply the half-mosaic value (no squaring or redundant conversions)—DiffBragg already reports degrees, so hand them straight to `CrystalConfig`.
- `ML_domain_size_ang` can be missing; guard with sensible defaults and emit diagnostics instead of crashing.
- Updating diagnostics must not spam production runs; only persist the mosaic value in the existing JSON blocks that are already behind plan tooling.
- Mosaic spreads <1e-5 degrees can underflow; clamp to a minimum (e.g., `np.finfo(float).eps`) before handing to the simulator to avoid zero-rotation degeneracy.

If Blocked:
- Record the exception/evidence in `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-21T010000Z/summary.md`, note the blocker + attempted command in `docs/fix_plan.md` Attempts History and `galph_memory.md`, and decide whether the next loop needs a nanobrag_torch source patch (harness initiative) before touching other focus items.
