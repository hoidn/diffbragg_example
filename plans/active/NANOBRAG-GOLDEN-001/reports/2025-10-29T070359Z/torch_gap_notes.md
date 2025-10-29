# Torch Dataset Gap Notes

## Current Fixture Status
Manifest dataset_name: simple_cubic_fallback
Hashes:
- bragg: 110abca6a4417e0ec577b8098ec0672e88b0fc32168d3f4572b1712016d13241
- loss_mask: 9301d36f09eb6a155bab9f1115e4d8b429866003d272e8892db535965239db82
- metadata: 7e919e5948dfbe7f33b40f664af2d0ffe0bacca97564779ee320d3f541122e91
- target: 3ae4d01ef0a57dd8f38e33882bf25bc83f0e4277e7d7cbee63317ba120672e1c

## Canonical Dataset Gap
No canonical torch outputs present under plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T063817Z/.

The `simple_cubic_fallback` dataset was generated synthetically in PARITY-HARNESS-002 (2025-10-29T010131Z) as a bootstrap fixture to enable DB_AT_001 selector development before real simulator integration.

## Why Canonical Dataset Blocked
Per `plans/active/NANOBRAG-GOLDEN-001/implementation.md`:
- **Phase A2** requires full-panel DiffBragg baseline (`bragg_diffbragg.npy`)
- **Phase A3** requires paired nanobrag_torch forward output for comparison
- DiffBragg `diffBragg_forward` fails with CUDA assertion (see `blocking_summary.md`)
- No full-panel DiffBragg tensor available for paired metrics/manifest

## Plan Re-Scope Options
1. **Accept ROI-level parity**: Revise exit criteria to use `dbex.refine_one` HDF5 outputs (92 ROIs × 12×12)
2. **Decouple captures**: Generate torch tensors independently, defer DiffBragg baseline requirement
3. **Wait for simtbx patch**: Block until upstream fixes diffBraggCUDA.cu:708 cleanup bug

## References
- Fallback dataset provenance: `plans/active/PARITY-HARNESS-002/reports/2025-10-29T010131Z/summary.md`
- Blocker documentation: `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T070359Z/blocking_summary.md`
- Spec requirements: `docs/spec-db-core.md:20-41`, `docs/forward_equivalence.md:21-52`
