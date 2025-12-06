# ARCH-IMPL-CONFORMANCE-001 — Findings Inventory (Phase A Planning)

## Date: 2026-01-13T150000Z

## Scope

Inventory SCALE-008, SCALE-009, and ARCH-FACTORY-001 findings to identify duplicated scaling/calibration semantics and prepare for Phase A contract alignment work.

## SCALE-008: Stage A vs Mapping Baseline Alignment

**Finding ID**: SCALE-008
**Date**: 2025-11-25
**Tags**: scaling, stage_a, calibration
**Status**: Active

**Summary**:
When `build_mapping_stage_a_context` multiplies `spot_scale_override` to cancel the N_cells-induced amplitude collapse, Stage A still derives `log_scale_baseline=log(√spot_scale_override)` from the adjusted calibration and re-applies the same factor, producing `scale_ratio_before≈2.0e4` and `bragg_before_mean≈2.8e5 ADU` even though mapping emits `scale_ratio_masked=1.0`.

**Contract Gap**:
Stage A must honor a mapping-provided baseline override (keyed off `diagnostics["calibration_adjusted_for_n_cells"]`) so zero-iteration intensity stays aligned once mapping fixes the masked mean.

**Code References**:
- `dbex/refinement/stage_a.py:442-443` (Stage A sqrt scaling pattern)
- `plans/active/TOOLING-VIS-001/reports/2025-11-25T235500Z/db_at_029/db_at_029_metrics.json`

**Relevance to ARCH-IMPL-CONFORMANCE-001**:
Identifies **baseline override contract** between mapping and Stage A — currently implicit, needs explicit ARCH-CONTRACT definition.

## SCALE-009: Reconstruction Scaling Parity

**Finding ID**: SCALE-009
**Date**: 2025-12-02
**Tags**: scaling, reconstruction, calibration, architecture
**Status**: Active (partially addressed by ARCH-SIM-CONSTRUCTION-001)

**Summary**:
Reconstruction helpers (`build_final_bragg_from_stage_*_telemetry`) must apply `sqrt(spot_scale_override)` post-run to every simulator output, matching the Stage A pattern (stage_a.py:442-443). Omitting this multiplication produces simulator raw outputs ~23,900× too small, causing DB-AT-028/029 failures.

**Additional Gap**:
Reconstruction cold path must thread `beam_flux`, `beam_exposure`, `beamsize_mm` from `calibration_metadata` to `beam_config` for architectural consistency.

**Code References**:
- `dbex/refinement/reconstruction.py:167-223` (reconstruction helper cold path)
- `dbex/refinement/stage_a_utils.py:267` (beam calibration threading pattern)
- `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-02T233717Z/summary.md`

**Current State**:
ARCH-SIM-CONSTRUCTION-001 addressed this at implementation level, but **no ARCH-CONTRACT defines the canonical owner API** for scaling/calibration application. Reconstruction cold path still duplicates Stage A logic instead of calling a shared helper.

**Relevance to ARCH-IMPL-CONFORMANCE-001**:
Identifies **duplicated scaling semantics** across Stage A vs reconstruction. Candidate for Phase B canonical owner API + duplicate removal.

## ARCH-FACTORY-001: Unified Simulator Factory (Forward-Only Scope)

**Finding ID**: ARCH-FACTORY-001
**Date**: 2025-11-24
**Tags**: architecture, simulator, factory, autograd, scope
**Status**: Active

**Summary**:
Unified simulator factory (`create_unified_simulator` in `dbex/refinement/helpers.py`) is designed for **forward-only simulation** paths (zero-iteration mapping, forward helpers without gradients). Factory MUST NOT be used in refinement closures (loss computation with autograd) because:
1. Factory returns pre-built Simulator (breaks autograd graph construction)
2. Refinement closures need differentiable Simulator instantiation to track gradients through detector/crystal parameters

**Scope Clarification** (Phase B2, 2025-11-24T000000Z):
- **Category A** (lines 1482, 1619, 2626, 3164, 3515, 4260, 4728): refinement closures requiring direct Simulator (DO NOT WIRE)
- **Category B** (lines 2174, 3809): post-refinement forward models (low-priority wiring, deferred)
- **Category C** (lines 593, 625, 762): Stage A warm-cache context construction (PERF-WARM-SIM-001 scope)

**Successfully Wired**:
- `simulate_forward_once`, `simulate_forward_torch` (Phase B2a -56 lines)
- `refine_one` CLI (Phase B2b(i) -23 lines)

