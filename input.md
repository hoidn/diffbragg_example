Summary: Patch the SQUARE-lattice oversample path so omega is applied once per pixel (not per subpixel), restoring the missing 1e-6 factor in `Simulator.run` and revalidating DB-AT-028/029.
Mode: Parity
ActionType: implementation_ready
DecisionStatus: patch_ready
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: integration
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py --output-dir plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-11T180000Z --n-cells 41 29 32 --oversample 13 --phi-count 1 --mosaic-count 1 --spixels 1 --fpixels 1 | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-11T180000Z/square_lattice_probe_os13.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells --maxfail=1 | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-11T180000Z/pytest_partiality.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-11T180000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-11T180000Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-11T180000Z/pytest_db_at_028_029.log
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-11T180000Z/
Findings Applied (Mandatory):
  - SIM-CONSTR-PARTIALITY-001 — fixes must live inside the simulator owner path; document every nanobrag patch + env tag and keep telemetry hooks wired so future probes/tests observe the change.
  - PROBE-FREEZE-001 — reuse the sanctioned probe + architecture test only; do not create/extend plan-local scripts.
  - SCALE-009 — reconstruction + simulator paths must satisfy the `(Na·Nb·Nc)^2` lattice contract and DB-AT-028/029 chi²/ROI thresholds before closing the initiative.
Pointers:
  - docs/spec-db-core.md:60-140 — SCALE-009 lattice scaling definition and DB-AT acceptance gates.
  - docs/architecture/calibration_scaling.md:80-145 — spot-scale precedence + Lorentz handling; cite when reasoning about omega placement.
  - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-11T010000Z/summary.md — evidence that `normalized_intensity = raw_sum × 1e-6` for oversample>1 while oversample=1 is correct.
ARCH Contracts (mandatory):
  - SCALE-009 lattice scaling (docs/spec-db-core.md:60-140); owner API: `nanobrag_torch.simulator.compute_physics_for_position` / `Simulator.run`; failure class: implementation bug (omega application deletes lattice weight).
  - Diagnostic script policy (prompts/supervisor.md §10; enforced by tests/architecture/test_probe_contracts.py); owner: `tests/architecture/test_probe_contracts.py`; failure class: implementation bug if we add/extend plan-local probes instead of instrumenting owner code/tests.
Do Now (hard validity contract)
Implement:
  - `src/nanobrag-torch/src/nanobrag_torch/simulator.py::Simulator.run` — For `crystal.shape == CrystalShape.SQUARE` with `oversample > 1`, accumulate `subpixel_physics_intensity_all` without immediately multiplying by `last_omega`. Apply the Lorentz/polarization omega scalar exactly once after the sum (matching the oversample==1 branch) so the Riemann-sum normalization from Phase C.35 is preserved. Keep existing behavior for non-SQUARE lattices. Update the `_partiality_stats` debug payloads to continue emitting `trace_subpixel_F_total_sq_sum`, `trace_subpixel_omega_last/mean`, and `trace_normalized_intensity`, plus a new flag/field if needed to prove that the post-sum omega multiplier executed.
  - `tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells` — tighten the assertions so both cpu/cuda legs verify `(Na·Nb·Nc)^2` within ≤1% when oversample>1, and check that the steps scalar + new telemetry fields exist (catch regressions if omega is re-applied inside the accumulation loop).
  - `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py` — keep the telemetry ingest in sync with the simulator changes (e.g., display the new omega-applied flag plus the ratio between `trace_subpixel_F_total_sq_sum` and the now-correct normalized intensity) so the Markdown/JSON clearly show the restored factor.
  - Environment freeze bookkeeping — save the simulator diff as `plans/active/ARCH-SIM-CONSTRUCTION-001/patches/omega_compensation.patch`, rerun `python -m pip install -e src/nanobrag-torch`, log the command + git status in `patches/environment_tag.md` (e.g., `nanobrag-partiality-2026-01-11`), and append a short note to `docs/findings.md::SIM-CONSTR-PARTIALITY-001` documenting the omega compensation change + tag.
Validate:
  - Re-run the single-pixel probe + architecture partiality test + DB-AT-028/029 commands listed above with artifacts rooted at `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-11T180000Z/`.
Forbidden This Loop:
  - no new probes
  - do not extend plan-local diagnostic scripts (PROBE-FREEZE-001)
  - do not alter non-SQUARE lattice paths or Stage A/mapping helpers; keep changes scoped to the simulator owner path + existing tests
