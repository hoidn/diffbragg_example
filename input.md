Summary: Advance TORCH-BRIDGE-001 Phase A so the bridge helper delivers spec-aligned tensors, masks, and per-panel slices with proper guards.
Mode: TDD
Focus: TORCH-BRIDGE-001 — Bridge DataLoad to `nanobrag_torch`
Branch: integration
Mapped tests: pytest -v tests/dbex/test_nanobrag_bridge.py::TestPrepareRefinementInputs::test_tensor_contract; pytest -v tests/dbex/test_nanobrag_bridge.py::TestPrepareRefinementInputs::test_mask_polarity; pytest -v tests/dbex/test_nanobrag_bridge.py::TestPrepareRefinementInputs::test_pixel_pitch_guard
Artifacts: plans/active/TORCH-BRIDGE-001/reports/2025-10-28T222910Z/{do-now-notes.md,pytest.log}
Do Now:
1. TORCH-BRIDGE-001 A1 (plans/active/TORCH-BRIDGE-001/implementation.md) — Author `tests/dbex/test_nanobrag_bridge.py` fixtures around the existing DIALS sample assets and codify tensor/ROI expectations (`target`, `background`, trusted mask, panel slices); tests: pytest -v tests/dbex/test_nanobrag_bridge.py::TestPrepareRefinementInputs::test_tensor_contract
2. TORCH-BRIDGE-001 A1 (plans/active/TORCH-BRIDGE-001/implementation.md) — Implement `RefinementInputs` + `prepare_refinement_inputs` producing background-subtracted targets, loss mask `(background >= 0) & trusted`, and `[panel, slow, fast]` panel slices while zeroing invalid pixels; tests: pytest -v tests/dbex/test_nanobrag_bridge.py::TestPrepareRefinementInputs::test_tensor_contract
3. TORCH-BRIDGE-001 A2 (plans/active/TORCH-BRIDGE-001/implementation.md) — Enforce invariants for axis ordering, mask polarity, and square pixel pitch with explicit error messaging and unit coverage; tests: pytest -v tests/dbex/test_nanobrag_bridge.py::TestPrepareRefinementInputs::test_mask_polarity; pytest -v tests/dbex/test_nanobrag_bridge.py::TestPrepareRefinementInputs::test_pixel_pitch_guard
Priorities & Rationale:
- Honor `[panel, slow, fast]` ordering and loss-mask policy per docs/spec-db-core.md:20 and docs/spec-db-core.md:55 to keep torch parity with Spec DB contracts.
- Follow detector/beam mapping guardrails (custom vectors, pixel pitch equality) outlined in docs/config_crosswalk.md:22-34 and docs/spec-db-core.md:35-41.
- Mirror DIALS bbox semantics and mask alignment as mandated by docs/dials_api.md:10-24 to avoid ROI drift.
- Execute Phase 1 helper scope from plans/nanobrag_integration_plan.md:32-59 before advancing to config hydration.
How-To Map:
- export KMP_DUPLICATE_LIB_OK=TRUE
- mkdir -p plans/active/TORCH-BRIDGE-001/reports/2025-10-28T222910Z
- pytest -v tests/dbex/test_nanobrag_bridge.py::TestPrepareRefinementInputs::test_tensor_contract | tee plans/active/TORCH-BRIDGE-001/reports/2025-10-28T222910Z/pytest.log
- pytest -v tests/dbex/test_nanobrag_bridge.py::TestPrepareRefinementInputs::test_mask_polarity | tee -a plans/active/TORCH-BRIDGE-001/reports/2025-10-28T222910Z/pytest.log
- pytest -v tests/dbex/test_nanobrag_bridge.py::TestPrepareRefinementInputs::test_pixel_pitch_guard | tee -a plans/active/TORCH-BRIDGE-001/reports/2025-10-28T222910Z/pytest.log
- Capture implementation/design notes in plans/active/TORCH-BRIDGE-001/reports/2025-10-28T222910Z/do-now-notes.md
Pitfalls To Avoid:
- Forgetting `[panel, slow, fast]` ordering when stacking tensors from simtbx outputs.
- Dropping the −1 sentinel semantics on background subtraction, leading to ROI bleed.
- Running pytest without `KMP_DUPLICATE_LIB_OK=TRUE`, which violates torch parity guardrails.
- Allowing trusted mask polarity to flip (True must mean include); assert orientation once loaded.
- Skipping pixel pitch guards; rectangular panels must raise early per spec.
- Writing artifacts outside the initiative reports directory or omitting artifact references in ledgers.
- Ignoring the broken docs/pytorch_runtime_checklist.md symlink—log gaps and rely on crosswalk/runtime notes until fixed.
- Leaving helper without explicit error messages, complicating downstream debugging.
- Overlooking dependency on plans/nanobrag_integration_plan.md Phase 1 before touching Phase B items.
- Forgetting to update Attempts History with Metrics/Artifacts placeholders after execution.
If Blocked:
- If DIALS fixtures fail to load, capture stack traces in the artifact notes, mark TORCH-BRIDGE-001 as blocked in docs/fix_plan.md with repro commands, and halt implementation.
- If mask assets are unavailable, log the gap, add a backlog TODO pointing to required data, and pause helper work until resolved.
Findings Applied (Mandatory):
- GEOMETRY-001 — Plan enforces precise detector mapping and pixel pitch guardrails when shaping bridge outputs.
- CONFORMANCE-001 — Plan maps pytest selectors and mandates `KMP_DUPLICATE_LIB_OK=TRUE` before running targeted tests.
