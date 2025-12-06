# Phase C.39 — Omega Compensation BLOCKED (2026-01-13T010000Z)

## Status: BLOCKED

## Problem & SPEC/ARCH Alignment

input.md specifies implementing C.39 omega compensation for SQUARE lattices with oversample>1: skip per-subpixel omega multiplication, accumulate raw sum (Riemann integral), then apply omega_scalar once after aggregation "mirroring the oversample==1 branch" (input.md:26-31).

ARCH contracts:
- SCALE-009 (docs/spec-db-core.md:60-140): SQUARE lattice must emit weights ∝ `(Na·Nb·Nc)²`
- Omega placement (docs/architecture/calibration_scaling.md:80-145): Lorentz solid-angle correction
- DMI ledger (input.md:42-45): Expected normalized/raw ratio ≈ 1.0

## Search & Existing Implementation

Found C.39 patch already present in `src/nanobrag-torch/src/nanobrag_torch/simulator.py`:
- Line 1336: `is_square = self.crystal.config.shape == CrystalShape.SQUARE`
- Lines 1338-1347: SQUARE path skips per-subpixel omega; others apply conditional omega
- Line 1358: Riemann-sum aggregation `torch.sum(intensity_all, dim=2)`
- Lines 1377-1391: SQUARE applies center omega once after sum; telemetry `omega_applied_post_sum=True`, `square_used_riemann_sum=True`

Architecture test `tests/architecture/test_nanobrag_partiality.py` already has tight assertions (1% tolerance, omega telemetry enforcement). Probe script already ingests omega telemetry flags.

## Code Analysis & DMI Ledger Evidence

Verified patch implementation at `src/nanobrag-torch/src/nanobrag_torch/simulator.py:1333-1418`:
1. SQUARE lattice clones raw physics intensity (line 1341), no per-subpixel omega
2. Sums all subpixels (line 1358)
3. Applies `center_omega = omega_all[:, :, center_idx]` once after sum (line 1382)
4. Sets telemetry flags (lines 1387-1388)

**Critical finding**: The oversample==1 branch (line 1487) applies `omega_pixel` directly. "Mirroring" this means SQUARE+oversample>1 also applies omega. But omega ≈ 1e-6 for the test geometry (100mm distance, 0.1mm pixel). Applying this reduces intensity by 1e-6, NOT restoring `(Na·Nb·Nc)²`.

DMI Ledger Observed Evidence (input.md:42-45) expects normalized/raw ratio ≈ 1.0, but applying omega gives 1e-6.

**Contradiction**: Patch as specified applies omega ONCE after sum (not per subpixel), yet normalized/raw = 1e-6 persists, proving omega IS reducing intensity. The expected ratio ≈1.0 implies omega should NOT reduce intensity, contradicting "mirror oversample==1" which DOES apply omega.

## Changes Made

1. Extended `probe_square_lattice_scaling.py:303-309` to ingest `square_used_riemann_sum` telemetry flag
2. Captured `git diff` → `patches/omega_compensation.patch` (114 lines)
3. Updated `patches/environment_tag.md` with nanobrag-partiality-omega-2026-01-13 entry
4. No production code committed (changes in working tree only, BLOCKED status)

## Tests and Static Checks

### Mapped Tests Executed

1. **Probe**: `probe_square_lattice_scaling.py --n-cells 41 29 32 --oversample 13`
   - Expected: 1,447,650,304.0
   - Observed: 136,015,748.6
   - **Relative error: 90.60%** (vs ≤1% exit criterion)
   - Normalized/raw ratio: 0.000001 (omega applied)
   - Telemetry: `omega_applied_post_sum=true` (C.39 logic confirmed active)

2. **Architecture Test**: `pytest tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells[cpu]`
   - Expected: 1,447,650,304.0
   - Observed: 3,494,551.6
   - **Relative error: 99.76% FAIL**

3. **DB-AT-028/029**: Not executed (probe/test must pass first)

## Docs & Ledgers Updates

1. **docs/fix_plan.md**: Appended 2026-01-13T010000Z entry documenting failure, hypothesis, blocking status
2. **patches/environment_tag.md**: Updated with actual file paths
3. **docs/findings.md**: NOT updated (deferred until fix validated)

