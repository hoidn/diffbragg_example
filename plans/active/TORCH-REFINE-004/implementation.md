# TORCH-REFINE-004 — Stage B Fhkl modifiers implementation plan

## Context & guardrails
- Stage B is optional but must preserve Stage A geometry behavior (docs/spec-db-workflow.md §7; plans/nanobrag_integration_plan.md §Stage B).
- Differentiable HKL interpolation is mandatory when Stage B runs and requires the ±1 halo grid (REFINE-005, docs/architecture/pytorch_design.md §1.1.1).
- Structure factors remain unscaled pre-simulation (SCALE-001/002) and refined MTZ telemetry stays authoritative (SCALE-003/007).
- Default behavior keeps Stage B disabled; opt in via config/CLI so Stage C smoke and nucleus paths remain stable until Stage B clears its gate.

## Phase 1 — Config + metadata scaffolding
- [ ] Extend `dbex/nanobrag_refinement.py::RefinementConfig` with Stage B knobs (`enable_stage_b`, `stage_b_mode="shell" | "per_reflection"`, shell count/edges, modifier clamp, improvement gate).
- [ ] Add helper to precompute HKL shell metadata (e.g., `compute_hkl_shell_lookup`) using unit-cell metrics so Stage B can map each grid voxel to a shell index on-device.
- [ ] Surface Stage B toggles through CLI wiring (`dbex/refine_one.py` torch backend path) and `RefinementConfig` instantiation; refuse enablement unless `hkl_metadata["has_halo"]` is true.

## Phase 2 — Stage B optimization loop (shell mode)
- [ ] Insert Stage B block in `run_nanobrag_refinement` between Stage A completion and optional Stage C, freezing Stage A tensors.
- [ ] Parameterize shell modifiers with positive transform (softplus/log-exp) and apply them lazily inside the LBFGS closure to a copy of `hkl_grid`; ensure gradients flow end-to-end.
- [ ] Record Stage B telemetry (`modifier_count`, `shell_edges`, `modifier_values`, improvement trace, status, default_F guard) using `RefinementTelemetry` and add `"B"` entry to the returned dict.

## Phase 3 — Persistence & telemetry plumbing
- [ ] Update `_write_torch_outputs` to emit Stage B telemetry groups under `/torch_diagnostics/stage_B`, including stage mode, modifier stats, and any default_F fallback counter.
- [ ] Extend CLI logging so Stage B status/improvement print alongside Stage A/C summaries, maintaining deterministic ordering.

## Phase 4 — Tests + documentation
- [ ] Add deterministic Stage B smoke in `tests/dbex/test_torch_refine_smoke.py` (e.g., `test_stage_b_shell_modifiers`) asserting: Stage B telemetry present, ≥ calibrated improvement vs Stage A final, shell modifier deltas sane, no default_F fallback when halo grid in use.
- [ ] Adjust existing Stage A / Stage C smokes to explicitly disable Stage B (config flag) and confirm gating expectations unchanged.
- [ ] Update `docs/TESTING_GUIDE.md` and `docs/development/TEST_SUITE_INDEX.md` with new selector + environment requirements; refresh `docs/fix_plan.md` Attempts History once artifacts collected.

## Phase 5 — Follow-up (post-merge calibration)
- [ ] Measure observed Stage B improvement on canonical refGeom assets, calibrate `stage_b_min_loss_improvement` threshold + test assertion, and document outcome in `docs/findings.md` if the acceptance gate shifts from the current ≥3% placeholder.

## Exit reminders
- Capture targeted logs (`collect_stage_b.log`, `pytest_stage_b_shell.log`, Stage A comparison traces) under `plans/active/TORCH-REFINE-004/reports/<timestamp>/`.
- Keep Environment Freeze intact; if Stage B uncovers missing nanobrag_torch hooks, raise blocker instead of installing packages.
