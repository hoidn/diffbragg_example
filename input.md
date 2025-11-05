Summary: Halo the Stage A HKL grid and re-enable interpolation so the smoke regains the ≥5% gate.
Mode: none
Focus: TORCH-REFINE-002D — Stage A HKL-aware perturbation dataset
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion
Artifacts: plans/active/TORCH-REFINE-002D/reports/2025-11-05T083500Z/

Do Now:
- TORCH-REFINE-002D
  - Implement: dbex/nanobrag_bridge.py::build_structure_factor_grid — add an optional ±1 halo (metadata + tensor padding) and document the toggle so Stage A can interpolate fractional HKL coordinates without hitting `default_F`.
  - Implement: dbex/nanobrag_refinement.py::run_nanobrag_refinement — extend `RefinementConfig` with an interpolation flag and honor it when wiring `Crystal.interpolate`, preserving the NN default for datasets without a halo.
  - Implement: tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion — request the haloed grid, enable interpolation, drop the interim xfail, and assert ≥5% masked-MSE improvement with telemetry logging the achieved delta.
  - Validate: KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --maxfail=1
  - Artifacts: plans/active/TORCH-REFINE-002D/reports/2025-11-05T083500Z/

How-To Map:
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. mkdir -p plans/active/TORCH-REFINE-002D/reports/2025-11-05T083500Z
3. KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion | tee plans/active/TORCH-REFINE-002D/reports/2025-11-05T083500Z/collect_stage_a.log
4. KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --maxfail=1 | tee plans/active/TORCH-REFINE-002D/reports/2025-11-05T083500Z/pytest_stage_a.log
5. Record the post-run improvement + iteration count in plans/active/TORCH-REFINE-002D/reports/2025-11-05T083500Z/summary.md alongside telemetry excerpts.

Pitfalls To Avoid:
- Do not mutate canonical HKL assets; halo padding must be applied in-memory only (Environment Freeze).
- Keep tensor overrides on the refinement device/dtype without `.detach()` to satisfy GRADIENT-001.
- Preserve the deterministic perturbation magnitudes (+2/+1/+1% cell, +1.5° Z) so REFINE-004 remains truthful.
- Maintain ≥95% HKL hit rate; log new metadata if padding shifts ranges.
- Ensure interpolation toggle defaults to False to protect other datasets until halo support is proven.
- Avoid introducing new scripts outside plans/active/TORCH-REFINE-002D/bin/ unless promotion criteria are met.
- Capture failing selectors verbatim if improvement <5% and mark the block before retrying.
- Respect existing findings: do not remove the telemetry assertions that guard misset plumbing.

If Blocked:
- Capture stack traces or sub-5% improvement metrics in plans/active/TORCH-REFINE-002D/reports/2025-11-05T083500Z/blocked.md, update docs/fix_plan.md Attempts History, and log the block in galph_memory.md before pivoting focus.

Findings Applied (Mandatory):
- REFINE-003 — Orientation overrides must flow through `misset_deg_override`; retain deterministic misset telemetry when enabling interpolation.
- REFINE-004 — Deterministic perturbation stays test-scoped; ≥5% gate must pass before we retire the finding.
- REFINE-005 — Halo + interpolation must prevent `default_F` fallback when fractional HKL land near grid edges.
- GRADIENT-001 — Orientation tensors must remain differentiable; avoid scalar conversions in the new toggle path.

Pointers:
- docs/fix_plan.md:60 — TORCH-REFINE-002D status, attempts, and refreshed Phase 1 plan.
- plans/active/TORCH-REFINE-002D/implementation.md:18 — Halo/interpolation work breakdown (P1.1–P1.3, P2.1–P2.2).
- tests/dbex/test_torch_refine_smoke.py:200 — Stage A acceptance criteria and telemetry assertions.
- dbex/nanobrag_bridge.py:559 — Current HKL grid builder stub targeted for halo support.
- dbex/nanobrag_refinement.py:340 — Crystal wiring where interpolation toggle must be honored.

Next Up (optional):
1. Run the Stage A smoke on GPU to confirm device-agnostic gradients once halo interpolation lands.
