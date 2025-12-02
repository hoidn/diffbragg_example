# Phase B3 Complexity Assessment — ExperimentModel Adapter

## Context
Phase B2 COMPLETE (2025-11-24T000000Z): all forward-only simulation paths now use unified factory (forward helpers, refine_one CLI, -79 lines total). Phase B3 objectives per implementation.md:68-71: implement ExperimentModel adapter path behind explicit flag (default OFF), parity-first, no loss/warm-cache changes.

## API Verification
Verified `ExperimentModel` exists in nanobrag_torch.models.experiment:
```python
from nanobrag_torch.models.experiment import ExperimentModel

# Constructor signature (verified 2025-11-24T044933Z):
ExperimentModel(
    crystal_config: CrystalConfig,
    detector_config: DetectorConfig,
    beam_config: BeamConfig,
    device: Optional[torch.device] = None,
    dtype: torch.dtype = torch.float32,
    param_init: str = 'frozen',
    hkl_data: Optional[torch.Tensor] = None,
    hkl_metadata: Optional[dict] = None
) -> ExperimentModel
```

**API Alignment:** Matches docs/nanobrag_api.md specification ✓

## Scope Analysis

### Implementation Location
Add adapter function in `dbex/refinement/helpers.py` (alongside `create_unified_simulator`):
```python
def simulate_via_experiment_model(
    detector_config, crystal_config, beam_config, hkl_grid, hkl_metadata,
    spot_scale_override=None, device=None, dtype=torch.float32,
    calibration_metadata=None
) -> Tuple[torch.Tensor, float, dict]:
    """
    Thin adapter wrapping ExperimentModel(param_init="frozen") for parity testing.

    Returns:
        image: torch.Tensor (spixels, fpixels)
        sqrt_scale: float (for post-run scaling by CALLER)
        metadata: dict
    """
```

### Implementation Steps
1. **Import** ExperimentModel inside function (lazy import per ARCH-ENGINE-002)
2. **Instantiate** with param_init="frozen" (no trainable parameters)
3. **Attach HKL** via experiment.set_structure_factors(hkl_data, hkl_metadata) or constructor args
4. **Run** experiment() to get output image
5. **Compute sqrt_scale** from spot_scale_override (matching factory pattern per SCALE-004)
6. **Return** (image, sqrt_scale, metadata)

### Integration Points
Wire adapter to test_experiment_parity.py (Phase A3 test):
- Load tiny dxtbx fixture
- Build configs via existing bridge helpers
- Call `simulate_via_experiment_model` with configs + HKL
- Compare output to `create_unified_simulator` (factory baseline)
- Assert parity within 1e-6 tolerance

### Flag Design
Add explicit adapter flag to RefinementConfig (default OFF):
```python
@dataclass
class RefinementConfig:
    # ... existing fields ...
    use_experiment_model_adapter: bool = False  # Phase B3: ExperimentModel parity path
```

**Usage:** Only test_experiment_parity.py enables this flag; production paths remain unchanged.

## Complexity Rating: STRAIGHTFORWARD

### Low-Risk Factors
1. **API exists** and matches spec (verified via import test)
2. **Thin wrapper** pattern proven successful in Phase B2 factory (~150 lines)
3. **No production changes** — adapter behind flag, default OFF
4. **Existing validation** — Phase A3 test stub already defines acceptance criteria
5. **Config creation** — proven pattern from Phase B2 (bridge helpers)
6. **HKL attachment** — known API per docs/nanobrag_api.md

### Estimated Effort
**1 loop** (~2-3 hours):
- Implementation: ~100-150 lines adapter function (~60min)
- Test wiring: remove xfail marker, implement parity check (~45min)
- Validation: run Phase A3 test + DB-AT-024 regression guard (~30min)
- Documentation: decision.md + summary.md (~30min)

### Validation Strategy
**Primary:** test_experiment_parity.py::test_parity_small_fixture (Phase A3)
- Remove xfail marker
- Load tiny fixture (dbex_files/*/refGeom.expt + mtz)
- Build configs for single panel
- Run factory path: create_unified_simulator
- Run adapter path: simulate_via_experiment_model
- Assert outputs match within 1e-6 (max abs diff, per-pixel MSE)

**Regression Guards:**
- DB-AT-024 mapping parity (adapter NOT used, factory path unchanged)
- test_stage_a_expansion (adapter NOT used, production path unchanged)

### Risks & Mitigations

**Risk 1: HKL attachment API mismatch**
- Likelihood: LOW (API documented in nanobrag_api.md)
- Mitigation: Verify `experiment.set_structure_factors` or constructor args via inspection
- Fallback: Use constructor args `hkl_data`/`hkl_metadata` if method doesn't exist

**Risk 2: Output shape/dtype mismatch**
- Likelihood: LOW (ExperimentModel documented to return (spixels, fpixels) tensor)
- Mitigation: Add shape/dtype validation in adapter, log mismatch
- Fallback: Add shape normalization if ExperimentModel returns different layout

**Risk 3: param_init="frozen" parity drift**
- Likelihood: MEDIUM (ExperimentModel may have different internal wiring)
- Mitigation: Parity test with 1e-6 tolerance; if fails, document delta and assess acceptability
- Fallback: Adjust tolerance or mark test xfail with parity findings

**Risk 4: Circular import**
- Likelihood: LOW (ExperimentModel is top-level model, unlikely to depend on dbex)
- Mitigation: Lazy import inside adapter function
- Fallback: Import at module scope if no circular dep detected

## Decision: APPROVE Phase B3 ready_for_implementation

**Verdict:** Phase B3 is STRAIGHTFORWARD and ready for Ralph execution in 1 loop.

**Confidence:** HIGH (~90%) implementation will succeed based on:
1. API exists and matches spec
2. Thin wrapper pattern proven in Phase B2
3. Test stub already defines acceptance criteria
4. No production path changes (adapter behind flag)

**Next Actions:** Author ready_for_implementation Do Now for Ralph with comprehensive Phase B3 protocol (8 steps: API verification, adapter implementation, test wiring, validation, decision synthesis, docs update, commit).

## Findings Applied
- ARCH-ENGINE-002: Lazy imports inside adapter function
- SCALE-004: Post-run sqrt_scale computation (factory pattern)
- POLICY-001: Environment Freeze (ExperimentModel exists, no engine patches needed)
- PERF-WARM-001: Warm-cache OFF in parity test

## Artifacts
- `phase_b3_complexity_assessment.md` (this file)
- Code inspection (ExperimentModel import verification, API signature)

## Timestamp
2025-11-24T044933Z
