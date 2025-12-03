Summary: Capture Stage-A scale diagnostics so we know why DB-AT-028/029 still fail even after the mask fix, then rerun the selectors with fresh evidence.
Mode: none
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: integration
Mapped tests: tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity; tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-12T010000Z/

Do Now:
- Implement: `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_stage_a_scale_alignment.py` (Tier‑2 script) that (a) loads the refGeom_small dataset via `tests.dbex.test_torch_refine_smoke.refgeom_dataload`, (b) builds a mapping context with `build_mapping_stage_a_context`, (c) runs `create_perturbed_geometry` + `simulate_forward_once` to mimic the Stage‑A smoke fixture, and (d) records masked/unmasked means, `RefinementInputs.global_scale_hint`, and telemetry log-scale values for both the zero-iteration stack and the reconstruction helper. Emit a JSON summary (e.g., `stage_a_scale_alignment.json`) and a short Markdown note in the new report directory.
- Evidence: Rerun `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_simulator_outputs.py` with the current small-detector calibration (`sp.proc/calibration/config_torch_smoke_small.json`) and stash the JSON/log under the 2025-12-12T010000Z artifact tree so we know raw outputs are still aligned after the calibration refresh.
- Validate selectors: Execute DB-AT-028/029 with the canonical smoke env vars and point `DBAT028_ARTIFACT_DIR`/`DBAT029_ARTIFACT_DIR` at the new report directory so the metrics, mapping context fixtures, and DEBUG blocks are captured together.
- Summarize: append a short `summary.md` in `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-12T010000Z/` noting the probe outputs, parity ratios, and the latest chi²/ROI numbers so the fix-plan Attempts History can cite a single pointer.

How-To Map:
1. Stage-A scale probe (run on CPU for determinism):
```
ART=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-12T010000Z
mkdir -p "$ART"
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_DETECTOR_SIZE=small \
DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_stage_a_scale_alignment.py \
  --detector-size small \
  --calibration-config sp.proc/calibration/config_torch_smoke_small.json \
  --device cpu \
  --out-dir "$ART/scale_probe" \
  | tee "$ART/scale_probe.log"
```
   The script should write `scale_probe/stage_a_scale_alignment.json` with masked/unmasked means, scale ratios, and telemetry values for mapping vs. reconstruction.
2. Reconfirm raw parity with the latest calibration:
```
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_DETECTOR_SIZE=small \
DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_simulator_outputs.py \
  --detector-size small \
  --device cpu \
  --output "$ART/simulator_intensity_metrics.json" \
  | tee "$ART/compare_simulator_outputs.log"
```
3. Run the mapped selectors with artifact capture:
```
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_DETECTOR_SIZE=small \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json \
DBAT028_ARTIFACT_DIR="$ART/db_at_028" \
DBAT029_ARTIFACT_DIR="$ART/db_at_029" \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" \
  | tee "$ART/pytest_db_at_028_029.log"
```
   Confirm both selectors collect (no skips) and stash the emitted `db_at_028_metrics.json` / `db_at_029_metrics.json` under the artifact subdirectories called out above.
4. Summarize: add a short bullet list to `$ART/summary.md` pointing at `scale_probe`, the intensity metrics JSON, and the pytest log so Galph can cite a single report entry.

Pitfalls To Avoid:
- Do not touch production code paths outside the new probe; limit edits to the plan-scoped script and keep reconstruction logic untouched this loop.
- Reuse the same calibration + HKL assets as the Stage-A smoke fixture (set `DBEX_SMOKE_CALIB_PATH` / `DBEX_SMOKE_HKL_PATH`), otherwise the probe data won’t match the pytest setup.
- Stay in ADU mode (leave `adu_per_photon=None`) so target and model means are comparable; do not introduce photon conversion in the probe.
- Ensure the probe runs on CPU (device flag) to avoid CUDA nondeterminism that could mask small ratio deltas.
- Keep artifact directories isolated per timestamp; do not overwrite the 2025-12-11 evidence.
- Remember to export `KMP_DUPLICATE_LIB_OK=TRUE` / `NANOBRAGG_DISABLE_COMPILE=1` before invoking pytest so grad/chi² traces remain deterministic.

If Blocked:
- If the probe still reports `target_mean / bragg_mean ≈ 1` yet DB-AT-028 fails, capture the JSON + log and flag ARCH-SIM-CONSTRUCTION-001 as suspecting a spec/test mismatch in `docs/fix_plan.md` Attempts History.
- If pytest skips because `DBAT028_ARTIFACT_DIR` / `DBAT029_ARTIFACT_DIR` aren’t writable, create the directories, rerun collection, and log the failure signature in `$ART/blockers.md` before stopping.
- If the intensity probe ratios drift again, stop and record the diverging values; do not chase DB-AT tolerances until raw parity is re‑established.

Findings Applied (Mandatory): SCALE-001 (docs/findings.md:33) — keep the scaling analysis bounded to the documented spot_scale override contract; PHYSICS-LOSS-001 (docs/findings.md:35) — when inspecting chi² traces, ensure we keep the variance-weighted definition intact and capture the full telemetry.

Pointers:
- docs/spec-db-workflow.md:33 — Calibration & Unit Conventions describing spot_scale and ADU vs photon policy.
- docs/config_crosswalk.md:145 — notes on post-sim scaling in ADU mode that the probe must respect.
- docs/findings.md:33 — SCALE-001 background on avoiding double spot-scale application.
- dbex/vis/mapping.py:120 — `build_mapping_stage_a_context` logic the probe should call to mirror DB-AT inputs.
- plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-11T230000Z/db_at_028/db_at_028_metrics.json — latest failing metrics for comparison.

Next Up (optional): Once the scale probe identifies the divergence, either (a) patch the offending Stage A helper or (b) open a spec-change initiative if telemetry proves the DB-AT gates are inconsistent with the calibrated targets.
