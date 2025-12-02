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
Based on a review of the provided code, here are the identified bad design patterns and code smells, categorized by their nature.

### 1. Excessive Parameter Lists (Data Clumps)
**Severity: High**

Throughout the `refinement` sub-package, functions frequently accept 15+ arguments. This indicates that groups of data (like detector, beam, crystal, hkl_grid) always travel together but aren't encapsulated into a cohesive object passed around.

*   **Location:** `dbex/refinement/stage_a_impl.py` (e.g., `_build_stage_a_lbfgs_closure`), `stage_b_impl.py`, `stage_c_impl.py`.
*   **Example:** `_run_stage_c_lbfgs` takes `config`, `device`, `dtype`, `param_values`, `telemetry_state`, `stage_c_context`, `crystal`, `hkl_grid`, `detector`, `beam`, `inputs`, `canonical_baseline`, `stage_a_ctx`, etc.
*   **Recommendation:** Consolidate these into the existing `RefinementContext` or a new `SimulationState` object. The code partially attempts this with `StageAContext`, but then unpacks it and passes individual attributes into helper functions anyway.

### 2. Procedural Code Masquerading as OOP
**Severity: High**

The `StageA`, `StageB`, and `StageC` classes in `dbex/refinement/stage_*.py` are "anemic" classes. They contain almost no logic and simply delegate to massive, static "implementation" functions in `*_impl.py` files.

*   **Location:** `dbex/refinement/stage_a.py` vs `dbex/refinement/stage_a_impl.py`.
*   **Evidence:** `StageA.run` essentially just calls `_build_stage_a_params`, then `_build_stage_a_lbfgs_closure`, then `_run_stage_a_lbfgs`.
*   **Impact:** This defeats the purpose of polymorphism. State is passed manually between these static functions via dictionaries (`telemetry_state`, `param_values`) rather than being stored as instance attributes on the `Stage` object.
*   **Recommendation:** Move the logic from `_impl.py` methods directly into the `Stage` classes. Store `optimizer`, `params`, and `telemetry` as instance variables `self.optimizer`, `self.params`, etc.

### 3. Violation of Separation of Concerns in IO
**Severity: Medium**

The `writer.py` module is responsible for serializing output to HDF5, but it also performs significant computational work, including running an optimization loop.

*   **Location:** `dbex/io/writer.py` -> `write_torch_outputs`.
*   **Evidence:** Lines 105-125 import `scipy.optimize.minimize` and run a Nelder-Mead optimization to calculate `opt_bragg_scale` for every ROI *during* the writing phase.
*   **Impact:** This makes the I/O layer expensive and side-effect heavy. Writing results should not involve running new physics/math optimizations.
*   **Recommendation:** Move the `roi_check` / scaling optimization logic into a post-processing or analysis module (e.g., `dbex.analysis.scoring`). The writer should only receive final scores/scales.

### 4. Open/Closed Principle Violation in Engine
**Severity: Medium**

The `RefinementEngine` knows too much about the internal details of specific stages, specifically regarding telemetry and caching.

*   **Location:** `dbex/refinement/engine.py`.
*   **Evidence:** Inside `RefinementEngine.run`, there are explicit checks: `if stage.name == "stage_b": self._stage_b_shell_edges = ...`.
*   **Impact:** If you add `StageD`, you must modify the `RefinementEngine` code to handle its specific caching needs.
*   **Recommendation:** Stages should return a generic `CacheContext` or `Artifacts` object that the engine stores opaquely and passes to the next stage, rather than the engine manually extracting specific fields like `shell_edges`.

### 5. "God Object" / Low Cohesion (Bridge)
**Severity: Medium**

`nanobrag_bridge.py` acts as a dumping ground for disparate responsibilities.

*   **Location:** `dbex/nanobrag_bridge.py`.
*   **Evidence:** It handles:
    1.  Data preparation (`prepare_refinement_inputs`)
    2.  Configuration translation (dxtbx -> nanobrag_torch config)
    3.  Physics logic (`compute_baseline_misset_deg`)
    4.  Simulation execution (`simulate_forward_once`)
    5.  Calibration loading
*   **Recommendation:**
    *   Move config factories to `dbex.factories`.
    *   Move `simulate_forward_once` to `dbex.physics`.
    *   Keep `nanobrag_bridge` strictly for data structure conversion.

### 6. Pervasive Lazy Imports
**Severity: Low (but annoying)**

Almost every function performs imports inside the function body. While the documentation claims this is for "Environment Freeze" or "startup performance" (ARCH-ENGINE-002), it creates code smells.

*   **Location:** Everywhere, e.g., `dbex/geometry/crystallography.py`, `dbex/physics/forward.py`.
*   **Evidence:** `try: import torch ... except ImportError`.
*   **Impact:** It hides dependencies. You don't know a function requires `scipy` or `nanobrag_torch` until runtime execution hits that specific line. It makes static analysis tools less effective.

### 7. Mutable State via Dictionaries ("Mystery Meat")
**Severity: Medium**

The code relies heavily on passing dictionaries (`telemetry_state`, `param_values`) between helper functions to mutate state.

*   **Location:** `dbex/refinement/stage_a_impl.py` -> `_build_stage_a_lbfgs_closure`.
*   **Evidence:** The closure captures `telemetry_state` and updates lists inside it (e.g., `loss_trace_full.append(...)`).
*   **Impact:** It is difficult to track where a variable is modified. Explicit return values or class attributes are clearer than mutating a passed-in dictionary.

### 8. Hardcoded Logic in `run_nanobrag_refinement`
**Severity: Medium**

The main runner function has complex conditional branching to handle stage orchestration, effectively hardcoding the "Stage A only" vs "Stage A -> B" paths.

*   **Location:** `dbex/nanobrag_refinement.py`.
*   **Evidence:**
    ```python
    if stage_a_only_mode:
        # ... logic ...
    elif stage_a_b_mode:
        # ... different logic ...
    else:
        # ... engine delegation logic ...
    ```
*   **Impact:** This makes the pipeline rigid. The `RefinementEngine` was introduced to solve this, but the legacy "inline" logic still exists and wraps the engine usage in conditionals.
*   **Recommendation:** Deprecate the inline logic immediately. Construct the list of stages based on config, then call `engine.run(stages)`.

### 9. Over-Specification in Comments
**Severity: Low (Process Smell)**

The code is heavily decorated with references to project management tickets (e.g., "REFINE-007", "TORCH-GEOMETRY-PARITY-002").

*   **Location:** Everywhere.
*   **Impact:** While useful for traceability in a regulated environment, it makes the code harder to read. The code should explain *what* and *how*, while git commit messages or external design docs explain the *historical why*. When the ticket system eventually changes or is archived, these comments become noise.
