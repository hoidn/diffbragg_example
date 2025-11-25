### Turn Summary
Prepared a ready-for-implementation plan to add masked mapping diagnostics and align the CPU/GPU probe outputs with DB-AT-028/029 artifacts.
Latest probe shows CPU↔CUDA mapping parity but the mapping baseline remains uncorrelated (ROI CC≈-0.04 both devices); caught scale_ratio_mapping using unmasked Bragg means in db_at_028 metrics.
Next: implement the masked metric fixes, rerun the probe and DB-AT-028/029 selectors, and compare masked vs unmasked stats to isolate the mapping baseline mismatch.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T055039Z/ (input.md)
