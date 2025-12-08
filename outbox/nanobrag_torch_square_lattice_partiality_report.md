# nanobrag_torch SQUARE Lattice Partiality / Intensity Issues — DBEX Integration Report

Prepared by: DBEX maintainers (Galph/Ralph agent loop)  
Context: DBEX + `nanobrag_torch` integration, DB‑AT‑028/029 “Stage‑A Structure / Intensity Parity”

This report summarizes the remaining SQUARE‑lattice partiality/intensity problems observed when using `nanobrag_torch` as the simulator backend for DBEX. The goal is to hand over a concise, evidence‑backed description of the issue for nanobrag_torch maintainers, together with concrete repro steps and pointers to in‑repo diagnostics.

We avoid relying on ephemeral runtime logs; all references below point to checked‑in tests and markdown reports in this repository.

---

## 1. Contract and Enforcement Test

**Spec contract**

- Spec‑DB core (DBEX): `docs/spec-db-core.md` §§60‑140 define the lattice weight contract. For the SQUARE lattice shape, lattice weights must scale as:
  \[
    I(N_a, N_b, N_c) \propto (N_a \cdot N_b \cdot N_c)^2
  \]
  when evaluated at sufficient precision.
- This is the basis for DB‑AT‑028/029’s expectations about Stage‑A intensity and ROI correlation when changing `N_cells`.

**Architecture enforcement test**

- File: `tests/architecture/test_nanobrag_partiality.py`
- Selector: `tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells`
- Purpose: enforce the SQUARE lattice contract at the simulator level, independent of DBEX.
- Test structure (non‑exhaustive summary, see file for details):
  - Uses `nanobrag_torch.config` and models directly:
    - `CrystalConfig(default_F=100.0, N_cells=(1,1,1), shape=CrystalShape.SQUARE)`
    - `CrystalConfig(default_F=100.0, N_cells=(Na,Nb,Nc), shape=CrystalShape.SQUARE)` with `Na=41, Nb=29, Nc=32`
    - `DetectorConfig(distance_mm=100.0, pixel_size_mm=0.1, spixels=10, fpixels=10, oversample=13)`
    - `BeamConfig()` (defaults; wavelength_A=1.0)
  - Runs two simulations on the same detector:
    1. Base: `N_cells=(1,1,1)` → intensity `I₁ = image_base.sum()`
    2. Scaled: `N_cells=(Na,Nb,Nc)` → intensity `I₂ = image_scaled.sum()`
  - Expected lattice scaling:
    - `expected_ratio = (Na * Nb * Nc) ** 2`
  - Assertions:
    - `steps_scalar` in `partiality_stats` must be 1.0 for SQUARE shape (integral normalization, no `oversample²` factor).
    - When `oversample=13` and `shape=SQUARE`, telemetry flags `omega_applied_post_sum=True` to ensure omega is applied once after Riemann sum (SQUARE‑specific path).
    - Ratio constraint:
      - `relative_error = |(I₂/I₁) − expected_ratio| / expected_ratio < 0.01` (1% tolerance)
      - Additional sanity check that `I₂/I₁` lies in `[0.8, 1.2] * expected_ratio`.

In the **current nanobrag_torch version used by DBEX**, this test fails badly: intensities are orders of magnitude too small, even though the per‑axis sincg kernel appears correct (see §3).

---

## 2. High‑Level Symptom and Impact

**Observed behavior (summary):**

- For the 10×10 detector architecture test with `N_cells = (41,29,32)` and `oversample=13`, DBEX observes:
  - `expected_ratio = (Na·Nb·Nc)² = 1,447,650,304.0`
  - `observed_ratio = I₂/I₁ ≈ 3,494,551.6`
  - `relative_error ≈ 99.76%`  
    → intensity under‑scaled by a factor of about **414×** compared to the Spec‑DB contract.

- Additional probes under `plans/active/ARCH-SIM-CONSTRUCTION-001/` show:
  - Raw subpixel sum ratio before omega application:
    - `raw_sum_ratio ≈ 1.36e8` vs expected `1.44765e9` → about **9.4%** of expected.
  - Lattice amplitude:
    - `F_latt_observed ≈ 4,206.5` vs expected `38,048.0` → about **11.06%** of expected amplitude.
    - Squaring this amplitude would predict ≈1.22% of expected intensity, but the actual intensity ratio is ≈9.4%, implying multiple compounding issues in how the lattice is aggregated and applied.