**Code References**:
- `dbex/refinement/helpers.py:82-216` (factory implementation)
- `plans/active/TORCH-API-ALIGN-001/reports/2025-11-24T000000Z/phase_b2_scope_clarification.md`

**Contract Gap**:
**No explicit ARCH-CONTRACT defines when to use factory vs direct Simulator instantiation**. Current guidance is implicit in ARCH-FACTORY-001 finding.

**Relevance to ARCH-IMPL-CONFORMANCE-001**:
Identifies **factory contract ambiguity** — needs explicit ARCH-CONTRACT in architecture docs clarifying:
- When to call `create_unified_simulator` (forward-only paths)
- When to instantiate `Simulator` directly (refinement closures with autograd)
- Calibration threading responsibilities (factory vs caller)

## Synthesis: Candidate ARCH-CONTRACTs for Phase A

Based on these three findings, ARCH-IMPL-CONFORMANCE-001 Phase A should define:

### ARCH-CONTRACT-001: Simulator Factory Scope
- **Owner**: `dbex.refinement.helpers.create_unified_simulator`
- **Responsibility**: Forward-only simulator construction with calibration threading
- **Consumers**: `simulate_forward_once`, `simulate_forward_torch`, CLI forward helpers, reconstruction cold paths
- **Anti-pattern**: Using factory in refinement closures (breaks autograd)
- **Enforcement test**: TBD (Phase B)

### ARCH-CONTRACT-002: Post-Run Scaling Pattern
- **Owner**: TBD (candidate: canonical forward helper or Stage A scaling utility)
- **Responsibility**: Apply `sqrt(spot_scale_override)` to raw simulator outputs
- **Current duplicates**: `stage_a.py:442-443`, `reconstruction.py:~220-223`, `stage_a_utils.py:267`
- **Contract**: All forward paths must apply sqrt scaling consistently
- **Enforcement test**: TBD (Phase B parity test)

### ARCH-CONTRACT-003: Mapping → Stage A Baseline Override
- **Owner**: `dbex.vis.mapping.build_mapping_stage_a_context` (producer) + `dbex.refinement.stage_a` (consumer)
- **Responsibility**: Mapping provides adjusted `log_scale_baseline` when N_cells correction applied; Stage A must consume it
- **Current state**: Stage A ignores mapping baseline, re-derives from raw calibration metadata
- **Contract**: Explicit handoff via `calibration_metadata["log_scale_baseline_source"]` flag
- **Enforcement test**: TBD (Phase B baseline parity test)

## Contradictions / Drift vs Implementation

### SCALE-009 vs Current State
SCALE-009 (2025-12-02) describes omitting `sqrt(spot_scale_override)` as the root cause, but subsequent ARCH-SIM-CONSTRUCTION-001 work (Phases C.6-C.14, 2025-12-10 through 2025-12-18) revealed:
- The issue was NOT missing sqrt multiplication alone
- Multiple factors contributed: trusted mask threading, N_cells gate propagation, baseline alignment
- Current implementation (as of 2025-12-18) applies sqrt scaling correctly

**Drift**: SCALE-009 finding is partially obsolete; should be updated to reflect multi-factor nature of the parity issue.

### ARCH-FACTORY-001 vs Calibration Threading
ARCH-FACTORY-001 defines factory scope (forward-only) but **does not specify calibration threading contract**. Finding mentions beam_flux/exposure/beamsize threading is needed (per SCALE-009), but doesn't clarify whether:
- Factory should accept calibration_metadata and thread it internally, OR
- Caller should extract calibration fields and pass them explicitly to factory

**Ambiguity**: No single source of truth for factory calibration contract.

## Next Steps (Phase A)

1. **Review architecture docs**: Check if `docs/architecture/calibration_scaling.md` or `docs/architecture/module_map.md` already define these contracts
2. **Identify duplicated code**: Search for all instances of `sqrt(spot_scale_override)` multiplication and beam calibration threading
3. **Propose ARCH-CONTRACT definitions**: Draft explicit contracts for factory scope, scaling pattern, and baseline override
4. **Plan Phase B remediation**: Design canonical owner APIs + duplicate removal strategy

## Artifacts Cross-References

- `docs/findings.md:42` (SCALE-008)
- `docs/findings.md:43` (SCALE-009)
- `docs/findings.md:90` (ARCH-FACTORY-001)
- `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-02T233717Z/` (SCALE-009 origin)
- `plans/active/TORCH-API-ALIGN-001/reports/2025-11-24T000000Z/` (ARCH-FACTORY-001 scope clarification)
