Summary:
- Align docs/IDL/module-map with the new `dbex/refinement/{inputs,config_factories}.py` split so references to `dbex/nanobrag_bridge.py` reflect the current responsibilities.

Mode: Docs

InitiativeType: architecture

Focus: ARCH-BRIDGE-RESP-001 — Writer / bridge responsibility split

Branch: integration

Mapped tests:
- none — docs-only

Artifacts: plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-02T094947Z/

Do Now:
- Update `docs/data_dependency_manifest.md` so the RefinementInputs sections cite `dbex.refinement.inputs.RefinementInputs` (dataclass) / `prepare_refinement_inputs` as the prep owner and mention the config factories now live under `dbex/refinement/config_factories.py`. The ROI helper entry should remain untouched apart from mentioning that prep/config responsibilities moved.
- Revise the Torch backend description in `docs/architecture/live_backend.md` to explicitly mention the new modules (prep in `dbex/refinement/inputs.py`, config builders in `dbex/refinement/config_factories.py`) and describe `dbex/nanobrag_bridge.py` as orchestration plus HKL helpers.
- Update `docs/architecture/module_map.md` by inserting rows for `dbex/refinement/inputs.py` and `dbex/refinement/config_factories.py`, and rewrite the `dbex/nanobrag_bridge.py` row so it only covers orchestration/HKL helpers.
- Refresh `docs/architecture/data_telemetry_flow.md` so the prep step references `dbex/refinement/inputs.prepare_refinement_inputs` and the ROI scoring step points at `dbex.io.roi_scoring` (mentioning that prep/config logic now lives under refinement/).
- Fix the `inputs` row in `docs/architecture/dbex/io/writer.idl.md` so it references `dbex.refinement.inputs.RefinementInputs` (dataclass) rather than the old bridge namedtuple.

How-To Map:
1. Use `apply_patch` on each doc to avoid breaking formatting; maintain Markdown tables with the same alignment as today.
2. When editing the module map, copy the existing table row style (pipe-separated headings) and keep the tests/spec references accurate.
3. After editing, proofread the affected sections and jot down a short summary in `plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-02T094947Z/summary.md` describing which docs were updated.

Pitfalls To Avoid:
- Do not alter any normative spec language—only update module names/paths and descriptions.
- Keep GEOMETRY/CONFIG references intact; the doc changes should highlight the new module homes without deleting guardrail text.
- This is a docs-only loop, so avoid touching Python sources or running tests unless you discover a doc that depends on new code behavior.

If Blocked:
- If you uncover additional doc references that clearly need updating but are ambiguous, log them in `plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-02T094947Z/blockers.md` with file/line context and stop for guidance instead of guessing new wording.

Findings Applied (Mandatory):
- GEOMETRY-001 / GEOMETRY-002 / GEOMETRY-003 — geometry/config docs must still call out the same mapping rules after renaming modules.
- CONFIG-001 — maintain `[panel, slow, fast]` and mask polarity language while updating file paths.
- DIAGNOSTICS-001 & PHYSICS-LOSS-001/002/003 — keep the variance-weighted loss messaging intact when editing the writer/ROI sections.

Pointers:
- docs/spec-db-workflow.md:16-45 for prep/calibration wording to cite.
- docs/config_crosswalk.md:17-95 for detector/beam/crystal mapping references.
- plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-03T020500Z/bridge_split_summary.md for the before/after responsibility table you can mirror in docs.
- plans/active/ARCH-BRIDGE-RESP-001/implementation.md (Phase C checklist) for current status.

Next Up (optional):
- After the docs are updated, we can schedule a loop to remove the bridge re-export layer and update any residual external scripts/tests.
