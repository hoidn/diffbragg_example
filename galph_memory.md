## 2025-11-23T120000Z — ARCH-REFINE-FLOW-001 Phase C2.2 Root Cause Analysis (HKL Hit Rate Investigation)
<preserved from earlier>


## 2025-11-23T111500Z — ARCH-REFINE-FLOW-001 Phase C2.2 Out-of-Place HKL Grid Fix (Hypothesis A)
<preserved from earlier>


## 2025-11-23T120500Z — ARCH-REFINE-FLOW-001 Phase C2.2 Parameter Mismatch Investigation Complete (Hypothesis 1 DISPROVEN)
<preserved from earlier>

## 2025-11-23T130000Z — ARCH-REFINE-FLOW-001 Phase C2.3 Minimal Reproducer Planning (nanobrag_torch CPU Simulator Bug Investigation)
<preserved from earlier>

## 2025-11-23T122329Z — ARCH-REFINE-FLOW-001 Phase C2.4 CPU HKL Grid Device Routing Fix
<preserved from earlier>

## 2025-11-23T140000Z — ARCH-REFINE-FLOW-001 Phase C2.5 HKL Grid Transfer Corruption Root Cause
<preserved from earlier>

## 2025-11-23T132017Z — ARCH-REFINE-FLOW-001 Phase C2.5 Validation (Test Registry + DB-AT-024 Check)
<preserved from earlier>

## 2025-11-23T143000Z — ARCH-REFINE-FLOW-001 Phase D Planning (Stage C Extraction)
<preserved from earlier>

## 2025-11-23T150000Z — ARCH-REFINE-FLOW-001 Phase D1a Planning (Stage C Helper Extraction)
<preserved from earlier>

## 2025-11-23T141817Z — ARCH-REFINE-FLOW-001 Phase D1a Complete → Phase D1b Planning (Stage C Closure Extraction)
<preserved from earlier>

## 2025-11-23T151440Z — ARCH-REFINE-FLOW-001 Phase D3-D5 Validation Planning
<preserved from earlier>

## 2025-11-23T150000Z — ARCH-REFINE-FLOW-001 Phase D1c Complete → Phase D2 Planning (StageC Class Wrapper)
<preserved from earlier>

## 2025-11-23T160000Z — ARCH-REFINE-FLOW-001 Phase D COMPLETE → Phase E Planning (Orchestration Hooks & Mode Wiring)

