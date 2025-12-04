# Phase C.30 Loop Summary — Single-Pixel Square Lattice Scaling Probe

**Initiative:** ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
**Date:** 2026-01-02T010000Z
**Mode:** Parity
**ActionType:** parity_localization
**DecisionStatus:** localized
**Actor:** Ralph

## Problem & SPEC/ARCH Alignment

Per docs/spec-db-core.md:60-140, the SQUARE lattice shape must produce weights proportional to (Na·Nb·Nc)² when N_cells=(Na,Nb,Nc). The enforcement test `tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells` has been failing with ~99.75% shortfall, indicating a systematic bug in the lattice weight computation within `src/nanobrag-torch/src/nanobrag_torch/simulator.py::compute_physics_for_position` (SQUARE branch).

**ARCH Contract:** docs/spec-db-core.md:60-140
**Owner:** `nanobrag_torch.simulator.compute_physics_for_position` (SQUARE branch)
**Contract Violation:** Lattice weights do not scale with (Na·Nb·Nc)²

Previous instrumentation (Phase C.29, 2025-12-27T180000Z) captured per-axis sincg evidence showing F_latt_a/b/c medians (0.06, 0.09, -0.001) << Na/Nb/Nc (41, 29, 32), suggesting collapse in the sincg product. Phase C.30 was tasked with creating a minimal reproduction outside the Stage A baseline context.

## Search & Existing Implementation

Reviewed existing probe scripts under `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/`:
- `compare_stage_a_baseline.py` (2220 LOC) — complex Stage A + mapping reconstruction helper
- `probe_stage_a_scale_alignment.py` (424 LOC) — mask alignment diagnostic
- Other comparison scripts (simulator_outputs, simulate_forward_once_vs_reconstruction)

**Decision:** Implement new thin wrapper `probe_square_lattice_scaling.py` that directly calls `nanobrag_torch.Simulator` owner APIs with minimal configuration (1×1 detector, single phi/mosaic, trace pixel enabled).

**Referenced APIs:**
- `nanobrag_torch.simulator.Simulator:557` — constructor accepting crystal, detector, configs
- `nanobrag_torch.config.CrystalConfig:97` — N_cells, shape, phi_steps, mosaic_domains
- `nanobrag_torch.config.DetectorConfig:168` — distance_mm, pixel_size_mm, spixels, fpixels, oversample
- `nanobrag_torch.config.BeamConfig:496` — wavelength_A defaults

## Code Analysis Performed

**Trace output analysis** (from square_lattice_probe.log lines 12-51, 53-92):

Base case (N_cells=1,1,1):
- `F_latt_a=1, F_latt_b=1, F_latt_c=1` → `F_latt=1` (expected)
- `F_cell_interpolated=100`
- `I_before_scaling_post_polar=1102634752` → normalized intensity=1.102634e+03
- Final intensity: 6.524461e+00

Scaled case (N_cells=41,29,32):
- `F_latt_a=41, F_latt_b=29, F_latt_c=32` → `F_latt=38048` (matches Na·Nb·Nc=38,048)
- `F_cell_interpolated=100` (same)
- `I_before_scaling_post_polar=93296965713920` → normalized intensity=9.329689e+07
- Final intensity: 5.520526e+05

**Key observation:** F_latt product is correctly computed (38,048 = 41×29×32), but the final intensity ratio (5.52e5 / 6.52) = 84,612.8 is ~17,000× smaller than the expected (38,048)² = 1,447,650,304.

The trace shows `I_before_scaling_pre_polar` and `I_before_scaling_post_polar` differ by negligible amounts (polarization correction). The normalized intensity scales by ~84,600× (93,296,897 / 1,102,634 ≈ 84,600), which matches the observed final intensity ratio, suggesting the bug is **not** in post-normalization scaling but rather in the intensity computation itself where F_latt² should contribute.

## Changes Made

