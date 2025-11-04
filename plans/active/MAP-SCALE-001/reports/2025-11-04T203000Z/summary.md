# MAP-SCALE-001 Supervisor Analysis (2025-11-04T181906Z)

## One-off analysis

### Calibration sweep (N_cells vs flux involvement)
```
NANOBRAGG_DISABLE_COMPILE=1 python - <<'PY'
import numpy as np
from pathlib import Path
from tests.fixtures.parity_loader import compute_parity_metrics
from dbex.data_load import DataLoad
from dbex.nanobrag_bridge import (
    prepare_refinement_inputs,
    simulate_forward_once,
    load_refined_mtz,
    load_calibration_metadata,
)

repo = Path('.')
fixtures = repo / 'tests' / 'fixtures' / 'golden_data' / 'simple_cubic'

args = type('Args', (), {
    'mtzFile': str(repo/'scaled.mtz'),
    'mtzCol': 'F,SIGF',
    'exptName': str(fixtures/'refined.expt'),
    'exptIdx': 0,
    'reflName': str(fixtures/'refined.refl'),
    'maskFile': str(repo/'747_mask.pkl'),
})()

load = DataLoad(args)
inputs = prepare_refinement_inputs(
    data=load.data,
    background_image=load.background_image,
    trusted_mask=load.trusted_mask,
    bbox=load.bbox,
    pids=load.pids,
    detector=load.detector,
    adu_per_photon=None,
)

indices, amps = load_refined_mtz(fixtures/'refined_structure_factors.mtz')
calib = load_calibration_metadata(fixtures/'config_torch.json')
canonical = np.load(fixtures/'bragg_torch.npy')
if canonical.ndim == 3 and canonical.shape[0] == 1:
    canonical = canonical[0]
mask = inputs.loss_mask[0]

cases = {
    'calibration_full': calib,
    'calibration_no_Ncells': {**calib, 'N_cells': None},
    'calibration_no_beam': {**calib, 'beam_flux': None, 'beam_exposure': None, 'beamsize_mm': None},
    'calibration_spot_only_dict': {'spot_scale_override': calib['spot_scale_override']},
    'legacy_spot_param': None,
}

spot_only = calib['spot_scale_override']

def run_case(calibration_dict, use_legacy=False):
    if use_legacy:
        bragg, diag = simulate_forward_once(
            inputs=inputs,
            detector=load.detector,
            beam=load.beam,
            crystal=load.crystal,
            experiment=load.Expt,
            hkl_indices=indices,
            hkl_amplitudes=amps,
            spot_scale_override=spot_only,
            calibration=None,
        )
    else:
        bragg, diag = simulate_forward_once(
            inputs=inputs,
            detector=load.detector,
            beam=load.beam,
            crystal=load.crystal,
            experiment=load.Expt,
            hkl_indices=indices,
            hkl_amplitudes=amps,
            calibration=calibration_dict,
        )
    canonical_metrics = compute_parity_metrics(bragg[0], canonical, loss_mask=mask)
    target_metrics = compute_parity_metrics(bragg[0], inputs.target[0], loss_mask=mask)
    mean_masked = float(bragg[inputs.loss_mask].mean())
    return {
        'corr_vs_canonical': canonical_metrics.correlation,
        'sum_ratio_vs_canonical': canonical_metrics.sum_ratio,
        'rmse_vs_canonical': canonical_metrics.rmse,
        'corr_vs_target': target_metrics.correlation,
        'sum_ratio_vs_target': target_metrics.sum_ratio,
        'rmse_vs_target': target_metrics.rmse,
        'bragg_mean_masked': mean_masked,
        'diag_mean': float(diag['bragg_stats']['mean']),
        'sqrt_spot_scale': float(diag['sqrt_spot_scale']),
    }

for name, case in cases.items():
    try:
        if name == 'legacy_spot_param':
            metrics = run_case(None, use_legacy=True)
        else:
            metrics = run_case(case)
    except Exception as exc:
        print(f"Case: {name}\n  ERROR: {exc}\n---")
        continue
    print(f"Case: {name}")
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"  {key}={value:.6e}")
        else:
            print(f"  {key}={value}")
    print('---')
PY
```
Output:
```
/home/ollie/miniconda3/envs/simtbx/lib/python3.9/site-packages/dials/extensions/__init__.py:3: UserWarning: pkg_resources is deprecated as an API. See https://setuptools.pypa.io/en/latest/pkg_resources.html. The pkg_resources package is slated for removal as early as 2025-11-30. Refrain from using this package or pin to Setuptools<81.
  import pkg_resources
auto-selected 3-fold oversampling
[HKL stats] h=[-22,8] k=[-27,12] l=[-28,9] hit_rate=55720855/56016009 (99.47%)
Case: calibration_full
  corr_vs_canonical=-1.585200e-03
  sum_ratio_vs_canonical=7.614111e+09
  rmse_vs_canonical=2.011362e+13
  corr_vs_target=-1.813885e-03
  sum_ratio_vs_target=9.359846e+09
  rmse_vs_target=2.011362e+13
  bragg_mean_masked=5.899076e+11
  diag_mean=2.968184e+10
  sqrt_spot_scale=5.643325e+08
---
auto-selected 1-fold oversampling
[HKL stats] h=[-22,8] k=[-27,12] l=[-28,9] hit_rate=6191206/6224001 (99.47%)
Case: calibration_no_Ncells
  corr_vs_canonical=6.266547e-02
  sum_ratio_vs_canonical=2.347877e+04
  rmse_vs_canonical=6.037172e+06
  corr_vs_target=4.333963e-02
  sum_ratio_vs_target=2.886189e+04
  rmse_vs_target=6.037194e+06
  bragg_mean_masked=1.819031e+06
  diag_mean=1.318974e+06
  sqrt_spot_scale=5.643325e+08
---
auto-selected 3-fold oversampling
[HKL stats] h=[-22,8] k=[-27,12] l=[-28,9] hit_rate=55720855/56016009 (99.47%)
Case: calibration_no_beam
  corr_vs_canonical=-1.585200e-03
  sum_ratio_vs_canonical=7.614111e+09
  rmse_vs_canonical=2.011362e+13
  corr_vs_target=-1.813885e-03
  sum_ratio_vs_target=9.359846e+09
  rmse_vs_target=2.011362e+13
  bragg_mean_masked=5.899076e+11
  diag_mean=2.968184e+10
  sqrt_spot_scale=5.643325e+08
---
auto-selected 1-fold oversampling
[HKL stats] h=[-22,8] k=[-27,12] l=[-28,9] hit_rate=6191206/6224001 (99.47%)
Case: calibration_spot_only_dict
  corr_vs_canonical=6.266547e-02
  sum_ratio_vs_canonical=2.347877e+04
  rmse_vs_canonical=6.037172e+06
  corr_vs_target=4.333963e-02
  sum_ratio_vs_target=2.886189e+04
  rmse_vs_target=6.037194e+06
  bragg_mean_masked=1.819031e+06
  diag_mean=1.318974e+06
  sqrt_spot_scale=5.643325e+08
---
auto-selected 1-fold oversampling
[HKL stats] h=[-22,8] k=[-27,12] l=[-28,9] hit_rate=6191206/6224001 (99.47%)
Case: legacy_spot_param
  corr_vs_canonical=6.266547e-02
  sum_ratio_vs_canonical=2.347877e+04
  rmse_vs_canonical=6.037172e+06
  corr_vs_target=4.333963e-02
  sum_ratio_vs_target=2.886189e+04
  rmse_vs_target=6.037194e+06
  bragg_mean_masked=1.819031e+06
  diag_mean=1.318974e+06
  sqrt_spot_scale=5.643325e+08
---
```

## Takeaways
- Injecting `N_cells` from calibration drives simulator intensity up by ~3.2e5× (mask mean jumps from 1.82e6 to 5.9e11) and correlation collapses to ~0, exactly matching Ralph’s failing run.
- Beam flux/exposure metadata do not change current bridge output because they are not yet wired into the torch models; removing them has no effect on metrics.
- Leaving `N_cells=None` preserves prior behavior (corr≈0.063 vs canonical, ≈0.043 vs target), confirming the regression source and narrowing the parity gap to geometry + structure-factor alignment rather than beam metadata.

## Next Steps
- Revert `N_cells` plumbing in `create_crystal_config`/`simulate_forward_once` until the simulator implements the same sample clipping semantics as the canonical generator.
- Update the Do Now to reinstate flux/beamsize/exposure parsing only after wiring them through `TorchCrystal(..., beam_config=...)` with validated scaling semantics; otherwise treat them as diagnostic metadata.
- Capture regression details in docs/fix_plan.md Attempts History and log a new SCALE finding describing the N_cells overshoot guardrail.
