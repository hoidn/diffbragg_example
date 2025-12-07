# ARCH-IMPL-CONFORMANCE-001 — Module Inventory (Phase A Planning)

## Date: 2026-01-13T150000Z

## Scope

Identify candidate owner modules for scaling/calibration contracts and locate duplicated semantics across Stage A, reconstruction, and bridge helpers.

## Candidate Owner Modules

### dbex/refinement/stage_a.py
**Role**: Stage A refinement implementation (warm-cache, zero-iteration baseline, LBFGS closure)

**Scaling/Calibration Semantics**:
- Line ~442-443: Post-run sqrt(spot_scale_override) multiplication pattern
- Computes `log_scale_baseline` from calibration metadata or derives from masked intensity ratio
- Threads beam_flux, beam_exposure, beamsize_mm from calibration metadata

**Duplicated Logic**:
- `sqrt(spot_scale_override)` multiplication (also in reconstruction.py)
- Beam calibration threading (also in stage_a_utils.py, reconstruction.py)

**Ownership Assessment**:
**NOT a good canonical owner** — Stage A is a consumer, not a producer of baseline/scaling utilities. Moving this logic here would create circular dependency (reconstruction would call Stage A just for scaling).

### dbex/refinement/reconstruction.py
**Role**: Reconstruction helpers for building Bragg stacks from Stage A/B/C telemetry

**Scaling/Calibration Semantics** (`build_final_bragg_from_stage_a_telemetry`):
- Line ~167-223: Cold path simulator construction
- Extracts `spot_scale_override` from `config.calibration_metadata`
- Applies `sqrt(spot_scale_override)` post-run (matching Stage A pattern)
- Threads `beam_flux`, `beam_exposure`, `beamsize_mm` from calibration metadata
- Baseline alignment logic (lines ~392-445): when cache unavailable, computes masked mean and applies `baseline_alignment_factor`

**Duplicated Logic**:
- Sqrt scaling (duplicates stage_a.py:442-443)
- Beam calibration threading (duplicates stage_a_utils.py:267)
- Baseline computation (duplicates Stage A masked-mean logic)

**Ownership Assessment**:
**NOT a good canonical owner** — Reconstruction is also a consumer. It replicates Stage A / mapping logic to rebuild outputs when cache is unavailable. Canonical owner should be upstream (bridge/factory/utilities).

### dbex/nanobrag_bridge.py
**Role**: Bridge layer between high-level refinement API and nanobrag_torch simulator

**Key Functions**:
- `simulate_forward_once` (line ~1406): Zero-iteration forward helper used by mapping and test fixtures
- `simulate_forward_torch`: Similar helper for torch-mode refinement
- Factory wiring: calls `create_unified_simulator` for forward-only paths

**Scaling/Calibration Semantics**:
- `simulate_forward_once` receives calibration metadata, threads it to factory
- **Does NOT apply sqrt scaling** — returns raw simulator outputs
- Calibration threading happens via factory call

**Ownership Assessment**:
**Good candidate for canonical forward helper API** — Already used by mapping, tests, and CLI. If we promote this to the canonical "zero-iteration forward model" entry point, Stage A and reconstruction can call it instead of duplicating logic.

**Gaps**:
- Does not currently apply sqrt scaling (callers do it post-hoc)
- No baseline override mechanism for mapping → Stage A handoff

## Duplicated Semantics Analysis

### Pattern 1: sqrt(spot_scale_override) Multiplication

**Locations**:
1. `dbex/refinement/stage_a.py:442-443` (Stage A post-run scaling)
2. `dbex/refinement/reconstruction.py:~220-223` (reconstruction cold path post-run scaling)
3. `dbex/refinement/stage_a_utils.py:267` (context)

**Current behavior**:
Each module independently:
- Extracts `spot_scale_override` from `config.calibration_metadata`
- Computes `sqrt_spot_scale = sqrt(spot_scale_override)`
- Multiplies raw simulator outputs by `sqrt_spot_scale`

**Duplication type**: Logic duplication (same computation, same formula, same context)

**Canonical owner candidate**:
- **Option A**: `dbex.nanobrag_bridge.apply_calibration_scaling(bragg_raw, calibration_metadata)` — new utility function
- **Option B**: Extend `simulate_forward_once` to return **scaled** outputs (breaking change, requires fixing all call sites)
- **Option C**: Create `dbex.refinement.scaling_utils.apply_sqrt_spot_scale(bragg, calibration_metadata)` — shared utility

**Recommendation**: **Option C** (new utility module) — least invasive, preserves existing API contracts, allows gradual migration.

### Pattern 2: Beam Calibration Threading

**Locations**:
1. `dbex/refinement/stage_a_utils.py:267` (Stage A warm-cache context construction)
2. `dbex/refinement/reconstruction.py:~170` (reconstruction cold path)

**Current behavior**:
Each module independently:
- Extracts `beam_flux`, `beam_exposure`, `beamsize_mm` from `calibration_metadata`
- Passes them to `create_beam_config`

**Duplication type**: Boilerplate duplication (same extraction pattern, different contexts)

