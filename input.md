Summary: Introduce typed telemetry dataclasses for Stages B and C so the remaining LBFGS helpers stop mutating anonymous dicts and RefinementEngine artifacts/tests can rely on stable fields per ARCH-STAGE-CTX-001 + PHYSICS-LOSS-001/002.
Mode: none
InitiativeType: architecture
Focus: ARCH-STAGE-CONTEXT-001 — Stage Context + Engine Artifact Boundary
Branch: integration
Mapped tests:
- tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small
- tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke --smoke-detector-size=small
- tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small
- tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full
Artifacts: plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T083500Z/

Do Now:
- FocusItem: ARCH-STAGE-CONTEXT-001 Phase B.3.2 — Stage B/C telemetry-state dataclasses.
- Implement: `dbex/refinement/context.py::{StageBTelemetryState,StageCTelemetryState}` — add two dataclasses mirroring the Stage A structure (loss/χ²/MSE traces, perf counters, variance-floor stats, best snapshots, optional panel diagnostics). Include docstrings citing ARCH-STAGE-CTX-001 + PHYSICS-LOSS-001/002 and default factories for mutable lists. Provide helper accessors (or simple `isinstance` shims) so callers can handle either dataclass or legacy dict inputs while we finish migrating the CLI monolith.
- Implement: `dbex/refinement/stage_b_impl.py::_build_stage_b_params` and `_run_stage_b_lbfgs`, `dbex/refinement/stage_b.py::StageB._build_lbfgs_closure`/`StageB.run`, and `_check_stage_b_baseline_parity` — instantiate/use `StageBTelemetryState` instead of plain dicts, updating read/write sites to use attribute access while keeping compatibility guards (`if isinstance(telemetry_state, dict)`). Preserve StageBArtifacts baseline fields and ensure RefinementTelemetry output is unchanged.
- Implement: `dbex/refinement/stage_c_impl.py::_build_stage_c_params`/`_run_stage_c_lbfgs` and `dbex/refinement/stage_c.py::StageC._build_lbfgs_closure`/`StageC.run` — swap the Stage C telemetry dict for the new dataclass, keep the `DBEX_STAGE_C_PANEL_DIAG_DIR` hook (panel diagnostics list lives on the dataclass), and make sure REFINE-013 best-snapshot persistence still works.
- Validate: run the mapped smoketests, capturing logs under the artifact directory; Stage B per-reflection and Stage C full-detector remain expected failures (baseline gradient-flow & PERF-WARM-SIM-001). Call out any deviation from the known signatures.

How-To Map:
1. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md mkdir -p plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T083500Z/{panel_diag_small,panel_diag_full}`
2. Stage B shell (expected PASS): `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T083500Z/pytest_stage_b_shell.log`
3. Stage B per-reflection (known failure): same env/selector `tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke --smoke-detector-size=small | tee .../pytest_stage_b_per_reflection.log`; record that the failure message matches the existing ASU-gradient defect (see reports/2025-12-02T020900Z/blocked.md).
4. Stage C small detector (PASS, captures panel diag): `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_STAGE_C_PANEL_DIAG_DIR=plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T083500Z/panel_diag_small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee .../pytest_stage_c_small.log`
5. Stage C full detector (known PERF-WARM-SIM-001 failure): rerun with `DBEX_SMOKE_DETECTOR_SIZE=full DBEX_STAGE_C_PANEL_DIAG_DIR=.../panel_diag_full` and capture logs/telemetry at `.../pytest_stage_c_full.log`; verify failure signature matches the +0.067% χ² regression documented in fix_plan.md.
6. Archive any generated panel diagnostics JSON + pytest logs inside the artifact directory (include collect-only output if you run it for debugging).

Pitfalls To Avoid:
- Do not regress the existing RefinementTelemetry schema or StageBArtifacts baseline metrics; tests rely on those exact keys.
- Keep dict compatibility until the CLI monolith flips—wrap attribute mutations with `if isinstance(..., dict)` shims instead of removing dict support outright.
- Preserve the Stage C panel diagnostics hook: failing to write `panel_loss_diag_c` will break PERF-WARM-SIM-001 evidence capture.
- Maintain variance-floor counters as mutable list wrappers; copying tensors will break cache reuse.
- Stage B per-reflection and Stage C full-detector failures are expected; treat any new failure mode or success (e.g., gate unexpectedly passes) as a regression and pause.

If Blocked:
- Capture stack traces/logs under `plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T083500Z/blocked.md` and update docs/fix_plan.md if the dataclass swap exposes a deeper dependency (e.g., legacy CLI unhandled). Note whether the block affects Stage B, Stage C, or both.
- If a smoketest fails differently from the known signatures, stop after collecting artifacts (pytest log, telemetry JSON, panel diagnostics) so we can reassess scope before more code churn.

Findings Applied (Mandatory):
- ARCH-STAGE-CTX-001 — Replace Stage B/C data clumps and mutable dict plumbing with typed contexts/dataclasses.
- ARCH-ENGINE-002 — Stage wrappers must uphold the RefinementStage protocol and emit stable telemetry fields for the engine/writer.
- PHYSICS-LOSS-001/002 — Dual loss metrics and variance-floor telemetry must remain intact while refactoring storage.
- REFINE-007 / PERF-WARM-SIM-001 — Stage C smoketest gates (offset reduction + χ² regression) remain the authoritative acceptance criteria; leave thresholds untouched.

Pointers:
- dbex/refinement/context.py:520-650 — Stage A dataclass implementation to mirror for Stages B/C.
- dbex/refinement/stage_b_impl.py:520-930, dbex/refinement/stage_b.py:120-940 — current Stage B telemetry dict lifecycle that needs conversion.
- dbex/refinement/stage_c_impl.py:120-750 and dbex/refinement/stage_c.py:160-760 — Stage C param builders/closures that still mutate dicts and manage panel diagnostics.
- docs/TESTING_GUIDE.md §2, docs/development/TEST_SUITE_INDEX.md — selectors/env vars for the mapped smoketests.

Next Up (optional):
- After Stage B/C telemetry moves to dataclasses, Phase C can focus on letting RefinementEngine/writer consume artifacts without poking private dict keys.
