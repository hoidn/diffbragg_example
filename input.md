# Input for Ralph — TORCH-GEOMETRY-PARITY-003 Phase A Evidence Synthesis

## Summary
Investigate root cause of `det(U₀)=1.000557` from mapping MOSFLM A*, synthesize dxtbx audit evidence, and document hypotheses before committing to hybrid parameterization design.

## Mode
none

## Focus
TORCH-GEOMETRY-PARITY-003 — Investigate det(U)≠1 Root Cause & Implement Hybrid Parameterization (Phase A: Root Cause Investigation)

## Branch
integration

## Mapped tests
none — evidence-only

## Artifacts
`plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T121500Z/`

## Do Now

**Phase A0: Evidence Synthesis**
1. Create `plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T121500Z/phase_a0_evidence_synthesis.md` documenting:
   - Summary of PARITY-002 Phase C1 findings (raw U-matrix parity=3.5e-18, det(U₀)=1.000557, quaternion parity=~4e-05)
   - Summary of PARITY-002 Phase C2/C3 failure metrics (A_scale_only: chi² +125687%, CC→-0.045)
   - Key question: Why is det(U)≠1, and what does the 0.06% volume offset represent?

**Phase A1: dxtbx A*/Cell Audit (PRIMARY TASK)**
2. Implement analysis script `plans/active/TORCH-GEOMETRY-PARITY-003/bin/audit_dxtbx_a_star_cell.py` (T2-tier script with argparse, see scriptization policy) to:
   - Load canonical refGeom experiment from `sp.proc/refGeom.expt`
   - Extract `crystal.get_A()` (9-element tuple, row-major) and reshape to (3,3)
   - Extract `crystal.get_unit_cell()` parameters (a, b, c, α, β, γ)
   - Compute `B_ideal = reciprocal_matrix_from_unit_cell(cell)` using `cctbx.uctbx.unit_cell(...).fractionalization_matrix().reshape(3,3).T`
   - Derive `U_from_dxtbx = A_star @ inv(B_ideal)`
   - Compute `det(A_star)`, `det(B_ideal)`, `det(U_from_dxtbx)`
   - Check if dxtbx has `crystal.get_B()` API (test via try/except); if it exists, compare against `B_ideal`
   - Compute isotropic scale factor: `s = det(U_from_dxtbx)^(1/3)` (cube root of determinant)
   - Validate identity: `A_star ≈ U_from_dxtbx @ B_ideal` (max abs diff)
   - Emit JSON report: `dxtbx_a_star_cell_audit.json` with all metrics
3. Run the script: `python plans/active/TORCH-GEOMETRY-PARITY-003/bin/audit_dxtbx_a_star_cell.py --expt sp.proc/refGeom.expt --out plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T121500Z/dxtbx_a_star_cell_audit.json`
4. Archive console output to `plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T121500Z/audit_dxtbx.log`

**Phase A2: Metadata Review**
5. Inspect `sp.proc/refGeom.expt` (DIALS experiment JSON) for:
   - Calibration metadata (check for scale factors, processing history, upstream refinement flags)
   - Environmental conditions (temperature, pressure if recorded)
   - MOSFLM or DIALS indexing parameters
6. Document findings in `plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T121500Z/metadata_review.md`

**Phase A3: Numerical Precision Test**
7. Validate cctbx fractionalization_matrix roundtrip stability:
   - Start with known unit cell (a, b, c, α, β, γ) from dxtbx crystal
   - Compute `B_ideal = cctbx_cell(...).fractionalization_matrix().reshape(3,3).T`
   - Reconstruct cell from B_ideal: extract lengths and angles
   - Measure roundtrip error (max abs difference in parameters)
8. Confirm det(U) computation is numerically stable (no float32/float64 truncation issues)
9. Document results in `plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T121500Z/numerical_precision_test.md`

**Phase A4: Hypothesis Decision**
10. Synthesize A0-A3 results into `plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T121500Z/phase_a_root_cause_determination.md`:
    - Primary hypothesis verdict (H1: dxtbx inconsistency, H2: physical scaling, H3: numerical error, or combination)
    - Evidence supporting/refuting each hypothesis
    - Confidence level (high/medium/low) for root cause
    - Recommendation for Phase B parameterization approach
    - If root cause remains ambiguous, document as "empirical det offset" and note that hybrid parameterization must accommodate it regardless

## How-To Map

