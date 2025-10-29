# NANOBRAG-GOLDEN-001 Planning Notes (2025-10-29T074423Z)

## Reality Check
- `tests/fixtures/golden_data/simple_cubic/manifest.json` still advertises `simple_cubic_fallback`; no canonical tensors exist.
- `nanobrag_torch` imports cleanly in the frozen simtbx environment; canonical torch capture is unblocked.
- DiffBragg canonical capture log (2025-10-29T063817Z/canonical_capture.log) still shows `GPUassert: invalid argument` at diffBraggCUDA.cu:708 despite `simtbx_diffBragg_ext.so` rebuild evidence; need fresh verification post-patch.
- ROI bbox catalog (282 entries) and legacy ROI HDF5 (92 groups) inventories are available for downstream parity alignment.

## Plan Sketch
1. Re-run DiffBragg forward-only capture using `capture_diffbragg_only.py` with the rebuilt extension to confirm whether DIFFBRAGG-001 is resolved in practice; persist logs/artifacts under `.../golden_dataset/legacy/full_panel/`.
2. If DiffBragg succeeds, execute `capture_torch_only.py` to emit canonical `[panel, slow, fast]` tensors via `nanobrag_torch`, recording metrics and config snapshots under `.../golden_dataset/torch/`.
3. Reconcile ROI counts (282 vs 92) with supervisor guidance; update manifest delta outline accordingly if full-panel canonical dataset is accepted.
4. Refresh DB_AT_001 parity/forward pytest runs (full execution + collect-only) to capture metrics after canonical data swap; update TESTING_GUIDE and TEST_SUITE_INDEX using new artifact paths.
5. Draft ledger/doc updates (fix_plan Attempts History, findings extensions) contingent on DiffBragg verification outcome.

## Open Questions
- Does supervisor prefer full 282-ROI coverage or subset aligning with 92 ROI legacy baseline?
- Should DIFFBRAGG-001 finding be amended if rebuilt extension resolves the CUDA assert during standalone forward capture?

