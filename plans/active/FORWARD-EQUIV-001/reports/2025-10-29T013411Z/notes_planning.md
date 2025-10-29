# FORWARD-EQUIV-001 Planning Notes — 2025-10-29T013411Z

## Reality Check
- TORCH-BRIDGE-001 and TORCH-CLI-003 exit criteria satisfied; artifacts provide bridge smoke metrics (`plans/active/TORCH-BRIDGE-001/reports/2025-10-28T230500Z/smoke_metrics.json`) and CLI diagnostics (`plans/active/TORCH-CLI-003/reports/2025-10-29T003751Z/summary.md`).
- PARITY-HARNESS-002 Phase A delivered manifest scaffolding under `tests/dbex/test_db_at_001_parity.py`; selector DB_AT_001 currently exercises manifest integrity only (no forward pass).
- `docs/forward_equivalence.md` and `docs/spec-db-conformance.md` define acceptance thresholds (median ROI corr ≥0.2, ≥90% localization) and artifact layout.
- Torch backend remains stubbed (`dbex/refine_one.py:_stub_bragg_tensor`), so forward-equivalence metrics expected to miss thresholds; test must xfail with diagnostics per spec §4.

## Key References
- `docs/forward_equivalence.md:1-98`
- `docs/spec-db-conformance.md:1-40`
- `docs/TESTING_GUIDE.md:50-70`
- `docs/development/TEST_SUITE_INDEX.md:10-25`
- Findings: CONFORMANCE-001, CONFIG-001, MASKING-001, TESTING-003

## Proposed Harness Shape
1. Reuse `tests/dbex/test_nanobrag_smoke.py` fixtures for DataLoad and bridge inputs; extend to return DiffBragg forward via `dbex.run_diffbragg`.
2. Introduce metrics helper that ingests DiffBragg/Torch tensors + loss mask and returns correlation/MSE/RMSE/max|Δ|/sum ratio per ROI.
3. Persist artifacts under `plans/active/FORWARD-EQUIV-001/reports/<ts>/forward_equiv/` (legacy/, torch/, metrics.json, roi_metrics.csv, overlays/, traces/).
4. Implement pytest `DB_AT_001` that xfails when thresholds fail but still records metrics/artifact path in log message to satisfy ledger policy.

## Open Questions / Risks
- DiffBragg forward invocation requires valid ROI background/parameters; need to confirm `DataLoad` fixture provides enough context without refinement.
- Stub torch tensor is random; consider seeding RNG to make metrics deterministic for reproducibility.
- Need coordination with PARITY-HARNESS-002 so manifest tests coexist with forward-equivalence suite (possibly separate module or mark subset with `pytest.mark.manifest`).
- Ensure artifact directory creation uses repo-relative path and is cleaned or ignored by `.gitignore`.

## A1 Reality Check — Asset Verification (2025-10-29T013411Z)

### Required Files Status
All required refGeom assets confirmed present in project root:
- `refGeom.expt` (5,169 bytes) ✓
- `refGeom.refl` (205,852 bytes) ✓
- `scaled.mtz` (2,927,468 bytes) ✓

### Asset Availability
✓ All required files exist and have non-zero size
✓ No fallback steps from README:60-90 required
✓ Assets generated from prior runs (TORCH-BRIDGE-001 used these successfully)

### Artifact Directory Structure
Created artifact structure per `docs/forward_equivalence.md:54-74`:
```
plans/active/FORWARD-EQUIV-001/reports/2025-10-29T013411Z/forward_equiv/
    legacy/      # DiffBragg forward Bragg tensor + config
    torch/       # nanobrag_torch stub Bragg tensor + config
    metrics/     # (moved to root of forward_equiv/)
    overlays/    # diff/residual heatmaps
    traces/      # optional trace logs
```

### Next Steps
Proceed to A2-A4: Capture baseline tensors from both DiffBragg and torch stub paths using existing bridge infrastructure.

