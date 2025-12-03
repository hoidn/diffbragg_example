# Input for Ralph — ARCH-SIM-CONSTRUCTION-001 Phase C.2 (Debug Probe: Simulator Output Comparison)

## Summary
Create debug probe comparing Stage A vs reconstruction simulator raw outputs to isolate sqrt(spot_scale) discrepancy.

## Mode
none (evidence collection)

## InitiativeType
architecture

## Focus
ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment (Training vs Reconstruction)

## Branch
integration

## Mapped Tests
- `none — evidence-only` (probe will generate comparison artifacts but won't run pytest)

## Artifacts
`plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-04T160000Z/`

## Do Now

### Background
Three implementation attempts show systematic sqrt-factor confusion:
- **Without sqrt multiplication:** `bragg_after = 1.025e-05` (23,400× too small vs expected 0.24)
- **With sqrt multiplication:** `bragg_after = 5711` (23,800× too LARGE vs expected 0.24)

Debug instrumentation (loop i=451) revealed:
- Raw simulator output: `1.839e-14`
- Expected (working backwards from test assertions): `bragg_raw ≈ 4.3e-10`
- **Ratio: 23,400× discrepancy in raw output itself, not just scaling application!**

This suggests simulators built by Stage A vs reconstruction produce intrinsically different raw magnitudes.

### Hypothesis
Stage A's warm-cache path (via `_build_stage_a_context`) may apply calibration differently than reconstruction's cold path (via `create_unified_simulator`), resulting in simulators that internally embed different scalings despite identical input configs.

### Task
Create `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_simulator_outputs.py` (T2 script) that:

1. **Load test fixture data** (use `test_stage_a_smoke_parity.py` fixture setup as reference):
   - Load `refgeom_dataload` (from `tests/dbex/test_torch_refine_smoke.py::refgeom_dataload`)
   - Build `mapping_context` via `build_mapping_stage_a_context`
   - Extract `hkl_indices`, `hkl_amplitudes`, `calibration_metadata` (`spot_scale_override`, `beam_flux`, etc.)
   - Build `hkl_grid` via `build_structure_factor_grid`

2. **Build Stage A warm-cache simulators** (replicating stage_a.py warm cache construction):
   - Call `_build_stage_a_context(detector, beam, crystal, trusted_mask, hkl_grid, hkl_metadata, ...)`
   - Extract `stage_a_ctx.simulators[0]` (first panel)
   - Run simulator: `bragg_stage_a_raw = stage_a_ctx.simulators[0].run()`
   - Compute mean: `bragg_stage_a_raw.mean().item()`

3. **Build reconstruction cold-path simulator** (replicating reconstruction.py cold path):
   - Extract `detector[0]` (first panel), `beam`, `crystal`
   - Call `create_unified_simulator(detector_config, crystal_config, beam_config, hkl_grid, hkl_metadata, spot_scale_override=spot_scale_override, ...)` matching reconstruction.py:193-206
   - Run simulator: `bragg_recon_raw = simulator.run()`
   - Compute mean: `bragg_recon_raw.mean().item()`

4. **Compare outputs**:
   - Print both means with full precision
   - Compute ratio: `bragg_stage_a_raw.mean() / bragg_recon_raw.mean()`
   - Print `spot_scale_override`, `sqrt(spot_scale_override)`
   - Check if ratio ≈ 1.0 (match) or ≈ sqrt(spot_scale) (discrepancy)

5. **Save results to JSON**:
   - `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-04T160000Z/simulator_comparison.json`
   - Include: `bragg_stage_a_mean`, `bragg_recon_mean`, `ratio`, `spot_scale_override`, `sqrt_spot_scale`, `match_within_1pct` (bool)

6. **Write summary**:
   - `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-04T160000Z/summary.md`
   - Interpret results: if ratio ≈ 1.0, scaling bug; if ratio ≈ sqrt(spot_scale), simulator construction bug

### Expected Outcomes
- **Ratio ≈ 1.0:** Simulators match; bug is in scaling application (reconstruction should apply sqrt)
- **Ratio ≈ sqrt(spot_scale) ≈ 5.57e8:** Simulators differ; warm-cache path embeds calibration that cold path doesn't

### How-To Map

```bash
# Run comparison probe
python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_simulator_outputs.py \
  --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-04T160000Z/simulator_comparison.json

# Check results
cat plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-04T160000Z/simulator_comparison.json
cat plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-04T160000Z/summary.md
```

## Pitfalls To Avoid
1. **Device/dtype neutrality:** Use same device/dtype for both simulators (CPU, float32)
2. **Exact config matching:** Ensure both paths use identical `crystal_config`, `beam_config`, `detector_config`
3. **Warm cache isolation:** Don't call `_retarget_stage_a_simulators` before capturing raw output; we want construction-time state
4. **HKL grid identity:** Use the SAME `hkl_grid` tensor (via `.to(device)`) for both paths
5. **Calibration threading:** Ensure reconstruction cold path receives `calibration_metadata` dict with all fields (not just `spot_scale_override`)

## If Blocked
- Missing test data: Use `sp.proc/refGeom_00000/` as fallback (full detector, known calibration)
- Import errors: Add necessary imports from `dbex.refinement.stage_a_utils`, `dbex.refinement.helpers`, `dbex.vis.mapping`
- Simulator construction failure: Log full exception + config values; mark blocked in `summary.md`

## Findings Applied
- SCALE-002: sqrt(spot_scale) post-run application
- ARCH-FACTORY-001: Unified factory contract
- GRADIENT-004: Device/dtype neutrality

## Pointers
- Factory contract: `dbex/refinement/helpers.py:83-151` (create_unified_simulator)
- Stage A warm cache builder: `dbex/refinement/stage_a_utils.py:177-400` (_build_stage_a_context)
- Reconstruction cold path: `dbex/refinement/reconstruction.py:173-206`
- Test fixture setup: `tests/dbex/test_stage_a_smoke_parity.py:70-142`
- Debug evidence from loop i=451: `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-04T121500Z/debug_output.txt`

## Next Up
(none — this is a pure evidence loop; next loop will analyze probe results and issue corrective Do Now)
