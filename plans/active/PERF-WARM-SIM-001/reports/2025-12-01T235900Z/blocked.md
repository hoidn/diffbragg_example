# PERF-WARM-SIM-001 Phase D.4 — BLOCKED

## Problem
Simulator rebuild implementation works for panel-mode (small detector) but fails for ROI-mode (full detector) with IDENTICAL failure signature across multiple loops, triggering repeat-failure guard.

## Evidence

### Small Detector (panel-mode): PASSED
- roi_mode: panel
- Offset: 0.25mm → 1.49e-08mm (99.999% reduction) ✓
- Chi²: +0.0055% improvement ✓  
- Telemetry: plans/active/PERF-WARM-SIM-001/reports/2025-12-01T235900Z/telemetry_stage_c_small.json

### Full Detector (ROI-mode): FAILED (identical to prior loop)
- roi_mode: roi
- Offset: 0.25mm → 0.46532484889030457mm (0.0% reduction, INCREASED) ✗
- Chi²: -2.25% degradation ✗  
- Telemetry: plans/active/PERF-WARM-SIM-001/reports/2025-12-01T235900Z/telemetry_stage_c_full.json
- **CRITICAL**: Final offset value identical to 15+ decimal places across loops despite code changes

## Implementation Summary
Updated `dbex/refinement/stage_c_impl.py::_retarget_stage_a_detectors` (lines 68-141):
1. Rebuild panel Simulator instances after updating detector configs (using dataclasses.replace to avoid config mutation)
2. Rebuild ROI entry simulators when `stage_a_ctx.roi_entries` exists
3. Preserve crystal references so `_retarget_stage_a_simulators` can reattach Stage A final crystal

## Root Cause Hypotheses
1. **ROI-mode execution bypass**: ROI-mode paths may use a different simulator cache not updated by `_retarget_stage_a_detectors` 
2. **Panel-id mapping issue**: Multi-panel detector geometry introduces ROI→panel mapping errors during retargeting  
3. **Simulator cache shadowing**: `_retarget_stage_a_simulators` (called after `_retarget_stage_a_detectors`) may inadvertently revert simulator state for ROI paths
4. **ROI slicing bypasses updated simulators**: ROI logic may directly access pre-rebuild simulator instances

## Blocker Justification
- Repeat-failure guard triggered (Ralph prompt ground_rules)
- Same acceptance criterion failed with byte-identical telemetry across 2+ loops
- Implementation changes had zero effect on full-detector outcome but fixed small-detector
- Further implementation attempts without architectural investigation violate repeat-failure policy

## Supervisor Actions Required
1. Investigate ROI-mode vs panel-mode execution path divergence (dbex/refinement/stage_c_impl.py:536-650)
2. Trace `stage_a_ctx.roi_entries` usage and panel_id mapping during retargeting  
3. Check if `_retarget_stage_a_simulators` (stage_a_impl.py:227-237) inadvertently breaks ROI simulator state
4. Consider callchain analysis of ROI-mode closure path to identify where stale simulators persist
