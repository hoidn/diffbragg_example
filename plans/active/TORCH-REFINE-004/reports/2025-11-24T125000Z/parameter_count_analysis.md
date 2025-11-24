# Phase 6 Parameter Count Analysis

## Test Fixture Space Group

**MTZ File:** `tests/fixtures/golden_data/simple_cubic/refined_structure_factors.mtz`

**Space Group:** P 1 (No. 1) — Triclinic, no symmetry

**Unit Cell:** (27.41, 32.12, 34.50, 88.66°, 71.55°, 68.10°)

**Total Reflections (with Bijvoet mates):** 69,614

**Space Group Order:** 1 (no symmetry operations except identity)

**Estimated ASU Unique Reflections:** ~69,614 (P1 has no symmetry, so ASU = full sphere)

## Parameter Count Estimates by Space Group

| Space Group | Symmetry | Order | ASU Fraction | Estimated n_asu (typical protein) |
|-------------|----------|-------|--------------|-----------------------------------|
| P1 | Triclinic | 1 | 1/1 | 50K-100K |
| P21 | Monoclinic | 2 | 1/2 | 25K-50K |
| P212121 | Orthorhombic | 4 | 1/4 | 12K-25K |
| P43212 | Tetragonal | 8 | 1/8 | 6K-12K |
| P432 | Cubic | 48 | 1/48 | 1K-2K |

**Source:** Symmetry order from International Tables for Crystallography. ASU fraction = 1/order for centrosymmetric groups (Friedel pairs reduce by additional factor 2 when anomalous_flag=False).

## Test Fixture Analysis

**Fixture Space Group:** P1 (No. 1)

**Implications:**
- P1 has **NO symmetry operations** (order=1)
- ASU = full reciprocal sphere (every reflection is unique)
- Bijvoet mates (+h,k,l) and (-h,-k,-l) are treated as equivalent (anomalous_flag=False reduces count by ~2x)
- **Effective n_asu ≈ 69,614 / 2 ≈ 35,000** unique ASU reflections (accounting for Friedel pairs)

**Parameter Count:** ~35K trainable modifiers + 1 fixed halo modifier (index 0)

**Total Parameters:** ~35,001

## Optimizer Choice Recommendation

### Parameter Count Gate

**Threshold:** 10,000 unique ASU reflections

**Logic:**
```python
if n_asu_unique < 10000:
    optimizer = "LBFGS"  # Spec default per spec-db-workflow.md:107
else:
    optimizer = "Adam"   # Spec-permitted for large parameter counts
    learning_rate = 1e-3  # Default heuristic
```

### Test Fixture Decision

**n_asu ≈ 35,000 > 10,000 threshold**

**Recommended Optimizer:** **Adam** (with learning rate 1e-3)

**Rationale:**
1. LBFGS limited-memory approximation degrades with >10K parameters
2. LBFGS requires full closure recomputation per line search (expensive for 35K parameters)
3. Adam scales linearly with parameter count, no line search overhead
4. Spec permits Adam: "Stage B MAY use L-BFGS or Adam" (spec-db-workflow.md:107)

### Learning Rate Heuristics

**Adam Default:** 1e-3
- Standard starting point for Adam optimization
- Per-parameter adaptive learning rates handle scale differences

**Fallback:** 1e-4
- If 1e-3 causes instability or divergence
- More conservative, slower convergence

**Schedule:** Fixed learning rate initially, optional decay after plateau detection

## Memory Considerations

### ASU Index Map Storage

**HKL Grid Size:** ~512³ voxels (typical for d_min=1.5Å on 50Å unit cell)

**HKL ASU Map:** (512, 512, 512) int64 → ~1.07 GB GPU memory

**Breakdown:**
- 512³ = 134,217,728 voxels
- int64 = 8 bytes per voxel
- Total: 134,217,728 × 8 = 1,073,741,824 bytes ≈ 1.07 GB

**Impact:** Acceptable for modern GPUs (≥8GB VRAM). Stored once during Stage B setup, reused per iteration.

### ASU Modifiers Storage

**n_asu_unique:** ~35,000

**log_modifiers Parameter:** (35000,) float32 → ~140 KB GPU memory

**Gradient Storage:** (35000,) float32 → ~140 KB

**Optimizer State (Adam):** 2× parameters (m, v) → ~280 KB

**Total Stage B Memory Overhead:** ~1.07 GB (map) + 0.56 MB (params + gradients + optimizer) ≈ **1.07 GB**

**Memory Budget:** Acceptable. Stage A baseline uses ~3-5 GB for HKL grid + detector tensors.

## Parameter Count Summary

**Test Fixture (P1):**
- Space Group: P1 (No. 1)
- Estimated n_asu: ~35,000 unique ASU reflections
- Recommended Optimizer: Adam (learning rate 1e-3)
- Memory Overhead: ~1.07 GB GPU memory

**Typical Space Groups:**
- P1: 50K-100K parameters → Adam required
- P21: 25K-50K parameters → Adam recommended
- P432: 1K-2K parameters → LBFGS feasible

**Gate Threshold:** 10,000 ASU reflections (LBFGS vs Adam decision point)

## Findings for Implementation

**REFINE-006 (ASU Parameter Count):** P1 test fixture has ~35K unique ASU reflections, requiring Adam optimizer (spec-permitted per spec:107). Dynamic optimizer selection based on n_asu_unique threshold (10K gate) ensures LBFGS remains default for high-symmetry space groups while scaling to P1/P21 low-symmetry cases.

**POLICY-001 (Environment Freeze):** cctbx.miller API confirmed available (tested 2025-11-24T125000Z). Use existing cctbx installation, no new packages required.
