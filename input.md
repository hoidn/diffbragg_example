Summary: Preserve Stage A telemetry coverage while flagging the ≥5% gate as blocked on an HKL grid rebuild.
Mode: none
Focus: TORCH-REFINE-002 — Stage A expansion — full crystal and orientation
Branch: integration
Mapped tests: pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --maxfail=1
Artifacts: plans/active/TORCH-REFINE-002/reports/2025-11-05T041539Z/

Do Now:
- TORCH-REFINE-002
  - Implement: tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion — run the smoke with baseline refGeom geometry (no perturbation), assert telemetry structure (misset_xyz_deg keys + quaternion norm) before gating, then call `pytest.xfail` with REFINE-004/005 rationale when improvement <5% so the HKL dependency is explicit while keeping the deterministic helper available for future HKL-ready datasets.
  - Validate: pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --maxfail=1
  - Artifacts: plans/active/TORCH-REFINE-002/reports/2025-11-05T041539Z/

How-To Map:
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. mkdir -p plans/active/TORCH-REFINE-002/reports/2025-11-05T041539Z
3. KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion | tee plans/active/TORCH-REFINE-002/reports/2025-11-05T041539Z/collect_stage_a.log
4. KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --maxfail=1 | tee plans/active/TORCH-REFINE-002/reports/2025-11-05T041539Z/pytest_stage_a.log

Pitfalls To Avoid:
- Keep orientation tensors differentiable; no `.item()`/`.detach()` when inspecting telemetry.
- Do not delete `create_perturbed_geometry`; just stop calling it until HKL assets are rebuilt.
- Ensure telemetry assertions execute before issuing `pytest.xfail`, so orientation plumbing stays validated.
- Preserve deterministic seeds/ROI sampling so telemetry comparisons remain meaningful.
- Note REFINE-005: HKL grid must match the perturbed basis; avoid partial perturbations that still break lookups.
- Respect Environment Freeze — no new installs or MTZ regeneration within the loop.
- Archive logs under the new timestamped report directory; never overwrite prior attempts.

If Blocked:
- Capture the failure signature (e.g., telemetry missing keys, pytest crash) in plans/active/TORCH-REFINE-002/reports/2025-11-05T041539Z/blocked.md, update docs/fix_plan.md Attempts History, and add a galph_memory entry marking the focus blocked before pivoting.

Findings Applied (Mandatory):
- REFINE-001 — Warm-start log_scale and clamp before exponentiation to keep gradients finite.
- REFINE-002 — Canonical dataset only yields ~0.15% improvement; ≥5% requires extra headroom.
- REFINE-003 — Orientation path must remain differentiable through CrystalConfig misset overrides.
- REFINE-004 — Deterministic perturbation lives in the smoke harness; production assets stay untouched.
- REFINE-005 — Perturbing geometry without rebuilding the HKL grid produces 0% hit rate; until reindexed data exists, expect the ≥5% gate to xfail.
- GRADIENT-001 — Crystal overrides remain tensors; avoid reinjecting MOSFLM A* when overrides are active.

Pointers:
- docs/spec-db-workflow.md:30 — Stage A gate rationale and telemetry contract.
- docs/fix_plan.md:31 — TORCH-REFINE-002 attempts history and Option D notes.
- plans/active/TORCH-REFINE-002/implementation.md:18 — Phase checklist with Option D expectations.
- plans/active/TORCH-REFINE-002/reports/2025-11-05T035905Z/blocked.md — HKL grid failure signature.
- docs/findings.md:35 — REFINE-004/005 dataset constraints.

Next Up (optional):
1. Draft TORCH-REFINE-002D initiative for HKL-aware perturbation dataset once xfail guardrails land.
