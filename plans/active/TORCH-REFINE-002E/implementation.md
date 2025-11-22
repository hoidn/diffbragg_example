# TORCH-REFINE-002E — Fix Stage A Zero-Point Geometry Discontinuity

Status: in_progress  
Spec Owners: docs/spec-db-workflow.md, docs/spec-db-core.md, docs/spec-db-conformance.md  
Evidence Root: `plans/active/TORCH-REFINE-002E/reports/`

## Scope

- Align Stage‑A explicit cell+misset parameterizations with the DB‑AT‑024 mapping geometry so that
  zero geometry deltas reproduce the mapping forward model (Bragg tensor + chi-squared) within
  floating‑point tolerance.
- Provide plan‑local tooling to inspect A*/U matrices and trace optimizer behavior when Stage‑A
  degrees of freedom are enabled on top of the mapping zero point.

## Phases

1. **Phase A — Matrix Diagnosis**
   - Author `bin/probe_crystal_matrix_parity.py` to compare MOSFLM‑injected A* (mapping path) with
     Stage‑A explicit cell+misset A* (parameterization path).
   - Emit `crystal_matrix_parity.json` with `max_abs_diff`, Frobenius norm, and `U_error` diagnostics
     under `reports/<ts>/`.

2. **Phase B — Derivation Repair**
   - Implement `derive_robust_misset` and refactor `compute_baseline_misset_deg` so baseline misset
     is derived from `A* = U·B_ideal` with `U = A*·B_ideal^{-1}` projected to a proper rotation and
     inverted to XYZ Euler angles (GEOMETRY‑003).
   - Wire the robust baseline misset into Stage‑A mapping helpers (e.g. `stage_a_mapping_adam_debug`)
     so their zero‑parameter configuration uses the mapping orientation even when `crystal_overrides`
     disable MOSFLM A* injection.

3. **Phase C — Validation**
   - Rerun `test_stage_a_expansion` and Stage‑A mapping debug phases 1–5 to confirm:
     - Stage‑A expansion smoke remains green.
     - Matrix parity probe reports `max_abs_diff` at or below floating‑point noise.
     - Mapping‑aligned Stage‑A Adam experiments show stable or improving chi-squared and ROI
       correlations for the blockwise variants, with particular scrutiny on `A_scale_only` and `D_full`.

## Notes

- Environment Freeze applies; do not modify external packages or toolchains. All geometry changes
  must be confined to the `dbex` bridge/refinement stack and plan‑local tooling.
- Upstream `nanobrag_torch` behavior (e.g., sample clipping, tricubic interpolation) is treated as
  authoritative; any suspected issues should be logged as external findings rather than patched
  locally in this loop.

