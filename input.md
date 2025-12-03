Summary: Align the reconstruction cold path with Stage A by threading panel trusted masks into `create_detector_config`, rerun the simulator comparison probe to prove the raw magnitudes now match, and execute DB-AT-028/029 with artifact dirs so the selectors collect after the fix.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: integration
Mapped tests: tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity, tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-03T161601Z/

Do Now:
- Implement: `dbex/refinement/reconstruction.py::build_final_bragg_from_stage_a_telemetry` — when building detector configs in the cold path, pass the per-panel trusted mask (`inputs.trusted_mask[pid]`) into `create_detector_config` so reconstruction zeroes untrusted pixels the same way Stage A warm cache does; guard against `inputs.trusted_mask` being `None`.
- Capture: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_simulator_outputs.py --detector-size small --device cpu --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-03T161601Z/simulator_intensity_metrics.json` — expect the cross-path raw ratios to collapse to ≈1.0; keep the generated summary.md in the same directory.
- Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-03T161601Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-03T161601Z/db_at_029 DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-03T161601Z/pytest_db_at_028_029.log` — artifact dirs stop the selectors from skipping and retain metrics for review.

How-To Map:
1. `ARTIFACTS=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-03T161601Z && mkdir -p "$ARTIFACTS" "$ARTIFACTS/db_at_028" "$ARTIFACTS/db_at_029"`
2. Edit `dbex/refinement/reconstruction.py` so the cold-path `create_detector_config` call includes `trusted_mask=inputs.trusted_mask[pid]` when that array exists, and keep the warm-cache branch untouched.
3. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_simulator_outputs.py --detector-size small --device cpu --output "$ARTIFACTS/simulator_intensity_metrics.json"`
4. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT028_ARTIFACT_DIR="$ARTIFACTS/db_at_028" DBAT029_ARTIFACT_DIR="$ARTIFACTS/db_at_029" DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee "$ARTIFACTS/pytest_db_at_028_029.log"`

Pitfalls To Avoid:
- Stay within the repo; do not patch or reinstall `nanobrag_torch` (Environment Freeze).
- Only modify the reconstruction cold path—Stage A warm cache already handles masks correctly.
- Ensure mask arrays remain boolean/float tensors (0/1) so Simulator masking matches spec.
- Keep the oversample override (`oversample=3`) untouched and continue using the small-detector smoke fixture for deterministic results.
- Run pytest with the new `DBAT028_ARTIFACT_DIR`/`DBAT029_ARTIFACT_DIR` env vars; without them the selectors will skip again.

If Blocked:
- If `inputs.trusted_mask` is unexpectedly `None`, capture that state in `$ARTIFACTS/blocked.md` (include repr of `inputs`), update `docs/fix_plan.md` + `galph_memory.md`, and pause implementation.
- If the smoke assets are missing or pytest fails before collecting the Stage A tests, save the full traceback to `$ARTIFACTS/blocked.md` and stop; do not weaken selectors or patch dependencies.

Findings Applied:
- SCALE-009 — Reconstruction helpers must mirror Stage A’s scaling/masking conventions; passing the trusted mask keeps the cold path compliant.
- DIAG-OVERSAMPLE-001 — Keep oversample explicitly at 3 so we isolate the masking fix and avoid re-triggering auto-selection bugs already documented.

Pointers:
- docs/spec-db-core.md:34 — Trusted mask contract (True = include) and shape requirements we must honor when passing masks to the simulator.
- docs/spec-db-core.md:109 — Loss/masking semantics clarifying why untrusted pixels must be zeroed before computing chi².
- dbex/refinement/reconstruction.py:187 — Cold-path detector construction that needs the trusted-mask plumbing.
- plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-09T210000Z/summary.md — Evidence showing the 18% raw magnitude gap that this fix addresses.
