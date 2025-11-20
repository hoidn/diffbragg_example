# EXT-REQ-001 — Sparse HKL Support Request (nanobrag_torch)

## Context
Stage B now enforces ASU-constrained structure-factor refinement. dbex must map a compact vector of per-ASU multipliers (`G_asu`) onto the dense P1 HKL grid (`hkl_data`) before every forward pass and gather gradients back after each backward pass. Because `N_unique << N_voxels`, this scatter/gather is both memory-heavy and awkward to maintain purely in the orchestration layer.

## Request
- **Subject:** Differentiable sparse scatter/gather helper ("SparseCrystal") in nanobrag_torch.
- **Question to maintainer:** Can nanobrag_torch accept HKL data as a sparse tensor or `(indices, values)` tuple and apply multipliers internally, keeping the symmetry mapping intact?
- **Expected benefit:** ~90% reduction in HKL memory footprint for P1 grids, simplified ASU parameter plumbing, fewer Python-side copies, and lower risk of symmetry mismatches.

## Priority & Interim Plan
- **Priority:** Low (optimization). v1 will implement scatter/gather inside dbex to satisfy the spec immediately.
- **Interim:** Document the ASU map contract in the bridge and keep the sparse request on the maintainer’s radar so future nanobrag_torch releases can adopt a native sparse HKL path.