1. **Created** `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py` (254 lines)
   - Thin wrapper accepting CLI args: `--output-dir`, `--n-cells`, `--oversample`, `--phi-count`, `--mosaic-count`, `--spixels`, `--fpixels`, `--device`
   - Instantiates `DetectorConfig` with oversample parameter
   - Instantiates `CrystalConfig` with phi_steps, mosaic_domains (not oversample/phi_count/mosaic_count which don't exist on CrystalConfig)
   - Creates two `Simulator` instances: base (1,1,1) and scaled (Na,Nb,Nc)
   - Captures trace output via `debug_config={'collect_partiality_stats': True, 'trace_pixel': [0,0]}`
   - Emits JSON + Markdown + console log

2. **Generated artifacts** under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-02T010000Z/`:
   - `square_lattice_scaling.json` — intensities, ratios, deviation factor (0.000058x)
   - `square_lattice_scaling.md` — formatted report with ❌ contract violation marker
   - `square_lattice_probe.log` — full trace output with F_latt_a/b/c values
   - `pytest_partiality.log` — enforcement test failure (10×10 detector: observed=3.56e6 vs expected=1.45e9)

**File modifications:**
- 1 file added: `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py` (254 lines)
- 4 artifact files generated

## Tests and Static Checks

**Probe script execution:**
```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py \
  --output-dir plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-02T010000Z \
  --n-cells 41 29 32 --oversample 13 --phi-count 1 --mosaic-count 1 --spixels 1 --fpixels 1 \
  | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-02T010000Z/square_lattice_probe.log
```
**Result:** SUCCESS — Base intensity=6.524461e+00, Scaled intensity=5.520526e+05, Observed ratio=84,612.8 vs Expected=1,447,650,304

**Enforcement test re-run:**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' \
pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells --maxfail=1 \
  | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-02T010000Z/pytest_partiality.log
```
**Result:** FAILED (expected) — Lattice weight scaling violation: observed=3,557,859.0, expected=1,447,650,304.0, relative_error=99.75%

Both probe (1×1 detector) and enforcement test (10×10 detector) reproduce the same deterministic DMI: the (Na·Nb·Nc)² scaling is off by ~17,000× to ~400×.

**Static checks:** Not applicable (evidence-only loop, no production code changes)

## Docs & Ledgers Updates

1. **docs/fix_plan.md** — Added attempt entry at line 853+:
   - Phase C.30 complete timestamp: 2026-01-02T010000Z
   - Key metrics: base=6.52e+00, scaled=5.52e+05, observed ratio=84,612.8, expected=1.45e9, deviation=0.000058x
   - Status: decision-carrying evidence captured
   - Next action: analyze sincg implementation in simulator.py::compute_physics_for_position SQUARE branch

2. **docs/findings.md** — No new entry (evidence only; awaiting root cause diagnosis)

3. **Artifacts organized:**
   - All JSON/Markdown/log files under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-02T010000Z/`
   - Probe output: square_lattice_scaling.{json,md}, square_lattice_probe.log
   - Enforcement log: pytest_partiality.log

## Next Step

**Most important follow-up:** Analyze the sincg implementation in `src/nanobrag-torch/src/nanobrag_torch/simulator.py::compute_physics_for_position` (SQUARE branch) to determine why the intensity scaling is missing ~4 orders of magnitude. The trace shows F_latt_a/b/c are correctly computed (41, 29, 32), and the product F_latt=38,048 is correct, but the final intensity ratio suggests F_latt² is not being applied correctly—possibly a missing square operation or incorrect intensity accumulation formula. Propose targeted patch under patch_ready DecisionStatus once root cause is identified.

---

### Turn Summary

Delivered single-pixel square lattice scaling probe capturing massive (Na·Nb·Nc)² shortfall (observed ratio 84,612 vs expected 1.45e9, deviation=0.000058x). Trace logs confirm F_latt components correct (41,29,32 → product 38,048) but intensity missing ~4 orders of magnitude. Enforcement test reproduces same DMI (10×10 detector: 99.75% error). Evidence now isolates bug to intensity formula in SQUARE branch. Next: analyze sincg squaring/accumulation logic for missing F_latt² application.

**Artifacts:** `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-02T010000Z/` containing square_lattice_scaling.{json,md}, square_lattice_probe.log, pytest_partiality.log
