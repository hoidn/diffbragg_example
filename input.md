Summary: Capture full-panel Stage A spot-profile energy partitions (ROI vs halo vs FWHM) so we can localize the simulator’s deterministic parity crisis before escalating to a nanobrag_torch patch.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-22T150000Z/db_at_028 DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-22T150000Z/db_at_029 DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-22T150000Z/

Do Now (hard validity contract):
- Implement: `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py::main`
  - Add `--collect-spot-profiles` (store_true) and `--spot-profile-halo-pixels` (int, default 10, clamp ≥1) CLI flags. When the flag is set, reuse the full-panel `bragg_before` tensor that `build_final_bragg_from_stage_a_telemetry` already returns to compute, for every reflection matched ROI: ROI energy, halo energy (expand bbox ±halo pixels, clamp to detector bounds), ROI fraction of halo, ROI fraction of total panel energy, halo bbox, peak value, and approximate FWHM on fast/slow axes (width of contiguous pixels ≥ 0.5 × peak).
  - Store those values back into each `reflection_roi_matches` entry plus a new JSON block `spot_profile_stats` summarizing median ROI fractions (inside vs halo vs panel), extremes (top 5 with most off-ROI energy, top 5 with narrowest FWHM), and provenance (halo pixels, command line, geometry mode). Emit the same numbers in console output so automation logs remain human-readable.
  - Write a helper (`_summarize_spot_profiles`) that also renders a short Markdown report (`plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-22T150000Z/spot_profile_summary.md`) listing the worst five ROIs by ROI fraction, their HKL indices, ROI/halo energy, and FWHM so reviewers can reference the evidence without opening the JSON.
  - Run the probe once with spot-profile capture enabled:  
    `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBEX_SMOKE_HKL_PATH=sp.proc/calibration/smoke_refined_structure_factors_small.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --geometry-mode baseline --collect-spot-profiles --spot-profile-halo-pixels 10 --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-22T150000Z/spot_profile_probe.json | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-22T150000Z/spot_profile_probe.log`
  - After the run, call `python - <<'PY' ...` (or jq) to extract the new `spot_profile_stats` medians into `spot_profile_summary.md` alongside the top/bottom ROI tables so the doc is auditable.
