# Transformation Ledger — Stage A vs Independent Reference (2025-12-21T010000Z)
Evidence source: `stage_a_baseline_probe_baseline.json`. Stage A and mapping conserve total intensity yet misallocate it per ROI when compared to the independent DIALS reflection table and HKL amplitudes.

| ROI | Panel | BBox (s0,s1,f0,f1) | HKL | I_ref pix^-1 | Target mean | StageA mean | StageA/Target | Target/Ref | StageA/Ref | |F|^2 pix^-1 | StageA/|F|^2 |
| --- | ----- | ------------------ | --- | ------------ | ----------- | ----------- | ------------- | ---------- | ---------- | ------------- | ------------- |
| 0 | 0 | [897,909,17,29] | [-10,2,0] | 8.694e+00 | 7.809e+00 | 1.986e-02 | 2.543e-03 | 8.981e-01 | 2.284e-03 | 9.953e+00 | 1.995e-03 |
| 5 | 0 | [605,617,156,168] | [-5,4,-2] | 5.833e-01 | 1.120e+00 | 7.745e-01 | 6.916e-01 | 1.920e+00 | 1.328e+00 | 1.212e+01 | 6.393e-02 |
| 13 | 0 | [202,214,338,350] | [1,5,-7] | 9.004e+02 | 9.015e+02 | 2.567e+01 | 2.847e-02 | 1.001e+00 | 2.850e-02 | 2.605e+02 | 9.854e-02 |
| 20 | 0 | [708,720,688,700] | [-1,-5,4] | 7.799e+00 | 7.952e+00 | 7.145e-01 | 8.986e-02 | 1.020e+00 | 9.162e-02 | 3.367e+00 | 2.122e-01 |
| 28 | 0 | [661,673,940,952] | [1,-9,4] | 3.097e+00 | 3.532e+00 | 4.509e-01 | 1.277e-01 | 1.140e+00 | 1.456e-01 | 2.704e+03 | 1.668e-04 |

Stage A’s fractional ratios swing from 7e-05 to 2.34e+02 relative to the independent reference even though Target/Ref ≈ 1.0. This deterministic distortion arises upstream of reconstruction (Stage A vs mapping CC=0.999) and indicates the simulator is sampling a single mosaic orientation, effectively using a sinc kernel without averaging across domains.