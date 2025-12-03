Summary: Author a reciprocal-lattice probe so we can quantify and document the HKL offset between nanobrag_torch and dxtbx before fixing Stage-A mapping parity.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-SIM-HKL-BOUNDS-001 — Stage-A / mapping HKL alignment
Branch: integration
Mapped tests: pytest -vv tests/dbex/test_data_load_sigma_map.py
Artifacts: plans/active/ARCH-SIM-HKL-BOUNDS-001/reports/2025-12-03T161200Z/

Do Now:
- Implement: plans/active/ARCH-SIM-HKL-BOUNDS-001/bin/probe_crystal_hkl_alignment.py::main — CLI tool must load the canonical refGeom smoke dataset (default small detector) via dbex.data_load.DataLoad, build the mapping context, instantiate nanobrag_torch.models.Crystal from the same CrystalConfig (respecting calibration metadata/N_cells), and emit JSON + summary files comparing nanobrag_torch reciprocal vectors against dxtbx crystal.get_A() plus the current HKL stats.
- Implement: plans/active/ARCH-SIM-HKL-BOUNDS-001/reports/2025-12-03T161200Z/summary.md — Summarize the probe findings (A* deltas, HKL ranges, in-bounds fraction) and cite the JSON/CLI command.
- Validate: pytest -vv tests/dbex/test_data_load_sigma_map.py

How-To Map:
- Run the probe (CPU to keep it deterministic): `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-HKL-BOUNDS-001/bin/probe_crystal_hkl_alignment.py --detector-size small --out-dir plans/active/ARCH-SIM-HKL-BOUNDS-001/reports/2025-12-03T161200Z/ --device cpu`
- After artifacts are written, create the Markdown summary in the same directory describing the measured offsets and HKL coverage.
- Guardrail pytest for regression confidence: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv tests/dbex/test_data_load_sigma_map.py`

Pitfalls To Avoid:
- Do not mutate MappingStageAContext inputs in-place; copy tensors before moving them between devices.
- Keep dataset paths canonical (refGeom, scaled.mtz, 747_mask.pkl); no ad-hoc fixtures.
- Import nanobrag_torch after pushing the repo root onto sys.path so the editable install is used, not /home/ollie/Documents/nanoBragg fallbacks.
- Respect calibration metadata (spot_scale_override, N_cells) when building CrystalConfig so the probe mirrors Stage-A zero-point semantics.
- Clamp tensor-to-numpy conversions via `.detach().cpu().numpy()` — avoid `.item()` on vectors that still require gradients.
- Capture both JSON metrics and human-readable summary; the findings update depends on both.
- Run with `NANOBRAGG_DISABLE_COMPILE=1` to avoid compile cache churn during diagnostics.
- Do not delete or overwrite prior DIAG artifacts; use the new timestamped reports directory.

If Blocked:
- If nanobrag_torch import fails or DataLoad cannot open the smoke dataset, record the full stack trace, drop a stub summary in the artifacts directory, and mark ARCH-SIM-HKL-BOUNDS-001 as blocked with the error signature in docs/fix_plan.md and galph_memory.md (include which asset path failed).

Findings Applied (Mandatory):
- docs/findings.md:51 (DIAG-OVERSAMPLE-001) — HKL stats prove Stage-A and mapping both miss the grid; this probe must quantify the underlying reciprocal-space mismatch before any fix is attempted.

Pointers:
- docs/spec-db-core.md:20 (geometry + HKL mapping contract)
- docs/spec-db-conformance.md:261 (DB-AT-024/027/028 zero-point requirements)
- plans/active/ARCH-SIM-HKL-BOUNDS-001/implementation.md
- docs/findings.md:51 (DIAG-OVERSAMPLE-001 evidence)

Next Up (optional):
- Once the probe is in place, Phase B will isolate the misalignment inside `create_crystal_config` or `nanobrag_torch.models.crystal.Crystal` so we can repair the HKL coverage.
