# NANOBRAG-GOLDEN-001 — Canonical DB-AT-001 Golden Dataset

## Phase A — Canonical tensor capture
- [ ] **A1 — Environment + dependency validation**: Confirm `nanobrag_torch` editable install is available (or document acquisition plan) and verify refGeom dataset inputs (expt/refl/mtz) plus structure-factor sources exist (`docs/spec-db-core.md:20-41`, `plans/nanobrag_integration_plan.md:23-54`). Record validation log under `reports/<timestamp>/golden_dataset/`.
- [ ] **A2 — DiffBragg baseline export**: Run legacy DiffBragg forward-only pipeline to capture `bragg_diffbragg.npy`, ROI metrics, and config JSON; stash under `golden_dataset/legacy/` with command log (`docs/forward_equivalence.md:21-37`).
- [ ] **A3 — nanoBragg2 forward capture**: Invoke `nanobrag_torch` via bridge helpers to produce canonical torch `bragg` tensors for all panels, ensuring `[panel, slow, fast]` ordering and mask alignment; persist under `golden_dataset/torch/` with simulator config snapshots (`docs/nanobrag_api.md:21-83`).

## Phase B — Manifest + verification
- [ ] **B1 — Manifest & metadata update**: Rewrite `tests/fixtures/golden_data/simple_cubic/manifest.json` (or successor path) with canonical provenance fields (generator command, git rev, structure-factor source) and SHA256 checksums; update `metadata.json` with beam/detector/crystal records referencing captured configs (`docs/spec-db-conformance.md:23-26`).
- [ ] **B2 — Fixture + checksum tests**: Extend `tests/fixtures/parity_loader.py` and related pytest fixtures to validate new manifest layout (multi-panel support, canonical notes) while keeping square pixel/panel guards (`docs/TESTING_GUIDE.md:74-85`).
- [ ] **B3 — Regeneration tooling**: Update or replace `scripts/generate_simple_cubic_golden.py` with canonical generator that calls DiffBragg + `nanobrag_torch`; document usage and inputs inside the script header and in `docs/index.md` (`plans/nanobrag_integration_plan.md:32-88`).

## Phase C — Parity harness integration
- [ ] **C1 — Harness dataset swap**: Point DB_AT_001 parity tests at canonical dataset directory, remove synthetic noise injection, and compare torch output vs target/diffbragg baseline as dictated by the spec (`docs/forward_equivalence.md:46-52`, `docs/spec-db-tracing.md:15-24`).
- [ ] **C2 — Threshold enforcement**: Update parity test assertions to require correlation ≥0.2 and localization ≥0.9 (xfail only on documented simulator gaps) and ensure artifact writers log canonical manifest checksums (`docs/spec-db-conformance.md:23-26`).
- [ ] **C3 — Documentation sync**: Refresh `docs/TESTING_GUIDE.md` §2, `docs/development/TEST_SUITE_INDEX.md`, and `docs/index.md` to reflect canonical dataset availability, artifact paths, and new selector status; reference artifacts from this initiative (`docs/prompt_sources_map.json`).

## Phase D — Closure
- [ ] **D1 — Artifact archival**: Collect DiffBragg vs torch metrics, overlays, and generation logs under `plans/active/NANOBRAG-GOLDEN-001/reports/<timestamp>/golden_dataset/` with summary README.
- [ ] **D2 — Knowledge base update**: Add durable lessons (e.g., simulator invocation pitfalls, structure-factor prep) to `docs/findings.md` if not already recorded; cite source paths.
- [ ] **D3 — Ledger wrap-up**: Update `docs/fix_plan.md` Attempts History with final metrics/artifacts and transition status to `done`.
