Summary: Stand up the typed RefinementContext builder and wire Stage A/B/C + RefinementEngine to consume it so the engine no longer relies on ad-hoc dicts.
Mode: none
Focus: ARCH-REFINE-001 — Refinement Engine Modularization & Torch IO
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=small; tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small; tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T115900Z/
Do Now:
- Implement: dbex/refinement/context.py::build_refinement_context — add the new RefinementContext dataclass/builder and update RefinementEngine.run plus StageA.run/StageB.run/StageC.run to pull geometry/HKL/baseline state from this object instead of loose dicts, wiring run_nanobrag_refinement to pass `{"context": ctx, ...}` for the Stage A-only, Stage A→B, and Stage A→B→C branches.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-001/reports/2025-12-01T115900Z/telemetry_stage_smokes.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py -k "test_stage_a_expansion or test_stage_b_shell_modifiers or test_stage_c_detector_microslip" --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T115900Z/pytest_stage_smokes.log
How-To Map:
1. Create `dbex/refinement/context.py` defining `RefinementContext` (RefinementInputs, detector, beam, crystal, hkl_grid, hkl_metadata, optional baseline_crystal/baseline_detector, `extras: Dict[str, Any] = field(default_factory=dict)`) plus `build_refinement_context(...)` that validates tensor/device expectations and records provenance in docstring citing specs; export helper from `dbex/refinement/__init__.py`.
2. Update `run_nanobrag_refinement` Stage-A-only, Stage-A→B, and Stage-A→(B)→C branches to call `build_refinement_context(...)` once, pass the result via the `'context'` key into `RefinementEngine.run`, and keep existing stage telemetry payloads untouched for downstream stages.
3. Teach `RefinementEngine.run` to require `'context'` in the per-stage inputs dict, propagate it unchanged when enriching downstream inputs, and raise `ValueError("RefinementContext missing ...")` if someone calls the engine without it.
4. Modify `StageA.run`, `StageB.run`, and `StageC.run` so each starts with `ctx = inputs['context'] if isinstance(inputs, dict) else inputs` and references `ctx.refinement_inputs`, `ctx.detector`, etc., while continuing to pull `stage_a_telemetry`, `stage_a_ctx`, and `stage_b_telemetry` from the inputs dict for downstream coordination.
5. Execute the three mapped selectors separately so telemetry artifacts stay distinct:
   - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-001/reports/2025-12-01T115900Z/telemetry_stage_a.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T115900Z/pytest_stage_a.log`
   - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-001/reports/2025-12-01T115900Z/telemetry_stage_b.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T115900Z/pytest_stage_b.log`
   - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-001/reports/2025-12-01T115900Z/telemetry_stage_c.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T115900Z/pytest_stage_c.log`
Pitfalls To Avoid:
- Do not mutate simulator creation sites to use the forward-only factory (ARCH-FACTORY-001 forbids that inside refinement closures).
- Keep RefinementContext device/dtype neutral; never stash CUDA tensors that would break CPU collectors.
- Preserve Stage A ctx propagation (`stage_a_ctx` cache) when adding the context key so Stage B/C warm paths still work.
- Avoid mixing context fields with mutable telemetry dicts—stage-specific payloads (stage_a_telemetry, stage_b_telemetry) still travel outside the dataclass.
- Ensure the new ValueError in RefinementEngine mentions ARCH-REFINE-001 so callers know the contract changed.
- Capture telemetry logs for every pytest run; smoke selectors rely on `DBEX_SMOKE_TELEMETRY_PATH` for perf audits.
- Keep Environment Freeze intact: no new dependencies or package changes while adding the module.
If Blocked:
- If any selector fails because a stage does not receive `context`, archive the failing log/telemetry under the artifacts path, document the exact error signature plus the missing key in docs/fix_plan.md Attempts History, and mark the fix-plan item blocked until the wiring bug is understood.
Findings Applied (Mandatory):
- ARCH-FACTORY-001 — Refinement closures must keep direct Simulator construction; the new context must not route through the forward-only factory.
- REFINE-010 — Small-detector smokes force panel mode, so the shared context must expose the canonical ROI count used by auto-panel validators.
- ARCH-ENGINE-003 — Engine telemetry enrichment stays in place; ensure the refactor preserves stage name→telemetry mappings so `stage_modes`/`engine_protocol` remain intact.
Pointers:
- docs/fix_plan.md:301 — Scope + checklist for Phase B.1 context scaffolding.
- docs/spec-db-workflow.md:76 — Stage B/C normative requirements that rely on shared context geometry/HKL state.
- docs/spec-db-workflow.md:116 — Stage smoke dataset policy driving the mapped selectors and telemetry handling.
- docs/TESTING_GUIDE.md:161 — Required env vars + expectations for Stage A/B/C smokes.
Next Up (optional): Once RefinementContext is live, Phase B.2 can introduce JobContext (args/DataLoad/calibration) and start moving HKL grid construction into the context builder.
