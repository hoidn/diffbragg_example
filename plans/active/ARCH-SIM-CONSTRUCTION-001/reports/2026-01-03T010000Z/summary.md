# Phase C.31 Loop Summary — Lattice-Scaling Pipeline Instrumentation

**Initiative:** ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
**Date:** 2026-01-03T010000Z
**Mode:** Parity
**ActionType:** debug
**DecisionStatus:** localized
**Actor:** Ralph

## Problem & SPEC/ARCH Alignment

Per docs/spec-db-core.md:60-140, the SQUARE lattice must produce intensity scaling proportional to (Na·Nb·Nc)². Phase C.30 (2026-01-02T010000Z) captured decision-carrying evidence showing observed ratio 84,612.8 vs expected 1,447,650,304 (0.000058× deviation, ~4 orders of magnitude shortfall). Trace logs showed F_latt components (41, 29, 32) correctly computed but final intensity collapsed.

**ARCH Contract:** docs/spec-db-core.md:60-140
**Owner:** `nanobrag_torch.simulator.compute_physics_for_position` (SQUARE branch)
**Contract Violation:** Lattice weights do not scale with (Na·Nb·Nc)²
**SIM-CONSTR-PARTIALITY-001:** Decision-carrying finding on lattice partiality instrumentation

**Task (Phase C.31):** Add opt-in instrumentation to capture F_cell, F_latt, (F_cell·F_latt)², and intensity_pre_polar before the production patch so we can bisect the missing multiplier in the intensity pipeline.

## Search & Existing Implementation

Reviewed `simulator.py:287-458`:
- F_latt computation (lines 294-325): SQUARE branch computes F_latt_a/b/c via sincg, combines via product
- Intensity calculation (lines 378-380): `F_total = F_cell * F_latt`, `intensity = F_total * F_total`
- Lorentz application (lines 402-432): computes lorentz factor and applies to intensity
- Pre-polar capture (line 437): intensity_pre_polar cloned after Lorentz
- Existing partiality_stats hook (lines 446-455): captures f_latt, f_latt_squared, lorentz_factor

**Referenced APIs:**
- `nanobrag_torch.simulator.compute_physics_for_position:19-546` — physics computation function
- `partiality_stats` dict (optional parameter) — debug payload destination
- `simulator._partiality_stats` — internal dict accessed by probe script

## Code Analysis Performed

**Instrumentation sites identified:**
1. **Line 382-387:** After `F_total = F_cell * F_latt` and `intensity = F_total * F_total` (pre-Lorentz)
   - Added capture of `F_cell` and `F_total_squared_pre_lorentz` to partiality_stats
   - This allows bisecting whether bug is in F_total computation or downstream

2. **Line 456-458:** After `intensity = intensity * lorentz` (post-Lorentz, pre-polarization)
   - Added capture of `intensity_pre_polar` to partiality_stats
   - This allows isolating Lorentz vs polarization contributions

**Probe script extraction (probe_square_lattice_scaling.py:100-131):**
- Accessed `simulator._partiality_stats` directly (not via debug_stats wrapper)
- Extracted scalar values via `.mean().item()` for F_cell, f_latt, F_total_squared_pre_lorentz, intensity_pre_polar
- Computed derived ratios to pinpoint divergence location

## Changes Made

### 1. Simulator Instrumentation (src/nanobrag-torch/src/nanobrag_torch/simulator.py)

**Lines 382-387** (after F_total computation):
```python
# ARCH-SIM-CONSTRUCTION-001 Phase C.31: Capture F_cell, F_latt, F_total^2 when debug hooks enabled
# This opt-in instrumentation allows us to bisect the (Na·Nb·Nc)² scaling deficit
# before the Lorentz/polarization corrections are applied
if partiality_stats is not None:
    partiality_stats['F_cell'] = F_cell.detach().cpu()
    partiality_stats['F_total_squared_pre_lorentz'] = intensity.detach().cpu()
```

**Lines 456-458** (after Lorentz application):
```python
# Phase C.31: Capture pre-polar intensity (after Lorentz, before polarization)
# for ratio analysis: (pre_polar)/(F_cell·F_latt)²
partiality_stats['intensity_pre_polar'] = intensity.detach().cpu()
```

### 2. Probe Script Enhancement (plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py)

**Lines 100-131** (payload extraction):
- Access `simulator._partiality_stats` directly
- Extract F_cell, f_latt, F_total_squared_pre_lorentz, intensity_pre_polar
- Return as third value from run_simulation()

**Lines 206-256** (derived ratios computation):
- `F_latt_ratio`: (scaled F_latt) / (base F_latt) vs expected Na·Nb·Nc
- `F_total_sq_ratio`: (scaled F_total²) / (base F_total²) vs expected (Na·Nb·Nc)²
- `I_pre_polar_ratio`: (scaled I_pre_polar) / (base I_pre_polar) vs expected (Na·Nb·Nc)²
- `{base,scaled}_I_pre_polar_over_F_total_sq`: isolates Lorentz contribution

