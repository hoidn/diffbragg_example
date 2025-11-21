Summary: Unblock Stage B ROI telemetry capture by logging shell-modifier deltas into the smoke-test telemetry JSON and re-running the Stage B smokes with the summary script.
Mode: Perf
Focus: PERF-WARM-SIM-001 — Warm simulator; eliminate per-iteration re-instantiation
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small; tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=full
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T125551Z/

Do Now:
- Focus Item: PERF-WARM-SIM-001
- Implement: tests/dbex/test_torch_refine_smoke.py::_record_stage_telemetry — persist `telemetry.param_deltas` (JSON-safe floats/lists) plus the existing perf counters so Stage B telemetry JSON includes shell modifier statistics for both detector sizes.
- Implement: plans/active/PERF-WARM-SIM-001/bin/summarize_stage_b_roi.py::main — load the list-of-stage telemetry payloads, filter `stage=="stage_b_shell_modifiers"`, ingest the new `param_deltas`, and emit a consolidated ROI/perf/modifier summary JSON for the small + full runs.
- Test: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T125551Z/telemetry_stage_b_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-21T125551Z/pytest_stage_b_small.log
- Re-test: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T125551Z/telemetry_stage_b_full.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=full | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-21T125551Z/pytest_stage_b_full.log
- Script: python plans/active/PERF-WARM-SIM-001/bin/summarize_stage_b_roi.py --telemetry plans/active/PERF-WARM-SIM-001/reports/2025-11-21T125551Z/telemetry_stage_b_small.json --telemetry plans/active/PERF-WARM-SIM-001/reports/2025-11-21T125551Z/telemetry_stage_b_full.json --out plans/active/PERF-WARM-SIM-001/reports/2025-11-21T125551Z/stage_b_roi_summary.json
- Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T125551Z/

How-To Map:
1. Update `_record_stage_telemetry` so the payload appends `"param_deltas": telemetry.param_deltas` (convert numpy scalars to Python floats) before writing JSON; keep canonical metadata and perf counters intact.
2. Patch `summarize_stage_b_roi.py` to iterate over the telemetry list, pick entries where `entry["stage"] == "stage_b_shell_modifiers"`, pull ROI/perf counters plus the new `param_deltas`, and preserve dataset labels from the JSON instead of inferring from filenames.
3. Re-run the Stage B smoke twice (small + full) with the telemetry env vars above so fresh JSON/logs land under the new artifacts directory; confirm the pytest gate sees `roi_mode="roi"` on both runs.
4. Execute the summary script with both telemetry files to emit `stage_b_roi_summary.json`, then use that output + pytest logs to refresh docs/findings.md (PERF-WARM-008) and append the new Attempts History note in docs/fix_plan.md before handing the artifacts to Ralph.

Pitfalls To Avoid:
- Do not touch Stage C code/tests in this loop—layered-scope guard keeps the work item within Stage B.
- Preserve Environment Freeze: no package installs or CUDA/torch changes.
- Ensure `telemetry.param_deltas` serialization handles nested dicts/lists (Stage A) and floats (Stage B) without lossy rounding.
- Keep telemetry payload append-only; don’t overwrite prior entries if telemetry files already exist—merge with the existing list.
- Capture canonical (full-detector) telemetry even if the first small-detector run passes; ROI totals ≥92 are mandatory evidence.
- Don’t rename the Stage B pytest selector; selectors must stay consistent with docs/TESTING_GUIDE.md §2.
- Avoid leaking Stage A ROI knobs into cold-mode paths; the tests should still assume warm cache semantics.
- If GPUs are unavailable or tests fail for reasons unrelated to telemetry logging, stop and log the block instead of downgrading the selector.
- Keep the summary script under plans/active/.../bin (T2); no ad-hoc python -c commands in the How-To Map.

If Blocked:
- Save failing pytest output plus the telemetry JSON snippet to plans/active/PERF-WARM-SIM-001/reports/2025-11-21T125551Z/blockers.txt, note the error signature in docs/fix_plan.md, and update galph_memory.md before pivoting per instructions.

Findings Applied (Mandatory):
- PERF-WARM-005 — Warm vs cold ROI gating demands perf counters tag `roi_mode`; telemetry JSON must mirror that contract for both detector sizes.
- PERF-WARM-006 — Stage B reuse of StageAContext ROI caches must stay intact; rerunning the smokes with telemetry proves reuse didn’t regress.
- PERF-WARM-007 — Canonical Stage B smokes enforce perf-counter invariants, so tests must still assert warm cache metrics after the telemetry writer changes.
- PERF-WARM-008 — Stage B canonical runs now require `roi_mode="roi"` with ≥92 ROIs; refreshed telemetry and the summary script will provide the evidence to rewrite this finding.

Pointers:
- tests/dbex/test_torch_refine_smoke.py:1-120 — `_record_stage_telemetry` payload builder that currently drops `param_deltas`.
- dbex/nanobrag_refinement.py:1989-2056 — Stage B telemetry assembly showing shell modifier param_deltas that must reach the logs.
- plans/active/PERF-WARM-SIM-001/reports/2025-11-21T124101Z/telemetry_stage_b_small.json — Existing telemetry file demonstrating the missing `param_deltas` field.
- plans/active/PERF-WARM-SIM-001/bin/summarize_stage_b_roi.py — Summary script to update once telemetry JSON carries shell modifiers.
- docs/TESTING_GUIDE.md:31-52 — Telemetry + detector-size policy for Stage A/B/C smokes.

Next Up (optional): With telemetry fixed, consider replaying Stage C full-detector smoke to confirm its ROI/perf counters still align with Stage B.

Mapped Tests Guardrail: `pytest --collect-only tests/dbex/test_torch_refine_smoke.py -k test_stage_b_shell_modifiers` already reports 1 collected node; reruns reuse that selector with different `--smoke-detector-size` values.

Hard Gate: Do not close this focus until both Stage B telemetry files show `cache_mode="warm"`, `roi_mode="roi"`, `roi_count_total={29,92}`, shell modifier `param_deltas` recorded, and stage_b_roi_summary.json cites the artifact paths.

Normative Math/Physics: Stage B must continue minimizing the variance-weighted chi-squared from docs/spec-db-core.md §§57–68; telemetry/logging changes must not alter the optimization math.
