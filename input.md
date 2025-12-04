Summary: Capture the actual slow/fast subpixel offset grids used by `_compute_physics_for_position` so we can prove why k/l never reach Δ≈0 before scheduling another simulator fix.
Mode: Parity
ActionType: parity_localization
DecisionStatus: exploring
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: integration
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py --output-dir plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-08T150000Z --n-cells 41 29 32 --oversample 13 --phi-count 1 --mosaic-count 1 --spixels 1 --fpixels 1 | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-08T150000Z/square_lattice_probe.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells --maxfail=1 | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-08T150000Z/pytest_partiality.log
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-08T150000Z/
Findings Applied (Mandatory):
  - SIM-CONSTR-PARTIALITY-001 — SQUARE lattice sincg must honor `(N_a·N_b·N_c)^2`; instrumentation stays inside the owner module.
  - SCALE-009 — DB-AT-028/029 remain the acceptance selectors; we still owe a lattice-compatible simulator.
  - PROBE-FREEZE-001 — all new visibility must flow through `_partiality_stats` + existing probes/tests (no new plan-local scripts).
Pointers:
  - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-07T150000Z/summary.md — HKL tensor evidence (Phase C.35) showing k/l offsets never touch the sincg lobe.
  - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-08T010000Z/ralph_turn_summary.md — normalization patch results (41.5% parity, steps_scalar=1).
  - docs/spec-db-core.md:60-140 — SCALE-009 lattice contract.
ARCH Contracts (mandatory):
  - docs/spec-db-core.md:60-140 — Owner: `nanobrag_torch.simulator::Simulator.run`; failure class: implementation bug (SQUARE lattice weighting still violates SCALE-009 contract).
  - docs/architecture/calibration_scaling.md:10-60 — Owner: simulator/reconstruction scaling path; failure class: implementation bug (Stage A/reconstruction rely on simulator magnitude parity).
Do Now (hard validity contract)
1. Implement: `src/nanobrag-torch/src/nanobrag_torch/simulator.py::_compute_physics_for_position` — when `collect_partiality_stats` **and** `trace_pixel` are both active, capture the raw slow/fast subpixel offsets (or their HKL deltas before sincg) for the traced pixel and store them under `_partiality_stats['subpixel_offsets']` (e.g., `{'slow': tensor(...), 'fast': tensor(...), 'phi': ..., 'mosaic': ...}`). Keep this instrumentation debug-only so production runs stay untouched.
2. Implement: `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py` — plumb the new offset telemetry, summarize min/median/max per axis in both the JSON and Markdown outputs, and print a short console block so we can immediately see whether each axis straddles zero.
3. Validation: rerun the single-pixel probe (command above) to capture the new telemetry and rerun the partiality architecture test (`pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells --maxfail=1`). No DB-AT reruns until this evidence lands.
Forbidden This Loop:
  - no new plan-local diagnostic scripts
  - do not touch Stage A/B/C code paths (owner evidence only)
  - no DB-AT selector runs (probe + architecture test only)
DMI Section:
  - Independent Reference: `(N_a·N_b·N_c)^2` lattice scaling per docs/spec-db-core.md and DB-AT-028/029 telemetry.
  - Transformation Ledger: `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-02T010000Z/square_lattice_scaling.md`, `.../2026-01-05T150000Z/square_lattice_scaling.md`, `.../2026-01-07T150000Z/square_lattice_scaling.md`, `.../2026-01-08T010000Z/pytest_partiality.log`, `.../2026-01-08T010000Z/square_lattice_probe.log`.
  - Source Trace Anchors: `src/nanobrag-torch/src/nanobrag_torch/simulator.py::Simulator.run` (subpixel offsets + sincg), `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py` (evidence harness).
  - Consumption-State Measurements: `_partiality_stats['steps_scalar']`, `_partiality_stats['f_latt']`, new subpixel offset telemetry, single-pixel probe ratios, partiality pytest ratios.
  - Boundary Bisection Step: capture offset grids → determine whether one axis still samples only positive deltas; next action chosen based on telemetry.
  - Probe Budget: reuse existing probe + architecture test only (0/2 new probes consumed).
How-To Map:
  - mkdir -p plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-08T150000Z
  - Apply the simulator + probe edits above, keeping instrumentation behind the existing debug flag.
  - Run the mapped commands to populate `square_lattice_probe.log`, `square_lattice_scaling.{json,md}`, and `pytest_partiality.log` under the new report directory.
Pitfalls To Avoid:
  - Do not widen instrumentation beyond the debug flag; production code must stay untouched.
  - Keep telemetry in `_partiality_stats`; no new files or plan-local diagnostics (PROBE-FREEZE-001).
  - Avoid DB-AT selector churn until we know which axis still misses Δ≈0.
  - Ensure the new telemetry is JSON-serializable (CPU tensors or `.tolist()`); avoid GPU-only tensors in `_partiality_stats`.
  - Include absolute + signed stats so we can tell whether offsets straddle zero.
If Blocked: Document the issue in `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-08T150000Z/summary.md`, update docs/fix_plan.md + galph_memory.md, and prepare to escalate to spec_change (e.g., oversample increase) if simulator offsets already straddle zero.
Doc Sync Plan (Conditional): none — no new tests are added.
