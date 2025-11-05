Summary: Prepare ready-for-implementation handoff so Stage A refinement hits ≥5% loss drop by wiring log_cell_a_delta through the torch crystal config.
Mode: none
Focus: TORCH-REFINE-001 — Implement LBFGS refinement nucleus (Stage A)
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py::test_loss_decreases
Artifacts: plans/active/TORCH-REFINE-001/reports/2025-11-05T021259Z/

Do Now (hard validity contract)
- Implement: dbex/nanobrag_refinement.py::run_nanobrag_refinement — route `log_cell_a_delta` into a differentiable `create_crystal_config` override (update dbex/nanobrag_bridge.py::create_crystal_config as needed) so LBFGS can move cell_a and achieve ≥5% loss drop.
- Validate: pytest -v tests/dbex/test_torch_refine_smoke.py::test_loss_decreases --maxfail=1
- Artifacts: plans/active/TORCH-REFINE-001/reports/2025-11-05T021259Z/pytest_refine_smoke.log

How-To Map
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. env KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_loss_decreases --maxfail=1 | tee plans/active/TORCH-REFINE-001/reports/2025-11-05T021259Z/pytest_refine_smoke.log
3. jot telemetry status + improvement delta into plans/active/TORCH-REFINE-001/reports/2025-11-05T021259Z/summary.md

Pitfalls To Avoid
- Do not break deterministic ROI sampling (leave seed=42, reuse sampled panels).
- Keep all optimization-path tensors on device without `.detach()`/`.item()` conversions (see GRADIENT-001).
- Preserve existing log_scale warm-start/clamp behavior from REFINE-001 while adding cell overrides.
- Ensure `create_crystal_config` overrides accept torch.Tensor without casting to numpy; guard other call sites.
- Update both closure and final render paths so Bragg outputs use the same perturbed crystal config.
- Avoid environment/tooling changes; rely only on repository sources.
- Keep telemetry schema stable (no key renames) and include improvement message when status="early_stop".
- When touching tests, keep selector stable; do not downgrade acceptance threshold without supervisor sign-off.

If Blocked
- Capture the failure signature (stack trace or unexpected telemetry) in plans/active/TORCH-REFINE-001/reports/2025-11-05T021259Z/summary.md and downgrade fix_plan status to blocked with rationale; notify supervisor for rescoping.

Findings Applied (Mandatory)
- REFINE-001 — Maintain scale warm-start and log-scale clamp while extending nucleus to cover crystal DoF.
- GRADIENT-001 — Preserve tensor-based overrides so autograd path remains intact (no `.item()` when wiring crystal parameters).

Pointers
- docs/spec-db-workflow.md:24 — Stage A requires global scale + crystal DoF with ≥5% loss drop.
- plans/nanobrag_integration_plan.md:172 — Refinement nucleus contract for LBFGS closure and DoF set.
- dbex/nanobrag_refinement.py:200 — Current placeholder for applying `log_cell_a_delta` (needs real crystal override).
- dbex/nanobrag_bridge.py:445 — CrystalConfig helper to extend with tensor overrides.
- tests/dbex/test_torch_refine_smoke.py:108 — Acceptance criteria enforcing ≥5% improvement.

Next Up (optional)
- Investigate tensor override plumbing for additional Stage A DoFs once loss threshold clears.
