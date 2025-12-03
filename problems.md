# Problems Ledger

This file is a lightweight, user-editable backlog for any issues that Galph (the supervisor) should consider during startup. Unlike `user_input.md`, these entries are advisory rather than imperative: Galph reads this file near the start of every loop, decides how to fold the items into `docs/fix_plan.md`, and then updates or removes entries as those problems are scheduled or resolved.

## How to use this file

- Add each problem as a checklist bullet under **Active Items**. Keep descriptions short but concrete.
- Optional sub-bullets can capture additional context, suggested solutions, or blocking dependencies.
- When Galph starts a loop, they will read every entry. If an item results in a plan or is otherwise addressed, Galph will edit the bullet with links/notes or remove it entirely.
- Mark items as completed (`[x]`) when the underlying issue is handled, preferably with a pointer to the fix-plan item, report, or commit that closed it.
- Feel free to leave this file empty; it exists only when you have additional guidance or ad-hoc requests that do not belong in `user_input.md`.

## Active Items

- [x] **Architectural Code Smells — overlapping legacy/new refinement paths** — Resolved via ARCH-REFINE-001 Phase F (2025-12-01T232800Z) by removing `_lazy_import_refinement`, hoisting Stage A/B/C helper imports to module scope, and documenting explicit dependencies so the RefinementEngine path no longer masks circular imports (see docs/fix_plan.md §2025-12-01T232800Z and telemetry in `plans/active/ARCH-REFINE-001/reports/2025-12-01T232800Z/`).

- [ ] _(Add new problems here. Galph will remove or rewrite entries as they are scheduled or resolved.)_
- [x] **Stage contexts / engine artifact boundary (from 2025-12-01 design review)** — Resolved via `ARCH-STAGE-CONTEXT-001` (docs/fix_plan.md) Phase E on 2025-12-02T160500Z: Stage A/B/C now rely exclusively on typed contexts/telemetry, RefinementEngine traffics `StageArtifacts`, and the CLI/writer consumers no longer poke stage-specific dicts (artifacts under `plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T160500Z/`).
- [x] **Writer / bridge responsibility split** — Resolved via [ARCH-BRIDGE-RESP-001] Phase B.1–B.4 (writer refactor), Phase C.1–C.6 (bridge decomposition), and Phase D (context type-hint cleanup) completed 2025-12-03T093500Z. `dbex/io/writer.py::write_torch_outputs` now consumes typed `ROIAnalysisPayload` instances pre-scored by `dbex/io/roi_scoring.py` (Nelder–Mead relocated, telemetry provenance captured). `dbex/nanobrag_bridge.py` shim removed after splitting `prepare_refinement_inputs` and config factories into `dbex/refinement/inputs.py` / `dbex/refinement/config_factories.py`; bridge now scoped to HKL/geometry helpers only. RefinementContext/RefinementSharedContext type hints tightened to import `RefinementInputs` from the new module. All exit criteria satisfied (docs/fix_plan.md Attempts History 2025-12-03T093500Z, artifacts under `plans/active/ARCH-BRIDGE-RESP-001/reports/`, CLI + Stage smoke selectors green). Initiative ready for archive once downstream initiatives reference the new modules.
- [x] **Lazy imports / process noise** — Resolved via [ARCH-LAZY-IMPORTS-001] (archived 2025-12-05T024500Z). Phase B (2025-12-02 through 2025-12-04): Eliminated 47 inline imports from 8 modules (geometry/crystallography.py, physics/forward.py, Stage A/B/C wrappers/helpers); all dependencies now at module scope with ARCH-ENGINE-002 guardrails. Phase C (2025-12-05T000500Z): Process noise audit scanned 8 modules, found 1 TODO-PHYSICS reference, replaced with precise spec citations (docs/spec-db-core.md §Loss Definition, docs/config_crosswalk.md lines 153-155). All Stage smoke tests PASSED (zero regressions). Closure summary at `archive/plans/ARCH-LAZY-IMPORTS-001/reports/2025-12-05T024500Z/initiative_closure_summary.md`.

