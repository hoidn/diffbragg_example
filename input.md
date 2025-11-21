Summary: Enable Stage B shell modifiers to reuse warmed ROI slices and prove the ROI/panel telemetry via Stage B smoke runs.
Mode: Perf
Focus: PERF-WARM-SIM-001 — Warm simulator; eliminate per-iteration re-instantiation
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T121804Z/

Do Now:
- Focus Item: PERF-WARM-SIM-001
- Implement: dbex/nanobrag_refinement.py::run_nanobrag_refinement — add a Stage B ROI-mode path that iterates StageAContext.roi_entries whenever Stage A ROI mode is active, so shell modifiers operate on the warmed ROI simulators instead of whole panels and telemetry/perf counters record ROI totals accurately.
- Implement: tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers — update the perf counter asserts to expect `roi_mode` to follow the Stage A ROI knob ("roi" for cropped smokes, "panel" for canonical runs) and validate ROI totals/sample counts for both detector sizes.
- Test: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T121804Z/telemetry_stage_b_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-21T121804Z/pytest_stage_b_small.log
- Re-test: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T121804Z/telemetry_stage_b_full.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=full | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-21T121804Z/pytest_stage_b_full.log
- Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T121804Z/

How-To Map:
1. Wire a `stage_b_roi_mode_active` flag in `dbex/nanobrag_refinement.py` (near lines 1540-2100) that mirrors Stage A’s ROI knob when the warm cache has ROI entries, and branch `compute_loss_stage_b` so ROI work items index `stage_a_ctx.roi_entries` with slice-level target/mask tensors instead of whole panels.
2. Update the Stage B ROI sampler/perf counters to iterate ROI indices when ROI mode is active, track sampled ROI counts (not just panel IDs), and surface the active `roi_mode` string through both telemetry and the perf counter dict.
3. Refresh `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` to assert the new ROI-mode behavior: cropped smoke runs must report `cache_mode="warm"`, `roi_mode="roi"`, and sampled ROI totals that match `len(refinement_inputs.panel_slices)`, while canonical full-detector runs must fall back to panel mode but keep the perf counters >0.
4. Run the small-detector Stage B smoke command (env + telemetry path above) and inspect the resulting telemetry JSON/log to ensure ROI metrics populate; repeat with `--smoke-detector-size=full` to confirm panel fallback, storing both logs/telemetry under the new artifacts directory.

Pitfalls To Avoid:
- Do not touch Stage A ROI sampling seeds or `StageAContext` structure—reuse the existing sampled index lists so determinism holds.
- Keep the variance-weighted loss math identical for ROI vs panel paths (refs: docs/spec-db-core.md §57-68); only change the loops/samplers.
- Stage B warm cache must stay optional: when ROI mode is disabled or stage_a_ctx is None, fall back cleanly to the current panel code without dereferencing ROI entries.
- Ensure perf counter dicts always include numeric values (ints/floats) even in cold-mode to avoid breaking telemetry serialization.
- Guard the test asserts with informative messages so perf regressions point at `cache_mode`/`roi_mode` mismatches instead of generic failures.
- Leave Stage C ROI logic untouched; only Stage B should change in this loop per layered-scope guard.

If Blocked:
- Capture the failing pytest output (`tee` log), the telemetry JSON snippet showing the mismatch, and log the command + error message in plans/active/PERF-WARM-SIM-001/reports/2025-11-21T121804Z/blockers.txt.
- Update docs/fix_plan.md Attempts History and galph_memory.md with the blocking evidence, then switch focus per instructions.

Findings Applied (Mandatory):
- PERF-WARM-003 — ROI sampling is required to break the 1.01× plateau, so Stage B must honor the ROI mode instead of rendering whole panels.
- PERF-WARM-005 — Benchmark evidence (plans/active/PERF-WARM-SIM-001/reports/2025-11-21T103232Z/) shows ROI vs panel yields ≥10× wins; this change preserves that ROI mode into Stage B telemetry.
- PERF-WARM-006 — Stage B/C must reuse Stage A detector configs/masks; ensure the ROI branch takes advantage of StageAContext caches rather than rebuilding.
- PERF-WARM-007 — Canonical Stage B/C perf counters now gate warm-cache behavior; updated tests must keep those asserts strict so regressions fail quickly.

Pointers:
- dbex/nanobrag_refinement.py:1540 — Stage B warm-cache plumbing and `compute_loss_stage_b` implementation that needs the ROI branch.
- tests/dbex/test_torch_refine_smoke.py:920 — Stage B smoke harness where the perf counter assertions live.
- docs/TESTING_GUIDE.md:31-53 — Detector-size and telemetry guardrails that define the strict gates for canonical runs.
- plans/active/PERF-WARM-SIM-001/reports/2025-11-21T133500Z/benchmark_summary.json — Latest warm-vs-cold metrics to cite in findings after verification.

Next Up (optional): If Stage B ROI mode lands cleanly, consider rerunning `benchmark_stage_a_cache.py --modes warm cold` to refresh the findings with the new ROI counters.

Doc Sync Plan (Conditional): Not needed — no new selectors or renamed tests in this loop.

Mapped Tests Guardrail: Stage B selector already collects >0 cases; if `pytest --collect-only` ever returns 0, author a minimal test before landing code.

Hard Gate: Do not mark the initiative done unless both Stage B smoke runs (small + full) pass with telemetry capturing non-zero ROI/panel counts per docs/TESTING_GUIDE.md §2.

Normative Math/Physics: Follow docs/spec-db-core.md §57-68 for the variance-weighted chi-squared equation; ROI-mode must use the same `Sum((pred-obs)^2 / (pred.detach()+sigma^2))` definition with the sigma_floor clamp.