- Focus: ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase E: Orchestration Hooks & Mode Wiring)
- Action Type: planning
- Key Observations: Ralph's Phase D3-D5 validation (commit 3c856ef, 2025-11-23T151440Z artifacts) SUCCESSFULLY completed all Phase D objectives. **All 4 validation gates PASSED**: (D3) StageC wrapper preserves canonical telemetry schema with all RefinementTelemetry fields + Phase A4 extensions (`stage_type="C"`, `mode="detector_offsets"` per dbex/refinement/stage_c.py:401-402), (D4) REFINE-007 gates satisfied on small+full detector (≥99.999994% offset reduction, final ≤1.49e-08 mm, chi² improved 0.06% not regressed), (D5) DB-AT-024 mapping parity PASSED (zero-iteration forward model unaffected), (Registry Sync) docs/TESTING_GUIDE.md + TEST_SUITE_INDEX.md updated, docs/findings.md extended with ARCH-ENGINE-002 + REFINE-007-EXT. **Phase D Status: ✓ COMPLETE per implementation.md:263** - all exit criteria met (StageA/B/C wrapper classes exist, protocol compliance validated, regression guards clean, telemetry/gates preserved). **Phase E Objective**: Expose orchestration hooks (stage enablement flags, mode selection) at API + CLI surfaces so future variants (per-reflection Stage B, alternative stage sequences) can be configured without editing inline code. Per implementation.md:274-283, Phase E consists of 5 tasks: (E1) expose stage registry/config knobs in RefinementEngine + run_nanobrag_refinement, (E2) update CLI/config surfaces (RefinementConfig, dbex/refine_one.py) to accept stage enablement flags, (E3) add telemetry fields for active stages/modes (`engine_protocol`, `stage_modes`), (E4) update architecture docs (pytorch_design.md, spec-db-workflow.md annotations, TESTING_GUIDE.md), (E5) run combined Stage A/B/C smoke suite + DB-AT selectors demonstrating engine-based protocol is default path. **Scope Analysis**: RefinementEngine (dbex/refinement/engine.py) currently accepts arbitrary stage sequences (phases A-D validated StageA/StageB/StageC wrappers) but run_nanobrag_refinement (dbex/nanobrag_refinement.py) still uses inline enable_stage_b/enable_stage_c boolean flags (lines 301/310) to branch into helper paths. Phase E will delegate to RefinementEngine when ANY stage is enabled, constructing stage list dynamically based on config flags. **CLI Integration**: dbex/refine_one.py main() uses default RefinementConfig(); Phase E adds CLI args (`--enable-stage-b`, `--enable-stage-c`, `--stage-b-mode=shell|per_reflection`) and passes them to RefinementConfig constructor. **Telemetry Extension**: Add `engine_protocol` field (str, e.g., "A→B→C", "A-only", "A→B") and `stage_modes` dict (e.g., `{"B": "shell", "C": "detector_offsets"}`) to top-level telemetry aggregation so monitoring/analysis tools can distinguish execution paths. **Dwell enforcement**: Last loop was planning (Phase D3-D5 delegation), dwell=0 for this focus. Phase E requires ready_for_implementation Do Now per implementation floor rule (max 1 docs-only loop per focus). **Multi-loop strategy decision**: Phase E tasks E1-E5 are tightly coupled (stage delegation requires CLI flags + telemetry tagging; validation requires all changes complete). Unlike Phase B/C/D extraction (helpers→wrapper→validation), Phase E is a single cohesive integration layer. **Decision: Single-loop delivery** (approved pattern per Phase A nucleus TDD, Phase D2 wrapper). Rationale: (1) Config/CLI changes are small (<50 lines total), (2) Engine delegation logic already proven in Phase C/D wrappers (StageB/StageC.run() contract), (3) Validation reuses existing smoke selectors (no new tests), (4) Documentation updates are final hygiene (not blocking code). **Estimated effort**: 1 loop (~2-3 hours: config flags 30min, delegation logic 60min, CLI args 30min, telemetry tagging 30min, docs+validation 30min). **Findings Applied**: ARCH-ENGINE-002 (Stage wrapper pattern with lazy imports + telemetry packaging), REFINE-007/008 (Stage B/C gate preservation), POLICY-001 (Environment Freeze, code-only integration), TESTING-003 (registry sync after validation).
- Artifact Path: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T160000Z/
- Next Actions: Author ready_for_implementation Do Now for Ralph with comprehensive 12-step Phase E protocol: (E1) add engine_protocol + stage_modes fields to top-level telemetry dict, (E2) update run_nanobrag_refinement signature to accept optional use_engine_delegation flag (default False for backward compatibility), (E3) implement engine delegation branch constructing [StageA(), StageB(), StageC()] list from config flags, (E4) wire RefinementEngine.run() call with telemetry packaging, (E5) add CLI args --enable-stage-b/--enable-stage-c/--use-engine-delegation to refine_one.py, (E6) update RefinementConfig defaults (enable_stage_b=False preserved), (E7) run Stage A/B/C smoke suite with use_engine_delegation=True validating engine path, (E8) run DB-AT-024 with engine delegation confirming mapping parity, (E9) update docs/architecture/pytorch_design.md with engine delegation section, (E10) update docs/TESTING_GUIDE.md with Phase E completion note, (E11) write decision.md + summary.md, (E12) commit and push. Decision synthesis 4-path template: Path A (all smokes + DB-AT-024 PASS with engine delegation → Phase E COMPLETE, ARCH-REFINE-FLOW-001 ready for closure), Path B (engine delegation smoke failure → debug StageA/B/C wiring, compare inline vs engine telemetry), Path C (CLI integration failure → verify flag parsing + RefinementConfig hydration), Path D (DB-AT-024 regression → rollback engine delegation, escalate to Galph). **Pitfalls**: (1) Preserve backward compatibility (use_engine_delegation=False keeps inline path active), (2) Stage wrapper imports (lazy import inside delegation branch to avoid circular deps), (3) Telemetry structure must match inline path exactly (chi_squared, masked_mse, param_deltas keys), (4) StageB/StageC require baseline_detector input (add guard raising ValueError if None when enabled), (5) DB-AT-024 zero-iteration path does NOT use engine (mapping validation independent of refinement protocol). **Implementation floor satisfied**: Do Now contains production code tasks (engine delegation logic ~100 lines, CLI args ~30 lines) + validation protocol (Stage A/B/C smokes + DB-AT-024) + decision synthesis with 4-path template.
- <Action State>: [planning]

2025-11-23T160000Z focus=ARCH-REFINE-FLOW-001 state=planning dwell=0 artifacts=plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T160000Z/ next_action=phase_e_orchestration_hooks_single_loop