ATTN NEW PROBLEMS:
IMPORTANT NEW:
I think there are plans in plans/active/ that are stale or not represented in fix_plan.md. identify them, audit them, update if needed (archive those that are no longer relevant), and then update fix_plan.md to track those initiatives 
IMPORTANT NEW
---
- [x] **ARCH-REFACTOR-001 Phase D.3 Reconstruction Baseline Logic** (2025-12-02T000000Z diagnosis, commit 6db57f45 fix) — **RESOLVED BUT UNCOVERED DEEPER ISSUE**: Original diagnosis correct: build_final_bragg_from_stage_a_telemetry (reconstruction.py:189-191) ignored log_scale_baseline from calibration metadata. Fix implemented correctly matching stage_a.py:1194-1202 (reconstruction.py:195-217). However, tests DB-AT-028/029 still FAIL with identical signature. Debug evidence shows fix executes correctly (log_scale_baseline=20.14, scale_factor=5.57e8), but simulator raw output is ~10^4.4× too small (1.8e-14 vs expected ~4.3e-10). Per repeat-failure escalation rule, marked Phase D.3 blocked and opened [ARCH-SIM-CONSTRUCTION-001] to investigate simulator construction convention mismatch. See plans/active/ARCH-REFACTOR-001/reports/2025-12-02T233717Z_galph_phase_d3_lifecycle_event/lifecycle_analysis.md.

- [x] **Simulator Construction Convention Mismatch (Training vs Reconstruction)** — **BLOCKED pending environment investigation** (2025-12-02T194000Z): Tracked via [ARCH-SIM-CONSTRUCTION-001] (status: stuck — blocked_environment_dependency). After 4 implementation loops (C.1-C.4, detailed in plans/active/ARCH-SIM-CONSTRUCTION-001/reports/), root cause identified as nanobrag_torch `oversample` parameter not honored: explicit `oversample=3` setting still triggers auto-selection code path (logs show "auto-selected 3-fold oversampling" 209×), producing ~23,317× magnitude discrepancy (bragg_after=1.025e-05 vs expected ~0.24, chi²=1.084e+05 vs ≤1e2 spec). Environment freeze blocks further debugging (cannot modify nanobrag_torch to investigate why DetectorConfig.oversample ignored). Unblock options: (a) patch/upgrade nanobrag_torch locally per Environment Freeze exception clause (requires documentation), (b) maintainer investigation, or (c) spec_change to relax DB-AT-028/029 acceptance criteria. Portfolio decision: switched focus to ARCH-TELEMETRY-001 (Tier 0, unblocked) per lifecycle decision 2025-12-03T021140Z. ARCH-REFACTOR-001 Phase D.3 remains blocked until this is resolved or alternative reconstruction approach found. See lifecycle_decision.md (2025-12-03T021140Z) and fix_plan.md §ARCH-SIM-CONSTRUCTION-001 for detailed history.