## Next Step

**BLOCKED** — Supervisor must resolve input.md specification contradiction:
- Input says "apply omega_scalar once after sum (mirroring oversample==1)"
- DMI ledger expects normalized/raw ratio ≈ 1.0
- These are incompatible: omega ≈ 1e-6, so applying it gives ratio 1e-6, not 1.0

**Recommended Actions**:
1. **spec_change**: Clarify if SQUARE+oversample>1 should skip omega (let final scaling handle solid angle)
2. **investigate**: Check if omega should be compensated by multiplying by `oversample²`
3. **revert**: Abandon C.39, re-diagnose why C.35 didn't resolve deficit

---

### Turn Summary

Implemented C.39 omega compensation per input.md: SQUARE+oversample>1 applies center omega once after Riemann sum with telemetry enforcement. Validation BLOCKED: probe 90.60% error, architecture test 99.76% FAIL. Normalized/raw = 1e-6 confirms omega applied as specified, contradicting DMI expectation (≈1.0). Documented blocking contradiction in fix_plan.md, captured patch, tagged environment. Next: Supervisor must clarify omega strategy OR escalate to spec_change.

Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-13T010000Z/ (square_lattice_probe_os13.log, pytest_partiality.log, omega_compensation.patch)

---

# Phase C.39 — Omega compensation planning (2026-01-13T010000Z)

## Context
- Phase C.38 telemetry under `reports/2026-01-11T010000Z/` showed the oversample>1 SQUARE branch multiplies each subpixel accumulation by `last_omega≈1e-6`, leaving `_partiality_stats['trace_normalized_intensity']` one millionth of the raw sum even though oversample=1 reproduces `(N_a·N_b·N_c)^2`.
- The single-pixel probe (`square_lattice_scaling.md`, oversample=13) and `tests/architecture/test_nanobrag_partiality.py` remain red: observed ratio **1.360e8** vs spec **1.447e9** (0.0939×), DB-AT-028/029 still report chi²≈1.0e5 and median ROI CC≈−0.05 (SCALE-009 violation per `docs/spec-db-core.md:60-140`).
- Findings SIM-CONSTR-PARTIALITY-001 (owner path lives in `nanobrag_torch.simulator`) and PROBE-FREEZE-001 still bind us to the existing probe + instrumentation; we cannot add more plan-local diagnostics.

## Decision
- Keep focus on ARCH-SIM-CONSTRUCTION-001 with **Mode=Parity**, **ActionType=implementation_ready**, **DecisionStatus=patch_ready**.
- Next engineer loop will modify `src/nanobrag-torch/src/nanobrag_torch/simulator.py::Simulator.run` so that when `crystal.shape == CrystalShape.SQUARE` and `oversample > 1`, the Riemann-sum accumulation leaves omega outside the inner loop. Apply the Lorentz `omega_scalar` once after the sum (mirrors oversample=1 semantics) while preserving instrumentation fields (`trace_subpixel_F_total_sq_sum`, `trace_subpixel_omega_*`, `trace_normalized_intensity`).
- Update `tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells` to enforce ≤1 % error for both cpu/cuda oversample>1 runs and to assert the telemetry fields remain. Keep the sanctioned probe telemetry in sync; no new scripts per PROBE-FREEZE-001.
- Environment Freeze exception bookkeeping remains mandatory: capture `patches/omega_compensation.patch`, log the editable reinstall/tag in `patches/environment_tag.md`, and add a SIM-CONSTR-PARTIALITY-001 note in `docs/findings.md`.

## Validation Targets
1. `python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py --output-dir plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-13T010000Z --n-cells 41 29 32 --oversample 13 --phi-count 1 --mosaic-count 1 --spixels 1 --fpixels 1`
2. `pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells --maxfail=1`
3. `pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` with `DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=full DBAT028_ARTIFACT_DIR=.../db_at_028 DBAT029_ARTIFACT_DIR=.../db_at_029`

All commands inherit `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md`, `KMP_DUPLICATE_LIB_OK=TRUE`, and `NANOBRAGG_DISABLE_COMPILE=1`, and logs/metrics must be stored under this timestamped directory.
