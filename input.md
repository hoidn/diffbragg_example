Summary: Implement Phase A2 baseline B_ideal variants to test whether deriving B_ideal from mapping's MOSFLM A* eliminates the symmetric strain component.
Mode: none
Focus: TORCH-REFINE-002E — Fix Stage A Zero-Point Geometry Discontinuity
Branch: integration
Mapped tests: none — evidence-only
Artifacts: plans/active/TORCH-REFINE-002E/reports/2025-11-22T091200Z/

Do Now:
- Focus Item: TORCH-REFINE-002E
- Implement: `dbex/nanobrag_bridge.py` — Add `recover_cell_from_a_star(a_star_matrix: np.ndarray) -> tuple[float, float, float, float, float, float]` helper that uses cctbx to recover unit cell parameters (a, b, c, α, β, γ) from a given 3×3 A* reciprocal matrix, enabling alternative B_ideal construction per Phase A2 (implementation.md:90-92).
- Implement: `dbex/nanobrag_bridge.py` — Extend `derive_robust_misset` (or create `derive_misset_with_custom_b_ideal`) to accept an optional `b_ideal_override: np.ndarray | None` parameter so we can test baseline misset derivation against both (1) the current dxtbx unit-cell B_ideal and (2) a recovered-cell B_ideal from mapping's MOSFLM A*.
- Implement: `plans/active/TORCH-REFINE-002E/bin/probe_crystal_matrix_parity.py` — Extend `run_probe` to build TWO Path-B crystal configs: (a) "PathB_unitcell" using the existing baseline misset logic with dxtbx unit cell, and (b) "PathB_recovered" using the MOSFLM A* recovered cell as B_ideal. Emit a JSON payload with side-by-side comparison: `{path_B_unitcell: {max_abs_diff, log_u_symmetric_norm, ...}, path_B_recovered: {...}}` so we can see whether the recovered-cell variant closes the strain gap to <1e-6.
- Test: Run the extended probe on canonical refGeom via `python plans/active/TORCH-REFINE-002E/bin/probe_crystal_matrix_parity.py --device cpu --out-dir plans/active/TORCH-REFINE-002E/reports/2025-11-22T091200Z/` and capture the comparison JSON plus log.

How-To Map:
1. In `dbex/nanobrag_bridge.py`, add a new helper `recover_cell_from_a_star(a_star: np.ndarray) -> tuple[float, float, float, float, float, float]`:
   - Use cctbx's `cctbx.uctbx.unit_cell` to construct a unit cell from the reciprocal basis vectors extracted from `a_star` (columns of A*).
   - cctbx can recover real-space cell parameters via the reciprocal metric tensor or direct inversion; consult `cctbx.uctbx` API docs or existing dials/dxtbx code for the canonical path.
   - Return (a, b, c, alpha_deg, beta_deg, gamma_deg) tuple.
2. Extend `derive_robust_misset` or add `derive_misset_with_custom_b_ideal(a_star_matrix, b_ideal_override, ...)` that computes `U = a_star @ np.linalg.inv(b_ideal_override)`, projects to a proper rotation, and inverts to XYZ Euler angles as in GEOMETRY-003.
3. In `probe_crystal_matrix_parity.py`:
   - After building Path A (MOSFLM A* injection), extract `a_star_A` from the Crystal via `compute_cell_tensors()`.
   - Call `recover_cell_from_a_star(a_star_A)` to get the recovered cell parameters.
   - Build `b_ideal_recovered` from those parameters (via cctbx or manual construction of reciprocal basis).
   - Derive two baseline missets: one with dxtbx unit cell (existing path), one with `b_ideal_recovered`.
   - Construct two Path-B crystals using each baseline misset variant.
   - Compute `U_error_unitcell` and `U_error_recovered`, run extended diagnostics for both, and emit a JSON with side-by-side summary.
4. Execute the probe CLI command above, capturing JSON + log in the new artifact directory.
5. Inspect the JSON to determine:
   - Does `path_B_recovered.log_u_symmetric_norm < 1e-6`? If yes, H2 (baseline cell mismatch) is confirmed and we should update GEOMETRY-003 to use the recovered cell.
   - If both paths still show strain ≈1e-3, we may need to investigate whether the MOSFLM A* itself encodes a non-standard cell or whether the probe's extraction of A* is inconsistent.

Pitfalls To Avoid:
- cctbx import hygiene: ensure `from cctbx import uctbx` is guarded or already present in `dbex/nanobrag_bridge.py`; the simtbx environment should have cctbx available.
- Do not change the existing `derive_robust_misset` signature or GEOMETRY-003 production paths yet; this is still diagnostic. The recovered-cell variant is a parallel test path.
- Preserve the existing JSON schema fields from Phase A0 so the probe output remains comparable.
- Run on CPU only (`--device cpu`) to avoid CUDA/compile noise.
- Ensure the probe emits both `path_B_unitcell` and `path_B_recovered` in the JSON so we can directly compare strain metrics.
- Do not modify the MOSFLM A* injection path (Path A) or `create_crystal_config` helpers; those are the reference.
- If `recover_cell_from_a_star` raises errors or returns degenerate cells, log the failure and defer Phase A2 to a follow-up after investigating cctbx API usage.

If Blocked:
- If cctbx cell recovery API is unclear or missing, fallback to manually computing the reciprocal metric tensor `G* = A*^T A*` and deriving cell parameters via standard crystallographic formulas; document the approach in a comment and capture the block in `docs/fix_plan.md`.
- If the recovered cell produces a singular or non-positive-definite B_ideal, save the intermediate matrices in `plans/active/TORCH-REFINE-002E/reports/2025-11-22T091200Z/blocker_matrices.json` and mark the initiative blocked pending geometry audit.

Findings Applied (Mandatory):
- GEOMETRY-003 — Probe must continue using the robust baseline misset path for the `path_B_unitcell` variant; the `path_B_recovered` variant tests an alternative B_ideal but follows the same misset derivation logic.
- RUNTIME-001 — Probe runs on CPU only.
- DXTBX-001 — When extracting A* from the mapping path, use `compute_cell_tensors()` from nanobrag_torch Crystal, not `crystal.get_A()` from dxtbx.
- GRADIENT-001 — Probe is diagnostic-only, no gradient concerns.

Pointers:
- docs/fix_plan.md:37 — TORCH-REFINE-002E ledger entry.
- plans/active/TORCH-REFINE-002E/implementation.md:90 — Phase A checklist A2 details.
- plans/active/TORCH-REFINE-002E/bin/probe_crystal_matrix_parity.py:1 — Current probe (Phase A0 diagnostics landed).
- dbex/nanobrag_bridge.py:723 — `compute_baseline_misset_deg` (GEOMETRY-003 path).
- dbex/nanobrag_bridge.py:752 — `derive_robust_misset` (existing robust misset logic).
- docs/spec-db-core.md — Geometry Mapping normative spec.
- docs/findings.md:GEOMETRY-003 — Baseline misset derivation policy.

Next Up (optional):
- If `path_B_recovered` closes the strain gap to <1e-6, proceed to Phase C1 (select branch G and update GEOMETRY-003 production paths to use recovered-cell B_ideal).
- If both variants still show strain ≈1e-3, pivot to Phase A3 (mapping forward vs Stage-A config comparison on a single panel/HKL subset) to isolate whether the gap is in the geometry tensors or the probe's extraction logic.
