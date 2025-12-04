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
