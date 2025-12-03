# Input for Ralph — Loop 2025-12-03T064931Z

## Summary
Capture a deterministic simulator trace proving the crystal/cell tensors and HKL lookup use inconsistent units so we can target the real root cause of the zero-output Stage A failures.

## Mode
Parity

## InitiativeType
diagnostics

## Focus
DIAG-NANOBRAGG-OVERSAMPLE-001 — nanobrag_torch Oversample Parameter Investigation

## Branch
integration

## Mapped tests
none — evidence-only

## Artifacts
plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/<timestamp>/

## Do Now

### Implement: plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/bin/trace_simulator_mismatch.py
1. Build a Tier‑2 diagnostic script that:
   - Loads `refGeom.expt`, `refGeom.refl`, `scaled.mtz`, and `747_mask.pkl` from repo root (no reliance on missing `sp.proc` fixtures).
   - Uses `create_beam_config`, `create_detector_config(..., oversample=3)`, and `create_crystal_config` to recreate the Stage A simulator inputs (nearest-neighbor only).
   - Instantiates `nanobrag_torch.simulator.Simulator` with `debug_config={'trace_pixel': [0, 0], 'printout': True}` so the console trace logs scattering vectors, rotated real/reciprocal vectors, HKL fractions, and intensity chain for pixel (fast=0, slow=0).
   - Writes both the raw trace log and a concise JSON summary (`beam_config`, `scattering_vec`, `rot_a/b/c`, `hkl_frac`, etc.) into `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/<timestamp>/`.

### Run + analyse the trace
2. Collect artifacts with a UTC timestamp and stash the outputs:
   ```bash
   timestamp=$(date -u +%Y-%m-%dT%H%M%SZ)
   report_dir=plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/$timestamp
   mkdir -p "$report_dir"
   python plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/bin/trace_simulator_mismatch.py \
     --output "$report_dir" \
     --trace-pixel 0 0
   ```
3. Review the generated log + JSON and confirm whether:
   - `scattering_vec` magnitudes are O(10^9) while `rot_a/b/c` magnitudes are O(10^-9).
   - `hkl_frac` stays ≈10^-9 despite HKL metadata spanning tens, proving HKL lookup always falls back to `default_F=0`.
4. Summarize the findings and hypotheses (unit mismatch between crystal tensors and scattering vectors, next fix targets) in `"$report_dir"/crystal_unit_analysis.md`, referencing DIAG-UNIT-001.

## How-To Map

```bash
timestamp=$(date -u +%Y-%m-%dT%H%M%SZ)
report_dir=plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/$timestamp
mkdir -p "$report_dir"
python plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/bin/trace_simulator_mismatch.py \
  --output "$report_dir" \
  --trace-pixel 0 0
vim "$report_dir"/crystal_unit_analysis.md
```

## Pitfalls To Avoid

- Stay evidence-only: no edits to production modules yet (Environment Freeze exception already documented under DIAG).
- Use repo-root fixtures (`refGeom.*`, `scaled.mtz`, `747_mask.pkl`) so the script does not fail on missing `sp.proc` assets.
- Capture the trace into files inside the timestamped report dir—do not leave giant logs in stdout.
- If imports fail, record the exact stack trace/log and exit non-zero so the block is obvious.
- Keep script deterministic (CPU, single panel) so future loops can diff traces.

## If Blocked

If the script cannot run (missing fixtures, nanobrag_torch import failure, etc.):
1. Save the failure log to `"$report_dir"/trace_failure.log`.
2. Note the blocker in `"$report_dir"/summary.md` and notify Galph so we can decide whether to fetch fixtures or downgrade scope.
3. Update docs/fix_plan.md Attempts History accordingly.

## Findings Applied

- DIAG-UNIT-001 — crystal/cell tensors in meters vs scattering vectors in Å⁻¹ collapses HKL lookup to `default_F=0`.
- DIAG-FLUX-001 — retracted; flux default already neutral and does not resolve zero-output.

## Pointers

- plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/implementation.md (Phase D checklist)
- plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T064931Z/simulator_trace.log (manual reference)
- docs/findings.md (DIAG-UNIT-001 entry)

## Next Up

- After evidence lands, plan Phase E to harmonize units inside `nanobrag_torch.models.Crystal` / `compute_physics_for_position` so DB-AT-028/029 can actually light up.
