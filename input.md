Summary: Patch the SQUARE-lattice oversample branch so omega is applied once per pixel (not per subpixel), restoring the missing 1e-6 factor in `Simulator.run` and revalidating DB-AT-028/029.
Mode: Parity
ActionType: implementation_ready
DecisionStatus: patch_ready
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: integration
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py --output-dir plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-12T010000Z --n-cells 41 29 32 --oversample 13 --phi-count 1 --mosaic-count 1 --spixels 1 --fpixels 1 | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-12T010000Z/square_lattice_probe_os13.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells --maxfail=1 | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-12T010000Z/pytest_partiality.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-12T010000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-12T010000Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-12T010000Z/pytest_db_at_028_029.log
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-12T010000Z/
Findings Applied (Mandatory):
  - SIM-CONSTR-PARTIALITY-001 — fixes must live inside the simulator owner path; document every nanobrag patch + env tag and keep telemetry hooks wired so future probes/tests observe the change.
  - PROBE-FREEZE-001 — reuse the sanctioned probe + architecture test only; do not create/extend plan-local scripts.
  - SCALE-009 — reconstruction + simulator paths must satisfy the `(Na·Nb·Nc)^2` lattice contract and DB-AT-028/029 chi²/ROI thresholds before closing the initiative.
Pointers:
  - docs/spec-db-core.md:60-140 — SCALE-009 lattice scaling contract and DB-AT acceptance gates.
  - docs/architecture/calibration_scaling.md:80-145 — spot-scale + Lorentz precedence; cite when reasoning about omega placement.
  - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-11T010000Z/summary.md — instrumentation proving normalized/raw ratio 1e-6 for oversample>1.
  - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-12T010000Z/summary.md — this loop’s handoff + scope reminder.
ARCH Contracts (mandatory):
  - SCALE-009 lattice scaling (docs/spec-db-core.md:60-140); owner API: `nanobrag_torch.simulator.compute_physics_for_position` / `Simulator.run`; failure class: implementation bug (omega placement deletes lattice weight).
  - Diagnostic script policy (prompts/supervisor.md §10; enforced by tests/architecture/test_probe_contracts.py); owner: `tests/architecture/test_probe_contracts.py`; failure class: implementation bug if we extend plan-local probes instead of instrumenting owner code/tests.
Do Now (hard validity contract)
Implement:
  - `src/nanobrag-torch/src/nanobrag_torch/simulator.py::Simulator.run` — In the oversample>1 branch, skip multiplying SQUARE-lattice accumulators by `last_omega`; sum `subpixel_physics_intensity_all` first, then apply `omega_scalar` exactly once after the sum (matching the oversample==1 path). Leave GAUSS/TOPHAT/ROUND behavior untouched.
  - Continue emitting `_partiality_stats['trace_subpixel_F_total_sq_sum']`, `trace_subpixel_omega_last/mean`, and `trace_normalized_intensity`; if omega now applies post-sum, add a boolean or scalar that proves the single application occurred so the probe + test can validate it.
  - `tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells` — tighten assertions so both cpu/cuda legs confirm `(41·29·32)^2` within ≤1% when oversample>1 and verify the telemetry fields exist (protect against regression if omega sneaks back inside the accumulation loop).
  - `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py` — keep telemetry ingest/reporting in sync with the simulator change so `square_lattice_scaling.{json,md}` clearly show normalized/raw≈1 and list the updated `_partiality_stats` markers.
  - Environment-freeze bookkeeping — save the simulator diff as `plans/active/ARCH-SIM-CONSTRUCTION-001/patches/omega_compensation.patch`, rerun `python -m pip install -e src/nanobrag-torch`, log the command/tag in `patches/environment_tag.md` (e.g., `nanobrag-partiality-2026-01-12`), and append a SIM-CONSTR-PARTIALITY-001 note in `docs/findings.md` describing the omega compensation change.
Validate:
  - Re-run the mapped probe, architecture partiality test, and DB-AT-028/029 commands above with artifacts captured under this timestamp. Summarize ratios, chi², and ROI corr deltas in `summary.md`.
Forbidden This Loop:
  - no new probes
  - do not extend plan-local diagnostic scripts (PROBE-FREEZE-001)
  - no edits outside simulator/tests/probe scope listed above (Stage A/mapping helpers stay untouched)
