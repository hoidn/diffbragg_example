Summary: Capture single-pixel square-lattice scaling evidence and refresh the failing enforcement log before scheduling another simulator patch.
Mode: Parity
ActionType: parity_localization
DecisionStatus: localized
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: integration
Mapped tests:
  - KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py --output-dir plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-02T010000Z --n-cells 41 29 32 --oversample 13 --phi-count 1 --mosaic-count 1 --spixels 1 --fpixels 1 | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-02T010000Z/square_lattice_probe.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells --maxfail=1 | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-02T010000Z/pytest_partiality.log
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-02T010000Z/
Findings Applied (Mandatory):
  - SIM-CONSTR-PARTIALITY-001 — enforcement test still red; collect decisive evidence before attempting another simulator patch.
  - DIAG-OVERSAMPLE-001 — HKL alignment confirmed, so the new probe can assume A* mapping is correct.
  - PROBE-FREEZE-001 — limit plan-local scripts to thin wrappers; the new probe must call `nanobrag_torch` owner APIs directly.
Pointers:
  - plans/active/ARCH-SIM-CONSTRUCTION-001/implementation.md:400-436 — Phase C.29 recap and Phase C.30 checklist for the square-lattice scaling probe.
  - docs/fix_plan.md:825-858 — Attempts history detailing the failed sincg patch and why we need a minimal reproduction.
  - docs/spec-db-core.md:60-140 — SQUARE lattice weighting contract ((Na·Nb·Nc)² scaling) that the enforcement test encodes.
ARCH Contracts (mandatory):
  - docs/spec-db-core.md:60-140 — Owner: `nanobrag_torch.simulator.compute_physics_for_position`; failure type: implementation bug (SQUARE lattice weights do not deliver `(Na·Nb·Nc)^2` scaling).
  - docs/config_crosswalk.md:71-118 — Owner: `dbex.nanobrag_bridge`/simulator factory; failure type: implementation bug (calibration/lattice conventions misapplied in reconstruction cold path).
Do Now (hard validity contract)
1. Implement: `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py` — thin wrapper that instantiates `nanobrag_torch.Simulator` twice (N_cells=(1,1,1) vs `(41,29,32)`) with a 1×1 detector, single phi/mosaic sample, and configurable oversample. The CLI must accept `--output-dir`, `--n-cells`, `--oversample`, `--spixels`, `--fpixels`, `--phi-count`, and `--mosaic-count`, enable `debug_config={'collect_partiality_stats': True, 'trace_pixel': [0,0]}`, and emit:
   * JSON file summarizing intensities, `(F_cell·F_latt)^2`, Lorentz/polarization factors, and the observed ratio.
   * Markdown file highlighting the same numbers plus commentary on how far the ratio deviates from `(Na·Nb·Nc)^2`.
   * Console log (captured via `tee`) that preserves the trace output for both cases.
2. Run the probe with the canonical `N_cells=(41,29,32)` (oversample 13, phi=1, mosaic=1, spixels=fpixels=1) and store JSON/Markdown/log artifacts under the reserved directory. Summarize the measured ratio + expected delta in `summary.md`.
3. Re-run `pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells --maxfail=1` (failure expected) so the latest enforcement evidence and probe output live in the same artifact tree. Note the failure in `summary.md` with the observed vs expected ratios.
Forbidden This Loop:
  - no edits to `src/nanobrag-torch/**` or enforcement tests — this loop is evidence only.
  - no DB-AT reruns or new plan-local probes beyond `probe_square_lattice_scaling.py`.
  - no changes to `GROWTH_CAP_EXCEPTIONS` or other ARCH-PROBE-FREEZE-001 guards.
How-To Map:
  1. `mkdir -p plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-02T010000Z` and implement the probe script per Do Now #1 (keep it ≤150 LOC, owner-only imports).
  2. `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py --output-dir plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-02T010000Z --n-cells 41 29 32 --oversample 13 --phi-count 1 --mosaic-count 1 --spixels 1 --fpixels 1 | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-02T010000Z/square_lattice_probe.log`.
  3. Inspect the generated JSON/Markdown to confirm they include base/scaled intensities, `(F_cell·F_latt)^2`, Lorentz/polarization factors, and the observed ratio; reference these numbers in `summary.md`.
  4. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells --maxfail=1 | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-02T010000Z/pytest_partiality.log` (capture failure output).
Pitfalls To Avoid:
  - The probe script must remain a thin wrapper; do not re-encode Stage A or reconstruction logic.
  - Set both `KMP_DUPLICATE_LIB_OK=TRUE` and `NANOBRAG_DISABLE_COMPILE=1` so the simulator runs deterministically and avoids torch.compile graph churn.
  - Do not “fix” the failing pytest; the goal is to document the current shortfall alongside the probe results.
  - Report ratios in both JSON and Markdown plus `summary.md` so downstream planning can compare against `(Na·Nb·Nc)^2`.
  - Keep artifacts organized under the reserved timestamp (JSON, Markdown, `.log`, pytest log, summary.md).
If Blocked: Capture the partial probe/pytest output under the artifacts directory, add a `blockers.md` with the failure description (command, stdout, traceback), and update docs/fix_plan.md Attempts History plus galph_memory with evidence explaining why the probe could not run (e.g., simulator import failure). Do not attempt simulator edits without new supervisor approval.
