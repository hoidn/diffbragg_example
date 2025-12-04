# Spot Profile Summary

**Initiative:** ARCH-SIM-CONSTRUCTION-001

**Geometry Mode:** baseline

**Halo Pixels:** 10

**Total Reflections:** 27

---

## Summary Statistics

- **Median ROI fraction of halo:** 0.6756
- **Median ROI fraction of panel:** 0.000042

---

## Top 5 ROIs with Most Off-ROI Energy

(Lowest ROI fraction of halo — energy spilling outside ROI bbox)

| Panel | BBox | HKL | ROI/Halo | ROI Energy | Halo Energy | FWHM (fast×slow) |
|-------|------|-----|----------|------------|-------------|------------------|
| 0 | [644:656,21:33] | (-7,5,-3) | 0.0054 | 8.32e-02 | 1.54e+01 | 0×0 |
| 0 | [661:673,940:952] | (1,-9,4) | 0.0082 | 6.49e+01 | 7.96e+03 | 0×0 |
| 0 | [535:547,842:854] | (2,-6,2) | 0.0096 | 3.35e+01 | 3.50e+03 | 0×0 |
| 0 | [257:269,37:49] | (-3,8,-9) | 0.0112 | 3.52e+01 | 3.14e+03 | 0×0 |
| 0 | [350:362,877:889] | (4,-5,-1) | 0.0181 | 2.42e+03 | 1.34e+05 | 0×0 |

---

## Top 5 ROIs with Narrowest FWHM

(Smallest geometric mean of fast/slow FWHM — most concentrated spots)

| Panel | BBox | HKL | FWHM (fast×slow) | ROI/Halo | Peak Value |
|-------|------|-----|------------------|----------|------------|
| 0 | [897:909,17:29] | (-10,2,0) | 0×0 | 0.0480 | 4.34e-01 |
| 0 | [644:656,21:33] | (-7,5,-3) | 0×0 | 0.0054 | 3.09e-02 |
| 0 | [257:269,37:49] | (-3,8,-9) | 0×0 | 0.0112 | 5.11e+00 |
| 0 | [939:951,65:77] | (-10,1,1) | 0×0 | 0.0784 | 4.16e-02 |
| 0 | [338:350,92:104] | (-3,7,-7) | 0×0 | 0.0268 | 4.51e+00 |

---

## Orientation Alignment

**Purpose:** Diagnose whether DB-AT-028/029 failures correlate with HKL misalignment (|Δhkl|) vs intensity-only divergence.

- **Reflections analyzed:** 27
- **Median |Δhkl|:** 0.0950
- **P25-P75 |Δhkl|:** 0.0773 - 0.1728
- **Max |Δhkl|:** 0.2473
- **Median resolution:** 3.60 Å
- **Median 2θ:** 15.59°
- **Pearson corr (|Δhkl| vs Stage A/ref ratio):** -0.2864 (27 pairs)

### Top 5 ROIs by HKL Misalignment

(Largest |Δhkl| = ||h_frac - h_int|| — worst orientation errors)

| Panel | BBox | HKL | |Δhkl| | Δhkl | Resolution (Å) | Stage A/Ref Ratio |
|-------|------|-----|-------|------|----------------|-------------------|
| 0 | [644:656,21:33] | (-7,5,-3) | 0.2473 | (-0.106,-0.135,-0.178) | 2.68 | 7.12e-05 |
| 0 | [661:673,940:952] | (1,-9,4) | 0.2330 | (0.135,0.128,0.140) | 3.06 | 1.46e-01 |
| 0 | [535:547,842:854] | (2,-6,2) | 0.2094 | (0.115,0.128,0.120) | 4.14 | 1.68e-02 |
| 0 | [257:269,37:49] | (-3,8,-9) | 0.1958 | (-0.085,-0.102,-0.144) | 2.56 | 2.94e-03 |
| 0 | [350:362,877:889] | (4,-5,-1) | 0.1945 | (0.117,0.106,0.113) | 3.46 | 3.10e+00 |

**Interpretation:**

- Weak correlation (-0.29) suggests orientation is not the primary driver.
- Next step: Focus on physics corrections (Lorentz/partiality/normalization).

---

## Physics Alignment

**Purpose:** Diagnose whether DB-AT-028/029 failures are due to missing Lorentz/partiality factors by comparing Stage A vs |F|²·LP expectations.

- **ROIs analyzed:** 27
- **Median Stage A / |F|²·LP:** 0.0201
- **P25-P75 Stage A / |F|²·LP:** 0.0007 - 0.0445
- **Median Stage A / |F|²:** 0.0934
- **Pearson corr (Stage A/|F|²·LP vs Stage A/ref):** 0.8076 (27 pairs)

### Resolution-Binned Analysis

| Bin | Resolution (Å) | N ROIs | Median Stage A / |F|²·LP |
|-----|----------------|--------|-------------------------|
| 0 | 2.23-5.65 | 24 | 0.0132 |
| 1 | 5.65-9.07 | 1 | 0.0234 |
| 2 | 9.07-12.48 | 1 | 0.8917 |
| 3 | 12.48-15.90 | 1 | 0.0275 |

### Worst 5 ROIs (largest deviation from expected Stage A / |F|²·LP ~ 1.0)

| Panel | BBox | HKL | Resolution (Å) | Stage A/Ref | Stage A/|F|²·LP | Stage A/|F|² | LP Factor |
|-------|------|-----|----------------|-------------|-----------------|--------------|----------|
| 0 | [644:656,21:33] | (-7,5,-3) | 2.68 | 7.12e-05 | 0.0001 | 0.0001 | 2.61 |
| 0 | [661:673,940:952] | (1,-9,4) | 3.06 | 1.46e-01 | 0.0001 | 0.0002 | 3.01 |
| 0 | [535:547,842:854] | (2,-6,2) | 4.14 | 1.68e-02 | 0.0001 | 0.0002 | 4.16 |
| 0 | [350:362,877:889] | (4,-5,-1) | 3.46 | 3.10e+00 | 0.0001 | 0.0005 | 3.44 |
| 0 | [257:269,37:49] | (-3,8,-9) | 2.56 | 2.94e-03 | 0.0002 | 0.0005 | 2.48 |

### Best 5 ROIs (closest to expected Stage A / |F|²·LP ~ 1.0)

| Panel | BBox | HKL | Resolution (Å) | Stage A/Ref | Stage A/|F|²·LP | Stage A/|F|² | LP Factor |
|-------|------|-----|----------------|-------------|-----------------|--------------|----------|
| 0 | [645:657,284:296] | (-4,2,0) | 4.92 | 2.03e+00 | 0.0523 | 0.2593 | 4.96 |
| 0 | [144:156,619:631] | (4,1,-6) | 3.57 | 3.21e+00 | 0.0698 | 0.2483 | 3.56 |
| 0 | [943:955,583:595] | (-5,-6,6) | 3.11 | 4.01e-01 | 0.3870 | 1.1892 | 3.07 |
| 0 | [739:751,610:622] | (-2,-4,4) | 5.38 | 2.68e+00 | 0.5267 | 2.8656 | 5.44 |
| 0 | [431:443,434:446] | (0,2,-2) | 11.46 | 2.34e+02 | 0.8917 | 10.4282 | 11.70 |

**Interpretation:**

- Median Stage A / |F|²·LP = 0.0201 << 1.0 suggests **Stage A is systematically under-predicting** even after LP correction.
- Next step: Verify LP factors are being applied in nanobrag_torch forward model, or audit missing partiality/mosaicity terms.

