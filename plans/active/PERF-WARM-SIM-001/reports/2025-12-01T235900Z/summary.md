### Turn Summary
Reframed PERF-WARM-SIM-001 around rebuilding Stage A warm-cache simulators so Stage C finally measures detector-offset geometry within the ≤0.05% χ² gate.
Updated docs/fix_plan.md and input.md with the simulator/ROI rebuild Do Now plus Stage C smoketest, warm-cache summary, and panel-diagnostics commands tied to the new artifact path.
Marked the problems-ledger “Architectural Code Smells” item complete now that ARCH-REFINE-001 Phase F removed `_lazy_import_refinement` and documented explicit stage dependencies.
Next: Implement `_retarget_stage_a_detectors` so it rebuilds Detectors+Simulators (including ROI caches), rerun Stage C small/full smokes with diagnostics, and compare Stage A vs Stage C panel reports under plans/active/PERF-WARM-SIM-001/reports/2025-12-01T235900Z/.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-12-01T235900Z/