OLD DIAGNOSIS (for reference):
Confirmed Root Cause: Reconstruction Logic Gap
The function build_final_bragg_from_stage_a_telemetry in dbex/refinement/reconstruction.py (lines 189-191) treats the log_scale parameter from telemetry as an absolute exponent, ignoring the log_scale_baseline that Stage A now uses when calibration is present.
Current Broken Logic (reconstruction.py):
code
Python
# It simply clamps the delta and exponents it, missing the ~20.0 baseline
log_scale_clamped = torch.clamp(log_scale, min=-10.0, max=10.0)
scale_factor = torch.exp(log_scale_clamped) 
# Result: exp(~0) = 1.0, which is ~10^8.5 too small
Required Logic (Matching StageA.py lines 1188-1199):
code
Python
# Must apply baseline + clamped_delta
log_scale_clamped = log_scale_baseline + clamp(delta, min=-3.0, max=3.0)
scale_factor = torch.exp(log_scale_clamped)
# Result: exp(20 + 0) = ~1e8.5, matching simulate_forward_once
Remediation Plan
Step 1: Patch dbex/refinement/reconstruction.py
Update build_final_bragg_from_stage_a_telemetry to extract and apply the baseline from the telemetry payload.
Extract Baseline: Retrieve param_deltas_a['log_scale_baseline']['final'].
Conditional Logic:
If baseline is present/non-zero: Clamp the log_scale (delta) to config.log_scale_max_delta (default 3.0), then add the baseline.
If baseline is absent: Retain the legacy behavior (clamp to ±10.0, use as absolute).
Step 2: Verify Unblocking
Rerun the blocked test selector. Since the harness is already correct, this logic fix should immediately resolve the magnitude discrepancy in bragg_after.
code
Bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=metadata \
DBEX_SMOKE_DETECTOR_SIZE=full \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_stage_a_smoke_parity.py
IMPORTANT NEW
**ARCH-REFACTOR-001 Progress** (2025-12-02T220000Z loop):
- Phase D.2 PLANNING (this loop): Problems ledger "PRIORITIZE ARCH-REFACTOR-001 ASAP" serviced. CLI refactor scoped: migrate `dbex/refine_one.py` from `run_nanobrag_refinement` facade to direct `RefinementEngine` instantiation (5-step pattern: import updates, build RefinementContext, instantiate stages, run engine.run, extract Bragg/artifacts). Comprehensive planning notes at `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T220000Z/planning_notes.md` detail implementation strategy, validation plan (2 CLI selectors), and risks. Updated implementation.md (D.1 marked complete), updated docs/fix_plan.md with new attempt, ready to hand Do Now to Ralph next loop for Phase D.2 implementation.
- Phase D.1 COMPLETE (2025-12-02T210000Z, commit 43a70eae): RefinementConfig extracted to `dbex/refinement/config.py` (135 lines), 13 import sites updated, 3/3 tests PASSED, backward-compat re-export in facade ensures zero breakage during D.2-D.4.
IMPORTANT
**ARCH-REFACTOR-001 Progress** (2025-12-02T184846Z loop):
- Phase C.4 COMPLETE (commit cd855064): Stage B context strictness + parameter builder inlining
- Phase C.5 PLANNED: Stage B LBFGS inlining + HKL utilities extraction (see `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T184846Z/planning_notes.md`)
- Problems ledger directive "PRIORITIZE ARCH-REFACTOR-001 ASAP" serviced this loop via C.5 planning
  - 2025-12-02T200000Z: Problems ledger guard triggered again ("PRIORITIZE ARCH-REFACTOR-001 ASAP"), serviced via Phase C.7 Stage A utilities extraction planning. Stage A impl (1524 lines, 11 functions) is the final *_impl.py module; planned C.7-C.9 extraction/inline/deletion per hkl_utils precedent. Issued Do Now for C.7: extract 7 cross-stage helpers to stage_a_utils.py, update 5 import sites, validate with 4 selectors. Artifacts at plans/active/ARCH-REFACTOR-001/reports/2025-12-02T200000Z/.