DMI Section:
  - Independent Reference: docs/spec-db-core.md:60-140 `(Na·Nb·Nc)^2` contract enforced independently by `tests/architecture/test_nanobrag_partiality.py` and DB-AT-028/029 selectors.
  - Transformation Ledger:
    | Field/Tensor | Expected (units/shape) | Producer (file:line) | Hydration (file:line) | Consumer (file:line) | Observed Evidence | Hypothesis |
    | --- | --- | --- | --- | --- | --- | --- |
    | Single-pixel ratio (oversample=13) | `(41·29·32)^2 = 1.447650304e9` photons | `probe_square_lattice_scaling.py:119-205` | `simulator.py:1180-1355` | `square_lattice_scaling.md:24-31` | 1.3601574985e8 (0.0939× spec) | Omega applied before Riemann summation deletes 90 % of intensity |
    | Raw vs normalized intensity | ratio should be ≈1 (omega applied once) | `simulator.py:1325-1365` | `_partiality_stats['trace_subpixel_*']` | `square_lattice_scaling.json:125-149` | `trace_subpixel_F_total_sq_sum=1.6148e17`, `trace_normalized_intensity=1.6148e11` → normalized/raw = 1e-6 | Oversample>1 branch multiplies by `last_omega` prematurely |
    | Architecture partiality test ratio | 1.447650304e9 | `tests/architecture/test_nanobrag_partiality.py:20-158` | same | `pytest_partiality.log:15-27` | 5.9038e8 (59% error) | Multi-pixel accumulation suffers same omega loss |
    | DB-AT-028 chi²/pixel initial | ≤1e2 | `tests/dbex/test_stage_a_smoke_parity.py` | Stage A telemetry | `db_at_028/db_at_028_metrics.json` | 2.1e5 | Acceptance failure driven by missing lattice weight |
    | DB-AT-029 median ROI corr | ≥0.2 | same | Stage A ROI stats | `db_at_029/db_at_029_metrics.json` | -0.053 | Same root cause |
  - Source Trace Anchors: `src/nanobrag-torch/src/nanobrag_torch/simulator.py:1180-1365` (omega application), `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py:119-311`, `tests/architecture/test_nanobrag_partiality.py:20-158`.
  - Consumption-State Measurements: `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-11T010000Z/square_lattice_scaling.{md,json}`, `pytest_partiality.log`, `db_at_028/db_at_029_metrics.json`.
  - Boundary Bisection Step: Move to the omega application boundary — after this patch the raw-vs-normalized ratio must collapse to 1.0 for oversample>1, and architecture + DB-AT selectors should trend toward spec; if not, investigate downstream scaling.
  - Probe Budget: unchanged (0/2 new probes used); instrumentation stays inside the simulator.
How-To Map:
  1. mkdir -p plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-11T180000Z/{db_at_028,db_at_029}
  2. Edit `src/nanobrag-torch/src/nanobrag_torch/simulator.py`, `tests/architecture/test_nanobrag_partiality.py`, and the sanctioned probe per the Do Now bullets.
  3. Capture the simulator diff as `patches/omega_compensation.patch`, run `python -m pip install -e src/nanobrag-torch`, and record the env tag in `patches/environment_tag.md`.
  4. Run the mapped probe + pytest commands, tee logs into the artifacts directory, and ensure DB-AT metrics JSON files land under the db_at_* subdirectories.
  5. Summarize results (ratios, chi², ROI corr) in `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-11T180000Z/summary.md` before handing off artifacts.
Pitfalls To Avoid:
  - Keep omega changes gated to SQUARE/oversample>1 so ROUND/GAUSS/TOPHAT behavior stays untouched.
  - Do not remove or bypass the existing `_partiality_stats` guard; production runs must see zero overhead when instrumentation is disabled.
  - Remember to re-run `pip install -e src/nanobrag-torch` after editing the vendor tree; Environment Freeze requires the patch + tag log.
  - Avoid tweaking Stage A/reconstruction scaling while this fix is in flight; focus strictly on the simulator defect.
  - Architecture test must remain deterministic — keep tolerances tight (≤1%) and assert telemetry fields exist to catch regressions early.
If Blocked: Record the failure (symptoms + logs) in `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-11T180000Z/summary.md`, update docs/fix_plan.md Attempts History + galph_memory.md, and escalate to spec_change or a separate architecture initiative if omega compensation cannot restore the `(Na·Nb·Nc)^2` ratio.
