Summary: Verify DiffBragg forward capture with the patched simtbx build and stage canonical torch tensors for NANOBRAG-GOLDEN-001.
Mode: Parity
Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
Branch: integration
Mapped tests: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001; KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001
Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T074423Z/{planning_notes.md,golden_dataset/legacy/,golden_dataset/torch/,golden_dataset/logs/,metrics/}
Do Now:
  1. NANOBRAG-GOLDEN-001::A2 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Copy `capture_forward.py` + helpers into the new report directory and rerun the DiffBragg baseline capture; persist stdout to `golden_dataset/logs/diffbragg_forward.log` and stash any full-panel tensors under `golden_dataset/legacy/full_panel/`; tests: none — evidence-only.
  2. NANOBRAG-GOLDEN-001::A3 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Execute `capture_torch_only.py` in the new report directory to emit canonical `[panel, slow, fast]` tensors and ROI metrics (`metrics/canonical_forward.json`, ROI CSV); tests: none — evidence-only.
  3. NANOBRAG-GOLDEN-001::D1 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Run DB_AT_001 parity + forward pytest selectors against the staged tensors, archive run/collect-only logs, and update docs/test registries with the new artifact paths; tests: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001; KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001; KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001; KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001.
Priorities & Rationale:
- docs/spec-db-core.md:20-33 — Canonical dataset must deliver `[panel, slow, fast]` tensors and bbox-aligned ROIs, so DiffBragg baseline verification is mandatory before manifest swap.
- docs/forward_equivalence.md:21-66 — Forward equivalence workflow requires paired DiffBragg/torch outputs plus metrics, guiding the A2/A3 capture tasks.
- docs/spec-db-conformance.md:23-26 — Acceptance profile DB-AT-001 mandates pytest coverage and artifact logging once canonical tensors exist.
- docs/nanobrag_api.md:28-45 — Torch capture must honor beam center swapping, mask alignment, and square pixel constraints when emitting tensors.
- docs/TESTING_GUIDE.md:63-70 — Selector registry updates depend on fresh collect-only logs tied to artifact paths from this loop.
- docs/findings.md (CONFIG-001, PARITY-001, DIFFBRAGG-001) — Existing lessons define hydration guardrails, ROI ordering expectations, and the need to confirm the CUDA fix before relying on DiffBragg forward outputs.
How-To Map:
- `cp plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T063817Z/capture_forward.py plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T074423Z/`
- `cp plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T063817Z/capture_diffbragg_only.py plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T074423Z/`
- `cp plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T063817Z/capture_torch_only.py plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T074423Z/`
- `cp plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T030352Z/golden_dataset/legacy/dbex_diffbragg_gpu.h5 plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T074423Z/golden_dataset/legacy/dbex_diffbragg_gpu.h5`
- `KMP_DUPLICATE_LIB_OK=TRUE libtbx.python plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T074423Z/capture_forward.py |& tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T074423Z/golden_dataset/logs/diffbragg_forward.log`
- `KMP_DUPLICATE_LIB_OK=TRUE libtbx.python plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T074423Z/capture_torch_only.py |& tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T074423Z/golden_dataset/logs/torch_forward.log`
- `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001 |& tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T074423Z/tests_db_at_001_parity.log`
- `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001 |& tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T074423Z/tests_db_at_001_forward.log`
- `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001 |& tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T074423Z/collect_db_at_001_parity.log`
- `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001 |& tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T074423Z/collect_db_at_001_forward.log`
- Document doc/test updates in `docs/TESTING_GUIDE.md` §2.1 and `docs/development/TEST_SUITE_INDEX.md` with the new artifact timestamps.
Pitfalls To Avoid:
- Do not trust prior diffBragg logs; rerun capture with the patched `.so` before copying tensors.
- Avoid mixing outputs across report directories; ensure all new artifacts live under 2025-10-29T074423Z.
- Preserve ROI ordering when generating metrics to remain compliant with PARITY-001 tracing.
- Keep `nanobrag_torch` runs deterministic (`torch.manual_seed(1337)`, single GPU) to avoid numeric drift between attempts.
- Monitor GPU memory; free torch tensors between panels to prevent OOM during full-panel capture.
- Retain `_temp.mtz` outputs for provenance until manifest updates have checksums recorded.
- Do not modify environment or reinstall packages; treat failures as blockers per Environment Freeze.
- Archive raw stdout/stderr for each long-running command under `golden_dataset/logs/` to satisfy documentation requirements.
- Confirm loss mask dtype before writing metrics to avoid boolean→float coercion bugs noted in CONFIG-001.
- Update fix_plan Attempts History with Metrics/Artifacts placeholders before closing the loop.
Environment: Frozen simtbx environment (`python` from conda env); no package installs or rebuilds permitted this loop. If a required import fails, stop the loop, record the blocker, and mark the initiative blocked per policy.
If Blocked: Capture the failure log under 2025-10-29T074423Z/golden_dataset/logs/, append a `blocked` Attempt in docs/fix_plan.md with Metrics/Artifacts placeholders, update galph_memory next_action to `switch_focus`, and notify supervisor that canonical capture remains blocked by DIFFBRAGG-001 regression.
Findings Applied (Mandatory):
- CONFIG-001 — Torch capture commands reuse bridge hydration helpers to maintain dxtbx→torch mapping fidelity.
- PARITY-001 — ROI metrics generation preserves deterministic ordering for first-divergence tracing.
- DIFFBRAGG-001 — Revalidates the CUDA cleanup fix before consuming DiffBragg outputs.
- TESTING-003 — Plans explicit collect-only runs + doc sync so Active selectors stay truthful.
Doc Sync Plan (Mandatory):
- DB_AT_001 parity selector — `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001 |& tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T074423Z/collect_db_at_001_parity.log` (update docs/TESTING_GUIDE.md §2.1 + TEST_SUITE_INDEX DB_AT table).
- DB_AT_001 forward equivalence selector — `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001 |& tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T074423Z/collect_db_at_001_forward.log` (refresh docs/TESTING_GUIDE.md §2.1 + TEST_SUITE_INDEX implementation coverage/DB-AT entries).