**Canonical owner candidate**:
- **Option A**: `create_unified_simulator` factory should accept `calibration_metadata` dict and handle extraction internally
- **Option B**: Create `dbex.refinement.config_factories.beam_config_from_calibration(beam, calibration_metadata)` wrapper

**Recommendation**: **Option A** (factory owns calibration threading) — aligns with ARCH-FACTORY-001 intent, reduces caller burden, centralizes contract.

### Pattern 3: Baseline Derivation (Mapping → Stage A)

**Locations**:
1. `dbex/vis/mapping.py::build_mapping_stage_a_context` (masked-mean adjustment, stores result in calibration_metadata)
2. `dbex/refinement/stage_a.py:~402-478` (recomputes masked-mean ratio, may override mapping baseline)

**Current behavior**:
- Mapping computes `target_mean_masked / bragg_mean_masked`, stores as `log_scale_baseline_source="mapping_masked_mean_adjustment"`
- Stage A **ignores** this flag and recomputes its own masked-mean ratio, overriding mapping baseline

**Duplication type**: Semantic duplication with conflict (both compute same thing, Stage A overrides mapping)

**Contract gap**: No ARCH-CONTRACT defines precedence (mapping vs Stage A)

**Canonical owner candidate**:
- **Mapping should be authoritative** for baseline when it provides adjusted value
- **Stage A should defer** to `calibration_metadata["log_scale_baseline"]` when `log_scale_baseline_source="mapping_masked_mean_adjustment"`

**Recommendation**: **Explicit handoff contract** — Stage A checks `log_scale_baseline_source` tag and skips re-derivation when mapping already adjusted.

## Proposed Module Ownership (Phase B Planning)

### Canonical Owner: `dbex.refinement.scaling_utils` (NEW MODULE)

**Responsibilities**:
- `apply_sqrt_spot_scale(bragg: np.ndarray | torch.Tensor, calibration_metadata: dict) -> same type`
- `extract_beam_calibration(calibration_metadata: dict) -> dict[str, float | None]`
- `should_defer_to_mapping_baseline(calibration_metadata: dict) -> bool`

**Consumers**:
- `dbex.refinement.stage_a` (replace local sqrt scaling with utility call)
- `dbex.refinement.reconstruction` (replace local sqrt scaling with utility call)
- `dbex.nanobrag_bridge` (optionally call utility for scaled outputs)

**Enforcement Test** (Phase B):
`tests/architecture/test_scaling_contracts.py::test_sqrt_scaling_parity` — assert Stage A, reconstruction, and bridge all produce identical sqrt-scaled outputs given same inputs.

### Enhanced Owner: `dbex.refinement.helpers.create_unified_simulator`

**New Responsibilities**:
- Accept `calibration_metadata: dict | None` parameter
- Extract beam_flux, beam_exposure, beamsize_mm internally
- Thread to `create_beam_config` (remove burden from callers)

**Breaking Change**: None (new optional parameter with default `None`)

**Consumers**:
- `dbex.nanobrag_bridge.simulate_forward_once` (pass calibration_metadata)
- `dbex.refinement.reconstruction` (pass calibration_metadata in cold path)
- Stage A warm-cache (if applicable)

**Enforcement Test** (Phase B):
`tests/architecture/test_factory_calibration.py::test_factory_threads_beam_calibration` — assert factory correctly extracts and applies beam calibration fields.

## Architectural Constraints

Per `docs/architecture/module_map.md` (if it exists — TODO: verify in next phase):
- `dbex.refinement.*` modules should **own** refinement logic, not bridge/simulator concerns
- `dbex.nanobrag_bridge` should **own** simulator construction and forward model wiring
- `dbex.vis.*` modules should **own** visualization and mapping logic

**Implication**: Scaling utilities belong in `dbex.refinement` (refinement concern), but simulator construction/calibration threading belongs in `dbex.nanobrag_bridge` or `dbex.refinement.helpers` (bridge concern).

**Proposed split**:
- **Scaling semantics** (sqrt multiplication, baseline derivation): `dbex.refinement.scaling_utils`
- **Calibration threading** (beam_flux/exposure/beamsize extraction): `dbex.refinement.helpers.create_unified_simulator` (enhanced factory)

## Next Steps (Phase B)

1. **Create `dbex/refinement/scaling_utils.py`** with canonical scaling API
2. **Update `create_unified_simulator`** to accept and thread `calibration_metadata`
3. **Refactor Stage A** to call scaling_utils instead of local sqrt computation
4. **Refactor reconstruction** to call scaling_utils instead of duplicating Stage A pattern
5. **Add baseline handoff contract**: Stage A checks `log_scale_baseline_source` before re-deriving
6. **Enforcement tests**: `test_scaling_contracts.py`, `test_factory_calibration.py`, `test_baseline_handoff.py`

## Artifacts Cross-References

- `dbex/refinement/stage_a.py:442-443` (sqrt scaling)
- `dbex/refinement/reconstruction.py:167-223` (cold path duplication)
- `dbex/refinement/stage_a_utils.py:267` (beam calibration)
- `dbex/refinement/helpers.py:82-216` (factory)
- `dbex/nanobrag_bridge.py:~1406` (`simulate_forward_once`)
- `dbex/vis/mapping.py::build_mapping_stage_a_context` (baseline adjustment)