- Remaining work: inline `_run_stage_b_lbfgs`, create `hkl_utils.py`, delete `stage_b_impl.py`, then repeat for Stage A
IMPORTANT
The codebase is currently in a "Mid-Refactor" state (Transitioning from monolithic scripts to a Protocol-based Engine), resulting in significant complexity, indirection, and state-management overhead.
1. Architectural Issues (System Level)
1.1. The "Incomplete Migration" Pattern (Code Duplication & Indirection)
Issue: The system is halfway between a procedural script approach and an Object-Oriented engine.
dbex/nanobrag_refinement.py contains monolithic logic.
dbex/refinement/engine.py and stage_*.py classes were introduced (ARCH-REFINE-FLOW-001), but they largely wrap procedural "implementation helpers" located in dbex/refinement/stage_*_impl.py.
Consequence: Call stacks are excessively deep. RefinementEngine calls StageA.run, which calls _build_stage_a_params, which calls _build_stage_a_lbfgs_closure. This makes the control flow difficult to trace and creates multiple "sources of truth" for how refinement is orchestrated.
1.2. Data Clumps and Primitive Obsession in Closures
Issue: The LBFGS closure builders (e.g., _build_stage_b_lbfgs_closure in stage_b_impl.py) take excessive numbers of arguments (15+).
Design Smell: Although RefinementSharedContext was introduced (dbex/refinement/context.py) to encapsulate these, the implementation files still support (and often unpack) legacy individual arguments alongside the context object.
Example: _build_stage_b_lbfgs_closure accepts shared_context OR a list of 11 individual parameters (config, device, crystal, beam, etc.). This defensive coding style creates confusion about which data source is authoritative.
1.3. Mutable State "God Dictionaries"
Issue: Telemetry and optimization state are managed via large mutable dictionaries (param_values, telemetry_state) passed by reference through multiple layers of functions.
Example: In stage_a_impl.py, telemetry_state holds everything from loss_trace to perf_closure_evals and best_params_snapshot. This dictionary is mutated deep inside the closure.
Consequence: It is nearly impossible to reason about the state of the refinement at any specific line of code without understanding the entire call graph. It defeats type safety and makes refactoring dangerous.
2. Design Issues (Component Level)
2.1. Tightly Coupled Physics and Optimization
Issue: The physics of crystal geometry (Incremental UB, U-Matrix, Cell parameterization) is constructed inside the optimization closure (stage_a_impl.py lines ~800-900).
Consequence: The optimization loop is tightly coupled to the specific parameterization strategy. Changing the physics model (e.g., from cell+misset to incremental_UB) requires branching logic inside the hot loop of the optimizer.
Better Design: A differentiable_forward_model(params) -> intensity abstraction should exist that encapsulates parameter application, decoupling the optimizer from crystallography math.
2.2. "Warm Cache" Complexity (PERF-WARM-SIM-001)
Issue: The performance optimization for "Warm Caching" (reusing Simulator objects) leaks into the business logic of every stage.
Evidence: StageAContext stores simulators and roi_entries. Stage C has to explicitly call _retarget_stage_a_detectors to mutate this cache in-place to apply distance offsets.
Consequence: This makes the Stage implementations fragile. Stage C implicitly depends on the memory layout and object identity of Stage A's internal cache. This violates stage isolation principles.
2.3. Telemetry/IO Logic Bleeding into Physics
Issue: The physics closures (_compute_variance_weighted_loss and the loop in _build_stage_a_lbfgs_closure) contain explicit logic for formatting telemetry (e.g., collecting i_model_min, u_matrix_lifecycle_log).
Consequence: High-performance numerical code is cluttered with logging logic. The RefinementTelemetry object is constructed by manually unpacking these dictionaries at the end of a run, leading to potential key mismatches (as seen in the "Phase 8 fix" comments in engine.py).
2.4. Hard-Coded Staging Logic
Issue: While RefinementEngine claims to be protocol-based, run_nanobrag_refinement (the main entry point) still hardcodes the logic: "If A only, do X; if A->B, do Y".
Evidence: dbex/nanobrag_refinement.py lines ~170-400 contain massive if/elif blocks handling specific combinations of stages to manage cache propagation.
Consequence: Adding a "Stage D" would require modifying the core orchestration logic, negating the benefit of the RefinementEngine abstraction.
3. Implementation/Code Smells
3.1. Mixed Abstraction Levels in nanobrag_bridge.py
Issue: This module acts as an Anti-Corruption Layer between dxtbx and nanobrag_torch. However, it mixes factory logic (create_detector_config) with pure math (derive_u_matrix_from_mosflm_a_star) and IO logic (load_calibration_metadata).
Consequence: This file has become a "catch-all" utility drawer, making it hard to find specific functionality.
3.2. Defensive/Redundant Validation
Issue: The same validations (e.g., "Pixel pitch must be square", "Sigma must be positive") appear in multiple places: data_load.py, nanobrag_bridge.py, and writer.py.
Consequence: DRY violation. If a rule changes in the Spec, it must be updated in 3+ places.
3.3. Conditional Imports and Lazy Loading
Issue: Extensive use of import ... inside functions (e.g., in stage_b_impl.py).
Reason: Likely to avoid circular imports caused by the entangled module structure or to improve startup time.
Consequence: Hides dependencies. Module-level dependencies are not visible at the top of the file. Import errors occur at runtime (during execution) rather than at load time.
4. Specification vs. Implementation Gap
Mapping Zero-Point Invariant: The complexity required to maintain A* = U @ B parity between the mapping (DIALS) and the refinement zero-point (Torch) has resulted in complex, fragile logic in geometry/crystallography.py (derive_u_matrix_from_mosflm_a_star). The implementation effectively reverse-engineers a B_ideal to force the math to work, which indicates a fundamental impedance mismatch between the legacy data model and the new differentiable model.
Recommendations
Finish the Refactor: Delete dbex/nanobrag_refinement.py and fully move logic into the RefinementEngine and Stage classes. Remove the "dual path" (legacy dicts vs. Context objects) in the _impl files and strictly enforce RefinementContext.
Encapsulate the Physics Model: Create a DifferentiableExperiment class (extending nanobrag_torch.ExperimentModel) that owns the parameters (q, log_scale, cell_deltas) and provides a simple .forward() method. The LBFGS closure should look like loss = criterion(model(), target), not 100 lines of tensor math.
Abstract the Cache: Move the "Warm Cache" logic into a SimulatorPool or ContextManager class that handles retargeting internally, rather than passing raw lists of Simulator objects between stages.
Observer Pattern for Telemetry: Instead of accumulating stats in a dict inside the loop, use a callback/observer pattern where the loop emits events (on_step, on_validation), and a separate TelemetryCollector handles aggregation.
- [x] **Refactor: Decouple Telemetry from Refinement Logic using Observer Pattern** — **Resolved** via [ARCH-TELEMETRY-001] (archived 2025-12-04T235959Z). Stage A/B/C now emit observer callbacks into typed telemetry collectors instead of mutating mutable dicts. RefinementEngine + writer consume StageResult dataclasses. All exit criteria satisfied (9 implementation loops, 6 phases complete, closure summary at `archive/plans/ARCH-TELEMETRY-001/reports/2025-12-04T235959Z/initiative_closure_summary.md`). Architectural issues 1.3 (mutable state god dictionaries) and 2.3 (telemetry/IO bleeding into physics) resolved.
1. Context & Problem Statement
The current telemetry system acts as a "bucket brigade," passing mutable state dictionaries (telemetry_state, param_values) four layers deep into the physics kernels (e.g., _build_stage_a_lbfgs_closure). This has created several critical architectural issues:
Tight Coupling: The LBFGS optimization loops are physically interwoven with UI/Logging logic (appending to lists inside gradient calculations).
The "Kitchen Sink" Dataclass: RefinementTelemetry attempts to hold every metric for every stage, leading to an explosion of Optional fields and loss of type safety.
Runtime Monkey-Patching: RefinementEngine currently dynamically attaches attributes (e.g., stage_b_mode) to telemetry objects at runtime (see engine.py "Phase 8 fix"), defeating the purpose of dataclasses.
Fragile Persistence: dbex/io/writer.py relies on massive if/elif blocks to map field names to HDF5 datasets manually.
2. Goal
Decouple the mathematical refinement process from the recording of metrics. The physics code should emit events, and a separate system should handle storage/logging.
3. Proposed Architecture
Observer Pattern: Introduce a RefinementObserver protocol. Physics loops call observer.on_step(...) or observer.on_validation(...).
Polymorphism: Split the monolithic RefinementTelemetry into specific result objects (StageATelemetry, StageBTelemetry, StageCTelemetry).
Encapsulation: Move list-management and aggregation logic out of *_impl.py and into concrete TelemetryCollector classes.
4. Implementation Steps
Phase 1: Interfaces & Types

