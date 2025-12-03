Summary: Normalize the reconstruction cold-path mask handling so it matches Stage A/mapping, then prove parity with the intensity probe and DB-AT-028/029 artifacts.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: main
Mapped tests: tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity; tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-11T230000Z/

Do Now:
- Implement: dbex/refinement/reconstruction.py::build_final_bragg_from_stage_a_telemetry — after each `create_detector_config` call, mirror Stage A’s mask normalization by moving `detector_config.mask_array` onto `config.device`/`torch.float32` (if not already) and pass it into `create_unified_simulator(..., mask_array=detector_config.mask_array)` so CUDA runs preserve trusted-mask gating; keep the coverage guard and avoid touching the warm-cache branch.
- Implement: plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_simulator_outputs.py (optional instrumentation) — if needed, extend the JSON output with the new `normalized_mask_in_use` flag so future diagnostics can assert the masks are applied. Skip if the existing logging already shows mask parity once reconstruction is fixed.
- Validate parity: rerun the intensity probe on the small detector dataset and capture JSON/logs under the new artifact directory; ensure `cross_path_ratios.stage_a_vs_reconstruction` and `.reconstruction_vs_mapping` collapse to ≈1.0 before proceeding to pytest.
- Run mapped selectors with full artifact capture (DB-AT-028/029) using the canonical env vars so we can confirm chi²/pixel ≤1e2 and median ROI correlation ≥0.2; tee pytest output into the artifact directory and keep the Stage A DEBUG printouts.

How-To Map:
1. Code edits — update `dbex/refinement/reconstruction.py` as described under Implement. Mimic the Stage A context (`stage_a_utils.py:247-308`) by checking `detector_config.mask_array` for `torch.Tensor` and calling `.to(device=config.device, dtype=torch.float32)` before invoking the factory. Then pass that tensor to `create_unified_simulator` via the `mask_array` parameter so helpers.py’s normalization branch executes even when `DetectorConfig` was built on CPU.
2. (Optional) If you enhance the probe logging, adjust `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_simulator_outputs.py` accordingly and keep the diff small; otherwise skip.
3. Rebuild intensity evidence:
```
ART=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-11T230000Z
mkdir -p "$ART"
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_simulator_outputs.py \
  --detector-size small \
  --device cpu \
  --output "$ART/simulator_intensity_metrics.json" \
  | tee "$ART/compare_simulator_outputs.log"
```
   Inspect the JSON; both `stage_a_vs_reconstruction` and `reconstruction_vs_mapping` ratios should be within ±1% of 1.0. If not, dump the `normalized_mask` stats before debugging further.
4. Re-run the parity selectors (full-detector smoke size) with artifact capture:
```
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBAT028_ARTIFACT_DIR="$ART/db_at_028" \
DBAT029_ARTIFACT_DIR="$ART/db_at_029" \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" \
  | tee "$ART/pytest_db_at_028_029.log"
```
   Make sure both selectors collect (no skips) and record the DEBUG block that prints `mask coverage` and `scale_factor`; chi²/pixel must fall ≤1e2 and median ROI correlation ≥0.2 per spec.
5. Drop the refreshed JSON/log paths into `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-11T230000Z/summary.md` so the ledger has a quick pointer.

Pitfalls To Avoid:
- Do not reintroduce the explicit `* sqrt_spot_scale` multiplication in reconstruction; scaling must remain solely through `log_scale_clamped` per SCALE-009.
- Keep mask normalization device-neutral: use `config.device` (CUDA vs CPU) and avoid hardcoding `torch.device("cuda:0")`.
- Leave the warm-cache branch untouched; fixes belong in the cold-path code that currently builds fresh detector configs.
- Preserve the coverage guard (≥50% trusted pixels) and logging so we can tell if future masks are skipped.
- Respect Environment Freeze: no package installs or nanobrag_torch edits—changes stay inside dbex/ scripts.
- Keep intensity probe output under the artifact directory; don’t overwrite prior evidence in other timestamps.

If Blocked:
- If the mask normalization still yields `normalized_mask is None`, capture the debug print (panel id, mask dtype/device) and add it to `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-11T230000Z/blockers.md`, then update `docs/fix_plan.md` + `galph_memory.md` with the error signature.
- If DB-AT-028/029 continue to fail despite ratios=1.0, record the new chi²/ROI numbers, stash the pytest log + metrics JSON, and halt; we may need a follow-up initiative (spec-change or calibration) instead of further tweaks.

Findings Applied (Mandatory): CLI-001 (trusted mask tensors must be normalized before DetectorConfig construction, so reconstruction must match Stage A’s `.to(device)` logic); SCALE-009 (reconstruction scaling stays in `log_scale_clamped`, so fixes cannot reintroduce the discarded `sqrt_spot_scale` multiplication).

Pointers:
- dbex/refinement/reconstruction.py:200 — cold-path detector loop and `create_unified_simulator` call site that needs mask normalization.
- dbex/refinement/stage_a_utils.py:247 — reference implementation showing how Stage A normalizes `detector_config.mask_array` before instantiating simulators.
- dbex/refinement/helpers.py:108 — `create_unified_simulator` normalization branch; passing `mask_array` allows it to move tensors onto the simulator device.
- plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-11T200000Z/callchain/static.md — detailed callchain notes driving this Do Now.

Next Up (optional): If this fix lands quickly, re-run the full-detector (DBEX_SMOKE_DETECTOR_SIZE=full) variant of DB-AT-028/029 to ensure the mask pipeline scales, then revisit whether Stage A baseline needs the mapping-derived log-scale override noted under SCALE-008.