**Impact on DB‑AT selectors:**

- DB‑AT‑028/029 (Stage‑A structure/intensity parity) run on top of this simulator behavior. With SQUARE‑lattice intensity under‑scaled by ~1–2 orders of magnitude,:
  - `chi²/pixel` and ROI correlation thresholds for DB‑AT‑028/029 are effectively unreachable, even when geometry, masks, and sigma are correct.
  - This is why the DBEX plan `[ARCH-SIM-CONSTRUCTION-001] Simulator Construction Convention Alignment` is marked as a Tier‑0 `blocked_pending_environment` issue in `docs/fix_plan.md`.

---

## 3. Diagnostic Evidence and Localization

The DBEX initiative `[ARCH-SIM-CONSTRUCTION-001]` spent 39 loops analyzing this behavior. Key conclusions (all in‑repo) are:

### 3.1 sincg kernel is correct — bug is downstream

- Source: `docs/fix_plan_archive.md` entry for `ARCH-SIM-CONSTRUCTION-001` at `2026-01-04T010000Z` (Phase C.32), summarized in the `SIM-CONSTR-PARTIALITY-001` and related findings.
- Diagnostic script: `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py`
  - Adds a high‑precision NumPy reference `sincg_reference(delta, N)` and compares it to `nanobrag_torch.utils.physics.sincg` for all sampled subpixels.
- Result:
  - Per‑axis sincg (`F_latt_a`, `F_latt_b`, `F_latt_c`) matches the reference to within:
    - median relative error < 1e‑4%
    - max relative error < 1e‑4%
  - Single‑sample F_latt at the Bragg peak center is correct (≈38,048).
  - **Downstream aggregation is wrong**:
    - Compounded `F_latt` (after whatever accumulation/averaging the simulator performs) shows:
      - reference median ≈ 2.32
      - production ≈ −3.81 (sign‑flipped, wrong magnitude)
      - both values are ≈6.1e‑5 of the expected `Na·Nb·Nc = 38,048`.
  - Enforcement architecture test still fails:
    - `observed_ratio ≈ 3.56e6` vs expected `1.44765e9` → ≈0.25% of expected at that point in the history.

**Conclusion:** the sincg kernel itself (per‑axis) is **not** the cause. The bug lies in the **SQUARE branch’s aggregation** of per‑axis sincg values into `F_latt`, and/or how these per‑sample values are accumulated/normalized across subpixels/sources/phi/mosaic.

### 3.2 Omega / solid‑angle handling is not the primary cause

- Later loops (C.39) implemented a SQUARE‑specific omega compensation path to ensure:
  - For SQUARE with `oversample>1`, omega is applied **once** after the Riemann sum, instead of per‑subpixel.
  - Telemetry flags `omega_applied_post_sum=True` and `square_used_riemann_sum=True` confirm this behavior.
- Source: `docs/fix_plan_archive.md` entries around lines `4136‑4147` and `docs/findings.md` entries `SIM-CONSTR-PARTIALITY-001`, `CONFIG-002`.
- Even with these changes:
  - The architecture test still fails with:
    - `expected_ratio = 1.447650304e9`
    - `observed_ratio ≈ 3,494,551.6`
    - `relative_error ≈ 99.76%` (≈414× deficit)
  - Probe logs show that **omega cancels in the ratio** (both base and scaled runs see similar omega), so the residual deficit must originate earlier:
    - raw subpixel sums before omega application already show the ~9.4% / 11% level deficits described in §2.

**Conclusion:** omega placement and oversample normalization have been adjusted and instrumented; they are not sufficient to fix the problem. The core issue remains in how SQUARE‑lattice F_latt is combined and used to scale intensities.

### 3.3 Final lifecycle decision

- `docs/fix_plan_archive.md` and `docs/fix_plan.md` mark `[ARCH-SIM-CONSTRUCTION-001]` as:
  - `Status: blocked_pending_environment`
  - Root cause: “sincg lattice factor computation bug in nanobrag_torch SQUARE branch” (downstream aggregation, not the sincg kernel).
  - Further DBEX‑side instrumentation is forbidden by PROBE‑FREEZE and Environment‑Freeze rules; loop budget (39 iterations) is exhausted.
