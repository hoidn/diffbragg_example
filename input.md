Summary: Capture the existing writer/bridge seam, add typed ROI analysis dataclasses, and document the new boundary so we can pull Nelder–Mead out of `write_torch_outputs` in the next loop.
Mode: none
InitiativeType: architecture
Focus: ARCH-BRIDGE-RESP-001 — Writer / bridge responsibility split
Branch: integration
Mapped tests:
- KMP_DUPLICATE_LIB_OK=TRUE pytest -q tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata
- pytest -q tests/dbex/test_nanobrag_bridge.py::TestPrepareRefinementInputs::test_tensor_contract
Artifacts: plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-02T213000Z/

Do Now:
- Implement: dbex/io/roi_analysis.py::ROIAnalysisPayload — Add a new module under `dbex/io/` that defines `ROITriptych` (panel_id, bbox, numpy arrays for data/bg/bragg), `ROIAnalysisPayload` (score, optimal scale, variance metadata), and a helper `build_roi_payloads_from_arrays(target, background, bragg, pids, bbox, scores=None, scales=None)` that packages existing arrays without mutating them. Keep everything numpy-based (no torch), include docstrings citing docs/spec-db-core.md §§20-46, and write minimal unit tests if necessary later.
- Document: docs/architecture/dbex/io/writer.idl.md & docs/data_dependency_manifest.md — Add a “ROI Analysis Payload” section describing the new typed parameter (fields, shapes, provenance) and extend the manifest with a short entry for the helper (inputs: ROI arrays, outputs: triptych/payload artifacts, telemetry fields).
- Evidence: plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-02T213000Z/boundary_audit.md — Capture the current callers of `write_torch_outputs` and `prepare_refinement_inputs` (just paths + context) plus a brief paragraph summarizing responsibilities; save the raw `rg` command outputs alongside the markdown.
- Validate: Re-run the CLI telemetry metadata test and the nanobrag bridge tensor contract test; store both pytest logs in the artifacts directory (e.g., `pytest_torch_writer_metadata.log`, `pytest_nanobrag_bridge_contract.log`).

How-To Map:
1. Boundary audit: `rg -n "write_torch_outputs" dbex tests > plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-02T213000Z/writer_callers.txt` and `rg -n "prepare_refinement_inputs" dbex tests > .../bridge_callers.txt`, then summarize the call graph + seam in `boundary_audit.md` (include one paragraph per function citing the new plan checkpoint).
2. New module: Create `dbex/io/roi_analysis.py` with the dataclasses + helper described above, add module-level `__all__`, and ensure the helper performs only packaging (no optimization). Add import guards/comments so future wiring knows where to hook ROI scoring.
3. Docs: Update `docs/architecture/dbex/io/writer.idl.md` by adding a section that defines the ROI analysis payload (fields, dataset mapping, provenance) and reference it from the API signature; extend `docs/data_dependency_manifest.md` with bullet(s) describing the helper’s inputs and required telemetry keys.
4. Tests/Artifacts: Run `KMP_DUPLICATE_LIB_OK=TRUE pytest -q tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata | tee plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-02T213000Z/pytest_torch_writer_metadata.log` and `pytest -q tests/dbex/test_nanobrag_bridge.py::TestPrepareRefinementInputs::test_tensor_contract | tee plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-02T213000Z/pytest_nanobrag_bridge_contract.log`. Ensure both command exits success and logs live under the artifacts path.

Pitfalls To Avoid:
- Do not change `write_torch_outputs` behavior yet; the new helper must be unused until the next loop.
- Keep dataclasses numpy-only so h5py callers can serialize without touching torch or SciPy.
- Avoid creating new dependencies or importing torch at module import time.
- When documenting the new interface, do not rename existing `/torch_diagnostics` keys or dataset paths.
- Ensure boundary audit artifacts are reproducible and placed under the initiative reports directory.
- No environment/toolchain changes per Environment Freeze; rely on stdlib/dataclasses only.

If Blocked:
- If adding the new module causes circular imports (e.g., `dbex/io/__init__.py` pulls writer, which imports ROI analysis), document the import stack in `boundary_audit.md`, revert the import addition, and note the block in docs/fix_plan.md + galph_memory before requesting a new initiative or plan change.

Findings Applied (Mandatory):
- DIAGNOSTICS-001 — Keep `/torch_diagnostics` schema stable; the new payload is additive only.
- PHYSICS-LOSS-001/002/003 — ROI packaging must preserve variance + mask semantics when we wire it later.
- GEOMETRY-001 & CONFIG-001 — Bridge documentation and helpers must continue to enforce square-pixel + mask polarity guards.

Pointers:
- plans/active/ARCH-BRIDGE-RESP-001/implementation.md:1 — Phase A checklist + compliance matrix.
- docs/architecture/dbex/io/writer.idl.md:1 — Current API contract to extend with ROI payload details.
- docs/data_dependency_manifest.md:1 — Manifest entry that must mention the new helper inputs/outputs.
- docs/spec-db-core.md:20 — ROI tensor and variance contract that govern the dataclass fields.
- dbex/io/writer.py:1 — Existing writer implementation; keep behavior unchanged while adding the helper module.
