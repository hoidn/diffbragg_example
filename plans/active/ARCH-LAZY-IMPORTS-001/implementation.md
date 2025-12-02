# Implementation Plan — ARCH-LAZY-IMPORTS-001

## Initiative
- ID: ARCH-LAZY-IMPORTS-001
- Title: Eliminate Lazy Imports & Process Noise
- Owner: Galph ↔ Ralph
- Spec Owner: docs/spec-db-workflow.md
- Status: planned

## Goals
- Replace ad-hoc lazy-import patterns in geometry/physics/stage helper modules with explicit module-scope dependencies so diagnostics/tests catch drift early.
- Strip historical ticket noise from docstrings/comments and replace it with references to specs/findings to keep future diffs readable.

## Phases Overview
- Phase A — Inventory & Dependency Map: Identify remaining lazy-import clusters, document their dependency constraints, and capture before/after metrics.
- Phase B — Leaf Module Import Cleanup: Convert geometry/physics leaf modules (e.g., `dbex/geometry/crystallography.py`, `dbex/physics/forward.py`) and Stage helper seams to explicit imports plus dependency guards.
- Phase C — Process Noise & Guardrails: Remove stale ticket callouts, add lint/test coverage for import hygiene, and codify new rules in docs + CI checklists.

## Exit Criteria
1. All torch/geometry helper modules called out in problems.md (“Lazy imports / process noise”) import their dependencies at module scope with documented guardrails; lazy imports remain only where circular dependencies are proven and documented.
2. Docstrings/comments reference spec/findings (e.g., GEOMETRY-001/003, ARCH-ENGINE-002) instead of historic ticket IDs; new lint/test selectors gate future regressions.
3. `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` enumerate any new hygiene selectors; `pytest --collect-only` logs for those selectors live under `plans/active/ARCH-LAZY-IMPORTS-001/reports/<timestamp>/`.
4. Problems ledger entry “Lazy imports / process noise” points to this initiative, and `docs/fix_plan.md` Attempts History documents the cleanup with artifact paths.

## Compliance Matrix (Mandatory)
- [ ] **Spec Constraint:** docs/spec-db-workflow.md §§30-90 — Pipeline modules must keep documented dependencies and initialization order.
- [ ] **Spec Constraint:** docs/spec-db-runtime.md §§10-25 — Runtime guardrails (device/dtype neutrality, deterministic imports) must remain intact.
- [ ] **Fix-Plan Link:** docs/fix_plan.md — Row [ARCH-LAZY-IMPORTS-001] (Tier 0 problems-ledger follow-up).
- [ ] **Finding/Policy ID:** ARCH-ENGINE-002 (lazy-import staging rules), GEOMETRY-001/003 (mapping dependencies), RUNTIME-001 (no compile interference), POLICY-001 (Environment Freeze).

## Spec Alignment
- **Normative Spec:** docs/spec-db-workflow.md; docs/spec-db-runtime.md.
- **Key Clauses:** Stage contract (§7), dependency ordering for detectors/beam/crystal configs, runtime import/torch.compile guardrails.

## Architecture / Interfaces
- **Key Data Types / Protocols:** `RefinementSharedContext`, Stage helper modules (`dbex/refinement/stage_a_impl`, etc.), geometry helpers (`dbex/geometry/crystallography.py`), physics forward helpers (`dbex/physics/forward.py`).
- **Boundary Definitions:** `[CLI/DataLoad] -> [Bridge/Config factories] -> [Geometry/Physics helpers] -> [Stage/Engine]`.
- **Sequence Sketch (Happy Path):** CLI builds configs (module-scope imports) → Stage helper uses shared context (no hidden imports) → telemetry/logging recorded with spec references.
- **Data-Flow Notes:** Torch/dxtbx/nanobrag_torch dependencies must be explicit so GPU/CPU device guards in docs/spec-db-runtime.md remain enforceable.

## Context Priming (read before edits)
- Primary docs/specs: docs/spec-db-workflow.md §§30-90, docs/spec-db-runtime.md §§10-25, docs/architecture.md (import conventions), docs/architecture/pytorch_design.md (vectorization guardrails).
- Required findings: ARCH-ENGINE-002 (lazy import policy), GEOMETRY-001/003 (mapping dependencies), RUNTIME-001 (compile guard).
- Related telemetry/attempts: Stage helper extraction artifacts under `plans/active/ARCH-REFINE-001/` plus TORCH-API-ALIGN initiatives (factory/ExperimentModel traces).
- Data dependencies: geometry helpers rely on nanobrag_torch + torch; physics forward helper uses structure-factor grids (per docs/data_dependency_manifest.md). No new external datasets required.

## Phase A — Inventory & Dependency Map
### Checklist
- [ ] A0: Create inventory report (`reports/<ts>/lazy_import_audit.md`) enumerating modules still using lazy imports (`rg "import .*" dbex -n | grep -n "    import"`), grouped by dependency reason (circular guard vs. oversight).
- [ ] A1: Document dependency graphs for geometry + physics helpers (callers, imported modules, spec citations) referencing `docs/spec-db-workflow.md`.
- [ ] A2: Identify process-noise hotspots (docstrings/comments referencing historic tickets) and tag them with findings/spec references for later cleanup.

