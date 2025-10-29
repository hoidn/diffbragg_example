# NANOBRAG-GOLDEN-001 Planning Notes (2025-10-29T023547Z)

## Reality check
- Confirmed existing golden data under `tests/fixtures/golden_data/simple_cubic/` carries `FALLBACK` provenance and synthetic Gaussian Bragg tensor.
- Verified refGeom inputs (`refGeom.expt`, `refGeom.refl`, `scaled.mtz`) are present in repo root for canonical dataset generation.
- No `nanoBragg2` dataset captured yet; `scripts/generate_simple_cubic_golden.py` still uses stub predictions.

## Key references
- `docs/spec-db-core.md:20-41` — tensor ordering, detector geometry, mask contracts.
- `docs/spec-db-conformance.md:23-26` — DB_AT_001 thresholds and selector requirements.
- `docs/forward_equivalence.md:21-52` — forward pass procedure and diagnostics.
- `plans/nanobrag_integration_plan.md:23-88` — bridge responsibilities and simulator invocation guidance.
- `docs/TESTING_GUIDE.md:74-85`, `docs/development/TEST_SUITE_INDEX.md:13-14` — parity harness selectors and artifact policy.

## Risks & assumptions
- Access to `nanobrag_torch` runtime is required; confirm installation path or coordinate acquisition before implementation.
- Structure-factor source for canonical dataset must be documented (DiffBragg output vs HKL file); ensure reproducible script.
- Parity thresholds may still fail if simulator gap persists; plan for conditional xfail rationale if canonical dataset exposes divergence.

## Next steps
1. Flesh out implementation checklist (A1-D3) in `plans/active/NANOBRAG-GOLDEN-001/implementation.md`.
2. Draft `input.md` Do Now covering dataset capture, manifest update, and docs/test sync.
3. Coordinate with engineer on `nanobrag_torch` environment validation and generator script updates.
