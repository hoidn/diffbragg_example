Summary: Hoist Stage A detector context so LBFGS stops rebuilding per ROI while keeping telemetry unchanged.
Mode: Perf
Focus: PERF-WARM-SIM-001 — Warm Simulator; Eliminate Per-Iteration Re-Instantiation
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion, tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-05T221200Z/

Do Now:
- PERF-WARM-SIM-001 — Warm Simulator; Eliminate Per-Iteration Re-Instantiation
  - Implement: dbex/nanobrag_refinement.py::run_nanobrag_refinement — introduce a Stage A panel context cache that precomputes detector configs/models plus trusted mask/target tensors so the LBFGS closure reuses them instead of rebuilding per panel, while keeping Stage B/C telemetry dictionaries identical.
  - Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion | tee $ARTIFACTS/collect_stage_a.log && KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --maxfail=1 --capture=tee-sys | tee $ARTIFACTS/pytest_stage_a.log
  - Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers | tee $ARTIFACTS/collect_stage_b.log && KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --maxfail=1 --capture=tee-sys | tee $ARTIFACTS/pytest_stage_b.log
  - Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-05T221200Z/

How-To Map:
- export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
- export ARTIFACTS=plans/active/PERF-WARM-SIM-001/reports/2025-11-05T221200Z
- mkdir -p "$ARTIFACTS"
- AUTHORITATIVE_CMDS_DOC=$AUTHORITATIVE_CMDS_DOC pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion | tee "$ARTIFACTS/collect_stage_a.log"
- KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 AUTHORITATIVE_CMDS_DOC=$AUTHORITATIVE_CMDS_DOC pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --maxfail=1 --capture=tee-sys | tee "$ARTIFACTS/pytest_stage_a.log"
- AUTHORITATIVE_CMDS_DOC=$AUTHORITATIVE_CMDS_DOC pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers | tee "$ARTIFACTS/collect_stage_b.log"
- KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 AUTHORITATIVE_CMDS_DOC=$AUTHORITATIVE_CMDS_DOC pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --maxfail=1 --capture=tee-sys | tee "$ARTIFACTS/pytest_stage_b.log"
- printf "Stage A/B warm-sim cache validated; see %s and %s\n" "$ARTIFACTS/pytest_stage_a.log" "$ARTIFACTS/pytest_stage_b.log" >> "$ARTIFACTS/summary.md"

Pitfalls To Avoid:
- Keep Environment Freeze intact; no package installs or runtime tweaks to chase perf.
- Preserve Stage A telemetry structure (`loss_trace_*`, `roi_count_sampled`, snapshots) byte-for-byte for downstream consumers.
- Do not reorder sampled panels; Stage B expects Stage A sample IDs in deterministic order (REFINE-008).
- Maintain `log_scale` warm-start/clamp semantics per REFINE-001 when refactoring closures.
- Ensure cached detector masks stay as float32 tensors with {0.0,1.0} polarity (CONFIG-001).
- Avoid keeping CUDA tensors; stay on CPU and honor `NANOBRAGG_DISABLE_COMPILE=1` (RUNTIME-001).
- Update cache invalidation when cell/orientation tensors change to prevent stale geometry.
- Capture collect-only logs before running selectors (TESTING-003) so docs remain synchronized.

If Blocked:
- Tee the failing command output to $ARTIFACTS/blocker.log, note the exception and offending panel/context, set docs/fix_plan.md status to `blocked` with the signature, and record the retry condition in galph_memory.md before exiting.

Findings Applied (Mandatory):
- REFINE-001 — Maintain scale warm-start and clamp bounds while reorganizing Stage A closure.
- REFINE-002 — Keep the ≥0.1% Stage A improvement gate semantics intact when caching detectors.
- CONFIG-001 — Cached detector masks must preserve polarity and dtype expected by nanobrag_torch.
- RUNTIME-001 — Run smokes with `NANOBRAGG_DISABLE_COMPILE=1` to avoid Dynamo interference.
- TESTING-003 — Collect-only logs precede pytest runs and land under the artifacts directory.

Pointers:
- dbex/nanobrag_refinement.py:394 — Stage A parameter initialization block targeted for cache reuse.
- dbex/nanobrag_refinement.py:537 — Current per-panel Detector instantiation inside the closure.
- plans/active/PERF-WARM-SIM-001/implementation.md:1 — Warm simulator implementation plan and task breakdown.
- docs/pytorch_runtime_checklist.md:26 — Runtime flags required for deterministic refinement tests.
- docs/development/testing_strategy.md:34 — Selector/collect-only cadence guardrails.

Next Up (optional):
- Extend the Stage A cache to reuse Crystal/Simulator objects and add perf counters under `/torch_diagnostics`.
- Apply the warm context pattern to Stage B shell modifiers once Stage A reuse is stable.
