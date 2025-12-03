# Phase D Trace Script Plan — 2025-12-03T130945Z

## Goal
Formalize the manual `simulator_trace.log` run (2025-12-03T064931Z) into a rerunnable Tier‑2 script that reproduces the crystal/unit mismatch evidence without hand editing nanobrag_torch. The script must emit both the raw TRACE_PY log and parsed metrics that prove the dot products are being computed with mismatched units (meters vs Å).

## Scope
- Script path: `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/bin/trace_simulator_mismatch.py`
- Inputs: cropped smoke fixtures (`sp.proc/refGeom_small/…`), refined MTZ (`sp.proc/calibration/smoke_refined_structure_factors_small.mtz` fallback `scaled.mtz`), calibration metadata when available, and trusted mask (`refGeom_small_mask.pkl`). No external downloads.
- Execution: CPU only, `KMP_DUPLICATE_LIB_OK=TRUE` and `NANOBRAGG_DISABLE_COMPILE=1` to match current diagnostics posture. Target pixel defaults to (fast=0, slow=0) but CLI flags should exist for other coordinates.
- Outputs per run (under timestamped reports dir supplied via `--out-dir`):
  1. `simulator_trace.log` — captured stdout from `Simulator.run()` with `printout=True`, `trace_pixel=[slow, fast]`.
  2. `simulator_trace_metrics.json` — parsed vectors (scattering, rot_a/b/c, hkl_frac/rounded) plus derived magnitudes and corrected dot products showing the 1e10 scale error.
  3. `crystal_unit_analysis.md` — short prose summary referencing the JSON metrics and citing `docs/spec-db-core.md §Units` + `DIAG-UNIT-001` finding.

## Implementation Notes
- Reuse `DataLoad` + `build_mapping_stage_a_context` from `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_simulator_outputs.py` to stay aligned with smoke fixtures and calibration precedence (see `docs/data_dependency_manifest.md:36-110`).
- Build Stage A warm cache with `_build_stage_a_context` and `RefinementConfig(oversample=3)` so cached simulators match the oversample threading fix.
- Instead of reconstructing configs manually, repurpose the cached simulator: set `simulator.debug_config = {"printout": True, "trace_pixel": [slow, fast]}` and update `simulator.printout` / `simulator.trace_pixel` fields before calling `run()` to avoid re-instantiation churn.
- Capture stdout via `contextlib.redirect_stdout` so the same command produces both the console log and the parsed metrics; parsing should use deterministic regexes (`TRACE_PY:` prefix) to avoid brittle string splitting.
- Derived metrics to include:
  * `scattering_vec_m_inv_norm` and `rot_a_vector_norm_reported` (shows q ≈ 5.8e9 m⁻¹ vs |a| ≈ 3.4e-9 labeled as “Å”).
  * `hkl_frac_raw` direct from trace (≈3e-9) plus `hkl_frac_corrected = raw * 1e10` to show the dot product would land in-range if real vectors stayed in Å.
  * `dot_raw` (`q_ang^-1 · a_m`) vs `dot_corrected` (`dot_raw * 1e10`) for transparency.
- CLI flags:
  * `--detector-size {small,full}` (default `small`) — choose dataset bundle.
  * `--trace-fast`, `--trace-slow` — pixel coordinates.
  * `--device` (default `cpu`).
  * `--out-dir` — required path to drop artifacts; script should create the directory.
- Validation command (to hand Ralph):
  ```bash
  AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
  DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_SIGMA_SOURCE=metadata \
  KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
  python plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/bin/trace_simulator_mismatch.py \
    --detector-size small --trace-fast 0 --trace-slow 0 --device cpu \
    --out-dir plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T130945Z/
  ```
- After the run, update `docs/findings.md` (DIAG-UNIT-001 row) with the new artifact path and mention that the parsing JSON quantifies the 1e10 mismatch so future loops can cite it directly.
