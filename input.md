Summary:
- Inventory remaining lazy-import hotspots and convert the geometry/physics helpers to explicit module-scope imports so Stage callers no longer hide dependencies.

Mode: none

InitiativeType: architecture

Focus: ARCH-LAZY-IMPORTS-001 — Lazy imports / process-noise hygiene

Branch: integration

Mapped tests:
- tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_runs_simulator
- tests/dbex/test_stage_a_smoke_parity.py::test_db_at_027_zero_point_parity

Artifacts: plans/active/ARCH-LAZY-IMPORTS-001/reports/2025-12-02T082202Z/

Do Now:
- Implement: plans/active/ARCH-LAZY-IMPORTS-001/reports/2025-12-02T082202Z/lazy_import_audit.md — Run the repo-wide lazy-import scan (`rg -n "^[[:space:]]\\+\\(from\\|import\\) " dbex -g'*.py'`) and summarize the top offenders (geometry helpers, physics forward helper, Stage *_impl modules) with short notes referencing ARCH-ENGINE-002 / GEOMETRY findings. Check the audit into this report directory so future loops can diff progress.
- Implement: dbex/geometry/crystallography.py::derive_u_matrix_from_mosflm_a_star — Move the torch/nanobrag_torch imports to module scope inside a guarded try/except (set sentinel values when the optional deps are missing) and update docstrings to cite GEOMETRY-001/003 instead of historic ticket numbers. Preserve the current ImportError message, keep the module a leaf (no dbex.* imports), and add a small helper to assert the optional deps exist before use.
- Implement: dbex/physics/forward.py::simulate_forward_torch — Promote torch/nanobrag_torch/bridge/helper imports to module scope with guarded try/except blocks, drop the per-call `from dbex.refinement.helpers import create_unified_simulator`, and refresh the module docstring to cite ARCH-ENGINE-002 / RUNTIME-001. Ensure the optional dependency errors stay descriptive and that the helper remains TEST-ONLY per docs/architecture/dbex/physics/forward.idl.md.
- Validate: tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_runs_simulator — Proves the CLI still boots with module-scope imports and the writer plumbing stays intact.
- Validate: tests/dbex/test_stage_a_smoke_parity.py::test_db_at_027_zero_point_parity — Exercises the crystallography helpers via Stage A zero-point parity so any import or docstring drift is caught in the canonical mapping test.

How-To Map:
1. `rg -n "^[[:space:]]\\+\\(from\\|import\\) " dbex -g'*.py' | tee plans/active/ARCH-LAZY-IMPORTS-001/reports/2025-12-02T082202Z/lazy_import_rg.txt` — capture the raw scan, then condense it into `lazy_import_audit.md` with headings for each module that still has lazy imports.
2. Edit `dbex/geometry/crystallography.py` so the optional torch/nanobrag_torch imports live behind a module-scope try/except; add a helper (e.g., `_require_torch_crystal()`) that raises the same ImportError. Update docstrings/comments to cite GEOMETRY-001/003 and remove historic ticket IDs.
3. Edit `dbex/physics/forward.py` to move the torch/nanobrag_torch/bridge/helper imports to module scope, keep the TEST-ONLY warning, and ensure `simulate_forward_torch` no longer does on-demand imports. Reference ARCH-ENGINE-002 / RUNTIME-001 in the docstring instead of old tracker notes.
4. `KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_runs_simulator | tee plans/active/ARCH-LAZY-IMPORTS-001/reports/2025-12-02T082202Z/pytest_cli_lazy_imports.log`
5. `DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py::test_db_at_027_zero_point_parity | tee plans/active/ARCH-LAZY-IMPORTS-001/reports/2025-12-02T082202Z/pytest_stage_a_parity.log`

Pitfalls To Avoid:
- Do not import dbex modules from `dbex/geometry/crystallography.py`; it must remain a leaf module to avoid Stage/context cycles.
- Keep optional dependencies optional: module-scope try/except blocks should set sentinels and raise the same ImportError message when nanobrag_torch/torch is unavailable.
- Preserve the TEST-ONLY warning in `dbex/physics/forward.py` and keep the function detached from production LBFGS closures.
- Cite findings/specs (GEOMETRY-001/003, ARCH-ENGINE-002, RUNTIME-001) in docstrings instead of historical ticket IDs; no drive-by commentary.
- Do not add new lazy imports while moving code; every helper should import dependencies once at module load.
- Follow Environment Freeze—no new pip installs; rely on existing optional deps.
- When running the Stage A parity test, export `NANOBRAGG_DISABLE_COMPILE=1` to avoid torch.compile interfering with grad/telemetry.
- Keep the CLI selector configured for the small smoke dataset; set `DBEX_SMOKE_DETECTOR_SIZE=small` explicitly.

If Blocked:
- If moving imports introduces a circular dependency that you cannot resolve quickly, stop, capture the failure signature in `plans/active/ARCH-LAZY-IMPORTS-001/reports/2025-12-02T082202Z/blockers.md`, and update `docs/fix_plan.md` + problems.md so we can consider a scoped architecture change next loop.

Findings Applied (Mandatory):
- ARCH-ENGINE-002 — Stage helpers and leaf modules must declare dependencies at module scope; ensure new imports follow that pattern.
- GEOMETRY-001 — Geometry mapping helpers must keep beam/DetectorConfig invariants; moving imports must not perturb those calculations.
- GEOMETRY-003 — Stage A misset baseline logic depends on these helpers; docstring updates should continue to cite the incremental UB contract.
- RUNTIME-001 — Tests touching torch grad paths must run with `NANOBRAGG_DISABLE_COMPILE=1`.
- POLICY-001 — No environment/package changes; stick to source edits + docs.

Pointers:
- docs/spec-db-workflow.md:30 — Stage contract + dependency expectations for helpers.
- docs/spec-db-runtime.md:10 — Runtime guardrails for torch imports/device handling.
- docs/architecture/pytorch_design.md:12 — Notes on vectorization/lazy-import policy for simulator helpers.

Next Up:
- Stage helper import cleanup (dbex/refinement/stage_a_impl.py and siblings) once the leaf modules stop hiding dependencies.
