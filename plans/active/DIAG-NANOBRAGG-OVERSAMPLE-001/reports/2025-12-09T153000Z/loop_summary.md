### Turn Summary
Extended Stage A warm-cache helpers with optional debug_config parameter (default None) to enable HKL statistics collection for diagnostic probes; updated compare_hkl_stats.py to collect stats from both Stage A simulators and simulate_forward_once.
Evidence confirms both paths have identical HKL coverage failure (0/9.4M in-bounds hits, observed Miller indices h∈[28,47] k∈[28,51] l∈[37,59] systematically offset beyond grid bounds h∈[-24,24] k∈[-28,28] l∈[-31,31]), proving this is NOT a Stage-A-specific configuration issue.
Next: Phase F complete; recommend closing DIAG-NANOBRAGG-OVERSAMPLE-001 and opening ARCH-SIM-HKL-BOUNDS-001 to investigate HKL grid construction or reciprocal-space transform alignment as root cause.
Artifacts: plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-09T153000Z/ (hkl_stats_comparison.json, summary.md, compare_hkl_stats.log)
