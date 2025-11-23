# Phase C2.2 Root Cause Analysis v3 — HKL Hit Rate Failure

## Executive Summary

Loop i=218 applied the out-of-place HKL grid fix (`torch.where` replacing in-place assignment) which **successfully resolved the gradient issue on CUDA** (small detector test PASSED), proving Hypothesis A was correct. However, the **full detector CPU fallback path still fails** with the same gradient error.

**Critical New Finding**: HKL hit rate on CPU path is **0%** (zero out of 224 million lookups succeeded). This means **all structure factor lookups return `default_F` (a gradient-free constant)**, breaking the autograd graph even though the HKL grid itself has gradients.

**Updated Root Cause**: The gradient break occurs because Miller indices (h,k,l) computed during CPU simulation are **fundamentally wrong** (k range [-1796,1708] is nonsensical), causing 100% HKL grid misses. This is almost certainly a **crystal parameter or configuration mismatch** between CUDA and CPU StageAContext construction, NOT a nanobrag_torch simulator bug.

## Evidence Chain

### 1. Out-of-Place Fix Works on CUDA

**Small Detector Test** (CUDA warm cache path):
- Status: **PASSED**
- Runtime: 13.75s
- Telemetry: `status='converged'`
- Shell modifiers: Converged with non-zero deltas
- HKL hit rate: Normal (not logged, but simulation succeeds)

**Conclusion**: The `torch.where` fix correctly preserves gradients when HKL lookups succeed.

### 2. CPU Path Has 0% HKL Hit Rate

**Full Detector Test** (CPU fallback path):
```
[HKL stats] h=[0,0] k=[-1796,1708] l=[0,1] hit_rate=0/224064036 (0.00%)
```

**What this means**:
- Across 224 million HKL lookups, **zero** succeeded
- h values: [0,0] (reasonable)
- k values: [-1796, 1708] (WAY out of bounds for typical protein HKL grid)
- l values: [0,1] (reasonable)

**Typical HKL grid bounds** for refGeom dataset: h∈[-20,20], k∈[-20,20], l∈[-20,20] (approximate).

The k-range being in the thousands suggests the Miller indices are being computed with **completely wrong reciprocal lattice vectors or crystal orientation**.

### 3. HKL Gradient Diagnostic Confirms Fix Works

```
[HKL_GRAD_CHECK] hkl_grid_modified.requires_grad=True, grad_fn=<WhereBackward0 object at ...>, device=cpu
```

During the closure call (where gradients matter), the HKL grid tensor has:
- ✅ `requires_grad=True`
- ✅ `grad_fn=<WhereBackward0>` (gradient graph intact)
- ✅ `device=cpu` (correct device)

**Conclusion**: The out-of-place `torch.where` construction is working perfectly. The gradient break happens **downstream** because `get_structure_factor` returns `default_F` for all lookups.

### 4. Why default_F Breaks Gradients

In `nanobrag_torch/models/crystal.py::get_structure_factor`:
```python
# When out of bounds:
F_values = torch.full_like(h, float(self.config.default_F), device=self.device, dtype=self.dtype)
```

This creates a **new tensor filled with a constant** that has **no gradient connection** to `hkl_data` or `shell_modifiers`. Even though `hkl_grid_modified` has gradients, if it's never actually indexed, those gradients can't flow to the loss.

## Root Cause Hypotheses (Ranked by Likelihood)

### Hypothesis 1: Crystal Parameter Mismatch (60% confidence)

**Theory**: When building the CPU StageAContext (line 2209), the crystal parameters passed to `_build_stage_a_context` don't match the CUDA path, resulting in wrong A* matrix or reciprocal lattice vectors.

**Evidence**:
- CPU context built at line 2209: `_build_stage_a_context(detector=detector, beam=beam, crystal=crystal, ...)`
- The `crystal` parameter is the **same dxtbx Crystal object** used for CUDA, so baseline parameters should match
- However, the context builder might apply transformations differently on CPU vs CUDA

**Where to look**:
- `dbex/nanobrag_bridge.py::create_crystal_config` — Does it handle CPU vs CUDA differently?
- `warm_crystal_config` creation at line 2464-2470 — Does `crystal_overrides_eval` differ between devices?
- MOSFLM A* injection — Are the vectors being computed correctly on CPU?