DMI Section:
  - Independent Reference: docs/spec-db-core.md:60-140 `(Na·Nb·Nc)^2` contract enforced independently by the partiality architecture test and DB-AT-028/029 selectors.
  - Transformation Ledger:
    | Field/Tensor | Expected (units/shape) | Producer (file:line) | Hydration (file:line) | Consumer (file:line) | Observed Evidence | Hypothesis |
    | --- | --- | --- | --- | --- | --- | --- |
    | Single-pixel ratio (oversample=13) | `(41·29·32)^2 = 1.447650304e9` photons | `probe_square_lattice_scaling.py:119-311` | `simulator.py:1180-1365` | `square_lattice_scaling.md:24-35` | 1.3601574985e8 (0.0939× spec) | Omega applied before Riemann sum deletes the lattice weight |
    | Raw vs normalized intensity | ratio should be ≈1.0 (omega applied once) | `simulator.py:1325-1365` | `_partiality_stats['trace_subpixel_*']` | `square_lattice_scaling.json:120-155` | `trace_subpixel_F_total_sq_sum=1.6148e17`, `trace_normalized_intensity=1.6148e11` → normalized/raw=1e-6 | Oversample>1 branch multiplies by `last_omega` before sum |
    | Architecture partiality ratio | 1.447650304e9 | `tests/architecture/test_nanobrag_partiality.py:20-158` | same | `pytest_partiality.log:15-27` | 5.9038e8 (59% error) | Same omega bug across multi-pixel grids |
    | DB-AT-028 chi²/pixel initial | ≤1e2 | `tests/dbex/test_stage_a_smoke_parity.py` | Stage A telemetry | `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-11T010000Z/db_at_028/db_at_028_metrics.json` | 2.1e5 | Acceptance failure driven by missing lattice weight |
    | DB-AT-029 median ROI corr | ≥0.2 | same | Stage A ROI stats | `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-11T010000Z/db_at_029/db_at_029_metrics.json` | -0.053 | Same root cause |
  - Source Trace Anchors: `src/nanobrag-torch/src/nanobrag_torch/simulator.py:1180-1365`, `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py:119-311`, `tests/architecture/test_nanobrag_partiality.py:20-158`.
  - Consumption-State Measurements: `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-11T010000Z/square_lattice_scaling.{md,json}`, `pytest_partiality.log`, `db_at_028/db_at_029_metrics.json`.
  - Boundary Bisection Step: Modify omega application boundary; success = normalized/raw→1 for oversample>1 plus architecture + DB-AT selectors trending toward spec. If parity still fails, move downstream to reconstruction scaling logic.
  - Probe Budget: unchanged (0/2 new probes used); all visibility flows through existing owner instrumentation.
How-To Map:
  1. `mkdir -p plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-12T010000Z/{db_at_028,db_at_029}`
  2. Edit the simulator/test/probe files per Do Now and capture the vendor diff as `patches/omega_compensation.patch`.
  3. `python -m pip install -e src/nanobrag-torch` and log the rebuild/tag in `patches/environment_tag.md` + `docs/findings.md`.
  4. Run the mapped probe + pytest commands above (tee outputs into this report directory);
     copy DB-AT metrics JSON files under the db_at_* subdirectories.
  5. Summarize ratios, chi², ROI corr in `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-12T010000Z/summary.md` and update docs/fix_plan.md + galph_memory.md after results land.
Pitfalls To Avoid:
  - Keep omega changes gated to `CrystalShape.SQUARE` with `oversample > 1`; non-square lattices rely on the current averaging semantics.
  - Do not remove or bypass `_partiality_stats` guards; instrumentation must remain no-op when debug flags are off.
  - Remember to reinstall the vendored simulator (`pip install -e src/nanobrag-torch`) and capture the patch/tag for Environment Freeze compliance.
  - Avoid tweaking Stage A/reconstruction scaling in this loop; focus strictly on the simulator owner path + regression tests.
  - Architecture test tolerances must stay tight (≤1%) to keep this failure mode observable in CI.
If Blocked: Record the failure (symptoms + logs) in `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-12T010000Z/summary.md`, update docs/fix_plan.md Attempts History + galph_memory.md, and escalate to spec_change or a new architecture initiative if omega compensation cannot restore the `(Na·Nb·Nc)^2` ratio.