**A1 Script Implementation (dxtbx audit):**
```bash
# Location: plans/active/TORCH-GEOMETRY-PARITY-003/bin/audit_dxtbx_a_star_cell.py
# Template header (see scriptization policy T2):
#!/usr/bin/env python3
"""
Audit dxtbx A*/cell relationship to investigate det(U)≠1 (initiative: TORCH-GEOMETRY-PARITY-003, owner: galph)
Inputs: --expt <path to DIALS experiment JSON>
Outputs: dxtbx_a_star_cell_audit.json under --out
Repro: python plans/active/TORCH-GEOMETRY-PARITY-003/bin/audit_dxtbx_a_star_cell.py --expt sp.proc/refGeom.expt --out <artifacts>/dxtbx_a_star_cell_audit.json
"""
import argparse
import json
import numpy as np
from dxtbx.model import ExperimentList
from cctbx import uctbx

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--expt', required=True, help='Path to DIALS experiment file')
    ap.add_argument('--out', required=True, help='Output JSON path')
    args = ap.parse_args()

    # Load experiment
    experiments = ExperimentList.from_file(args.expt, check_format=False)
    crystal = experiments[0].crystal

    # Extract A* (reshape from 9-element tuple to 3x3)
    A_star_tuple = crystal.get_A()
    A_star = np.array(A_star_tuple).reshape(3, 3)

    # Extract unit cell
    cell = crystal.get_unit_cell()
    a, b, c, alpha_deg, beta_deg, gamma_deg = cell.parameters()

    # Compute B_ideal using cctbx
    cctbx_cell = uctbx.unit_cell((a, b, c, alpha_deg, beta_deg, gamma_deg))
    B_ideal_flat = np.array(cctbx_cell.fractionalization_matrix())
    B_ideal = B_ideal_flat.reshape(3, 3).T  # Transpose to match MOSFLM convention

    # Derive U from A* and B_ideal
    U_from_dxtbx = A_star @ np.linalg.inv(B_ideal)

    # Compute determinants
    det_A = float(np.linalg.det(A_star))
    det_B = float(np.linalg.det(B_ideal))
    det_U = float(np.linalg.det(U_from_dxtbx))

    # Isotropic scale (cube root of det)
    s_isotropic = det_U ** (1.0 / 3.0)

    # Validate identity: A* ≈ U @ B_ideal
    A_star_reconstructed = U_from_dxtbx @ B_ideal
    max_abs_diff = float(np.max(np.abs(A_star - A_star_reconstructed)))

    # Check for crystal.get_B() API
    has_get_B = hasattr(crystal, 'get_B')
    B_dxtbx_match = None
    if has_get_B:
        B_dxtbx_tuple = crystal.get_B()
        B_dxtbx = np.array(B_dxtbx_tuple).reshape(3, 3)
        B_dxtbx_match = float(np.max(np.abs(B_ideal - B_dxtbx)))

    # Assemble report
    report = {
        "experiment_path": args.expt,
        "cell_parameters": {
            "a": float(a), "b": float(b), "c": float(c),
            "alpha_deg": float(alpha_deg), "beta_deg": float(beta_deg), "gamma_deg": float(gamma_deg)
        },
        "det_A_star": det_A,
        "det_B_ideal": det_B,
        "det_U_from_dxtbx": det_U,
        "isotropic_scale_factor": s_isotropic,
        "volume_offset_percent": 100.0 * (det_U - 1.0),
        "A_star_identity_max_abs_diff": max_abs_diff,
        "dxtbx_has_get_B": has_get_B,
        "B_dxtbx_vs_B_ideal_max_diff": B_dxtbx_match
    }

    with open(args.out, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"dxtbx audit complete. det(U)={det_U:.6f}, isotropic_scale={s_isotropic:.6f}")
    print(f"Report written to {args.out}")

if __name__ == "__main__":
    main()
```

**Execution:**
```bash
cd /home/ollie/Documents/diffbragg_example
python plans/active/TORCH-GEOMETRY-PARITY-003/bin/audit_dxtbx_a_star_cell.py \
  --expt sp.proc/refGeom.expt \
  --out plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T121500Z/dxtbx_a_star_cell_audit.json \
  > plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T121500Z/audit_dxtbx.log 2>&1
```

