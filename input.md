Summary: Capture per-subpixel coverage metrics for the square-lattice reproducibility probe so we can prove whether the (Na·Nb·Nc)^2 deficit stems from normalization or subpixel sampling before attempting another simulator fix.
Mode: Parity
ActionType: parity_localization
DecisionStatus: localized
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: integration
Mapped tests:
  - KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py --output-dir plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-05T010000Z --n-cells 41 29 32 --oversample 13 --phi-count 1 --mosaic-count 1 --spixels 1 --fpixels 1 | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-05T010000Z/square_lattice_probe.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-05T010000Z/pytest_partiality.log
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-05T010000Z/
Findings Applied (Mandatory):
  - SIM-CONSTR-PARTIALITY-001 — Lattice weights must reproduce (Na·Nb·Nc)^2 scaling; cite when summarizing the coverage results.
  - PROBE-FREEZE-001 — Keep diagnostics inside owner hooks (trace_pixel + partiality stats); no new plan-local probes.
Pointers:
  - docs/spec-db-core.md:60-140 — square lattice contract and `(Na·Nb·Nc)^2` expectation.
  - plans/active/ARCH-SIM-CONSTRUCTION-001/implementation.md:440-470 — Phase C.33 outcome + Phase C.34 plan.
  - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-05T010000Z/summary.md — supervisor notes for this loop.
ARCH Contracts (mandatory):
  - docs/spec-db-core.md:60-140 — Owner: `nanobrag_torch.simulator.compute_physics_for_position`; failure class: implementation bug (square lattice weight collapse).
  - docs/architecture/calibration_scaling.md:1-120 — Owner: `dbex/refinement/reconstruction` + simulator factory; failure class: implementation bug (scale parity vs Stage A).
Do Now (hard validity contract)
1. Implement: `src/nanobrag-torch/src/nanobrag_torch/simulator.py::run` — when `collect_partiality_stats` is enabled **and** `trace_pixel` is set, slice the partiality tensors down to the traced pixel before storing them (keep `delta_h/k/l`, `F_latt_a/b/c`, and `F_total_squared_pre_lorentz` per subpixel). Expose these arrays under new keys (e.g., `trace_delta_h`, `trace_F_total_sq`) so downstream tools can analyze per-subpixel coverage without emitting 100+ MB payloads for full detectors.
2. Implement: `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py` — consume the new trace tensors, compute counts for samples with `|Δ_h|`, `|Δ_k|`, and `|Δ_l|` below `1/N`, sum their `F_total_squared_pre_lorentz`, and report (a) fraction of subpixels hitting the central sincg lobe, (b) share of the total `F_total²` they contribute, and (c) the implied `(Na·Nb·Nc)^2` ratio if those samples dominated. Emit the new metrics in both JSON and Markdown under the reserved artifacts directory.
3. Run: `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py --output-dir plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-05T010000Z --n-cells 41 29 32 --oversample 13 --phi-count 1 --mosaic-count 1 --spixels 1 --fpixels 1 | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-05T010000Z/square_lattice_probe.log` (ensure the log shows the new coverage table and stores the JSON/Markdown under the artifacts path).
4. Run: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-05T010000Z/pytest_partiality.log`. Highlight whether the observed ratio changes once the coverage issue is quantified.
Forbidden This Loop:
  - no new plan-local probes or scripts
  - do not add instrumentation outside existing trace_pixel/partiality hooks
How-To Map:
  - export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md for all pytest invocations
  - mkdir -p plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-05T010000Z
  - apply the simulator + probe edits, collect the new coverage metrics via the probe command, and re-run the partiality architecture test with logs captured under the same artifacts directory
Pitfalls To Avoid:
  - keep partiality stats slicing guarded by trace_pixel to avoid huge tensors on Stage A runs
  - do not average tensors across all subpixels before computing the new metrics (work on raw per-subpixel arrays)
  - maintain PROBE-FREEZE policy: only extend the existing probe; no new helper scripts
  - cite SIM-CONSTR-PARTIALITY-001 when summarizing the deficit
  - leave `steps` normalization untouched until coverage evidence is captured
If Blocked: Document the blocker in `summary.md` + `docs/fix_plan.md`, keep `input.md` in parity_localization mode, and attach the raw `trace_delta_*` tensors under the artifacts directory so the next loop can continue the normalization audit.
DMI Section:
  - Independent Reference: Analytic `(Na·Nb·Nc)^2` scaling from docs/spec-db-core.md plus the single-pixel reproduction harness (independent of Stage A).
  - Transformation Ledger: Update `square_lattice_scaling.md` with ≥5 rows showing `|Δ_{h,k,l}|` thresholds, fraction of contributing subpixels, cumulative `F_total²`, observed ratio, and the implied `(Na·Nb·Nc)^2` delta.
  - Source Trace Anchors: `src/nanobrag-torch/src/nanobrag_torch/simulator.py:430-520`, `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py`, `tests/architecture/test_nanobrag_partiality.py`.
  - Consumption-State Measurements: Record `min_abs_delta_{h,k,l}`, counts of samples with `|Δ|<1/N`, cumulative `F_total²` for those samples, observed intensity ratio, and pytest output in the new artifacts tree.
  - Boundary Bisection Step: If coverage proves insufficient, the next loop targets the `steps` normalization / accumulation; if coverage is healthy, pivot to revisiting Lorentz/polar ordering.
  - Probe Budget: still 2 probes (Stage A telemetry + single-pixel). No new plan-local scripts allowed.
