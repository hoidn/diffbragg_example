# PARITY-HARNESS-002 — DB-AT Parity Harness

## Phase A — Golden Dataset & Manifest (Complete)
- [x] **A1 — Dataset reality check**: Verify nanoBragg2 golden data mirror availability; if absent, document FALLBACK strategy per `docs/spec-db-conformance.md:23-26` and `docs/spec-db-core.md:20-40`.  
- [x] **A2 — Golden dataset generation**: Produce synthetic simple-cubic tensors (bragg, target, loss mask) aligned to `[panel, slow, fast]` ordering; capture SHA256 manifest per `docs/spec-db-core.md:20-33`.  
- [x] **A3 — Loader & validation helpers**: Implement loader enforcing checksum, pixel pitch, and tensor ordering guards; expose fixtures for parity tests (`docs/spec-db-conformance.md:23-26`).  
- [x] **A4 — Registry sync**: Author DB_AT_001 manifest integrity tests and update selector docs/logs (TESTING-003) while re-running smoke harness for regression coverage.

## Phase B — Metrics & Artifact Utilities (Complete)
- [x] **B1 — Parity metrics helper**: Implement `compute_parity_metrics()` returning correlation, MSE, RMSE, max|Δ|, sum ratio, and localization stats for matched ROIs; respect thresholds in `docs/spec-db-conformance.md:23-26` and `docs/forward_equivalence.md:30-53`.
- [x] **B2 — Artifact writers**: Persist metrics JSON/CSV, overlays, and trace stubs under `plans/active/<initiative>/reports/<timestamp>/parity_harness/` per `docs/spec-db-tracing.md:10-24` and `docs/TESTING_GUIDE.md:87-90`.
- [x] **B3 — Harness fixtures**: Extend fixtures to hydrate DiffBragg and torch forward tensors, seeding RNG for reproducibility; ensure artifacts reference same dataset manifest.

## Phase C — DB_AT_001 Parity Test (Partially Complete: synthetic data only, pending real simulator)
- [x] **C1 — Threshold enforcement**: Parametrize test across dtype/device (CPU for now) and enforce correlation ≥0.2 and localization ≥90% with conditional `xfail` when simulator stub prevents success (`docs/spec-db-conformance.md:23-26`, `docs/forward_equivalence.md:46-52`).
- [x] **C2 — Artifact capture**: Emit diff heatmaps, per-ROI metrics, and trace logs, linking to manifest checksum; record artifact paths in pytest output to satisfy ledger cross-references (`docs/spec-db-tracing.md:10-24`).
- [x] **C3 — Doc & ledger sync**: Update `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` with final selector status + environment flags; append Metrics/Artifacts lines in `docs/fix_plan.md`. Ensure `pytest --collect-only` logs archived (TESTING-003).

## Phase D — Traceability Enhancements (Optional)
- [ ] **D1 — First divergence capture**: Integrate trace hooks to record first-difference metrics per ROI when parity thresholds fail (`docs/spec-db-tracing.md:15-24`).  
- [ ] **D2 — Findings updates**: Document durable lessons (e.g., manifest maintenance, parity thresholds) in `docs/findings.md` and link from testing docs.  
- [ ] **D3 — Simulator upgrade readiness**: Outline TODOs for replacing stub tensors with `nanobrag_torch` once available, including threshold adjustments and new regression artifacts.