- Pytest: Run the mapped DB-AT selectors above so chi²/ROI metrics capture the same failure signature under the new artifact path.
- Artifacts: Keep the probe JSON/log, Markdown summary, and both pytest outputs under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-22T150000Z/` (use subdirs like `db_at_028/`, `db_at_029/`) so the findings ledger can cite a single tree.

Deterministic Parity Crisis:
- Independent Reference: DIALS reflection table `sp.proc/refGeom_small/refGeom_small.refl` (refgeom smoke dataset). Its `intensity.sum.value` entries yield target/reference median 1.02, so it remains an external contract independent of Stage A/mapping implementations.
- Transformation Ledger:
  | Field | Units/frame | Producer (file:line) | Consumer (file:line) | Observed evidence | Hypothesis |
  | --- | --- | --- | --- | --- | --- |
  | ROI 14 HKL (0,2,-2) Stage A mean | ADU/pixel, panel 0 ROI [431:443,434:446] | plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py:857-929 | tests/dbex/test_stage_a_smoke_parity.py:323-398 | Stage A=407.7 vs ref=1.74 (233×) while target/ref=1.42 → chi² blips despite correct target scaling | nanobrag_torch concentrates energy into a few pixels because the simulated spot footprint is far narrower than the DIALS ROI |
  | ROI 11 HKL (1,6,-9) Stage A mean | ADU/pixel, panel 0 ROI [121:133,288:300] | plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py:857-929 | tests/dbex/test_stage_a_smoke_parity.py:323-398 | Stage A=95.7 vs ref=14.9 (6.4×) even though |F|²/pix=615; target/ref=0.90 | Post-run scaling ignores how intensity spills beyond the ROI halo, so the chi² gate sees ~6× excess energy while target stays near reference |
  | ROI 18 HKL (4,1,-6) Stage A mean | ADU/pixel, panel 0 ROI [144:156,619:631] | plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py:857-929 | tests/dbex/test_stage_a_smoke_parity.py:323-398 | Stage A=83.8 vs ref=26.1 (3.21×) while target/ref=0.98 | Simulator redistributes |F|² along one axis so ROI pixels overfill despite correct reflection magnitude |
  | ROI 27 HKL (4,-5,-1) Stage A mean | ADU/pixel, panel 0 ROI [350:362,877:889] | plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py:857-929 | tests/dbex/test_stage_a_smoke_parity.py:323-398 | Stage A=16.8 vs ref=5.42 (3.10×) but Stage A/|F|² = 4.5e-4 → intensity collapses vs HKL grid | Nanobrag_torch sampling misses most of the HKL energy, so whatever does land still saturates the ROI relative to the reference while neighboring pixels are starved |
  | ROI 17 HKL (-2,-4,4) Stage A mean | ADU/pixel, panel 0 ROI [739:751,610:622] | plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py:857-929 | tests/dbex/test_stage_a_smoke_parity.py:323-398 | Stage A=1.83 vs ref=0.68 (2.68×) while target/ref=1.57 | Even “minor” reflections overshoot ≈3×, so the crisis spans the entire ROI set, not just the brightest spikes |
- Boundary Bisection Step: Use the new spot-profile instrumentation to compare ROI vs halo energy fractions and per-axis FWHM for the exact ROIs listed above. If ≥80 % of Stage A energy still sits outside the DIALS bbox even after a 10 px halo, escalate to a nanobrag_torch debug patch (Environment Freeze exception) that logs per-reflection deposition in `nanobrag_torch/simulator.py::run`. Otherwise, continue refining the ROI/halo instrumentation to isolate which physics term is redistributing intensity before touching the simulator.

How-To Map:
- After editing the probe script, run the spot-profile probe command above (with `tee`) so both JSON and console diagnostics land under the new report tree. Keep the run single-shot; reruns should overwrite artifacts only if the first attempt fails.
- Immediately post-run, summarize the key fractions/FWHM by invoking `python - <<'PY'` (or jq) to read `spot_profile_probe.json` and append the medians + top/bottom ROI rows into `spot_profile_summary.md`. Reference the exact JSON paths (`spot_profile_stats.median_roi_fraction`, etc.) so reviewers can trace them.
- Reuse the existing jq snippets (or python) from prior loops to pull `reflection_bottom_n` entries; update the transformation ledger markdown by copying the fresh numbers if they shift materially.
- Execute the mapped DB-AT pytest commands with `DBAT028_ARTIFACT_DIR`/`DBAT029_ARTIFACT_DIR` pointing at the new report directory so chi²/pixel and ROI correlation JSON gets captured alongside the probe output.
- If CUDA memory becomes an issue during the probe, set `TORCH_COMPILE_DEBUG=1 NANOBRAGG_DISABLE_COMPILE=1` temporarily and rerun once before escalating; record any modifications in the report summary.

Pitfalls:
- Forgetting `--collect-spot-profiles` leaves the new JSON block empty and defeats the purpose of this loop.
- Halo expansion must clamp to detector bounds; negative indices will silently wrap in NumPy.
- ROI bounding boxes are `[x0,x1)` / `[y0,y1)`; do not treat `x1`/`y1` as inclusive when slicing or the energy sums will be off.
- FWHM computation should operate in ROI-local coordinates; forgetting to translate indices will pick the wrong cross-sections.
- Always run the probe in `--geometry-mode baseline`; perturbations mask the simulator defect.
- Keep environment vars (`DBEX_SMOKE_CALIB_PATH`, `DBEX_SMOKE_HKL_PATH`) identical to prior loops so evidence stays comparable.
- Do not touch production Stage A/B/C code in this loop; Environment Freeze only allows the probe + diagnostics edits being scheduled.
- Capture stdout via `tee`; missing logs make the ledger non-auditable and force rework.
- JSON may get large; avoid truncation by piping through `jq` or python when summarizing (no manual copy/paste errors).
- Be mindful of RNG: Stage A run seeds should stay identical (inherit from smoke fixture) to keep ROI ordering stable for ledger references.

If Blocked:
- If the probe fails (OOM, KeyError, etc.), log the exact command + traceback inside `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-22T150000Z/summary.md`, update `docs/fix_plan.md` Attempts History and `galph_memory.md` with the blocker, and flag whether it requires a nanobrag_torch instrumentation patch or fixture change before attempting again. Only escalate to Environment Freeze exception (editing `nanobrag_torch`) after this evidence lands; otherwise, pause and request supervisor guidance.