**Fix if confirmed**: One-line parameter correction in CPU context builder or crystal config creation.

### Hypothesis 2: A* Matrix Injection Bug (25% confidence)

**Theory**: When `misset_deg_override` or `crystal_overrides` are applied (line 2467-2469), the MOSFLM A* vectors might be computed incorrectly on CPU, leading to wrong reciprocal lattice.

**Evidence**:
- Stage B uses `crystal_overrides_eval` which includes cell parameter deltas
- GEOMETRY-003 finding documents baseline misset derivation via A* decomposition
- If A* → U,B decomposition differs between CPU/CUDA due to numerical precision, Miller indices will be wrong

**Where to look**:
- `dbex/nanobrag_bridge.py::create_crystal_config` A* injection logic (lines ~450-506 per GRADIENT-001)
- Reciprocal lattice vector computation in `Crystal.get_rotated_real_vectors`

**Fix if confirmed**: Patch to nanobrag_torch Crystal class or bridge helper, documented per POLICY-001.

### Hypothesis 3: Detector Geometry Mismatch (10% confidence)

**Theory**: CPU detector configs have wrong beam vector, pixel coordinates, or distance, leading to wrong scattering vectors and thus wrong Miller indices.

**Evidence**:
- Less likely because detector geometry is device-agnostic
- `_build_stage_a_context` uses same `detector` object for both paths
- Beam vector computation should be deterministic

**Where to look**:
- Beam vector in CPU vs CUDA simulators
- Pixel coordinate tensor device transfers

**Fix if confirmed**: Detector config parameter correction.

### Hypothesis 4: Numerical Precision Issue (5% confidence)

**Theory**: CPU vs CUDA floating point precision differences cause accumulated errors in Miller index calculation, pushing all indices out of bounds.

**Evidence**:
- Extremely unlikely to cause such dramatic differences (k-values in thousands)
- Both paths use `dtype=torch.float32`

**Fix if confirmed**: Increase precision or adjust tolerance; document as known limitation.

## Investigation Plan

### Phase 1: Crystal Parameter Diagnostics

**Objective**: Identify exactly which parameters differ between CUDA and CPU paths.

**Actions**:
1. Add diagnostic logging to `_build_stage_a_context` at line 548-552:
   ```python
   print(f"[CRYSTAL_CONFIG_CPU] device={device}")
   print(f"[CRYSTAL_CONFIG_CPU] cell_a={crystal_config.cell_a}, cell_b={crystal_config.cell_b}, cell_c={crystal_config.cell_c}")
   print(f"[CRYSTAL_CONFIG_CPU] cell_alpha={crystal_config.cell_alpha}, cell_beta={crystal_config.cell_beta}, cell_gamma={crystal_config.cell_gamma}")
   print(f"[CRYSTAL_CONFIG_CPU] mosflm_a_star={getattr(crystal_config, 'mosflm_a_star', None)}")
   print(f"[CRYSTAL_CONFIG_CPU] misset_deg={getattr(crystal_config, 'misset_deg', None)}")
   ```

2. Add corresponding diagnostics to CUDA path (where `stage_a_ctx` is built before line 2209)

3. Compare outputs side-by-side

### Phase 2: Reciprocal Lattice Vector Diagnostics

**Objective**: Verify that rot_a_star, rot_b_star, rot_c_star are correct on CPU.

**Actions**:
1. Add diagnostic in `nanobrag_torch/simulator.py::run()` around line 877-885:
   ```python
   if self.device.type == "cpu":
       print(f"[RECIP_LATTICE_CPU] rot_a_star[0,0]={rot_a_star[0,0]}")
       print(f"[RECIP_LATTICE_CPU] rot_b_star[0,0]={rot_b_star[0,0]}")
       print(f"[RECIP_LATTICE_CPU] rot_c_star[0,0]={rot_c_star[0,0]}")
   ```

2. Extract first few Miller indices before structure factor lookup

### Phase 3: Side-by-Side Comparison

**Objective**: Run both CUDA and CPU with identical inputs and compare all intermediate values.

**Actions**:
1. Extract crystal configs from both paths
2. Compare A* matrices, cell parameters, misset angles
3. Compare first 10 Miller indices from each path
4. Identify divergence point

