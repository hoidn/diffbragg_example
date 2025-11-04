# DB-AT-002 — Determinism Acceptance Harness

## Phase A — Reality Check & Inputs
- [ ] **A1 — Dependency audit**: Confirm FORWARD-EQUIV-002 artifacts provide canonical tensors + metrics needed as baselines; verify `tests/fixtures/golden_data/simple_cubic/` includes manifest checksum `2d1f8d67…8567aee`.
- [ ] **A2 — Environment rehearsal**: Dry-run determinism env guards (`CUDA_VISIBLE_DEVICES=''`, `TORCHDYNAMO_DISABLE=1`, `NANOBRAGG_DISABLE_COMPILE=1`, `KMP_DUPLICATE_LIB_OK=TRUE`) to ensure torch imports respect CPU-only execution (no CUDA probe).
- [ ] **A3 — Metric spec alignment**: Reconcile thresholds with `docs/development/testing_strategy.md` §2.7 (same-seed ≥0.9999999 correlation, diff-seed ≤0.7, ≥50% differing pixels) and `docs/TESTING_GUIDE.md` determinism row.

## Phase B — Harness Implementation
- [ ] **B1 — Same-seed parity**: Author `tests/dbex/test_forward_determinism.py::TestForwardDeterminism::test_DB_AT_002_same_seed` loading canonical tensors via parity loader, executing two simulator runs with identical seeds, asserting bitwise equality and metric thresholds.
- [ ] **B2 — Different-seed independence**: Add complementary test `test_DB_AT_002_diff_seed` verifying correlation ≤0.7 and ≥50% differing pixels using distinct RNG seeds; capture mask-aware pixel diff counts.
- [ ] **B3 — Artifact writer**: Emit determinism artifacts under `plans/active/DB-AT-002/reports/<timestamp>/determinism/` (metrics_same_seed.json, metrics_diff_seed.json, env.json, commands.txt) using shared helper.

## Phase C — Documentation & Registry Sync
- [ ] **C1 — Docs update**: Promote DB_AT_002 row in `docs/TESTING_GUIDE.md` / `docs/development/TEST_SUITE_INDEX.md` to Active with new artifact paths + metrics; cite determinism findings (CONFORMANCE-001, TESTING-003, RUNTIME-001).
- [ ] **C2 — Evidence capture**: Run targeted selector `CUDA_VISIBLE_DEVICES='' TORCHDYNAMO_DISABLE=1 NANOBRAGG_DISABLE_COMPILE=1 KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests -k DB_AT_002` plus `pytest --collect-only` with logs stored in the initiative report directory.
- [ ] **C3 — Ledger sync**: Append Attempts History entry to `docs/fix_plan.md` with metrics/commands/artifacts, update `docs/findings.md` if determinism gotchas surface, and mark initiative ready for closure.

