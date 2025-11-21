# Input

- Summary: Fix the canonical Stage B/C smokes by repairing the Stage B LBFGS scope bug and emitting real detector-offset telemetry so REFINE-SMOKE-CANONICAL can unblock PHYSICS-LOSS-001.
- Mode: Parity
- Focus: REFINE-SMOKE-CANONICAL — Restore canonical Stage B/C smoke convergence
- Branch: integration
- Mapped tests:
  * `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full`
  * `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=full`
- Artifacts: plans/active/REFINE-SMOKE-CANONICAL/reports/2025-11-21T042222Z/

## Do Now
- Focus Item: REFINE-SMOKE-CANONICAL
- Implement: `dbex/nanobrag_refinement.py::{closure_stage_b,run_nanobrag_refinement}` — add the missing `nonlocal` declarations + remove debug prints so Stage B updates `chi_squared_best_b`/snapshots safely, and plumb an optional `baseline_detector` so Stage C telemetry (`param_deltas`) records real initial/final distance offsets; update `tests/dbex/test_torch_refine_smoke.py::{test_stage_b_shell_modifiers,test_stage_c_detector_microslip}` (plus Stage C probe call sites) to pass the baseline detector and assert the telemetry.
- Test: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH=plans/active/REFINE-SMOKE-CANONICAL/reports/2025-11-21T042222Z/telemetry_full.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full | tee plans/active/REFINE-SMOKE-CANONICAL/reports/2025-11-21T042222Z/pytest_stage_c_full.log`
- Test: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH=plans/active/REFINE-SMOKE-CANONICAL/reports/2025-11-21T042222Z/telemetry_full.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=full | tee plans/active/REFINE-SMOKE-CANONICAL/reports/2025-11-21T042222Z/pytest_stage_b_full.log`
- Artifacts: plans/active/REFINE-SMOKE-CANONICAL/reports/2025-11-21T042222Z/

## How-To Map
1. Re-open `dbex/nanobrag_refinement.py` and update `closure_stage_b` (lines 1463-1503) to declare `nonlocal chi_squared_best_b, masked_mse_best_b, best_loss_full_b, best_params_snapshot_b` before the LBFGS body, then drop the temporary `print("DEBUG ...")` statements so log noise disappears.
2. Extend `run_nanobrag_refinement` to accept an optional `baseline_detector`; inside the Stage C block convert each panel's directed-distance delta to millimeters relative to the baseline detector (defaulting to zero when absent) and set `param_deltas_c['panel_{pid}_distance_offset_mm'] = {"initial": initial_offset_mm, "final": initial_offset_mm + bounded_offset, "delta": float(bounded_offset)}` (dbex/nanobrag_refinement.py:2017-2023).
3. Update every Stage C caller that already captures canonical geometry — `tests/dbex/test_torch_refine_smoke.py::{test_stage_c_detector_microslip,test_stage_b_shell_modifiers}`, `plans/active/TORCH-REFINE-003/bin/probe_stage_c_improvement.py`, and any other scripts that build a baseline detector — to pass the original detector into `run_nanobrag_refinement(baseline_detector=...)`; CLI/probe sites without a baseline can leave it as `None`.
4. After code changes, run the Stage C strict smoke command above with telemetry logging enabled; verify the new JSON shows `detector_offset_reduction_min≈0.8` and `detector_offset_final_abs_max≈0.0` instead of the bogus 1.00/0.0 pair.
5. Run the Stage B strict smoke command; confirm the UnboundLocalError is gone, Stage B status is `ok` or `early_stop`, and telemetry captures modifier deltas ≤±1% with `loss_improvement >= -1e-6`.
6. Append the new pytest logs plus the refreshed telemetry JSON to the artifacts directory and summarize the measured offsets/improvements in `docs/fix_plan.md` Attempts History.

## Pitfalls To Avoid
- Do not relax the strict gates in `tests/dbex/test_torch_refine_smoke.py`; the goal is to fix implementation telemetry, not weaken assertions.
- Keep `run_nanobrag_refinement` backwards-compatible by making `baseline_detector` optional and defaulting telemetry to zeros when no baseline exists.
- Preserve the variance-weighted chi-squared math (PHYSICS-LOSS-001/002); avoid touching the loss helper while editing Stage B/C scopes.
- Ensure tensor snapshots stay on the correct device when reassigning best shell modifiers—no inadvertent `.cpu()` calls inside the LBFGS closure.
- Capture telemetry/logs only under `plans/active/REFINE-SMOKE-CANONICAL/reports/2025-11-21T042222Z/` to honor the artifact policy.
- Use `KMP_DUPLICATE_LIB_OK=TRUE` and `NANOBRAGG_DISABLE_COMPILE=1` on all pytest invocations per docs/TESTING_GUIDE.md.
- Avoid editing Stage A code or fixtures unrelated to this initiative; we only touch the Stage B/C pathways and their tests.

## If Blocked
- If Stage B still raises an UnboundLocalError, capture the full stack trace plus `pytest_stage_b_full.log`, mark REFINE-SMOKE-CANONICAL blocked in `docs/fix_plan.md`, and call out the failing line in `galph_memory.md`.
- If Stage C telemetry still reports 100% reductions despite the baseline plumbing, archive the telemetry JSON, log the anomaly in the fix plan Attempts History, and halt rather than weakening the test.

## Findings Applied (Mandatory)
- REFINE-007 — Canonical Stage C must prove ≥80% detector-offset reduction with ≤0.05% chi-squared regression; telemetry must reference the actual injected offsets.
- REFINE-008 — Stage B strict gate requires ≤1e-6 chi-squared regression and ±1% shell modifiers, so the LBFGS fix must preserve these bounds and telemetry.
- PHYSICS-LOSS-001/002 — All stages must emit variance-weighted chi-squared traces with sigma-floor metadata; edits must retain these telemetry fields.

## Pointers
- tests/dbex/test_torch_refine_smoke.py:525-710 — Stage C microslip test harness consuming `param_deltas` and enforcing REFINE-007 gates.
- tests/dbex/test_torch_refine_smoke.py:724-920 — Stage B shell-modifier smoke plus telemetry assertions (REFINE-008).
- dbex/nanobrag_refinement.py:1463-1559 — Stage B LBFGS closure, best-parameter snapshots, and improvement gate logic.
- dbex/nanobrag_refinement.py:2017-2039 — Stage C telemetry assembly where `param_deltas` currently hard-code zero initial offsets.
- plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T031620Z/pytest_stage_smokes_full.log:460-509 — Evidence of the `chi_squared_best_b` UnboundLocalError under canonical smokes.
- plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T032803Z/telemetry_full.json:1-49 — Stage C telemetry claiming 100% offset reduction despite zero chi-squared change.
- docs/TESTING_GUIDE.md:48-120 & docs/development/TEST_SUITE_INDEX.md:12 — Stage smoke commands, env flags, and strict gate documentation.
- docs/spec-db-workflow.md:32-70 — Stage Smoke Dataset Policy plus Stage B/C normative behavior backing this repair.

## Next Up (optional)
1. Once Stage B/C canonical smokes pass, re-run PHYSICS-LOSS-001 Stage B/C selectors on the small-detector fixture to resume the shared variance-weighted helper work.

## Doc Sync Plan (Conditional)
- Not needed (no new selectors this loop).

## Mapped Tests Guardrail
- `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=full KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full`
- `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=full KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=full`
