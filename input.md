Summary: Compare nanobrag_torch's sincg kernel against an analytic reference so we can prove whether the (Na·Nb·Nc)^2 deficit lives inside the lattice kernel or downstream aggregation before touching simulator.py.
Mode: Parity
ActionType: parity_localization
DecisionStatus: localized
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: integration
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-04T010000Z/
Findings Applied (Mandatory):
  - SIM-CONSTR-PARTIALITY-001 — Partiality ledger + enforcement guard stay red until sincg reproduces (Na·Nb·Nc)^2; cite this when reporting error stats.
  - PROBE-FREEZE-001 — Continue using the owner probe + logging hooks; no new plan-local pipelines.
Pointers:
  - docs/spec-db-core.md:60-140 — SQUARE lattice scaling contract.
  - plans/active/ARCH-SIM-CONSTRUCTION-001/implementation.md:400-470 — Phase C.30/C.31 history + new Phase C.32 checklist.
  - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-03T010000Z/square_lattice_scaling.md — Payload evidence showing 0.000058× ratio with instrumentation hooks.
ARCH Contracts (mandatory):
  - docs/spec-db-core.md:60-140 — Owner: `nanobrag_torch.simulator.compute_physics_for_position`; failure type: implementation bug (SQUARE lattice must emit (Na·Nb·Nc)^2 when Δh/Δk/Δl≈0 per SIM-CONSTR-PARTIALITY-001).
  - tests/architecture/test_nanobrag_partiality.py — Owner: enforcement guard; failure type: implementation bug (test asserts scaling holds for both cpu/cuda backends).
Do Now (hard validity contract)
1. Implement: plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py::main — add a high-precision reference evaluator (NumPy float64 or Decimal) that computes `sin(NπΔ)/sin(πΔ)` for every sampled Δh/Δk/Δl (per-axis) and records per-axis absolute/relative error stats plus the compounded `F_latt` error relative to production. Summaries should surface max/median error, the Δ location of the worst point, and the resulting `(Na·Nb·Nc)^2` ratio using the reference values.
2. Implement: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-04T010000Z/summary.md — document whether the deficit occurs inside `nanobrag_torch.utils.physics.sincg` (production vs reference mismatch) or downstream aggregation. If the kernel is wrong, describe the suspected fix (e.g., missing half-angle scaling) to tee up Phase C.33; if the kernel matches the reference, note which downstream component remains suspect.
3. Run: KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py --output-dir plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-04T010000Z --n-cells 41 29 32 --oversample 13 --phi-count 1 --mosaic-count 1 --spixels 1 --fpixels 1 | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-04T010000Z/square_lattice_probe.log (verify JSON/Markdown now contain production vs reference comparisons).
4. Run: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-04T010000Z/pytest_partiality.log so we have enforcement logs aligned with the new probe evidence.
How-To Map:
  - mkdir -p plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-04T010000Z
  - KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py --output-dir plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-04T010000Z --n-cells 41 29 32 --oversample 13 --phi-count 1 --mosaic-count 1 --spixels 1 --fpixels 1 | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-04T010000Z/square_lattice_probe.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-04T010000Z/pytest_partiality.log
Pitfalls To Avoid:
  - Do not create new standalone probes; keep instrumentation inside the owner script per PROBE-FREEZE-001.
  - Keep the reference implementation opt-in and CPU-side so production runs remain unaffected.
  - Avoid averaging tensors before comparing to the reference; compute stats after matching the exact phi/mosaic dimensions to avoid “mean cancels sign” artifacts.
  - Cite SIM-CONSTR-PARTIALITY-001 in summary.md so the ledger links evidence to the finding.
  - Capture both JSON + Markdown diffs; missing artifacts invalidate the ledger entry.
If Blocked: Add a short note to summary.md + docs/fix_plan.md describing the blocker (e.g., reference evaluation overflow), attach intermediate logs under the artifact directory, and keep `input.md` in parity-localization mode until the reference path is unblocked.
DMI Section:
  - Independent Reference: Analytic sincg formula `sin(NπΔ)/sin(πΔ)` evaluated in float64/decimal acts as the independent comparator for the SQUARE kernel.
  - Transformation Ledger: Extend `square_lattice_scaling.md` with a ≥5-row table listing Δh/Δk/Δl sample, production sincg value, reference value, relative error, and resulting `(Na·Nb·Nc)^2` deficit. Include row for the worst offender plus a near-zero Δ sample.
  - Source Trace Anchors: nanobrag_torch/simulator.py:288-458, nanobrag_torch/utils/physics.py:33-86, probe_square_lattice_scaling.py:80-360.
  - Consumption-State Measurements: Record both production and reference `(Na·Nb·Nc)^2` ratios, per-axis error stats, and enforcement test output in the new artifact directory.
  - Boundary Bisection Step: If production vs reference sincg matches (error <1e-6), shift attention downstream (aggregation/summation); otherwise escalate to a Phase C.33 implementation loop targeting `sincg` itself.
  - Probe Budget: 2 active probes (Stage A baseline helper + square_lattice_scaling.py); do not add more scripts this loop.
