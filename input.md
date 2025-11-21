Summary: Plan Stage C warm-cache reuse so we stop rebuilding Detector/Simulator objects each iteration while keeping telemetry artifacts reproducible.
Mode: Perf
Focus: PERF-WARM-SIM-001 — Warm simulator; eliminate per-iteration re-instantiation
Branch: integration
Mapped tests:
  * tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small
  * tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T175716Z/

Do Now:
- Focus Item: PERF-WARM-SIM-001
- Implement: dbex/nanobrag_refinement.py::_build_stage_a_context — stash baseline per-panel distances/ROI maps in StageAContext so later stages can mutate cached detectors without recreating configs; include any helper you need to surface these tensors.
- Implement: dbex/nanobrag_refinement.py::compute_loss_stage_c — add a retarget helper that applies the bounded Stage C distance offsets to StageAContext simulators/ROI entries so warm-mode stops instantiating fresh Detector/Simulator objects; update the final Stage C reconstruction loop to reuse the warmed simulators as well, keeping the cold path unchanged.
- Test: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T175716Z/telemetry_stage_c_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-21T175716Z/pytest_stage_c_small.log
- Test: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T175716Z/telemetry_stage_c_full.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-21T175716Z/pytest_stage_c_full.log
- Test: python plans/active/PERF-WARM-SIM-001/bin/summarize_stage_c_roi.py --telemetry plans/active/PERF-WARM-SIM-001/reports/2025-11-21T175716Z/telemetry_stage_c_small.json --telemetry plans/active/PERF-WARM-SIM-001/reports/2025-11-21T175716Z/telemetry_stage_c_full.json --out plans/active/PERF-WARM-SIM-001/reports/2025-11-21T175716Z/stage_c_roi_summary.json | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-21T175716Z/summarize_stage_c_roi.log

How-To Map:
1. Modify `StageAContext` and `_build_stage_a_context` so each panel entry carries its baseline `distance_mm` tensor plus ROI→panel indices; expose a helper that returns per-panel mutable detector handles without copying.
2. Add `_retarget_stage_a_detectors(stage_a_ctx, distance_offsets, device)` (name flexible) beside `_retarget_stage_a_simulators`; it should apply the bounded offsets to every cached simulator plus ROI entry, respecting CPU fallbacks and keeping masks/tensors on the correct dtype/device.
3. In `compute_loss_stage_c`, replace the warm-cache branches that currently copy detector configs with calls to the new helper so ROI-mode iterations simply reuse cached simulators/detector tensors before running the loss; keep the cold-mode code path untouched.
4. Update the final Stage C reconstruction loop to reuse the warmed simulators after applying the distance offsets rather than instantiating another Detector/Simulator pair; ensure log_scale scaling + telemetry stay identical to current output.
5. Run the Stage C small-detector selector with the canonical env vars above, teeing output + telemetry JSON into the new artifacts directory.
6. Repeat for the full-detector selector (expect longer runtime); collect telemetry + pytest log under the same directory.
7. Generate `stage_c_roi_summary.json` via the summarizer so exit criterion #2 has the consolidated evidence; inspect the JSON for `cache_mode="warm"` and non-zero ROI counts before uploading.

Pitfalls To Avoid:
- Do not mutate the cached detectors when `stage_c_use_warm_cache` is false; cold path must still rebuild configs per iteration.
- Keep Stage B behavior intact—retarget helpers should only fire within the Stage C code paths you touch.
- Preserve dtype/device fidelity when retargeting detectors so CPU fallback (stage_b_full_eval_on_cpu) does not break Stage C telemetry.
- Reuse the existing perf-counter fields; do not rename telemetry keys or relax asserts in the smoke tests.
- Guard ROI mode carefully: Stage C canonical runs still expect `roi_mode="panel"` whenever Stage A ROI is disabled for canonical detectors.
- Avoid introducing new dependencies or scripts outside the initiative bin directory (environment freeze still applies).
- Validate that the retarget helper updates ROI simulators before reuse; stale geometry will invalidate Stage C offset gates.
- Capture telemetry/log artifacts directly under the new timestamped folder so docs/fix_plan references remain accurate.
- Keep the summarizer output schema identical so downstream tooling (`plans/active/PERF-WARM-SIM-001/bin/summarize_stage_c_roi.py`) continues to parse it.
- Honor `NANOBRAGG_DISABLE_COMPILE=1` and `KMP_DUPLICATE_LIB_OK=TRUE` in all pytest runs per runtime guardrails.

If Blocked:
- If Stage C still instantiates new detectors after your changes (e.g., because simulator API lacks setters), capture the failing evidence (stack traces, perf counters) in the artifact directory, log the limitation plus error signature in `docs/fix_plan.md`, and mark the fix-plan item blocked in galph_memory so we can reprioritize helper work.
- Should the smoke selector crash (CUDA OOM, telemetry mismatch), save the pytest log + telemetry JSON, reference the selector/gate that failed, and halt additional implementation until we triage it in the plan ledger.

Findings Applied (Mandatory):
- PERF-WARM-006 — Stage B/C must reuse Stage A cache structures; the retarget helper enforces this requirement for Stage C warm runs.
- PERF-WARM-007 — Keep Stage C perf-counter asserts/logging intact while capturing new telemetry evidence after the refactor.
- PERF-WARM-012 — CPU fallback must continue to report `cache_mode="warm"`; retarget helper needs to respect the cloned Stage A context when Stage B forces CPU evals.
- PERF-WARM-013 — Current Stage C warm runs still rebuild Detector/Simulator instances; this Do Now resolves that gap by mutating cached simulators instead of cloning configs.
- RUNTIME-001 — Pytest commands must continue to run with `NANOBRAGG_DISABLE_COMPILE=1` to avoid torch.compile interference.

Pointers:
- docs/fix_plan.md:37 — PERF-WARM-SIM-001 ledger entry, exit criteria, and Attempts History.
- plans/active/PERF-WARM-SIM-001/implementation.md:70 — Phase D checklist for the Stage C detector reuse scope.
- dbex/nanobrag_refinement.py:2238 — Stage C warm/cold branching that still instantiates new Detector/Simulator objects.
- docs/TESTING_GUIDE.md:51 — Stage C telemetry workflow (env vars + summarizer command) for mapped selectors.
- docs/development/TEST_SUITE_INDEX.md:12 — Registry row for the Stage A/B/C smoke selectors and canonical commands.

Next Up (optional):
- If Stage C reuse lands quickly, rerun the Stage B canonical smoke on CPU to confirm cache_mode stays warm and refresh ROI telemetry under the same artifact folder.
