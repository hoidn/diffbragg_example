# RUNTIME-VEC-001 Planning Notes — 2025-11-04T074738Z

## Focus
Plan the port of the nanoBragg2 source-weight runtime guard (`TestSourceWeights*`) into DBEX so the runtime vectorization selector becomes Active in the acceptance matrix.

## Key Observations
- Runtime checklist item §4 (`docs/pytorch_runtime_checklist.md:31-40`) still references the nanoBragg2 suite; DBEX lacks an equivalent test despite the selector row remaining Planned in `docs/TESTING_GUIDE.md:72` and `docs/development/TEST_SUITE_INDEX.md:28`.
- Upstream reference implementation lives at `../nanoBragg/tests/test_cli_scaling.py` (`TestSourceWeights` + `TestSourceWeightsDivergence`) and validates spec-a-core equal weighting thresholds (correlation ≥0.999, |sum_ratio−1| ≤5e-3) by invoking `python -m nanobrag_torch` with crafted sourcefiles.
- Environment freeze allows reuse of the packaged `nanobrag_torch` CLI; the test can operate via temporary directories without touching asset-heavy fixtures.
- Existing findings RUNTIME-001 and SCALE-001/002 remain relevant; no new findings yet but port must continue to assert equal weighting semantics and record metrics on divergence.

## Reality Check
No fix-plan item currently tracks this gap; create `RUNTIME-VEC-001` with dependencies on the runtime checklist + architecture notes, then stage an implementation Do Now for Ralph covering the initial test port and documentation sync.

## Next Actions
1. Add `RUNTIME-VEC-001` entry to `docs/fix_plan.md` (status=in_progress) with exit criteria covering test port, artifact capture, and documentation sync.
2. Draft `input.md` instructing Ralph to implement the DBEX test module, run targeted pytest/collect commands with artifacts under `plans/active/RUNTIME-VEC-001/reports/<timestamp>/`, and update docs accordingly.
3. Capture relevant CLI commands (baseline `python -m nanobrag_torch --help`) during implementation to confirm availability; treat missing CLI as blocker per Environment Freeze policy.
