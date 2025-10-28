Summary: Prepare Phase A plan for TORCH-BRIDGE-001 so the bridge yields torch-ready tensors, masks, and panel slices with spec-aligned guards.
Mode: TDD
Focus: TORCH-BRIDGE-001 — Bridge DataLoad to `nanobrag_torch`
Branch: integration
Mapped tests: pytest -v tests/dbex/test_nanobrag_bridge.py::TestPrepareRefinementInputs::test_tensor_contract; pytest -v tests/dbex/test_nanobrag_bridge.py::TestPrepareRefinementInputs::test_mask_polarity; pytest -v tests/dbex/test_nanobrag_bridge.py::TestPrepareRefinementInputs::test_pixel_pitch_guard
Artifacts: plans/active/TORCH-BRIDGE-001/reports/2025-10-28T210500Z/{do-now-notes.md,pytest.log}
Do Now:
1. TORCH-BRIDGE-001 A1 (plans/active/TORCH-BRIDGE-001/implementation.md) — Stand up `tests/dbex/test_nanobrag_bridge.py` fixtures that hydrate `DataLoad` on the sample expt/refl assets and assert target/background/mask shapes + `[panel, slow, fast]` ordering per spec; tests: pytest -v tests/dbex/test_nanobrag_bridge.py::TestPrepareRefinementInputs::test_tensor_contract
2. TORCH-BRIDGE-001 A1 (plans/active/TORCH-BRIDGE-001/implementation.md) — Implement `RefinementInputs` dataclass and `prepare_refinement_inputs` helper returning target tensor, loss mask, trusted mask, and panel slices while zeroing invalid pixels and preserving sentinel handling; tests: pytest -v tests/dbex/test_nanobrag_bridge.py::TestPrepareRefinementInputs::test_tensor_contract
3. TORCH-BRIDGE-001 A2 (plans/active/TORCH-BRIDGE-001/implementation.md) — Add invariants that enforce `[panel, slow, fast]` ordering, mask polarity, and square-pixel guard with a dedicated error pathway, plus unit coverage; tests: pytest -v tests/dbex/test_nanobrag_bridge.py::TestPrepareRefinementInputs::test_mask_polarity; pytest -v tests/dbex/test_nanobrag_bridge.py::TestPrepareRefinementInputs::test_pixel_pitch_guard
Priorities & Rationale:
- Align tensors/masks with Spec DB contracts for ordering and loss mask semantics (`docs/spec-db-core.md:20`, `docs/spec-db-core.md:55`).
- Mirror DIALS bbox slicing and mask formats while using DataLoad outputs as authoritative source (`docs/dials_api.md:9`, `docs/dials_api.md:23`).
- Map detector metadata into torch configs with explicit pixel pitch guard and mask polarity per crosswalk (`docs/config_crosswalk.md:22`, `docs/config_crosswalk.md:33`).
- Follow integration plan Phase 1 directives for helper outputs and error handling before Phase B hydration (`plans/nanobrag_integration_plan.md:32`, `plans/nanobrag_integration_plan.md:52`).
- Keep torch Detector expectations in view when preparing mask/ROI structures to avoid downstream remaps (`docs/nanobrag_api.md:24`, `docs/nanobrag_api.md:34`).
How-To Map:
- export KMP_DUPLICATE_LIB_OK=TRUE
- pytest -v tests/dbex/test_nanobrag_bridge.py::TestPrepareRefinementInputs::test_tensor_contract
- pytest -v tests/dbex/test_nanobrag_bridge.py::TestPrepareRefinementInputs::test_mask_polarity
- pytest -v tests/dbex/test_nanobrag_bridge.py::TestPrepareRefinementInputs::test_pixel_pitch_guard
- python - <<'PY'
from pathlib import Path
from types import SimpleNamespace
from dbex.data_load import DataLoad
args = SimpleNamespace(mtzFile='scaled.mtz', mtzCol='F', exptName='refGeom.expt', exptIdx=0, reflName='_geom_ref.refl')
inputs = DataLoad(args)
print(inputs.data.shape, inputs.background_image.shape)
PY
- mkdir -p plans/active/TORCH-BRIDGE-001/reports/2025-10-28T210500Z
Pitfalls To Avoid:
- Do not reorder axes; maintain `[panel, slow, fast]` alignment from simtbx outputs.
- Preserve −1 sentinel semantics when zeroing background-invalid pixels; avoid masking trusted data.
- Enforce pixel pitch equality using a tight tolerance to catch rectangular panels early.
- Keep trusted mask polarity (True/1 means include) consistent across tensors and configs.
- Avoid writing artifacts outside the designated reports directory.
- Leave legacy DiffBragg data files untouched; rely on copies under tests/fixtures if needed.
- Note `docs/pytorch_runtime_checklist.md` symlink is broken; use integration plan/runtime notes until restored.
If Blocked:
- If DIALS assets fail to load, log the failure, stash repro commands under the artifact path, mark TORCH-BRIDGE-001 blocked in docs/fix_plan.md, and reference the new TODO in Attempts History.
- If pixel pitch metadata missing, document the dataset gap, add a TODO to fix_plan backlog, and pause implementation pending maintainer guidance.
Findings Applied (Mandatory):
- GEOMETRY-001 — Guarding detector mapping, beam center order, and pixel pitch per docs/spec-db-core.md:35-41.
- CONFORMANCE-001 — Mapping planned pytest selectors and enforcing KMP flag per docs/spec-db-conformance.md:10-29.
