Summary: Instrument the oversample accumulation path so we can log raw per-subpixel sums vs normalized intensity and prove exactly where the ~0.094× lattice deficit enters before patching `Simulator.run`.
Mode: Parity
ActionType: parity_localization
DecisionStatus: localized
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: integration
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py --output-dir plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-11T010000Z --n-cells 41 29 32 --oversample 13 --phi-count 1 --mosaic-count 1 --spixels 1 --fpixels 1 | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-11T010000Z/square_lattice_probe_os13.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py --output-dir plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-11T010000Z --n-cells 41 29 32 --oversample 1 --phi-count 1 --mosaic-count 1 --spixels 1 --fpixels 1 | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-11T010000Z/square_lattice_probe_os1.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells --maxfail=1 | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-11T010000Z/pytest_partiality.log
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-11T010000Z/
Findings Applied (Mandatory):
  - SIM-CONSTR-PARTIALITY-001 — keep all `(Na·Nb·Nc)^2` evidence/instrumentation inside `nanobrag_torch` owner APIs; reuse the sanctioned single-pixel probe and architecture test only.
  - PROBE-FREEZE-001 — no new plan-local diagnostic scripts; extend the existing probe/test harnesses instead.
  - CONFIG-001 — cite detector/convention mapping rules (docs/config_crosswalk.md) when instrumenting so beam-center math stays untouched.
Pointers:
  - docs/spec-db-core.md:60-140 — SCALE-009 lattice contract definition and `(Na·Nb·Nc)^2` expectations.
  - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-10T150000Z/summary.md — oversample=1 vs oversample>1 evidence showing the deficit is confined to accumulation.
  - src/nanobrag-torch/src/nanobrag_torch/simulator.py:1180-1355 — oversample accumulation branch (steps scalar, omega application, per-subpixel sum).
ARCH Contracts (mandatory):
  - SCALE-009 lattice scaling (docs/spec-db-core.md:60-140); owner: `nanobrag_torch.simulator.compute_physics_for_position`; failure class: implementation bug — oversample accumulation still deletes ~90% of the lattice weight.
  - Diagnostic script policy (prompts/supervisor.md §10, enforced by tests/architecture/test_probe_contracts.py); owner: `tests/architecture/test_probe_contracts.py`; failure class: implementation bug if we add new probes instead of instrumenting inside owner APIs.
Do Now (hard validity contract)
Implement:
  - `src/nanobrag-torch/src/nanobrag_torch/simulator.py::Simulator.run` — inside the oversample > 1 branch, capture three debug values when `collect_partiality_stats` and `trace_pixel` are both enabled: (a) the raw `torch.sum(subpixel_physics_intensity_all, dim=2)` before any omega/last-value logic, (b) the omega scalar actually applied (`omega_all` entries vs `last_omega`), and (c) the final `normalized_intensity` that gets divided by `steps`. Store them under clear keys (e.g., `trace_subpixel_F_total_sq_sum`, `trace_subpixel_omega_last`, `trace_normalized_intensity`) so the probe can compare oversample=1 vs 13 without altering production semantics.
  - `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py` — extend the existing JSON/Markdown output to ingest the new stats, compute the ratio between the raw per-subpixel sum and the final normalized intensity, and emit both for oversample=13 and oversample=1 runs under the same timestamp. Highlight any additional normalization factors (omega vs steps) so the report spells out exactly where the ≈0.094× drop occurs.
Validation:
  - Re-run the probe twice (oversample 13 and 1) plus `pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells --maxfail=1` while teeing logs into the new timestamp directory listed above.
Forbidden This Loop:
  - no new plan-local probes
  - do not modify Stage A/mapping call sites; instrumentation must stay inside the simulator owner path
