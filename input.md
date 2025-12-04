Summary: Apply the Phase C.39 omega-compensation patch so SQUARE lattices with oversample>1 apply the Lorentz omega exactly once after the Riemann-sum accumulation, restoring the missing `(N_a·N_b·N_c)^2` lattice weight and revalidating DB-AT-028/029.
Mode: Parity
ActionType: implementation_ready
DecisionStatus: patch_ready
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: integration
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py --output-dir plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-13T010000Z --n-cells 41 29 32 --oversample 13 --phi-count 1 --mosaic-count 1 --spixels 1 --fpixels 1 | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-13T010000Z/square_lattice_probe_os13.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells --maxfail=1 | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-13T010000Z/pytest_partiality.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=full DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-13T010000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-13T010000Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-13T010000Z/pytest_db_at_028_029.log
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-13T010000Z/
Findings Applied (Mandatory):
  - SIM-CONSTR-PARTIALITY-001 — simulator fixes must land inside `nanobrag_torch.simulator` with telemetry preserved; every patch requires a captured diff/tag and findings note.
  - PROBE-FREEZE-001 — use the sanctioned probe + architecture test only; no new plan-local diagnostic scripts or extensions are allowed.
  - SCALE-009 — DB-AT-028/029 enforce the `(N_a·N_b·N_c)^2` lattice contract and calibrated chi²/ROI gates, so the simulator fix must restore these metrics before the initiative can close.
Pointers:
  - docs/spec-db-core.md:60-140 — SCALE-009 lattice-scaling contract and chi²/ROI acceptance gates for DB-AT-028/029.
  - docs/architecture/calibration_scaling.md:80-145 — Lorentz + calibration precedence (omega placement) that this patch must respect.
  - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-11T010000Z/summary.md — telemetry proving normalized/raw = 1e-6 for oversample>1 SQUARE lattices.
  - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-13T010000Z/summary.md — this loop’s scope, guardrails, and validation plan.
ARCH Contracts (mandatory):
  - SCALE-009 lattice scaling (docs/spec-db-core.md:60-140); owner: `nanobrag_torch.simulator.Simulator.run` + `compute_physics_for_position`; failure class: implementation bug causing `(N_a·N_b·N_c)^2` deficit.
  - Diagnostic-script policy (prompts/supervisor.md §10, enforced by tests/architecture/test_probe_contracts.py); owner: `tests/architecture/test_probe_contracts.py`; failure class: implementation bug if probe scripting bypasses owner APIs.
Do Now (hard validity contract)
Implement:
  - `src/nanobrag-torch/src/nanobrag_torch/simulator.py::Simulator.run` — When `crystal.shape == CrystalShape.SQUARE` and `oversample > 1`, skip multiplying `subpixel_physics_intensity_all` by `last_omega` per subpixel. Accumulate the raw sum, then apply `omega_scalar` exactly once after the Riemann-sum aggregation (mirroring the oversample==1 branch). Keep GAUSS/TOPHAT/ROUND behavior unchanged.
  - Preserve `_partiality_stats['trace_subpixel_F_total_sq_sum']`, `trace_subpixel_omega_{last,mean}`, and `trace_normalized_intensity`; add a boolean or scalar marker if needed so probes/tests can prove omega moved to the post-sum location without new plan-local scripts.
  - `tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells` — tighten assertions so both cpu/cuda legs observe `(41·29·32)^2` within ≤1% when `oversample>1`, and verify the telemetry fields still exist (guard regressions if omega sneaks back inside the accumulation loop).
  - `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py` — keep telemetry ingestion/reporting in sync so `square_lattice_scaling.{json,md}` surfaces the normalized/raw ratio and any new `_partiality_stats` markers.
  - Environment Freeze bookkeeping — capture the simulator diff as `plans/active/ARCH-SIM-CONSTRUCTION-001/patches/omega_compensation.patch`, rerun `python -m pip install -e src/nanobrag-torch`, tag the rebuild in `plans/active/ARCH-SIM-CONSTRUCTION-001/patches/environment_tag.md` (e.g., `nanobrag-partiality-2026-01-13`), and append a SIM-CONSTR-PARTIALITY-001 note in `docs/findings.md` describing the omega change.
Validate:
  - Re-run the mapped probe + partiality architecture test + DB-AT-028/029 commands above, teeing logs and copying DB-AT metrics into this timestamped directory. Summarize normalized/raw ratios, architecture-test ratios, and DB-AT chi²/ROI deltas in `summary.md`.
Forbidden This Loop:
  - no new probes
  - do not extend plan-local diagnostic scripts (PROBE-FREEZE-001)
  - no edits outside simulator/tests/probe scope listed above (Stage A/mapping helpers stay untouched)
