### ARCH-SIM-CONSTRUCTION-001: SQUARE normalization fix (2026-01-06T200000Z)

**Attempt #i=71**
- **What changed**: Implemented SQUARE lattice integral normalization per C.35 plan—lines 1086-1099 in `src/nanobrag-torch/src/nanobrag_torch/simulator.py` now set `oversample_norm=1` for CrystalShape.SQUARE (dropping `oversample²` factor), while GAUSS/TOPHAT/ROUND retain mean semantics (`oversample²`). Added `steps_scalar` emission via `_partiality_stats` for validation.
- **What test**: Single-pixel probe (oversample=13, N_cells=41,29,32), architecture enforcement test (`tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells`), DB-AT-028/029 (deferred—tests block based on acceptance failure)
- **Outcome**: **BLOCKED—Normalization fix correct per spec but parity NOT restored**
  - Implementation: ✅ CORRECT (steps_scalar==1 confirmed for SQUARE by test assertions)
  - Parity validation: ❌ FAILED (observed ratio 601M vs expected 1.45B = 41% error, tolerance 1%)
  - Root cause: **Sampling density issue**, not normalization bug
- **First Divergence**: SQUARE sincg peaks have width ~1/N_cells. For N_cells=(41,29,32) with oversample=13:
  - Single-pixel probe: 0/169 subpixels hit central lobe → 0.0058% of expected intensity
  - 10×10 detector test: ~41% of pixels well-aligned → 41% of expected intensity
  - Conclusion: Even with correct normalization, most pixels lack subpixels within narrow sincg peaks
- **Metrics**:
  - Test (10×10 detector): observed ratio = 601,278,195 (cpu) / 600,785,136 (cuda), expected = 1,447,650,304, relative error = 58.47% / 58.50% (tolerance 1%)
  - Probe (1×1 detector): observed ratio = 84,612.7, expected = 1,447,650,304, relative error = 99.99%
  - steps_scalar assertions: ✅ PASS (steps_scalar == 1 for SQUARE, both cpu/cuda)
  - Subpixel coverage (probe): 0/169 samples (0.00%) in central sincg lobe
- **Artifacts**: `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-06T200000Z/` (BLOCKED.md, square_lattice_probe.log, square_lattice_scaling.{json,md}, pytest_partiality.log)
- **Status**: **BLOCKED—sampling density insufficient for SQUARE lattice parity**
- **Next Hypothesized Divergence Boundary**: Per input.md line 40-41: "Apply the normalization fix; if `(Na·Nb·Nc)²` parity still fails, escalate to spec_change or revisit the sincg accumulation math." Normalization fix applied ✓, parity fails (58% error) ✗. Escalation required.
- **Blocker ID**: ARCH-SIM-CONSTRUCTION-001-PARITY-SAMPLING-001
- **Escalation Recommendations**:
  1. **spec_change**: Re-evaluate whether SQUARE lattice shape is appropriate for Stage-A smoke tests with oversample=13; consider relaxing tolerance to ~50% or restricting SQUARE to high-oversample scenarios (e.g., oversample=41 to guarantee Δ=0 sampling on all axes)
  2. **OR increase oversample**: Test with oversample=max(Na,Nb,Nc) to ensure at least one subpixel per axis lands in the sincg peak
  3. **OR adaptive sampling**: Implement peak-aware subpixel placement for SQUARE shape (architecture change, not bugfix)
  4. **OR change test expectations**: If 41% parity is acceptable, update test tolerance and spec accordingly
- **Finding**: docs/findings.md::SIM-CONSTR-PARTIALITY-001 (normalization fix documented; escalation note pending final decision)
- **Patch**: Implementation already committed in prior loop (lines 1086-1099 present in current code)
- **Environment**: No rebuild required (implementation pre-existing in codebase from previous C.33/C.34 work)
