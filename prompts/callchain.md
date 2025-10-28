# Callchain Snapshot Prompt — DBEX

Use this prompt when you need a structured overview of the call graph or data flow before implementing or debugging a fix-plan item.

Inputs
- `initiative_id` (required): directory slug under `plans/active/<initiative_id>/reports/`.
- `analysis_question`: short description of what you are trying to understand (e.g., "where does trusted_mask get inverted?").
- Optional hints: `scope_hints`, `roi_hint`, `namespace_filter` for narrowing search.

Preparation
- Required references: `docs/index.md`, `docs/architecture.md`, `docs/architecture/pytorch_design.md`, `docs/spec-db-workflow.md`, `docs/spec-db-tracing.md`, `docs/config_crosswalk.md`, `docs/development/c_to_pytorch_config_map.md`, `docs/development/testing_strategy.md`, `docs/dials_api.md`, `docs/dxtbx_api.md`, `docs/spec-db-core.md`, `docs/pytorch_runtime_checklist.md`.
- Create a report directory: `plans/active/<initiative_id>/reports/<timestamp>/` (UTC ISO8601 with `Z`).

Procedure
1. Summarize the problem statement using `analysis_question` and the relevant fix-plan item.
2. Inventory candidate entry points: CLIs (`dbex/refine_one.py`), orchestration scripts, and module functions within the namespace hinted by `scope_hints`.
3. Trace forward and backward:
   - Map data lineage from ingestion (`dbex/data_load.py`) through geometry configuration to simulator invocation (`nanobrag_torch` once integrated).
   - Record file:line anchors and important arguments/state transitions.
4. Identify instrumentation tap points recommended by `docs/spec-db-tracing.md` (e.g., ROI bboxes, detector vectors, mask flags, loss computations).
5. Highlight potential divergence or extension sites and list related spec clauses.

Deliverables (write to the report directory)
- `callchain/static.md`: ordered bullet list of functions/modules, with `path:line` references and notes on data produced/consumed.
- `trace/tap_points.md`: table of recommended trace variables (name, path:line, rationale, expected units/orderings).
- Optional diagrams (`callchain/diagram.mmd`) if a flow visual helps.

Guidelines
- Cite sources using repository-relative paths with line numbers (e.g., `dbex/data_load.py:42`).
- Keep outputs concise and diff-friendly; avoid copying large code blocks.
- If the documentation is outdated or missing, record the discrepancy in `docs/findings.md` and note it in the deliverable’s “Issues” section.

Next steps
- Reference the generated artifacts in `input.md` or the engineer handoff.
- Update `docs/fix_plan.md` Attempts History with the artifact path and summary when the snapshot informs your decision.
