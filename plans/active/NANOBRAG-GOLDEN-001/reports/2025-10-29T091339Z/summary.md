# NANOBRAG-GOLDEN-001 Loop Summary (2025-10-29T091339Z)

## Loop Status
**BLOCKED** — nanobrag_torch zero-output blocker persists despite scale injection and enhanced diagnostics

## Task Completion
- ✅ Enhanced `scripts/generate_simple_cubic_golden.py` with diagnostic logging
- ✅ Confirmed DiffBragg scale is being propagated to structure factor grid
- ✅ Ran canonical capture with full instrumentation
- ✅ Captured detailed metrics and logs
- ❌ nanobrag_torch simulator still produces all-zero output (BLOCKER)

## Key Findings

### Scale Application (VERIFIED WORKING)
The DiffBragg global scale IS being applied correctly:
- **BEFORE scaling**: amps min=1.546, max=518.3, mean=47.41
- **Scale factor**: sqrt(3.186e+17) = 5.645e+08
- **AFTER scaling**: amps min=8.728e+08, max=2.926e+11, mean=2.676e+10
- **HKL grid**: 69,614 reflections, 100% in-range, grid nonzero=69,614

### Zero-Output Confirmed (BLOCKER)
nanobrag_torch Simulator output:
- device=cuda:0, dtype=torch.float32, shape=[2527, 2463]
- **min=0.0, max=0.0, mean=0.0, nonzero=0**
- nanoBragg banner shows "incident fluence: 1e+18 photons/m^2" (initialization succeeded)
- No error messages or exceptions

### DiffBragg Baseline (SUCCESS)
- Refinement converged: 5 macro cycles, Resid=192876.84, sigZ=6.28
- Spot scale: 3.186e+17
- Baseline max: 36,169.54
- Nonzero pixels: 97,131

## Root Cause Hypotheses

### H1: Scale Magnitude Overflow (MOST LIKELY)
Structure factor amplitudes of ~2.9e+11 may overflow nanoBragg's internal float32 calculations. nanoBragg expects structure factors in electron units (~hundreds), not arbitrary scaled values.

**Evidence**:
- Scaling by 5.645e+08 produces structure factors 3 orders of magnitude larger than typical values
- nanoBragg C++ code may clip/zero out values that exceed internal thresholds
- No warnings or errors suggest silent overflow

**Test**: Try normalizing structure factors to electron-unit scale first, then scale output intensities instead

### H2: nanobrag_torch API Mismatch
The assignment `crystal_model.hkl_data = torch_grid` may not be the correct API pattern.

**Evidence**:
- No documentation or examples found for proper HKL data assignment
- nanobrag_torch 0.1.0 is early version, API may be incomplete or undocumented
- Grid assignment succeeds without error, suggesting some validation passed

**Test**: Inspect nanobrag_torch source code for proper HKL data assignment

### H3: Missing Critical Parameter
Some configuration parameter causes nanoBragg to skip all calculations.

**Evidence**:
- nanoBragg banner shows "1 mosaic domains over mosaic spread of 0 degrees"
- Zero mosaic spread might be pathological case
- Some internal flag might gate calculations

**Test**: Compare with working nanobrag_torch examples

### H4: CUDA Silent Failure
Device/memory issue causes silent zero-output.

**Evidence**:
- Grid is on cuda:0, simulator runs on cuda:0
- No CUDA errors logged
- Similar pattern seen in previous diffBraggCUDA.cu:708 bugs

**Test**: Check torch.cuda.get_device_properties() after run, try CPU mode

## Metrics
- Diagnostic enhancements: 3/3 added
- DiffBragg baseline: 1/1 captured (max=36,169.54)
- Structure factor scaling: VERIFIED (max 2.9e+11)
- HKL grid population: 100% (69,614 nonzero)
- torch baseline: 0/1 succeeded (max=0.0 BLOCKER)
- Error messages: 0

## Artifacts
All artifacts under `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T091339Z/`:
- `planning_notes.md` — Root cause analysis and hypotheses
- `canonical_capture.log` (897 KB) — Full capture trace with diagnostic logs
- `golden_dataset/legacy/bragg_diffbragg.npy` (24M) — DiffBragg baseline (max=36,169.54)
- `golden_dataset/torch/bragg_torch.npy` (24M) — All zeros (BLOCKER)
- `golden_dataset/torch/panel_metrics.json` — torch_max=0.0, torch_sum=0.0
- `torch_hkl_debug.json` — HKL statistics (100% in-range, grid_max=2.926e+11)
- `golden_dataset/metrics.json` — Parity summary (median_correlation=NaN)

## Code Changes
Modified `scripts/generate_simple_cubic_golden.py`:
1. Lines 114-120: Added amplitude logging before/after scaling
2. Lines 142-147: Added structure factor grid stats logging
3. Lines 495-500: Added RAW simulator output logging

## Recommendations

### Immediate Actions (Ralph → Supervisor)
1. **Escalate blocker** — Requires nanobrag_torch maintainer expertise or source code inspection
2. **Document findings** — Add TORCH-SCALE-001 and TORCH-SILENT-ZERO-001 to `docs/findings.md`
3. **Mark initiative blocked** — Update status in fix_plan.md with error signature

### Alternative Approaches (for next loop if unblocked)
1. **Test scale normalization** — Normalize structure factors to electron units first, scale output instead
2. **Inspect nanobrag_torch source** — Look for HKL data assignment API, internal clipping logic
3. **Test minimal reproducer** — Simple cubic, single HKL, verify nonzero output
4. **Downgrade scope** — Use DiffBragg-only golden dataset for parity tests

### Environment Freeze Compliance
- ✅ No packages installed/upgraded
- ✅ No toolchain modifications
- ✅ All changes limited to workspace source code
- ✅ Blocker documented per policy (cannot be remediated in-loop)

## Loop Outcome
**Implementation nucleus executed** (per stall-autonomy rule):
- ✅ Code change made: Added diagnostic logging (3 locations)
- ✅ Validation attempted: Ran canonical capture with instrumentation
- ❌ Exit criteria NOT met: torch still produces zero output

**Status**: BLOCKED — requires external expertise to resolve nanobrag_torch zero-output issue
