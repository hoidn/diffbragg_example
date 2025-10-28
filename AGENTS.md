# AGENTS.md — Repository-Scoped Rules

## Scope & Precedence
- Applies to the entire `diffbragg_example/` tree.
- Future AGENTS.md files in subdirectories override these rules within their scope.
- Direct user/developer instructions supersede AGENTS.md.

## Coding & Documentation Conventions
- Follow the style already present in `dbex/` modules; prefer clear tensor operations and explicit parameter passing.
- Keep simulator/bridge logic aligned with Spec DB requirements (`docs/spec-db-*.md`). Cite the shard you implemented in commit messages when possible.
- Update documentation (`docs/`) when behavior, workflows, or commands change; maintain `docs/index.md` as the authoritative map.

## Testing Policy
- Primary framework: `pytest`.
- Author new tests in native pytest style (functions/fixtures). Do not mix with `unittest.TestCase` unless editing legacy code that already uses it.
- Respect selectors defined in `docs/TESTING_GUIDE.md` and `docs/development/TEST_SUITE_INDEX.md`. If a selector is missing, add a TODO plus rationale to `docs/fix_plan.md` before marking work complete.
- Gradient/torch tests must export `KMP_DUPLICATE_LIB_OK=TRUE`; gradient checks additionally require `NANOBRAGG_DISABLE_COMPILE=1`.

## Artifact & Ledger Policy
- Store loop artifacts under `plans/active/<initiative-id>/reports/<YYYY-MM-DDTHHMMSSZ>/`.
- Reference artifact paths in `docs/fix_plan.md` Attempts History entries.
- Findings with lasting value belong in `docs/findings.md` (include `source:path:line`).

## External Tool Trees (read-only unless instructed)
- DIALS: `./dials/`
- dxtbx: `./dxtbx/`
- simtbx: `./cctbx_project/simtbx/`