- The portfolio explicitly recommends:
  - (A) nanobrag_torch maintainer investigation (preferred), or
  - (B) Spec‑DB change to relax DB‑AT‑028/029, or
  - (C) a dedicated diagnostics project in a different harness.

---

## 4. Reproduction Steps (for nanobrag_torch Maintainer)

These steps assume the DBEX repository with its pinned `nanobrag_torch` submodule or editable install.

1. **Run the partiality architecture test**

   ```bash
   # From the DBEX repo root
   KMP_DUPLICATE_LIB_OK=TRUE pytest -vv \
     tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells
   ```

   - Expected today: failure with a message similar to:
     - `expected ratio=1447650304.0, observed≈3.5e6, relative_error≈99.76%`
   - This test is intentionally minimal: no DIALS/cctbx; it uses only `nanobrag_torch` configs and models.

2. **Inspect the square‑lattice probe**

   ```bash
   # Optional but useful: DBEX diagnostic script
   python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py \
     --device cpu \
     --output-dir plans/active/ARCH-SIM-CONSTRUCTION-001/reports/local_probe/
   ```

   - This script emits:
     - Per‑axis sincg error statistics (showing the kernel is correct).
     - Compounded F_latt aggregation metrics (showing the downstream product is wrong).
     - Raw vs expected intensity ratios.

3. **Reference evidence**

   - `docs/fix_plan_archive.md`:
     - Entries tagged `[ARCH-SIM-CONSTRUCTION-001]` at:
       - `2026-01-04T010000Z` (Phase C.32 — sincg kernel validation, aggregation bug localization).
       - `2026-01-13T010000Z` and `2026-01-13T150000Z` (omega compensation experiments, 9.4%/11% deficits, 414× failure).
       - `2026-01-13T200000Z` (lifecycle decision, initiative marked blocked).
   - `docs/findings.md`:
     - `SIM-CONSTR-PARTIALITY-001` and `CONFIG-002` capture the partial fixes already applied (oversample normalization, beam‑center alignment) and the remaining error budget.

---

## 5. What We Believe Needs Attention Upstream

Based on the above, DBEX maintainers believe the primary remaining issues lie in the **SQUARE branch of nanobrag_torch’s simulator**, specifically:

1. **Aggregation of per‑axis sincg values into `F_latt`**
   - The per‑axis sincg values are correct, but the final `F_latt` product seen in partiality stats is both sign‑flipped and dramatically reduced in magnitude (≈6.1e‑5 of expected in some probes, ≈11% in later ones).
   - Candidate locations: the code that computes `F_latt = F_latt_a * F_latt_b * F_latt_c` and how that is averaged/accumulated over subpixels, phi steps, and mosaic domains.

2. **Use of `F_latt` to scale intensity**
   - Even when `F_latt` at the pixel center is correct (~38,048), the resulting intensity ratio is only ~0.25–9% of `(Na·Nb·Nc)²` across probes.
   - There may be a mismatch between the intended integral semantics for SQUARE (sum vs mean over subpixels) and the current implementation, especially with `oversample>1`.

3. **Consistency with Spec‑DB and tests**
   - The enforcement test in DBEX is intentionally simple and fully contained in `nanobrag_torch`’s public API; passing it should be compatible with the simulator’s own expectations about normalization.
   - Any upstream fix should:
     - Preserve the verified sincg kernel behavior.
     - Bring `test_square_lattice_applies_ncells` into the 1% tolerance band.
     - Allow DB‑AT‑028/029 to be re‑evaluated on the DBEX side.

DBEX cannot safely instrument or change these internals further under its Environment‑Freeze / PROBE‑FREEZE rules. We are therefore handing this over as a focused, upstream issue report.

Once a fix lands in `nanobrag_torch`, DBEX maintainers will:

- Update the local environment tag and patch ledger under `plans/active/ARCH-SIM-CONSTRUCTION-001/patches/`.
- Re‑run:
  - `tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells`
  - The square‑lattice probe script
  - DB‑AT‑028/029
- And, if those pass within the documented tolerances, clear the `blocked_pending_environment` status on `[ARCH-SIM-CONSTRUCTION-001]` in `docs/fix_plan.md`.

