### Turn Summary
Diagnosed the small-detector Stage C smoke failure as a warm-cache gradient break caused by `_retarget_stage_a_detectors` converting distance tensors into floats.
Logged GRADIENT-004 and refreshed docs/fix_plan.md plus input.md with the tensor-preserving Stage C plan and Stage B/C validation command.
Next: implement the Stage C tensor retargeting and rerun the small-detector Stage B/C smokes to prove the gradients flow again.
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T112335Z/
