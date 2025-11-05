### Turn Summary
Tightened bridge mask contract to use `torch.as_tensor` with explicit float32 dtype and added 0/1-value assertions so CLI-001 compliance stays verifiable.
Updated test to handle torch.Tensor masks via `torch.is_floating_point` check; reverted automatic linter addition of `custom_beam_vector` which broke Stage B torch.compile.
Next: re-run CLI refine-one telemetry smoke once bridge/test contract stabilizes to ensure mask asserts stay silent end-to-end.
Artifacts: plans/active/TORCH-REFINE-004/reports/2025-11-05T200729Z/ (pytest_bridge_mask.log, pytest_stage_b_regression.log)
