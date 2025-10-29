# PARITY-HARNESS-002 Implementation Plan — DB-AT Parity Harness Tests

## Phase A — Golden Dataset & Fixtures
- **A1 Dataset inventory**: Locate simple cubic golden data per `docs/parity_harness_spec.md:28-41`; document available paths and checksums.
- **A2 Mirror & manifest**: If external-only, mirror dataset under `tests/fixtures/golden_data/simple_cubic/` with `manifest.json` (SHA256 per §2.2); otherwise record provenance and validation command.
- **A3 Loader & checksum guard**: Add fixture/helper that loads tensors, validates manifest, and enforces `[panel, slow, fast]` ordering per `docs/spec-db-core.md:24` and pixel pitch guard per `docs/spec-db-core.md:43`.
- **A4 Baseline smoke guard**: Re-run `pytest -v tests/dbex/test_nanobrag_smoke.py` (with `KMP_DUPLICATE_LIB_OK=TRUE`) after fixture integration to ensure existing smoke coverage remains green; archive log.

**Validation:** Notes in `notes_phase_a.md` plus checksum log; failing checksum blocks progression.

## Phase B — Harness Utilities
- **B1 Metrics helper**: Implement `compute_parity_metrics` (see `docs/parity_harness_spec.md:78-161`) with numpy/scipy fallback and dtype/device reporting.
- **B2 Artifact writers**: Provide helpers to emit `metrics.json` and trace logs into `plans/active/PARITY-HARNESS-002/reports/<timestamp>/parity/` per §2.5-§2.6.
- **B3 Trace capture guard**: Wire configurable trace pixel selection honoring `docs/spec-db-tracing.md:10-26`; ensure traces round-trip to/from JSON.

**Validation:** Unit tests for helpers (device/dtype coverage) and sample artifact captured in reports directory.

## Phase C — DB-AT-001 Parity Test Implementation
- **C1 Test scaffolding**: Add `tests/dbex/test_db_at_001_parity.py` (or similar) with fixtures for golden data + harness utilities.
- **C2 Metrics enforcement**: Parametrize over dtype/device; ensure thresholds `correlation ≥ 0.99` and RMSE tolerance recorded in metrics.json (`docs/spec-db-conformance.md:24-26`).
- **C3 Artifact capture**: Save metrics, diff heatmap (if implemented), and trace logs to loop artifacts; record command + env flag `KMP_DUPLICATE_LIB_OK=TRUE` (§2.4).

**Validation:** `pytest -v tests -k DB_AT_001` passes on CPU; collect-only logs saved; docs/test registries updated to mark selector Active.

## Phase D — DB-AT-002 Determinism Test Implementation
- **D1 Same/different seed harness**: Extend utilities for paired runs with identical vs distinct seeds per `docs/parity_harness_spec.md:252-320`.
- **D2 Metric checks**: Enforce bitwise equality threshold for same-seed (max_abs_diff ≤1e-10) and decorrelation for diff-seed (correlation ≤0.7) per spec.
- **D3 CPU-only enforcement**: Ensure env guards `CUDA_VISIBLE_DEVICES='' TORCHDYNAMO_DISABLE=1 NANOBRAGG_DISABLE_COMPILE=1` documented and enforced.

**Validation:** `pytest -v tests -k DB_AT_002` passes on CPU with artifacts captured; docs/test registry updated.

## Phase E — Documentation & Ledger Sync
- **E1 Testing docs update**: Sync `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` with DB_AT_001/002 selectors, environment flags, and artifact references.
- **E2 Fix plan ledger**: Append Attempts History entries with Metrics/Artifacts lines; ensure `docs/fix_plan.md` status reflects reality.
- **E3 Summary & findings**: Publish summary.md, update `docs/findings.md` if new lessons discovered, and cross-link in `docs/index.md` if new artifacts/specs introduced.

**Validation:** Docs updated with authoritative references and artifact paths; loop summary stored under reports path.
