### Turn Summary
Aligned next steps around a CPU vs CUDA mapping-forward probe to pinpoint why DB-AT-028/029 mapping ROI CC is ≈-0.04 on the metadata-sigma smoke dataset.
Captured the GPU mapping failure signature (roi_cc_median_mapping≈-0.04, scale_ratio≈3e-03, chi2/pixel≈1.08e5) and recorded it in fix_plan + input with the new artifacts root.
Next: Ralph implements the CPU/GPU parity probe script and reruns DB-AT-028/029 with canonical env, logging CPU↔CUDA deltas.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T053220Z/