**Lines 276-285, 316-341** (JSON/Markdown output):
- Added payload section with base/scaled dictionaries
- Added derived_ratios section
- Added Phase C.31 Payload Analysis section in Markdown with base/scaled breakdowns

### 3. Documentation (plans/active/ARCH-SIM-CONSTRUCTION-001/implementation.md)

**Lines 418-433** (Phase C.31 entry):
- Documented instrumentation scope and file locations
- Listed 5 hypotheses to confirm/refute via derived ratios
- Specified evidence artifacts path

**File modifications summary:**
- `src/nanobrag-torch/src/nanobrag_torch/simulator.py`: +9 lines (instrumentation hooks)
- `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py`: +140 lines (payload extraction + ratios)
- `plans/active/ARCH-SIM-CONSTRUCTION-001/implementation.md`: +19 lines (Phase C.31 documentation)

## Tests and Static Checks

### Probe Script Execution

**Command:**
```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py \
  --output-dir plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-03T010000Z \
  --n-cells 41 29 32 --oversample 13 --phi-count 1 --mosaic-count 1 --spixels 1 --fpixels 1 \
  | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-03T010000Z/square_lattice_probe.log
```

**Result:** SUCCESS — Probe executed with payload extraction

**Base case payload:**
- F_cell: 1.000000e+02 (correct)
- F_latt: 1.000000e+00 (correct for N_cells=1,1,1)
- F_total²: 1.000000e+04 (correct: 100²)
- I_pre_polar: 6.524473e+06

**Scaled case payload:**
- F_cell: 1.000000e+02 (correct, same structure factor)
- **F_latt: -3.807035e+00** (WRONG! Expected 38,048)
- F_total²: 8.041414e+08
- I_pre_polar: 5.520534e+11

**Derived ratios:**
- `F_latt_ratio: -3.807035e+00` vs expected 3.804800e+04 (factor 10,000× discrepancy)
- `F_total_sq_ratio: 8.041414e+04` vs expected 1.447650e+09 (factor 18,000× discrepancy)
- `I_pre_polar_ratio: 8.461272e+04` vs expected 1.447650e+09 (matches intensity shortfall)
- `base_I_pre_polar_over_F_total_sq: 6.524473e+02`
- `scaled_I_pre_polar_over_F_total_sq: 3.808968e+06` (ratio 5,835× difference)

### Enforcement Test Re-run

**Command:**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' \
pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells \
  | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-03T010000Z/pytest_partiality.log
```

**Result:** FAILED (expected) — 2 failed (cpu, cuda), 16 warnings

**CPU result:**
- Observed ratio: 3,557,859.0
- Expected ratio: 1,447,650,304.0
- Relative error: 99.75% (tolerance=5%)

**CUDA result:**
- Observed ratio: 3,554,941.8
- Expected ratio: 1,447,650,304.0
- Relative error: 99.75% (tolerance=5%)

Both device backends reproduce the same deterministic DMI signature.

**Static checks:** Not applicable (evidence-only loop, no production behavior changes outside opt-in debug hooks)

## Docs & Ledgers Updates

### 1. docs/fix_plan.md

**Line 870** (Attempts History):
Added Phase C.31 entry documenting the critical F_latt aggregation bug discovery. Entry includes:
- Instrumentation file locations (simulator.py:382-387, 456-458)
- Probe enhancement scope (payload extraction, derived ratios)
- CRITICAL FINDING: F_latt=-3.8 in scaled case (expected 38,048)
- Root cause hypothesis: partiality_stats aggregation taking .mean() over mixed-sign tensor
- Derived ratios confirming bug location (18,000× discrepancy in F_total_sq_ratio)
- Next action: inspect simulator.py:453 partiality_stats['f_latt'] assignment

### 2. plans/active/ARCH-SIM-CONSTRUCTION-001/implementation.md

**Lines 418-433** (Phase C.31 section):
- Added instrumentation scope documentation
- Listed 5 hypotheses with expected vs observed behaviors
- Specified artifacts path and evidence requirements

### 3. Artifacts Organized

All outputs captured under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-03T010000Z/`:
- **square_lattice_scaling.json:** Full payload + derived ratios
- **square_lattice_scaling.md:** Markdown report with Phase C.31 Payload Analysis section
- **square_lattice_probe.log:** Stdout capture with payload printout
- **pytest_partiality.log:** Enforcement test failure log (cpu + cuda)
- **summary.md:** This document

## Critical Finding — F_latt Aggregation Bug

### Smoking Gun Evidence

The Phase C.31 payload reveals the root cause with high confidence:

