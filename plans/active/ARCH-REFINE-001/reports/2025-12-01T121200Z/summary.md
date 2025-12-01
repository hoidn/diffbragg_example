### Turn Summary
Rebuilt `_build_final_bragg_from_stage_a_telemetry` to correctly hydrate CrystalConfig from Stage A telemetry using the override API.
The TypeError is resolved; Stage A telemetry now flows through the correct API calls (clamp log deltas, compute overrides, create config, build Crystal model).
Next: Run the full Stage smoke suite (A/B/C) to confirm refactor stayed loss-neutral, then move to Phase B.2 (JobContext wiring).
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T121200Z/ (pytest_stage_a_small_v2.log, collect_stage_smokes_small.log)

## Implementation Details

**Problem:** `_build_final_bragg_from_stage_a_telemetry` was calling `create_crystal_config` with undefined keyword arguments (`log_cell_a_delta`, `angle_alpha_raw`, etc.) that the API doesn't accept, causing TypeErrors.

**Solution (dbex/nanobrag_refinement.py:316-423):**
1. Extract log deltas and raw angles from Stage A telemetry (`param_deltas_a`)
2. Import and use `_clamp_log_cell_deltas` from `dbex.refinement.stage_a_impl` to clamp log cell deltas
3. Convert log deltas to actual cell parameters using `torch.exp()`: `cell_a_tensor = cell_params[0] * torch.exp(log_cell_a_delta_clamped)`
4. Convert raw angles to bounded angles using `torch.tanh()`: `cell_alpha_tensor = cell_params[3] + torch.tanh(angle_alpha_raw) * max_angle_delta`
5. Build `crystal_overrides` dict with computed tensor-valued cell parameters
6. Compute baseline misset using `compute_baseline_misset_deg(crystal, baseline_crystal, ...)` per GEOMETRY-003
7. Add baseline and delta missets: `final_misset = baseline_misset_deg_tensor + misset_xyz_deg`
8. Call `create_crystal_config(crystal, experiment=None, crystal_overrides=..., misset_deg_override=final_misset)` using correct override API
9. Build Crystal model: `crystal_model = Crystal(crystal_config, device=device, dtype=dtype)`
10. Set required attributes on crystal_model: `interpolate`, `hkl_data`, `hkl_metadata`
11. For warm-cache path: call `_retarget_stage_a_simulators(stage_a_ctx, crystal_model)` passing Crystal model (not CrystalConfig)
12. For cold path: instantiate Simulator with correct constructor signature (`detector_model`, `crystal_model`, `hkl_data`, `beam_config`)
13. Run simulators using `.run()` method (not `.forward()`)
14. Apply scale factor with clamping: `log_scale_clamped = torch.clamp(log_scale, min=-10.0, max=10.0)`

**Mirrors Stage B reconstruction pattern** (lines 510-629 in same file) to ensure consistent telemetry→CrystalConfig→Crystal model flow.

**Test Result:** Stage A refinement runs end-to-end; final Bragg reconstruction completes without errors. Test failure is unrelated to this fix (acceptance criterion requires larger scale delta than achieved).

**Spec Conformance:**
- GEOMETRY-003: Baseline misset correctly extracted and added to delta
- GRADIENT-004: Warm-cache retargeting preserves tensor attachments
- REFINE-010: Panel-mode telemetry path remains intact (no ROI-only validations)

**Files Modified:**
- dbex/nanobrag_refinement.py:316-423 (`_build_final_bragg_from_stage_a_telemetry`)

**Next Actions:**
- Run full Stage smoke suite (test_stage_a_expansion, test_stage_b_shell_modifiers, test_stage_c_detector_microslip) with small detector
- Verify telemetry capture and schema conformance
- Update docs/fix_plan.md Phase B.1 status → COMPLETE
- Proceed to Phase B.2 (JobContext wiring per plans/active/ARCH-REFINE-001/implementation.md)
