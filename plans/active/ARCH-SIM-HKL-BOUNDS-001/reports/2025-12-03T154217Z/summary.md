### Turn Summary
Mapped Phase B follow-up for ARCH-SIM-HKL-BOUNDS-001 after the beam-center probe proved HKL math around (0,0,0) is correct but a global shift remains.
Code inspection shows Simulator caches the detector beam vector (sample→source) without negating it, so single-source runs compute q = k_out + k_in; multi-source already negates, so the fix is localized.
Authored input.md that directs Ralph to negate the cached beam vector, capture the Environment-Freeze patch, rerun compare_hkl_stats plus DB-AT-028/029, and refresh docs/fix_plan/findings with the evidence.
Next: implement the sign correction, regenerate the HKL stats + Stage-A metrics, and update the ledgers so ARCH-SIM-CONSTRUCTION-001 can unblock.
Artifacts: plans/active/ARCH-SIM-HKL-BOUNDS-001/reports/2025-12-03T154217Z/ (analysis_incident_beam_sign.md, input.md)