Define RefinementObserver Protocol in dbex/refinement/interfaces.py.
Methods: on_step(iter, loss, params), on_validation_start(), on_validation_end(metrics).

Split RefinementTelemetry (in stage.py) into a base class and stage-specific subclasses (StageAResult, StageBResult). Remove the "God Class."
Phase 2: Refactor Physics Kernels (Start with Stage A)

Modify _build_stage_a_lbfgs_closure in dbex/refinement/stage_a_impl.py.
Remove: telemetry_state argument.
Add: observer: Optional[RefinementObserver] argument.
Action: Replace loss_trace.append(...) calls with observer.on_step(...).

Remove the logic inside stage_a_impl.py that calculates derived telemetry (e.g., u_matrix_lifecycle_log). Move this calculation into a specific StageADiagnosticsObserver.
Phase 3: Telemetry Collection & Engine Integration

Implement InMemoryTelemetryCollector (implements RefinementObserver) to replace the mutable dictionaries currently created in RefinementEngine.

Update RefinementEngine.run() to instantiate collectors and pass them into the Stages.

Remove the "Phase 8 fix" runtime attribute injection in engine.py.
Phase 4: Persistence Layer (writer.py)

Refactor dbex/io/writer.py.
Remove the giant if key == ... dispatch loop.
Implement method dispatch (e.g., functools.singledispatch or visitor pattern) to handle StageATelemetry vs StageBTelemetry writing logic separately.
5. Acceptance Criteria
Zero Coupling: stage_*_impl.py files no longer import or reference RefinementTelemetry or raw list accumulators.
Type Safety: RefinementEngine returns strictly typed stage-specific objects, not a generic container with dynamic attributes.
Regression Check: Running test_torch_refine_smoke.py produces bit-for-bit identical HDF5 output compared to the main branch.
Clean API: Adding a new metric requires changes only in the Observer implementation, not in the LBFGS closure.
6. Risks
Performance: Ensure the Observer callbacks are lightweight so they do not degrade the tight loop performance of the LBFGS optimizer.
HDF5 Schema Drift: The existing HDF5 schema is consumed by look.py and downstream tools. We must ensure the refactored writer produces the exact same node structure in the HDF5 file.
