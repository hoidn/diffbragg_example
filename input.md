Summary: Extend the A* parity probe to decompose the residual U_error into rotation vs strain components and diagnose the 4e-5 matrix gap.
Mode: none
Focus: TORCH-REFINE-002E — Fix Stage A Zero-Point Geometry Discontinuity
Branch: integration
Mapped tests: none — evidence-only
Artifacts: plans/active/TORCH-REFINE-002E/reports/2025-11-22T090505Z/

Do Now:
- Focus Item: TORCH-REFINE-002E
- Implement: plans/active/TORCH-REFINE-002E/bin/probe_crystal_matrix_parity.py — extend Phase A0 diagnostics per implementation.md checklist A0. Add eigenvalue/singular-value decomposition of A*_pathA and A*_pathB, symmetric/antisymmetric decomposition of `logm(U_error)` to separate pure rotation from strain, and per-column norm + angle comparisons for reciprocal vectors a*/b*/c*.
- Implement: Save extended metrics to `plans/active/TORCH-REFINE-002E/reports/2025-11-22T090505Z/crystal_matrix_parity_extended.json` so we can quantify whether the 4e-5 gap is dominated by rotational error or symmetric strain.
- Test: Run the extended probe on canonical refGeom assets via `python plans/active/TORCH-REFINE-002E/bin/probe_crystal_matrix_parity.py --expt sp.proc/refGeom.expt --refl sp.proc/refGeom.refl --mtz scaled.mtz --mask 747_mask.pkl --calibration tests/fixtures/golden_data/simple_cubic/config_torch.json --refined-mtz tests/fixtures/golden_data/simple_cubic/refined_structure_factors.mtz --output plans/active/TORCH-REFINE-002E/reports/2025-11-22T090505Z/crystal_matrix_parity_extended.json | tee plans/active/TORCH-REFINE-002E/reports/2025-11-22T090505Z/probe_extended.log`

How-To Map:
1. Extend `probe_crystal_matrix_parity.py` with a new helper function `compute_extended_diagnostics(A_star_pathA, A_star_pathB, U_error)` that:
   - Computes eigenvalues of both A* matrices via `np.linalg.eigvalsh()` (symmetric part only for now; if needed, use `np.linalg.eig()` for full eigendecomposition).
   - Computes singular values via `np.linalg.svd()` to quantify scaling/strain in the principal axes.
   - Forms `log_U = scipy.linalg.logm(U_error)` and decomposes it into symmetric `(log_U + log_U.T)/2` and antisymmetric `(log_U - log_U.T)/2` parts so we can see how much of the error is a pure rotation vs a symmetric stretch.
   - Computes per-column norms (`||a*_A||`, `||a*_B||`, etc.) and inter-column angles for the reciprocal vectors to see if lattice distortion is axis-dependent.
2. Update the `MatrixParitySummary` dataclass to include new fields: `A_star_pathA_eigenvalues`, `A_star_pathB_eigenvalues`, `A_star_pathA_singular_values`, `A_star_pathB_singular_values`, `log_U_symmetric_norm`, `log_U_antisymmetric_norm`, `reciprocal_column_norms`, `reciprocal_column_angles`.
3. Invoke the new helper inside `main()` after computing `U_error` and merge the extended metrics into the summary dict before JSON emission.
4. Run the probe CLI command above with the canonical refGeom assets, capturing the JSON + log under the new artifacts directory.
5. Inspect the JSON to determine whether:
   - `log_U_symmetric_norm` is negligible (< 1e-6) → pure rotation error, focus on numerical/convention fixes.
   - `log_U_symmetric_norm` is significant (≥ 1e-5) → true strain component, investigate baseline B_ideal mismatch or cell recovery.

Pitfalls To Avoid:
- Do not change the baseline misset logic or bridge helpers in this loop; Phase A0 is strictly diagnostic—edits confined to the probe script.
- Preserve the existing JSON schema fields (`max_abs_diff`, `frobenius_norm`, `det_U_error`) so prior artifacts remain comparable.
- Avoid running the probe on refined.expt yet (that's checklist A1); this loop targets refGeom only per the canonical dataset policy.
- Keep imports minimal; `scipy.linalg.logm` is already available in the simtbx environment, so no new dependencies should be added.
- Ensure the probe runs on CPU to avoid CUDA/compile noise; the extended metrics are purely linear algebra on small 3×3 matrices.
- Do not emit log outputs or print statements that could clutter the pytest/CI logs if this probe gets wired into a selector later.
- Capture both the JSON artifact and the probe log under the timestamped directory so fix_plan can cite them in the Attempts History.

If Blocked:
- If `scipy.linalg.logm` is missing or raises import errors, fall back to a simpler Frobenius-norm comparison of `U_error - I` and defer the log-matrix decomposition to a follow-up loop; record the block in `docs/fix_plan.md` Attempts History.
- Should the probe crash on canonical refGeom due to singular A* matrices or degenerate crystal configs, save the stack trace + input paths in `plans/active/TORCH-REFINE-002E/reports/2025-11-22T090505Z/blocker.txt` and mark the initiative blocked so we can triage the geometry bug first.

Findings Applied (Mandatory):
- GEOMETRY-003 — Probe must use the robust baseline misset path (`derive_robust_misset`) when building the Path B crystal config; the existing probe already does this per e8c763b.
- RUNTIME-001 — Probe runs on CPU only (no `--device cuda`); `NANOBRAGG_DISABLE_COMPILE=1` not strictly needed here but harmless.
- CONFIG-001 — Ensure probe reuses the bridge helpers (`create_crystal_config`) with the same conventions (beam center swap, mask polarity, etc.) so A* extraction is consistent with production paths.
- GRADIENT-001 — Probe must avoid `.item()` or `.numpy()` on any tensor that might later participate in autograd; for this diagnostic-only script, all tensors are detached/CPU, so no gradient concerns.

Pointers:
- docs/fix_plan.md:37 — TORCH-REFINE-002E ledger entry, exit criteria, Attempts History.
- plans/active/TORCH-REFINE-002E/implementation.md:82 — Phase A checklist A0 details.
- plans/active/TORCH-REFINE-002E/bin/probe_crystal_matrix_parity.py:1 — Current probe implementation (eigenvalue/logm extensions to be added).
- docs/spec-db-conformance.md — Mapping-Aligned Stage A Initialization clause (normative zero-point requirement).
- docs/findings.md:7 — GEOMETRY-003 finding documenting the baseline misset derivation.

Next Up (optional):
- If the extended probe shows `log_U_symmetric_norm < 1e-6`, proceed to Phase A checklist item A1 (multi-config sweep on refined.expt and synthetic perturbations) to confirm the gap is numerical/convention-only.
- If `log_U_symmetric_norm >= 1e-5`, pivot to Phase A checklist item A2 (baseline B_ideal variants) to test whether using a recovered cell from MOSFLM A* eliminates the strain component.