DMI Section:
  - Independent Reference: docs/spec-db-core.md:60-140 `(Na·Nb·Nc)^2` lattice contract + SCALE-009 gates enforced by `tests/architecture/test_nanobrag_partiality.py` (independent acceptance comparator).
  - Transformation Ledger:
    | Field/Tensor | Expected (units/shape) | Producer (file:line) | Hydration (file:line) | Consumer (file:line) | Observed Evidence | Hypothesis |
    | --- | --- | --- | --- | --- | --- | --- |
    | Single-pixel intensity ratio (oversample=13) | `(Na·Nb·Nc)^2 = 1.447650304e9` photons | `probe_square_lattice_scaling.py:119-188` | `nanobrag_torch.simulator.Simulator.run:1180-1355` | `square_lattice_scaling.md:20-24` | Observed 1.3601574985e8 (0.0939× spec) | Oversample accumulation divides away ~90 % of the sum |
    | Single-pixel intensity ratio (oversample=1) | `(Na·Nb·Nc)^2` | same as above | same | `os1_square_lattice_scaling.md:20-24` | Observed 1.4476428501e9 (0.0005 % error) | Confirms simulator math is correct when no subpixel averaging occurs |
    | `partiality_stats['f_latt']` mean | ≈38,048 (dimensionless) | `simulator.py:360-458` | `probe_square_lattice_scaling.py:200-280` | `square_lattice_scaling.json` | Observed 4.2065e3 (mean of 169 samples) while raw entries still reach ±3.8e4 | Storing/using per-subpixel MEAN instead of sum |
    | Coverage ledger central-lobe mass | ≥99% of `F_total²` when Δ thresholds satisfied | `Simulator.run` coverage instrumentation `simulator.py:1500-1565` | `probe_square_lattice_scaling.py:308-372` | `square_lattice_scaling.md:93-107` | 93.53% of mass sits inside central lobe even though final intensity is only 9.4% of spec | Normalization after coverage is still wrong |
    | Architecture test ratio (10×10 detector) | 1.447650304e9 | `tests/architecture/test_nanobrag_partiality.py:24-158` | `pytest_partiality.log` | `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-10T010000Z/pytest_partiality.log` | Observed 6.0128e8 (≈41.5% of spec) after steps fix | Accumulation defect persists in multi-pixel case |
  - Source Trace Anchors: `src/nanobrag-torch/src/nanobrag_torch/simulator.py:1180-1355` (oversample accumulation), `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py:119-285` (sanctioned probe harness), `tests/architecture/test_nanobrag_partiality.py:20-160` (enforcement).
  - Consumption-State Measurements: `square_lattice_scaling.md:20-105`, `os1_square_lattice_scaling.md:20-40`, `pytest_partiality.log` in `reports/2026-01-10T010000Z/`.
  - Boundary Bisection Step: Compare the raw per-subpixel sum vs the final normalized intensity for oversample=13 and oversample=1; any discrepancy isolates the exact normalization stage responsible for the 0.094× drop.
  - Probe Budget: unchanged — use the sanctioned probe + architecture test only (0 of 2 new probes consumed).
How-To Map:
  - mkdir -p plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-11T010000Z
  - Apply the instrumentation edits described above (simulator + probe)
  - Run the oversample=13 probe command, inspect JSON/MD for new stats
  - Run the oversample=1 probe command, diff the ratios inside the same report directory
  - Re-run the partiality architecture test so enforcement logs see the new instrumentation
Pitfalls To Avoid:
  - Keep instrumentation behind the existing `collect_partiality_stats` flag so production smoke selectors stay untouched
  - Do not average the new stats inside the probe; capture sums vs normalized intensity so we can see raw ratios
  - Do not add CLI knobs or plan-local scripts — PROBE-FREEZE-001 requires all new visibility to live inside owner code/tests
  - Avoid touching Stage A/Refinement code paths until we confirm the simulator fix
  - Remember to capture both oversample=1 and oversample=13 runs under the same timestamp for apples-to-apples comparisons
If Blocked: Document the failure in `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-11T010000Z/summary.md`, update docs/fix_plan.md Attempts History + galph_memory, and be prepared to escalate toward a targeted simulator patch or an ARCH initiative if the accumulation logic proves unfixable via instrumentation.
