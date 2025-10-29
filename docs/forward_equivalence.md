# Forward Equivalence Smoke (Normative)

**Version:** 0.1  
**Date:** 2025-10-29  
**Status:** Active

## 1. Purpose

Establish a lightweight yet informative comparison between the legacy DiffBragg forward model and the `nanobrag_torch` bridge without running refinement. The goal is to ensure geometry/config propagation is correct and that the torch forward pass produces physically plausible intensities before attempting optimisation loops.

Forward equivalence is the only parallel numerical check required between the two backends. Refinement parity is intentionally out of scope; downstream validation should focus on convergence quality rather than identical parameter trajectories.

## 2. Inputs

- DIALS experiment/reflection files and MTZ data ingested through `dbex.data_load.DataLoad`.
- Bridge outputs from `prepare_refinement_inputs`.
- Legacy DiffBragg forward model invoked via `dbex.run_diffbragg`.

## 3. Procedure

1. **Generate Baseline (DiffBragg)**
   - Use the existing DiffBragg path (e.g., `python -m dbex.refine_one --noop ...`) to produce the forward `Bragg` tensor without refinement updates.
   - Persist the result in an artifact directory (HDF5 or NumPy).

2. **Generate Torch Forward**
   - Hydrate the torch configs (detector/beam/crystal) from the bridge outputs.
   - Run `nanobrag_torch` once per panel to obtain the torch `Bragg` tensor.
   - Persist the torch result alongside the DiffBragg output.

3. **Compute Metrics**
   - Sample ROIs (same selection used for smoke testing).
   - For each ROI, compute:
     - Pearson correlation.
     - Maximum absolute pixel difference.
     - Peak localization check (does the brightest pixel fall inside the central half-box?).
   - Aggregate median/percentile statistics.

4. **Optional Trace Capture**
   - Select a representative pixel per panel and emit trace logs (DiffBragg vs torch) to inspect configuration propagation and per-stage values.
   - Record the config objects used to generate each forward pass (detector, beam, crystal) for regression auditing.

5. **Visual Diagnostics (Optional)**
   - Heatmap of `torch - diffbragg`.
   - Overlay plots (DiffBragg, torch, residual).

## 4. Acceptance Thresholds

- Median ROI correlation ≥ 0.2.
- ≥ 90% of sampled ROIs have the brightest pixel within the central half-box.
- No assertion failure when thresholds are missed; instead:
  - Mark the pytest as `xfail` or `skip` with a diagnostic reason.
  - Attach metrics and traces for debugging.

## 5. Artifact Layout

All loop evidence for forward equivalence should live under:

```
plans/active/<initiative>/reports/<YYYY-MM-DDTHHMMSSZ>/forward_equiv/
    legacy/
        bragg_diffbragg.npy (or .h5)
        config_diffbragg.json
    torch/
        bragg_torch.npy
        config_torch.json
    metrics.json
    roi_metrics.csv
    overlays/
        roi_<idx>_diff.png
        roi_<idx>_residual.png
    traces/ (optional)
        roi_<idx>_diffbragg.log
        roi_<idx>_torch.log
```

## 6. Pytest Selector

`KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests -k DB_AT_001`

Guidelines:
- Selector SHOULD xfail (not fail) when thresholds are not met but diagnostics have been captured.
- Tests MUST record artifact paths in the loop report so the supervisor ledger can link to them.

## 7. References

- `plans/nanobrag_integration_plan.md` — Phase 1 forward-equivalence smoke.
- `docs/spec-db-conformance.md` — Forward Equivalence Profile (DB-AT-001).
- `docs/TESTING_GUIDE.md` §2 — Selector mapping.
- `docs/development/TEST_SUITE_INDEX.md` — Registry entry for DB-AT-001.

