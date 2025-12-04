Summary: Capture per-subpixel coverage metrics for the square-lattice reproducibility probe so we can prove whether the (Na·Nb·Nc)^2 deficit stems from normalization or subpixel sampling before touching production physics.
Mode: Parity
ActionType: parity_localization
DecisionStatus: localized
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: integration
Mapped tests:
  - KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py --output-dir plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-05T150000Z --n-cells 41 29 32 --oversample 13 --phi-count 1 --mosaic-count 1 --spixels 1 --fpixels 1 | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-05T150000Z/square_lattice_probe.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-05T150000Z/pytest_partiality.log
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-05T150000Z/
Findings Applied (Mandatory):
  - SIM-CONSTR-PARTIALITY-001 — Square-lattice sincg must deliver `(Na·Nb·Nc)^2` scaling; cite when interpreting coverage metrics.
  - PROBE-FREEZE-001 — Diagnostics must live inside owner hooks (trace_pixel + partiality stats); no new plan-local pipelines.
Pointers:
  - docs/spec-db-core.md:60-140 — Normative `(Na·Nb·Nc)^2` lattice weight contract for the SQUARE branch.
  - docs/architecture/calibration_scaling.md:1-120 — Calibration/scale threading requirements for reconstruction helpers (root issue tracked by this initiative).
  - docs/TESTING_GUIDE.md:65-90 — DB-AT-028/029 workflow and env knobs for baseline metrics capture.
  - plans/active/ARCH-SIM-CONSTRUCTION-001/implementation.md:420-500 — Phase C.33 outcome + Phase C.34 instrumentation plan.
  - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-05T150000Z/summary.md — supervisor notes for this loop.
ARCH Contracts (mandatory):
  - docs/spec-db-core.md:60-140 — Owner: `nanobrag_torch.simulator.compute_physics_for_position` (SQUARE branch); failure class: implementation bug (lattice weights collapse during accumulation).
  - docs/architecture/calibration_scaling.md:1-120 — Owner: `dbex/refinement/reconstruction` + simulator factory; failure class: implementation bug uncovered by ARCH-SIM-CONSTRUCTION-001.
Do Now (hard validity contract)
1. Implement: `src/nanobrag-torch/src/nanobrag_torch/simulator.py::Simulator.run` — when BOTH `collect_partiality_stats` and `trace_pixel` are set, slice `_partiality_stats` down to the traced pixel and cache guarded tensors (`trace_delta_{h,k,l}`, `trace_F_latt_{a,b,c}`, `trace_F_total_squared_pre_lorentz`). Keep everything behind the existing debug flags so Stage A/B production runs stay untouched.
2. Implement: `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py` — consume the new trace tensors, compute counts for samples with `|Δ_{h,k,l}| < 1/N`, total `F_total_squared_pre_lorentz` mass carried by those samples vs the remainder, and print the implied `(Na·Nb·Nc)^2` ratio if only the central lobe contributed. Persist the new metrics in both JSON and Markdown under this loop’s artifact directory.
3. Run: `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py --output-dir plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-05T150000Z --n-cells 41 29 32 --oversample 13 --phi-count 1 --mosaic-count 1 --spixels 1 --fpixels 1 | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-05T150000Z/square_lattice_probe.log` (the log must show the new coverage table, JSON, and Markdown payloads in this directory).
4. Run: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-05T150000Z/pytest_partiality.log` and note whether the observed `(Na·Nb·Nc)^2` ratio changes once coverage is quantified.
Forbidden This Loop:
  - no new plan-local probe scripts (extend existing hook + probe only)
  - do not add instrumentation outside the trace_pixel / partiality stats owner path
How-To Map:
  - export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md for pytest
  - mkdir -p plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-05T150000Z
  - apply the simulator + probe edits, collect the new coverage metrics via the probe command, and rerun the partiality architecture test while tee’ing logs into the artifacts directory
Pitfalls To Avoid:
  - keep trace tensors gated so Stage A/B production runs do not retain gigantic per-subpixel arrays
  - do not average tensors before counting `|Δ|<1/N`; operate on the raw per-subpixel arrays returned under the new trace keys
  - respect PROBE-FREEZE policy: only the existing probe may grow, and only as a thin wrapper over owner APIs
  - cite SIM-CONSTR-PARTIALITY-001 in the report so the lattice contract stays front-and-center
  - leave the `steps` normalization untouched until we know whether coverage is the culprit
If Blocked: Document the blocker in this loop’s `summary.md` + `docs/fix_plan.md`, keep input.md in Parity mode, and attach any raw `trace_delta_*` tensors to the artifacts tree so the next loop can continue the normalization audit.
DMI Section:
  - Independent Reference: Analytic `(Na·Nb·Nc)^2` scaling from docs/spec-db-core.md plus the single-pixel harness (independent of Stage A).
  - Transformation Ledger: Update `square_lattice_scaling.md` with ≥5 rows detailing `|Δ_{h,k,l}|` thresholds, fraction of subpixels hitting each threshold, cumulative `F_total²` mass, observed ratio, and the implied `(Na·Nb·Nc)^2` error.
  - Source Trace Anchors: `src/nanobrag-torch/src/nanobrag_torch/simulator.py:430-520`, `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py`, `tests/architecture/test_nanobrag_partiality.py`.
  - Consumption-State Measurements: Record `min_abs_delta_{h,k,l}`, counts of samples with `|Δ|<1/N`, total vs central-lobe `F_total²`, observed ratio, and pytest output in the new artifacts directory.
  - Boundary Bisection Step: If coverage is sparse, schedule `steps` normalization fix next; if coverage is healthy, pivot to Lorentz/polar ordering.
  - Probe Budget: 2 probes (Stage A telemetry + single-pixel harness). No new plan-local scripts allowed.
