Summary: Port the source-weight runtime guard into DBEX and activate the Runtime Vectorization selector.
Mode: none
Focus: RUNTIME-VEC-001 — Source weighting runtime guard
Branch: integration
Mapped tests: tests/dbex/test_runtime_vectorization.py::TestRuntimeVectorization::test_source_weights_ignored_per_spec
Artifacts: plans/active/RUNTIME-VEC-001/reports/2025-11-04T080000Z/{pytest_runtime_vec.log,collect_runtime_vec.log}

Do Now (hard validity contract)
- Focus Item: RUNTIME-VEC-001
- Implement: tests/dbex/test_runtime_vectorization.py::TestRuntimeVectorization::test_source_weights_ignored_per_spec (new module ensuring equal-weight enforcement)
- Validate: KMP_DUPLICATE_LIB_OK=TRUE RUNTIME_VEC_ARTIFACT_DIR=plans/active/RUNTIME-VEC-001/reports/2025-11-04T080000Z pytest -v tests/dbex/test_runtime_vectorization.py::TestRuntimeVectorization::test_source_weights_ignored_per_spec --maxfail=1 | tee plans/active/RUNTIME-VEC-001/reports/2025-11-04T080000Z/pytest_runtime_vec.log
- Artifacts: plans/active/RUNTIME-VEC-001/reports/2025-11-04T080000Z/{pytest_runtime_vec.log,collect_runtime_vec.log}

How-To Map
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. export RUNTIME_VEC_ARTIFACT_DIR=plans/active/RUNTIME-VEC-001/reports/2025-11-04T080000Z && mkdir -p "$RUNTIME_VEC_ARTIFACT_DIR"
3. export KMP_DUPLICATE_LIB_OK=TRUE && export NANOBRAGG_DISABLE_COMPILE=1
4. Sanity check CLI availability: python -m nanobrag_torch --help > "$RUNTIME_VEC_ARTIFACT_DIR/cli_help.txt"; treat failure as Environment Freeze block and log signature.
5. Author new module tests/dbex/test_runtime_vectorization.py using ../nanoBragg/tests/test_cli_scaling.py::TestSourceWeights as reference; create temporary sourcefiles in test using pathlib/tempfile, call `python -m nanobrag_torch` with weighted vs equal source lists, assert correlation ≥0.999 and |sum_ratio−1| ≤5e-3, and emit metrics JSON into "$RUNTIME_VEC_ARTIFACT_DIR/mapping_metrics.json" on failure.
6. Update docs/TESTING_GUIDE.md (Runtime vectorization row) and docs/development/TEST_SUITE_INDEX.md to mark selector Active, include command, env flags, runtime, artifact path, and referenced findings (RUNTIME-001, SCALE-001/002).
7. Run KMP_DUPLICATE_LIB_OK=TRUE RUNTIME_VEC_ARTIFACT_DIR="$RUNTIME_VEC_ARTIFACT_DIR" pytest -v tests/dbex/test_runtime_vectorization.py::TestRuntimeVectorization::test_source_weights_ignored_per_spec --maxfail=1 | tee "$RUNTIME_VEC_ARTIFACT_DIR/pytest_runtime_vec.log"
8. Run KMP_DUPLICATE_LIB_OK=TRUE RUNTIME_VEC_ARTIFACT_DIR="$RUNTIME_VEC_ARTIFACT_DIR" pytest --collect-only tests/dbex/test_runtime_vectorization.py -k TestRuntimeVectorization | tee "$RUNTIME_VEC_ARTIFACT_DIR/collect_runtime_vec.log"
9. Append Attempts History for RUNTIME-VEC-001 in docs/fix_plan.md with command strings, artifact paths, and references to updated docs.

Pitfalls To Avoid
- Do not install or upgrade packages; Environment Freeze applies (missing CLI import is a blocker).
- Keep temporary files inside pytest tmp_path or tempfile directories; no artifacts outside "$RUNTIME_VEC_ARTIFACT_DIR".
- Preserve torch environment flags (KMP_DUPLICATE_LIB_OK=TRUE, NANOBRAGG_DISABLE_COMPILE=1) before importing torch or running `python -m nanobrag_torch`.
- Ensure weighted vs equal runs share identical geometry parameters; only weights should differ.
- Capture failure metrics before assertions to aid reproducibility; include both correlation and sum_ratio.
- Avoid copying the entire nanoBragg2 suite verbatim—pare to the equal-weight guard for this loop and leave TODOs for remaining cases.
- Do not mark docs rows Active until pytest and collect-only artifacts exist (TESTING-003).
- Do not hard-code host-specific paths; rely on pathlib relative paths.
- Keep runtime under control (use 128×128 detector size and minimal oversample) to avoid slow CI regressions.

If Blocked
- Record failing command and stderr/stdout in "$RUNTIME_VEC_ARTIFACT_DIR/blocker_log.txt".
- Update docs/fix_plan.md Attempts History entry with the block reason and commands run.
- Append galph_memory next_action with `switch_focus` if CLI import or environment freeze cannot be resolved.

Findings Applied (Mandatory)
- RUNTIME-001 — Disable torch.compile (`NANOBRAGG_DISABLE_COMPILE=1`) for gradient/runtime tests.
- SCALE-001 — Prevent duplicate spot-scale application when preparing HKL data.
- SCALE-002 — Apply sqrt(spot_scale_override) as differentiable torch operation if scaling is required.
- TESTING-003 — Promote selectors to Active only after collect-only proves >0 tests and artifacts are archived.

Pointers
- docs/pytorch_runtime_checklist.md:31 — Runtime vectorization + equal weighting guidance.
- docs/architecture/pytorch_design.md:90 — Source weighting thresholds (corr ≥0.999, |sum_ratio−1| ≤5e-3).
- ../nanoBragg/tests/test_cli_scaling.py:252 — Reference implementation of `TestSourceWeights::test_source_weights_ignored_per_spec`.
- plans/active/RUNTIME-VEC-001/implementation.md:1 — Phased checklist for this initiative.
- docs/TESTING_GUIDE.md:70 — Runtime vectorization row to update once artifacts exist.

Next Up (optional)
- Port `TestSourceWeightsDivergence` parity assertions once the equal-weight guard is active.

Doc Sync Plan (Conditional)
- After the test passes, rerun Step 8 (`pytest --collect-only ...`) with logs saved to "$RUNTIME_VEC_ARTIFACT_DIR/collect_runtime_vec.log", then update docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md to reflect Active status and artifact paths.

Mapped Tests Guardrail
- Ensure `pytest --collect-only tests/dbex/test_runtime_vectorization.py -k TestRuntimeVectorization` reports ≥1 test; if it collects 0, stop and author the missing test before finishing the loop.