### Phase 4: Minimal Reproducer

**Objective**: Isolate whether the issue is in parameter setup or simulator physics.

**Actions**:
1. Create a minimal HKL grid with known bounds (e.g., h∈[-2,2], k∈[-2,2], l∈[-2,2])
2. Run CPU simulator with manual crystal config
3. Check if Miller indices stay in bounds
4. If yes → parameter bug; if no → simulator bug

## Decision Paths

### Path A: Parameter Fix (Most Likely)

**Scenario**: Diagnostics reveal a specific parameter mismatch in crystal config or A* injection.

**Actions**:
1. Apply targeted one-line fix (e.g., correct misset angle, fix cell parameter, adjust A* vector)
2. Revert HKL gradient diagnostic (lines 2455-2456)
3. Revert CPU fallback diagnostics (if they are no longer needed)
4. Run both small and full detector tests
5. If both PASS → Remove all diagnostics, update implementation.md, mark Phase C2.2 COMPLETE
6. Commit with message documenting parameter fix

**Next Loop**: Phase C validation suite (C3-C5)

### Path B: A* Injection Bug (Moderate Likelihood)

**Scenario**: Issue is in `create_crystal_config` A* → MOSFLM vector transformation.

**Actions**:
1. Apply patch to `dbex/nanobrag_bridge.py` or `nanobrag_torch` Crystal class
2. Save patch file in artifacts per POLICY-001
3. Document rebuild steps if nanobrag_torch patched
4. Validate both tests PASS
5. Update docs/findings.md with new finding
6. Commit with patch reference

**Next Loop**: Complete Phase C2.2 validation

### Path C: Simulator CPU Bug (Low Likelihood)

**Scenario**: Issue is deep in nanobrag_torch CPU-specific code paths.

**Actions**:
1. If minor: Apply targeted patch per POLICY-001 exception
2. If major: Escalate decision to defer CPU fallback support
3. Document as known limitation
4. Update PERF-WARM-011 finding with CPU fallback status
5. Mark CPU path as unsupported in docs

**Next Loop**: Proceed with CUDA-only Stage B validation or pivot to alternative architecture

### Path D: Numerical Precision (Very Low Likelihood)

**Scenario**: CPU/CUDA float32 precision differences cause divergence.

**Actions**:
1. Document precision sensitivity in findings
2. Consider increasing to float64 for CPU path
3. Add tolerance/bounds guards
4. Update specs with CPU precision requirements

**Next Loop**: Validate with increased precision

## Confidence Assessment

**Overall Confidence**: HIGH (~90%) that the issue is a parameter/configuration mismatch in CPU context construction, NOT a nanobrag_torch simulator bug.

**Supporting Evidence**:
1. Same simulator code works on CUDA (small detector)
2. Out-of-place HKL fix confirmed working via gradient diagnostic
3. HKL hit rate 0% is too dramatic for precision issue — must be wrong parameters
4. k-values in thousands suggests orders-of-magnitude error in reciprocal lattice

**Risk if Wrong**:
- Moderate: If it's a simulator bug, we may need to patch nanobrag_torch or defer CPU fallback
- Mitigation: Diagnostic instrumentation will reveal root cause quickly, allowing pivot

## Next Steps

1. Implement Phase 1-3 diagnostics (crystal config, reciprocal lattice, side-by-side comparison)
2. Run full detector test with diagnostics
3. Extract and analyze parameter comparison logs
4. Identify specific mismatch
5. Apply targeted fix per appropriate decision path
6. Validate both tests
7. Clean up diagnostics if successful
8. Document in findings

## Findings to Update

If parameter mismatch confirmed:
- **GRADIENT-003**: CPU fallback hit-rate failure due to [specific parameter] mismatch in StageAContext builder; fixed by [specific change]
- Update PERF-WARM-012 with CPU context parameter requirements

If A* bug confirmed:
- **GRADIENT-003**: A* → MOSFLM injection on CPU yields wrong reciprocal lattice; patched [file:line] per POLICY-001

If simulator bug confirmed:
- **GRADIENT-003**: nanobrag_torch CPU path has [specific issue]; patched OR marked unsupported pending upstream fix
