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
- [ ] **Writer / bridge responsibility split** — Outstanding review items 3 and 5: `dbex/io/writer.py::write_torch_outputs` still runs Nelder–Mead to compute `opt_bragg_scale`, and `dbex/nanobrag_bridge.py` remains a “god object” that mixes data prep, calibration loading, simulator execution, and physics helpers. Need follow-up initiative to relocate scaling checks into analysis tooling and split bridge responsibilities across factories/physics modules.
  - Tracked via fix-plan row [ARCH-BRIDGE-RESP-001] (2025-12-02T213000Z) with plan at `plans/active/ARCH-BRIDGE-RESP-001/implementation.md`.
  - 2025-12-02T091255Z: Phase B.3 writer refactor landed (writer now requires `roi_payloads` and emits `roi_scoring_method/roi_checker` telemetry), but CLI tests need updated typed `DetectorConfig` fixtures so `create_unified_simulator` can normalize masks/distance before asserting on new telemetry. See fix-plan attempts log and current Do Now for remediation.
- [ ] **Lazy imports / process noise** — Outstanding review items 6 and 9: several modules (`dbex/geometry/crystallography.py`, `dbex/physics/forward.py`, Stage helpers) still use pervasive lazy imports that hide dependencies, and code is saturated with historical ticket references. Requires a hygiene push once the architecture work above is stable.
  - Tracked via fix-plan row [ARCH-LAZY-IMPORTS-001] (2025-12-02T082202Z; plan at `plans/active/ARCH-LAZY-IMPORTS-001/implementation.md`).

ATTN NEW PROBLEMS:
---
IMPORTANT
PRIORITIZE ARCH-REFACTOR-001 ASAP
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
---
Refactor: Decouple Telemetry from Refinement Logic using Observer Pattern
ID: ARCH-TELEMETRY-001
Type: Technical Debt / Refactor
Priority: High
Effort: Large (5-8 days)
(Scheduled as fix-plan row [ARCH-TELEMETRY-001] on 2025-12-02; see plans/active/ARCH-TELEMETRY-001/implementation.md.)
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