**A2 Metadata Review:**
```bash
# Inspect experiment JSON for calibration metadata
python -c "from dxtbx.model import ExperimentList; \
  expts = ExperimentList.from_file('sp.proc/refGeom.expt', check_format=False); \
  import json; \
  print(json.dumps(expts[0].imageset.get_template(), indent=2))" \
  > plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T121500Z/metadata_snippet.txt 2>&1

# Manual inspection for processing history, indexing flags, environmental metadata
# Document findings in metadata_review.md
```

**A3 Numerical Precision Test:**
```python
# Inline probe (T1 — document in phase_a_root_cause_determination.md, not a separate script):
from cctbx import uctbx
import numpy as np

# Use canonical cell from dxtbx audit
a, b, c, alpha, beta, gamma = <extracted values>
cell_original = uctbx.unit_cell((a, b, c, alpha, beta, gamma))
B_ideal = np.array(cell_original.fractionalization_matrix()).reshape(3, 3).T

# Roundtrip: extract cell from B_ideal (inverse operation)
# (This may require manual matrix → cell parameter inversion; document the method used)
# Measure max abs error in (a', b', c', α', β', γ') vs original

# Validate det(U) computation stability
U_test = <sample 3x3 matrix with det ≈ 1.000557>
det_float32 = np.linalg.det(U_test.astype(np.float32))
det_float64 = np.linalg.det(U_test.astype(np.float64))
# Compare: should agree to ~1e-7
```

## Pitfalls To Avoid

1. **dxtbx API conventions**: `crystal.get_A()` returns 9-element tuple (row-major), NOT numpy array. Always `np.array(...).reshape(3,3)`. See DXTBX-001.
2. **cctbx fractionalization_matrix quirk**: Returns flat (9,) array. MUST `.reshape(3,3).T` to get proper B_ideal matrix. See TORCH-GEOMETRY-PARITY-002 Phase C2 shape bug.
3. **Protected Assets**: Do NOT modify `dbex/nanobrag_bridge.py`, `dbex/nanobrag_refinement.py`, or any production code in Phase A. This is evidence-only.
4. **Environment Freeze**: Assume frozen environment. If dxtbx API is missing (e.g., no `crystal.get_B()`), document as "not available" and proceed with B_ideal computed from unit cell.
5. **Scriptization policy**: Phase A1 audit script is T2 (decision-carrying, reused for validation). Include argparse, docstring header, and explicit output path.
6. **No spec paraphrasing**: Reference exact spec sections (e.g., "See `docs/spec-db-core.md §Geometry Mapping`") for matrix identities, not pseudo-code.

## If Blocked

- If `sp.proc/refGeom.expt` is missing or corrupted: check `sp.proc/` directory for alternative experiment files; document the blocker in `phase_a_root_cause_determination.md` and mark Phase A incomplete.
- If dxtbx import fails (environment issue): record exact error signature in Attempts History; do NOT attempt pip install. Mark blocked.
- If det(U) computation yields unexpected values (e.g., det<<1 or det>>1): document the anomaly, capture all intermediate matrices (A*, B_ideal, U) in the audit JSON, and flag for supervisor review.

## Findings Applied

- **DXTBX-001** (Active): dxtbx `crystal.get_A()` returns 9-element tuple (row-major) not numpy array; reshape as `np.array(A_tuple).reshape(3,3)`.
- **GEOMETRY-003** (Active): B_ideal-based mapping misset decomposition (current baseline; to be superseded by GEOMETRY-004 from this initiative).
- **No relevant findings** for det(U) investigation in the knowledge base yet; this initiative will create GEOMETRY-004 to document the root cause and parameterization choice.

## Pointers

- Escalation source: `plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T120500Z/phase_c2_c3_decision.json` (catastrophic failure metrics)
- Root cause context: `plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T113409Z/phase_c1_parity_failure_diagnosis.md` (alternative paths analysis)
- Spec alignment: `docs/spec-db-core.md:39-46` (Geometry Mapping), `docs/spec-db-workflow.md §Stage A` (mapping zero-point invariant)
- Implementation plan: `plans/active/TORCH-GEOMETRY-PARITY-003/implementation.md:41-66` (Phase A checklist + hypotheses)
- Fix plan ledger: `docs/fix_plan.md:81-95` (TORCH-GEOMETRY-PARITY-003 entry)

## Next Up (optional)

If Phase A evidence is conclusive:
- Phase B0: Design Evaluation Matrix (document Options 1-3 with DOF count, initialization formula, gradient flow sketch)
- Phase B1: Prototype isotropic scale extraction (`s = det(U)^(1/3)`)