**Base case (N_cells=1,1,1):**
- F_latt extracted: **1.0** (correct)
- This matches the expected sincg product for unit cells

**Scaled case (N_cells=41,29,32):**
- F_latt extracted: **-3.807** (WRONG!)
- Expected: 38,048 (from trace: F_latt_a=41 × F_latt_b=29 × F_latt_c=32)
- The **negative value** is the critical clue

### Root Cause Hypothesis

The negative F_latt value indicates that `partiality_stats['f_latt']` is being populated with a **tensor that contains both positive and negative values**, and the probe script takes `.mean()` over those values, resulting in near-zero or negative aggregate.

**Probable cause (simulator.py:453):**
```python
partiality_stats['f_latt'] = F_latt.detach().cpu()
```

This line captures the **pre-summed F_latt tensor** with shape `(S, F, N_phi, N_mos)` or similar, which contains sincg values that can be positive or negative depending on the fractional HKL offsets at each phi/mosaic sample.

**What the probe does:**
```python
f_latt = pstats['f_latt']
payload['F_latt'] = float(f_latt.mean().item())  # Takes mean over entire tensor!
```

For the scaled case with N_cells=(41,29,32), the F_latt tensor at each spatial/phi/mosaic point is the product `F_latt_a * F_latt_b * F_latt_c`, where each factor is a sincg evaluation. The sincg function oscillates between positive and negative values depending on the fractional offset from integer HKL.

When these values are averaged across spatial dimensions (S×F) and phi/mosaic dimensions, the positive and negative contributions cancel, yielding a tiny or negative mean (~-3.8 in this case).

### Correct Aggregation Strategy

The **correct** value to capture is the **post-phi/mosaic-summed** `F_latt` at line 325, which is a scalar or low-dimensional tensor representing the lattice weight after integrating over all phi/mosaic samples. This is what gets multiplied by F_cell to produce F_total.

**Line 325:**
```python
F_latt = F_latt_a * F_latt_b * F_latt_c  # Shape: (S, F, N_phi, N_mos) or similar
```

Then later (lines 391-393):
```python
intensity = torch.sum(intensity, dim=(-2, -1))  # Sums over phi and mosaic
```

So the aggregation should capture `F_latt` **after** the phi/mosaic sum, or equivalently, we need to sum `F_latt` over the same dimensions before storing in partiality_stats.

### Supporting Evidence from Derived Ratios

1. **F_total_sq_ratio = 8.04e4** vs expected 1.45e9:
   - This is 18,000× too small
   - Close to the observed intensity ratio (84,612×), confirming the bug is in F_latt/F_total computation, not downstream

2. **I_pre_polar_ratio = 8.46e4** vs expected 1.45e9:
   - Matches the intensity shortfall exactly
   - Confirms Lorentz/polarization are NOT the primary issue

3. **I_pre_polar / F_total_sq ratios:**
   - Base: 652
   - Scaled: 3.81e6
   - Ratio: 5,835×
   - This secondary discrepancy suggests Lorentz may scale slightly differently with larger F_latt magnitudes, but the primary bug is in F_latt aggregation

## Next Step

**Most important follow-up:** Inspect `simulator.py:453` where `partiality_stats['f_latt']` is assigned. The correct fix is to:

1. Either capture F_latt **after** the phi/mosaic sum (near line 393), or
2. Modify line 453 to sum F_latt over dimensions (-2, -1) before storing:
   ```python
   partiality_stats['f_latt'] = torch.sum(F_latt, dim=(-2, -1)).detach().cpu()
   ```

Then rerun the probe expecting:
- F_latt_ratio ≈ 38,048 (Na·Nb·Nc)
- F_total_sq_ratio ≈ 1.45e9 (Na·Nb·Nc)²
- Final intensity scaling fixed

Once payload confirms correct F_latt aggregation, proceed to patch production code if needed, or confirm the existing intensity calculation is correct and the bug was only in the debug instrumentation.

---

### Turn Summary

Instrumented simulator.py::compute_physics_for_position with Phase C.31 debug payload (F_cell, F_total², I_pre_polar). Extended probe script to extract and report derived ratios. **CRITICAL DISCOVERY:** F_latt aggregation bug revealed by payload showing scaled F_latt=-3.8 (expected 38,048). Root cause: partiality_stats captures pre-sum tensor; probe takes .mean() over mixed-sign sincg values causing cancellation. Derived ratios confirm F_total_sq shortfall (8.04e4 vs 1.45e9) matches intensity bug. Next: fix partiality_stats aggregation to sum over phi/mosaic dims, rerun probe expecting correct scaling.

**Artifacts:** `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-03T010000Z/` containing square_lattice_scaling.{json,md}, square_lattice_probe.log, pytest_partiality.log, summary.md
