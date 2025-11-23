### Turn Summary
Investigated CPU fallback logic for Stage B full detector OOM; confirmed `_build_stage_b_params` contains fallback code but test still fails with CUDA OOM at physics.py:79.
Root cause hypothesis updated: CPU fallback conditions (config/device/roi_mode) evaluate to False despite appearing satisfied; need diagnostic instrumentation to identify failing condition.
Next: Add telemetry logging to `_build_stage_b_params` and `_build_stage_b_lbfgs_closure` to capture condition values, then rerun test to identify bug.
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T092000Z/ (decision.md, pytest logs)
