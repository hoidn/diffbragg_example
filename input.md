Summary: Fix the nanobrag_torch incident-beam convention so Stage-A HKL queries fall inside the refined grid and DB-AT-028/029 can converge again.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-SIM-HKL-BOUNDS-001 — Stage-A / mapping HKL alignment
Branch: integration
Mapped tests:
- pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028"
- pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_029"
Artifacts: plans/active/ARCH-SIM-HKL-BOUNDS-001/reports/2025-12-03T154217Z/

Do Now:
- Implement: src/nanobrag-torch/src/nanobrag_torch/simulator.py::__init__ — store the incident beam unit vector as the SOURCE→SAMPLE direction by negating `detector.beam_vector`, update the default-without-detector fallback accordingly, and refresh the nearby comment so it cites docs/spec-db-core.md (§Detector conventions) plus DIAG-OVERSAMPLE-001. After editing, capture the patch per Environment Freeze rules (save `git diff -- src/nanobrag-torch/src/nanobrag_torch/simulator.py` to `plans/active/ARCH-SIM-HKL-BOUNDS-001/reports/2025-12-03T154217Z/patches/incident_beam_direction_fix.patch`) and mention the rebuild/test commands in summary.md.
- Document: plans/active/ARCH-SIM-HKL-BOUNDS-001/implementation.md Phase B, docs/fix_plan.md (ARCH-SIM-HKL-BOUNDS-001 Attempts), and docs/findings.md (DIAG-OVERSAMPLE-001 row) with the new root-cause analysis, patch reference, HKL stats artifact path, and Stage-A parity status so the doc graph stays consistent.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/bin/compare_hkl_stats.py --detector-size small --out-dir plans/active/ARCH-SIM-HKL-BOUNDS-001/reports/2025-12-03T154217Z/post_fix_hkl_stats to prove ≥99% in-bounds HKL coverage for both simulate_forward_once and the Stage-A warm cache.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-HKL-BOUNDS-001/reports/2025-12-03T154217Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-HKL-BOUNDS-001/reports/2025-12-03T154217Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" and archive the pytest log + metrics JSONs under the artifacts dir; if either selector still fails, capture the failure signature and gate values.

How-To Map:
- Edit simulator: use your editor on `src/nanobrag-torch/src/nanobrag_torch/simulator.py` and ensure `self.incident_beam_direction` is always initialized with `-self.detector.beam_vector.clone()` (and `torch.tensor([-1.0,0.0,0.0])` when no detector is present) plus refresh the comment to cite docs/spec-db-core.md §Detector conventions + DIAG-OVERSAMPLE-001; run `python -m compileall src/nanobrag-torch/src/nanobrag_torch/simulator.py` if you need a quick syntax check.
- Capture the environment patch: `git diff -- src/nanobrag-torch/src/nanobrag_torch/simulator.py > plans/active/ARCH-SIM-HKL-BOUNDS-001/reports/2025-12-03T154217Z/patches/incident_beam_direction_fix.patch` after edits; list the rebuild/test commands in `plans/active/ARCH-SIM-HKL-BOUNDS-001/reports/2025-12-03T154217Z/summary.md` per Environment Freeze exception.
- HKL stats probe: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/bin/compare_hkl_stats.py --detector-size small --out-dir plans/active/ARCH-SIM-HKL-BOUNDS-001/reports/2025-12-03T154217Z/post_fix_hkl_stats`.
- Stage-A smokes: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-HKL-BOUNDS-001/reports/2025-12-03T154217Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-HKL-BOUNDS-001/reports/2025-12-03T154217Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/ARCH-SIM-HKL-BOUNDS-001/reports/2025-12-03T154217Z/pytest_db_at_028_029_post_fix.log`.

Pitfalls To Avoid:
- Do not change detector conventions or HKL grid construction—only fix the incident-beam orientation.
- Keep all edits device/dtype neutral; no CPU-only shortcuts inside simulator.
- Maintain Environment Freeze rules: no pip installs, and every nanobrag_torch edit must be captured as a patch artifact with documented commands.
- Leave multi-source code paths untouched; they already negate the beam direction correctly.
- Use the canonical smoke fixtures from docs/data_dependency_manifest.md (refGeom_small assets) and keep `DBEX_SMOKE_SIGMA_SOURCE=metadata`.
- Capture HKL stats artifacts and pytest logs inside the assigned reports directory; do not scatter evidence elsewhere.
- If Stage A tests still fail, stop after collecting logs—do not start speculative refactors or spec changes inside this loop.

If Blocked:
- If nanobrag_torch imports or the fixture data fail to load, copy the traceback into `plans/active/ARCH-SIM-HKL-BOUNDS-001/reports/2025-12-03T154217Z/blockers.log`, update docs/fix_plan.md Attempts with the error signature, and mark the initiative blocked pending environment investigation instead of proceeding.
- If HKL stats remain out-of-bounds even after the beam-direction fix, capture the JSON + summary showing the unexpected ranges, update docs/findings.md with the new evidence, and halt—this would trigger a new architecture/spec initiative rather than repeated tweaks.

Findings Applied (Mandatory):
- docs/findings.md:51 (DIAG-OVERSAMPLE-001) — adhere to the documented HKL coverage lesson by using the same fixtures/configs and recording the post-fix stats.

Pointers:
- plans/active/ARCH-SIM-HKL-BOUNDS-001/implementation.md#phase-b — current plan + Phase B checklist updates required this loop.
- docs/spec-db-core.md:54-72 — detector convention / beam vector rules that demand source→sample orientation (cite in code comment).
- src/nanobrag-torch/src/nanobrag_torch/simulator.py:520-620 — current incident-beam initialization that needs the sign fix.

Next Up:
- Once Stage A HKL coverage and DB-AT-028/029 are green, reassess ARCH-SIM-CONSTRUCTION-001 to lift the Phase D.3 block on reconstruction.
