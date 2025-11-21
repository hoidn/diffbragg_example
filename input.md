Summary: Reuse the Stage A warm cache for Stage B/C compute paths and emit perf telemetry before replaying the Stage B/C smokes.
Mode: Perf
Focus: PERF-WARM-SIM-001 — Warm simulator; eliminate per-iteration re-instantiation
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers, tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T105321Z/

Do Now:
- Implement: dbex/nanobrag_refinement.py::compute_loss_stage_b — when `stage_a_ctx` exists, reuse its detector configs/simulators so Stage B no longer re-instantiates Detector/Simulator per closure, keep the current cold path as a fallback, and populate Stage B `perf_counters` (cache_mode, roi counts, closure_evals, forward_time_ms) before telemetry is serialized.
- Implement: dbex/nanobrag_refinement.py::compute_loss_stage_c — share Stage A’s warmed detector configs/masks for panel loops (only rebuild when distance overrides change), tag Stage C telemetry with the same perf counters/roi metadata, and ensure telemetry still reports baseline detector offsets.
- Test: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T105321Z/telemetry_stage_bc_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::{test_stage_b_shell_modifiers,test_stage_c_detector_microslip}
- Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T105321Z/

How-To Map:
1. Stage B warm reuse/perf: teach `compute_loss_stage_b` and the final Stage B bragg write-out to consume `stage_a_ctx.detector_models`/`simulators` when `config.enable_stage_a_warm_cache` is True (re-target cached simulators with the Stage B crystal/HKL grid) and to fall back to the existing `create_detector_config` loop when no cache is available. Emit Stage B `perf_counters` that mirror Stage A’s payload (cache_mode, roi_mode="panel", closure counts, forward_time stats) so `_record_stage_telemetry` picks them up.
2. Stage C warm reuse/perf: reuse `stage_a_ctx.detector_configs`/trusted-mask tensors to avoid retensorizing per panel, cloning configs only when you apply distance overrides, and add Stage C perf/roi metadata to `telemetry_c`. Keep bounded distance math + variance telemetry untouched.
3. Tests/telemetry capture:
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   DBEX_SMOKE_SIGMA_SOURCE=cli_override \
   DBEX_SMOKE_DETECTOR_SIZE=small \
   DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T105321Z/telemetry_stage_bc_small.json \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/dbex/test_torch_refine_smoke.py::{test_stage_b_shell_modifiers,test_stage_c_detector_microslip} \
     | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-21T105321Z/pytest_stage_bc_small.log
   ```
   Inspect the telemetry JSON to ensure Stage B/C perf counters include `cache_mode="warm"` and non-zero forward_time data.
4. Findings/docs: append the new Stage B/C perf metrics (speedups and cache modes) to `docs/findings.md` under PERF-WARM-005 (or a new PERF-WARM row) and log the evidence path + perf deltas in `docs/fix_plan.md` Attempts History once tests pass.

Pitfalls To Avoid:
- Do not mutate `stage_a_ctx` detectors in-place when cold mode is active; keep cache reuse gated on `enable_stage_a_warm_cache`.
- Preserve Stage B shell-modifier gates (≤±1 % delta, ≥−1e-6 loss regression); never relax tolerances to “test” perf.
- Ensure Stage C still references `baseline_detector` distances so detector-offset telemetry remains meaningful.
- Keep perf counters deterministic (no random sampling beyond the seeded ROI/panel choices).
- Avoid touching Stage A ROI sampling logic in this loop; layered-scope guard forbids mixing stages.
- No environment/toolchain tweaks (Environment Freeze). Treat missing imports as blockers rather than installing packages.
- Capture Stage B/C logs + telemetry in the artifacts path; do not overwrite older Stage A benchmark evidence.

If Blocked:
- Record the failure mode (e.g., Stage B still instantiates cold simulators, telemetry perf counters missing) in `docs/fix_plan.md` and drop the minimal stack trace into `plans/active/PERF-WARM-SIM-001/reports/2025-11-21T105321Z/blockers.txt`.
- Update `galph_memory.md` with `state=blocked`, note which selector or code path failed, and pivot only after documenting whether perf cache reuse is the blocker or if Stage A context needs changes.

Findings Applied (Mandatory):
- PERF-WARM-001 (`docs/findings.md:16`) — Stage A perf counters/benchmark scaffolding define the telemetry contract Stage B/C must now match.
- PERF-WARM-002 (`docs/findings.md:17`) — Warm cache must actually hoist detector/crystal creation; Stage B/C reuse should follow the same principle.
- PERF-WARM-003 (`docs/findings.md:16`) — Prior measurements show simulator loops dominate; extending the warm cache to Stage B/C directly addresses that gap.
- PERF-WARM-005 (`docs/findings.md:18`) — ROI/cold gating is warm-only; Stage B/C reuse must respect that so panel-mode cold runs remain valid controls.

Pointers:
- dbex/nanobrag_refinement.py:1499 — Stage B shell-modifier block and `compute_loss_stage_b` loops that still rebuild Detector/Simulator each closure.
- dbex/nanobrag_refinement.py:2052 — Stage C detector-microslip compute path that recreates detector configs/masks per panel.
- docs/TESTING_GUIDE.md:38 — Canonical Stage B/C smoke gates, env vars, and telemetry expectations for small/full detector runs.
- docs/spec-db-runtime.md:10 — Warm-cache guardrails require simulator reuse whenever detector shapes stay constant.

Next Up (optional):
- Once Stage B/C reuse lands, profile whether the warm vs cold ratio improves and decide if a dedicated Stage B benchmark or Stage C ROI sampler is needed to close exit criterion #1.
