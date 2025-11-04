# FORWARD-EQUIV-002 — Promote Forward Equivalence Smoke to Canonical Parity

## Phase A — Reality Check & Inputs
- [x] **A1 — Canonical dataset validation**: Confirm simple cubic golden tensors (DiffBragg + nanobrag) exist locally with checksum `2d1f8d671a6b051b23dd7a059f9fd8ff5605389bbe9a8e72cb44cbd7a8567aee`; capture manifest evidence under this initiative. (Artifacts: `plans/active/FORWARD-EQUIV-002/reports/2025-11-04T041500Z/forward_equiv/parity_harness/metrics.json`)
- [x] **A2 — Threshold rehearsal**: Recompute DB-AT-001 metrics via `compute_parity_metrics` to verify correlation ≥0.2 and localization ≥0.90 prior to updating the test. (Metrics: correlation=0.988, localization=1.0 from targeted run)

## Phase B — Harness Modernization
- [x] **B1 — Fixture swap**: Replace `stub_diffbragg` / `stub_torch` fixtures with canonical loaders (`load_golden_data`, `GoldenData`) and remove bespoke ROI sampling helpers in favor of parity utilities. (Code: `tests/dbex/test_forward_equivalence_complete.py`)
- [x] **B2 — Artifact routing**: Point artifact directory to `plans/active/FORWARD-EQUIV-002/reports/<timestamp>/forward_equiv/`, reuse `write_parity_artifacts`, and ensure first-divergence metadata (if any) is captured consistently. (Artifacts: `forward_equiv/parity_harness/{metrics.json,first_divergence.json,predicted.npy,target.npy}`)
- [x] **B3 — Assertion tightening**: Remove unconditional `pytest.xfail`, assert DB-AT-001 thresholds directly, and surface metrics via standard logging. (Runtime evidence: `pytest_forward_equiv.log`)

## Phase C — Documentation & Ledger Sync
- [x] **C1 — Docs refresh**: Update `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` to reflect the canonical dataset, new artifact path, and passing status; cite relevant findings (CONFORMANCE-001, TESTING-003, SCALE-001/002, PARITY-001).
- [x] **C2 — Evidence capture**: Run targeted selector + `--collect-only` with `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md`, store logs/metrics under this initiative's report, and record metrics in the Attempt entry.
- [x] **C3 — Ledger updates**: Append Attempts History entry in `docs/fix_plan.md` with command, metrics, artifacts, and findings applied; ensure initiative status reflects progress. (Entry: `docs/fix_plan.md` 2025-11-04T041500Z implementation)