DMI Section:
  - Independent Reference: SCALE-009 lattice scaling contract (docs/spec-db-core.md:60-140) enforced via the single-pixel probe + `tests/architecture/test_nanobrag_partiality.py` + DB-AT-028/029 selectors (independent harness vs production implementation).
  - Transformation Ledger:
    | Field/Tensor | Expected (units/shape/axis) | Producer (file:line) | Hydration (file:line) | Consumer (file:line) | Observed Evidence | Hypothesis |
    | --- | --- | --- | --- | --- | --- | --- |
    | Single-pixel ratio (oversample=13) | `(41·29·32)^2 = 1.447650304e9` photons | probe_square_lattice_scaling.py:119-311 | simulator.py:1180-1365 | square_lattice_scaling.md:24-35 | 1.3601574985e8 (0.0939× spec) | Omega applied before Riemann sum deletes lattice weight |
    | Raw vs normalized intensity | ratio ≈ 1.0 | simulator.py:1325-1365 | `_partiality_stats['trace_subpixel_*']` | square_lattice_scaling.json:120-155 | `trace_subpixel_F_total_sq_sum=1.6148e17`, `trace_normalized_intensity=1.6148e11` ⇒ 1e-6 ratio | Oversample>1 path multiplies by `last_omega` per subpixel |
    | Architecture partiality ratio | 1.447650304e9 | tests/architecture/test_nanobrag_partiality.py:20-158 | same | pytest_partiality.log | 5.9038e8 (59% error) | Same omega bug across multi-pixel grids |
    | DB-AT-028 chi²/pixel initial | ≤1e2 | tests/dbex/test_stage_a_smoke_parity.py | Stage A telemetry | db_at_028_metrics.json (2026-01-11T010000Z) | 2.1e5 | Acceptance failure tied to missing lattice weight |
    | DB-AT-029 median ROI corr | ≥0.2 | same | Stage A ROI stats | db_at_029_metrics.json (2026-01-11T010000Z) | -0.053 | Same root cause |
  - Source Trace Anchors: `src/nanobrag-torch/src/nanobrag_torch/simulator.py:1180-1365`, `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py:119-311`, `tests/architecture/test_nanobrag_partiality.py:20-158`.
  - Consumption-State Measurements: `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-11T010000Z/square_lattice_scaling.{md,json}`, `pytest_partiality.log`, `db_at_{028,029}_metrics.json`.
  - Boundary Bisection Step: Modify the oversample omega boundary; success criteria = normalized/raw→1 and architecture + DB-AT selectors trending toward spec. If deficit persists, move downstream to reconstruction scaling logic.
  - Probe Budget: unchanged (0/2 new probes used); all visibility flows through existing owner instrumentation.
How-To Map:
  1. `mkdir -p plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-13T010000Z/{db_at_028,db_at_029}`
  2. Implement the simulator/test/probe changes and capture `git diff` for `src/nanobrag-torch/.../simulator.py` and `tests/architecture/test_nanobrag_partiality.py`.
  3. `python -m pip install -e src/nanobrag-torch` and log the command/tag in `plans/active/ARCH-SIM-CONSTRUCTION-001/patches/environment_tag.md`; save the diff as `patches/omega_compensation.patch` and add a SIM-CONSTR-PARTIALITY-001 note in `docs/findings.md`.
  4. Run the mapped probe + pytest commands above (inherit the env vars exactly as written) while teeing logs into this report directory; copy the regenerated `square_lattice_scaling.{json,md}`, `pytest_partiality.log`, and `db_at_{028,029}_metrics.json` under the appropriate subdirectories.
  5. Summarize normalized/raw ratios, architecture-test ratios, and DB-AT chi²/ROI corr deltas in `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-13T010000Z/summary.md`, then update docs/fix_plan.md + galph_memory.md with outcomes.
Pitfalls To Avoid:
  - Keep omega edits gated strictly to SQUARE lattices with oversample>1; other lattice shapes still rely on mean semantics.
  - Do not remove `_partiality_stats` guards or add new instrumentation outside the existing hooks (PROBE-FREEZE-001, diagnostic_script_policy).
  - Remember to reinstall the vendored simulator and capture the diff/tag; skipping this violates the Environment Freeze exception bookkeeping.
  - DB-AT selectors must run with `DBEX_SMOKE_DETECTOR_SIZE=full` per docs/TESTING_GUIDE.md §1.1.
  - Architecture test tolerances must remain tight (≤1%) so regressions surface immediately.
If Blocked: Capture failure evidence (logs + metrics) under this timestamp, update docs/fix_plan.md Attempts History and galph_memory.md with the block reason, and consider escalating to spec_change or a follow-on architecture initiative if omega compensation cannot restore `(N_a·N_b·N_c)^2` parity.
