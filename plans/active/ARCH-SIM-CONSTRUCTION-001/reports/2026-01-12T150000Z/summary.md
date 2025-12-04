# Phase C.39 — Omega compensation (2026-01-12T150000Z)

## Context
- Previous loop (2026-01-12T010000Z) kept the initiative in **DecisionStatus=patch_ready** after instrumentation under `reports/2026-01-11T010000Z/` proved that the oversample>1 SQUARE-lattice branch multiplies each subpixel contribution by `last_omega ≈ 1e-6` before summing, so `_partiality_stats['trace_normalized_intensity']` is 1e-6 of `_trace_subpixel_F_total_sq_sum` even though oversample=1 runs match `(N_a·N_b·N_c)^2`.
- Reference contract: `docs/spec-db-core.md:60-140` (SCALE-009 lattice scaling) and `docs/architecture/calibration_scaling.md:80-145` require the reconstruction pipeline + simulator owner path to preserve calibrated intensity, so DB-AT-028/029 (tests/dbex/test_stage_a_smoke_parity.py) still fail with chi²≈1e5 / median ROI corr <0 because of the missing lattice weight.
- Findings in force: SIM-CONSTR-PARTIALITY-001 (owner path for square-lattice normalization + telemetry), PROBE-FREEZE-001 (no new plan-local probes; use sanctioned telemetry + architecture tests), SCALE-009 (DB-AT parity gates). Problems ledger entry “DB-AT-028/029 scale mismatch (SCALE-009…)” remains open and is the serviced backlog item this turn.

## Decision
- Stay focused on ARCH-SIM-CONSTRUCTION-001 with **Mode=Parity**, **ActionType=implementation_ready**, **DecisionStatus=patch_ready**. No new probes are allowed; evidence is already localized to the oversample omega boundary.
- Next implementation loop must edit `src/nanobrag-torch/src/nanobrag_torch/simulator.py::Simulator.run` so SQUARE lattices skip the per-subpixel `last_omega` multiplication when `oversample>1` and instead apply `omega_scalar` once after the Riemann-sum accumulation (match oversample=1 semantics). Non-SQUARE lattices remain unchanged.
- `_partiality_stats` instrumentation (`trace_subpixel_F_total_sq_sum`, `trace_subpixel_omega_last/mean`, `trace_normalized_intensity`) must remain intact; add a boolean or scalar marker if needed so probes/tests can confirm omega moved to the post-sum location without enabling new diagnostic scripts.
- Update `tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells` to assert both cpu/cuda legs hit `(41·29·32)^2` within ≤1% when oversample>1 and to guard the telemetry fields. Keep `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py` telemetry ingestion/reporting in sync.
- Environment-freeze bookkeeping is mandatory: capture the vendor diff as `plans/active/ARCH-SIM-CONSTRUCTION-001/patches/omega_compensation.patch`, rerun `python -m pip install -e src/nanobrag-torch`, tag the rebuild in `patches/environment_tag.md` (e.g., `nanobrag-partiality-2026-01-12`), and append a SIM-CONSTR-PARTIALITY-001 note in `docs/findings.md` describing the omega change.
- Validating tests (must tee logs/artifacts under this directory):
  1. `python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py --output-dir .../2026-01-12T150000Z --n-cells 41 29 32 --oversample 13 --phi-count 1 --mosaic-count 1 --spixels 1 --fpixels 1`
  2. `pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells --maxfail=1`
  3. `pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` with full Stage-A metrics env knobs so DB-AT telemetry lands in `db_at_{028,029}/`.
  (All commands inherit `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md`, `KMP_DUPLICATE_LIB_OK=TRUE`, `NANOBRAGG_DISABLE_COMPILE=1`, `DBEX_SMOKE_SIGMA_SOURCE=metadata`, `DBEX_SMOKE_DETECTOR_SIZE=full`, and the DB-AT artifact envs from the Do Now.)

## Next Actions for Ralph
1. Implement the omega compensation change inside `Simulator.run` (SQUARE + oversample>1 path) without touching other lattice shapes; keep instrumentation intact.
2. Update the partiality architecture test plus probe telemetry parser as described above.
3. Record the Environment-Freeze bookkeeping (patch file, editable reinstall command/tag, findings note) under `plans/active/ARCH-SIM-CONSTRUCTION-001/patches/` and `docs/findings.md`.
4. Re-run the mapped probe, partiality test, and DB-AT-028/029 selectors, storing logs/metrics under this timestamp (`square_lattice_probe_os13.log`, `square_lattice_scaling.{json,md}`, `pytest_partiality.log`, `pytest_db_at_028_029.log`, `db_at_{028,029}_metrics.json`).
5. Summarize whether normalized/raw now ≈1 and whether chi²/ROI corr trends approach spec in this directory, then update docs/fix_plan.md + galph_memory.md accordingly.

## Compliance / Guardrails
- Dwell: prior two loops were implementation-ready handoffs (no docs-only dwell violation); this loop remains patch-ready.
- Probe budget: 0/2 new probes used (reusing existing probe + instrumentation only).
- Non-negotiables satisfied: parity-first boundary localized to Simulator.run; Do Now lists exact owner function + pytest selectors; forbidden list (`no new probes`, `no plan-local script extensions`, `no edits outside simulator/tests/probe scope`) will be reiterated in input.md.