### Dependency Analysis (Required for Refactors)
- **Touched Modules:** `dbex/geometry/crystallography.py`, `dbex/physics/forward.py`, `dbex/refinement/stage_*_impl.py`, Stage classes.
- **Circular Import Risks:** Stage helpers import each other via `RefinementSharedContext`; plan to move heavy dependencies into shared factories or set up optional import guards with explicit documentation.
- **State Migration:** None yet; Phase A is documentation-only.

### Notes & Risks
- Inventory must distinguish necessary lazy imports (e.g., CLI options gating optional deps) vs. accidental ones to avoid regressing boot-time cost unnecessarily.

## Phase B — Leaf Module Import Cleanup
### Checklist
- [x] B1: Convert `dbex/geometry/crystallography.py` to module-scope imports with explicit optional dependency guards (`try/except ImportError` at top) and update references to GEOMETRY findings. *(2025-12-02T082202Z artifacts captured.)*
- [x] B2: Update `dbex/physics/forward.py::simulate_forward_torch` to import bridge/helpers at module scope, add dependency docstrings, and ensure tests cover the new import order. *(2025-12-02T082202Z artifacts captured.)*
- [ ] B3: Patch Stage helper modules (stage_a_impl/b_impl/c_impl) to rely on shared module-level imports or documented dependency injection, removing per-call `from ... import ...` statements. *Current focus: Stage B stack (stage_b_impl + StageB parity guard).*
- [ ] B4: Run targeted smoke selectors (`tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`, `tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_runs_simulator`, Gradcheck selectors) capturing collect + execution logs under this initiative.

### Notes & Risks
- Ensure import moves do not trigger heavier dependencies during CLI start-up (documented heuristics may require gating behind config detection).
- Watch for Environment Freeze — no new third-party installs allowed; rely on existing optional deps.

### Phase B.3 — Stage Helper Cleanup (2025-12-03T171500Z focus)
- Scope: Eliminate the remaining inline `import` usage across the Stage B stack (`dbex/refinement/stage_b_impl.py`, `StageB._build_lbfgs_closure` parity guard) so logging/telemetry dependencies are at module scope with documented guards.
- Deliverables this loop:
  - Move `json`, `os`, `logging`, and `Path` imports to module scope; add `logger = logging.getLogger(__name__)` for parity guard messaging.
  - Import `StageBTelemetryCollector` at module scope (no circular dependency) and update `_check_stage_b_baseline_parity` to rely on the eager import instead of per-call imports.
  - Replace ad-hoc `import logging` statements inside `_run_stage_b_lbfgs`, `_compute_loss_stage_b`, etc., with the shared module logger.
  - Capture pytest evidence for Stage B parity guard (`tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload`) and the Stage B shell smoke (`tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small`).
- Upcoming follow-up (current loop):
  - Stage A helpers (`_build_stage_a_context`, `_compute_panel_loss`, final diagnostics writer) still import `create_detector_config`, `create_crystal_config`, `Detector`, `Crystal`, and `Simulator` inside hot loops. Hoist these dependencies plus `Path/json` to module scope, document the requirement per ARCH-ENGINE-002, and delete the per-call import statements.
  - Stage C warm-cache helpers still import `warnings` and re-import `os/json` in the panel diagnostics block. Move `warnings` to module scope, rely on the existing module-level `os/json`, and ensure `_retarget_stage_a_detectors` and `_run_stage_c_lbfgs` reuse those imports rather than redeclaring them.
  - Validation: rerun `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=small`, `tests/dbex/test_torch_refine_smoke.py::test_stage_a_engine_delegation_telemetry`, and `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small`. Capture logs under `reports/<ts>/` for parity evidence.

## Phase C — Process Noise & Guardrails
### Checklist
- [ ] C1: Replace remaining historical ticket references in helper/stage docstrings with spec/finding citations; ensure diffs stay minimal.
- [ ] C2: Add lint/test guard (e.g., `tests/dbex/test_import_hygiene.py`) that scans for new lazy-import hotspots, referencing the artifact inventory from Phase A.
- [ ] C3: Update docs/TESTING_GUIDE.md + TEST_SUITE_INDEX.md with the new hygiene selector, add `pytest --collect-only` artifacts, and document enforcement in docs/findings.md if needed.

### Notes & Risks
- Lint/test guard must be narrow to avoid blocking legitimate optional imports (e.g., CLI gating). Provide allowlist for documented exceptions.

## Artifacts Index
- Reports root: `plans/active/ARCH-LAZY-IMPORTS-001/reports/`
- Latest run: `2025-12-03T223500Z/` *(Stage A/C lazy-import planning — artifacts reserved for this loop.)*
