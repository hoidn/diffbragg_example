# MAP-SCALE-001 Supervisor Loop Summary (2025-11-04T130000Z)

## Focus
- Align zero-iteration mapping outputs with DiffBragg-calibrated targets so DB_AT_024 can assert corr ≥ 0.2 and localization ≥ 0.90.

## Evidence Reviewed
- `plans/active/MAP-SCALE-001/reports/2025-11-04T120500Z/summary.md` & `blockers.md` — refined MTZ plumbing complete; thresholds still failing because test uses unrefined geometry.
- `docs/spec-db-conformance.md:44-55` — DB_AT_024 acceptance contract (corr/localization thresholds) to enforce.
- `docs/architecture.md:1-45` — DiffBragg→torch bridge expects coupled geometry + structure-factor inputs.
- `docs/findings.md` (SCALE-001/002/004) — calibration guardrails already in place; SCALE-004 missing refined-geometry clause.

## Key Observations
- Golden generator now emits `refined_structure_factors.mtz`; golden capture metrics (corr≈0.81, localization=100%) confirm DiffBragg refinement produces aligned amplitudes when geometry matches.
- DB_AT_024 still uses `refGeom.expt/refGeom.refl`, so refined Fopt are applied to an incompatible geometry, leaving corr≈0.0352 and localization=0% (artifact: `.../2025-11-04T120500Z/mapping_metrics.json`).
- Generator manifest still reports `experiment_source="refGeom.expt"`; fixtures lack refined `.expt/.refl`, so Ralph must propagate them to keep fixtures + manifest internally consistent.

## Decision
Adopt blockers.md Option 1: persist the DiffBragg-refined experiment/reflection set alongside the refined MTZ and update DB_AT_024 to consume the refined geometry.

## Implementation Guidance (hand-off to Ralph)
1. **Extend generator persistence:** In `scripts/generate_simple_cubic_golden.py::generate_simple_cubic_golden`, copy the refined experiment (`*_refined.expt`) and reflections (`*_refined.refl`) emitted by DiffBragg to both the canonical output (`torch/`) and `--fixtures` directory. Update manifest/metadata provenance fields to cite the refined assets. Keep MANIFEST-001 validations intact.
2. **Load refined assets in DB_AT_024:** In `tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::canonical_assets`, prefer the refined experiment/reflections from fixtures when present (fall back to legacy assets if missing) so `prepare_refinement_inputs` receives geometry consistent with the refined MTZ.
3. **Fixture hygiene:** After regeneration with `--fixtures`, ensure `tests/fixtures/golden_data/simple_cubic/` contains the refined `.expt/.refl/.mtz`. Leave legacy `refGeom.*` in repo root for backward compatibility; document selection logic in the fixture.
4. **Finding update:** Promote SCALE-004 to note the refined-geometry dependency (captured in this loop).

## Validation Targets
- Regenerate fixtures (authoritative command below) to refresh refined assets + manifest.
- Run targeted selector: `pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke --maxfail=1` with `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md` and existing env flags; expect PASS meeting thresholds.
- Optional confidence: `pytest --collect-only -k DB_AT_024` to confirm selector discovery after fixture swap.

## Next-Loop Inputs
Use this summary plus the updated finding + fix-plan entry to populate `input.md` for Ralph. Commands for Ralph (see How-To map):
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
python scripts/generate_simple_cubic_golden.py \
  --canonical-out plans/active/MAP-SCALE-001/reports/2025-11-04T130000Z/refined_capture \
  --emit-manifest \
  --fixtures tests/fixtures/golden_data/simple_cubic
```
(Artifacts from this rerun should be copied into `.../2025-11-04T130000Z/refined_capture/`.)
