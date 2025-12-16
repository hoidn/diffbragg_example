# spec-db-workflow.md — Workflow Specification (Normative)

<!--
Bootstrap iteration 2: Extracted from:
- dbex/refinement/engine.py (RefinementEngine protocol)
- dbex/refinement/stage_a.py (Stage A LBFGS crystal refinement)
- dbex/refinement/stage_b.py (Stage B Fhkl shell/per-reflection modifiers)
- dbex/refinement/stage_c.py (Stage C detector distance refinement)
- dbex/refinement/context.py (Context dataclasses)
- dbex/refinement/stage.py (RefinementStage protocol, RefinementTelemetry)
-->

---

## Overview (Normative)

- **Purpose:** Define the diffBragg refinement pipeline stages, data flow, and execution contracts.
- **Scope:** Engine protocol, stage ordering, stage-specific behaviors, context propagation, checkpointing.
- **Status:** Active. All implementations MUST conform.

---

## Pipeline Overview (Normative)

```
[Ingestion] → [Preparation] → [Stage A] → [Stage B (optional)] → [Stage C (optional)] → [Output]
```

The refinement pipeline SHALL execute in the order specified. Stage B and Stage C are optional; the engine MUST support arbitrary stage sequences (not hardcoded A→B→C).

**Pipeline Stages:**

| Stage | Purpose | Required |
|-------|---------|----------|
| Ingestion | Load experiment data, reflections, structure factors | Yes |
| Preparation | Build RefinementContext, sigma resolution, ADU→photon conversion | Yes |
| Stage A | Crystal orientation and unit cell refinement (LBFGS) | Yes |
| Stage B | Structure factor shell/per-reflection modifiers (LBFGS/Adam) | No |
| Stage C | Detector distance refinement (LBFGS) | No |
| Output | HDF5 writer, telemetry export | Yes |

---

## Engine Contract (Normative)

### RefinementEngine

**Purpose:** Protocol-based engine executing ordered Stage objects.

**Signature:** `engine = RefinementEngine(stages, config)`

**Inputs:**

| Parameter | Type | Contract |
|-----------|------|----------|
| `stages` | `List[RefinementStage]` | SHALL be non-empty. Stages execute in list order. |
| `config` | `RefinementConfig` | Device, dtype, optimizer params, stage flags. |

**Run Method:** `telemetry = engine.run(inputs, telemetry_sink)`

**Inputs:**

| Parameter | Type | Contract |
|-----------|------|----------|
| `inputs` | `Dict` | MUST contain `'context'` key with `RefinementContext` instance. |
| `telemetry_sink` | `Path` or `None` | Optional directory for intermediate artifacts. |

**Output:**
- Returns `Dict[str, RefinementTelemetry]` keyed by `stage.name`.

**Normative Requirements:**

1. Engine SHALL accept arbitrary stage sequences (MUST NOT hardcode Stage A→B→C flow).
2. Engine MUST execute stages in the order provided to `__init__`.
3. Engine MUST NOT skip stages or reorder them.
4. Engine SHALL raise `ValueError` if `'context'` key is missing from inputs.
5. Engine SHALL raise `ValueError` if stages list is empty.
6. Engine SHALL propagate `context` and prior stage telemetry to subsequent stages via enriched inputs dict.
7. Engine SHALL aggregate telemetry into `Dict[str, RefinementTelemetry]` keyed by `stage.name`.

**Error Conditions:**

| Condition | Behavior |
|-----------|----------|
| Empty stages list | SHALL raise `ValueError` with message "requires at least one stage" |
| Missing `'context'` key | SHALL raise `ValueError` with message containing "RefinementContext missing" |
| Non-dict inputs | SHALL raise `ValueError` with message containing "inputs to be a dict" |

---

### RefinementStage Protocol

**Purpose:** Interface contract for all refinement stages.

**Required Methods:**

| Method | Signature | Contract |
|--------|-----------|----------|
| `name` | Property → `str` | Stage identifier (e.g., `"stage_a"`, `"stage_b"`, `"stage_c"`). |
| `configure` | `(config) → None` | Configuration hook. MAY be no-op. |
| `run` | `(inputs, telemetry_sink) → Dict` | Execute stage, return telemetry dict. |

**Run Return Contract:**

Stage `run()` SHALL return a dict or `StageResult` containing:
- All fields required by `RefinementTelemetry` dataclass
- `stage_type`: str — Stage identifier
- `mode`: Optional[str] — Stage mode variant

**Normative Requirements:**

1. Stages MUST return telemetry dicts that include `stage_type` field.
2. Stages SHOULD NOT modify inputs in-place (copy if needed).
3. Stages MUST respect device/dtype neutrality (no hardcoded `.cuda()` calls).

---

## Stage Definitions (Normative)

### Stage A: Crystal Orientation Refinement

**Purpose:** Optimize global intensity scale and crystal parameters using LBFGS.

**Stage Name:** `"stage_a"`

**Optimized Parameters:**

| Parameter | Parameterization | Description |
|-----------|-----------------|-------------|
| `log_scale` | Log-space | Global intensity scale; `exp(log_scale)` applied to model. |
| `log_cell_a_delta` | Log-space delta | Unit cell length `a` perturbation. |
| `log_cell_b_delta` | Log-space delta | Unit cell length `b` perturbation. |
| `log_cell_c_delta` | Log-space delta | Unit cell length `c` perturbation. |
| `angle_alpha_raw` | Unbounded → tanh | Unit cell angle α perturbation. |
| `angle_beta_raw` | Unbounded → tanh | Unit cell angle β perturbation. |
| `angle_gamma_raw` | Unbounded → tanh | Unit cell angle γ perturbation. |
| `orientation_vec` | 3-vector → quaternion | Crystal misorientation (XYZ Euler angles). |

**Alternative Parameterizations:**

1. **U-matrix mode** (`config.use_u_matrix_parameterization=True`): Directly parameterize orientation matrix U via quaternion `q_params`.
2. **Incremental UB mode** (`config.use_incremental_ub=True`): Parameterize via quaternion delta `q_delta` and cell deltas relative to baseline.

**Inputs:**

| Input | Type | Source |
|-------|------|--------|
| `context` | `RefinementContext` | Engine inputs dict |
| `refinement_inputs` | `RefinementInputs` | Contains `target`, `loss_mask`, `panel_slices`, `trusted_mask`, `sigma_readout` |
| `detector` | dxtbx Detector | From context |
| `beam` | dxtbx Beam | From context |
| `crystal` | dxtbx Crystal | From context |
| `hkl_grid` | `torch.Tensor` | Structure factor grid from context |
| `baseline_crystal` | dxtbx Crystal | Optional baseline for misset extraction |

**Outputs:**

| Output | Type | Destination |
|--------|------|-------------|
| `telemetry` | `RefinementTelemetry` | Engine aggregation |
| `artifacts` | `StageAArtifacts` | Engine artifacts cache |
| `stage_a_ctx` | `StageAContext` | Warm cache for Stage B/C reuse |
| `canonical_baseline` | `Dict` | Final state snapshot for Stage B parity check |

**Normative Requirements:**

1. Stage A SHALL use LBFGS optimizer with strong Wolfe line search.
2. Stage A SHALL compute variance-weighted chi-squared loss per `spec-db-core.md` § Variance Model.
3. Stage A SHALL clamp cell deltas to `±config.log_cell_max_delta` (default: 0.1, ~10% change).
4. Stage A SHALL clamp angle deltas via `tanh(raw) * config.angle_max_delta_deg` (default: 10°).
5. When `config.enable_stage_a_warm_cache=True`, Stage A SHALL build and cache `StageAContext` with pre-built detector models and simulators.
6. Stage A SHALL emit `canonical_baseline` dict with final `chi_squared`, `log_scale`, cell params, and `misset_deg`.
7. Stage A SHALL track dual metrics: `chi_squared` (variance-weighted) and `masked_mse` (legacy).
8. Stage A SHALL report `variance_floor_clamp_fraction` in telemetry.

**Optimizer Configuration:**

| Parameter | Source | Default |
|-----------|--------|---------|
| `history_size` | `config.history_size` | 20 |
| `max_iter` | `config.max_iter` | 20 |
| `tolerance_grad` | `config.tolerance_grad` | 1e-7 |
| `tolerance_change` | `config.tolerance_change` | 1e-9 |
| `line_search_fn` | Fixed | `"strong_wolfe"` |

**ROI Sampling:**

1. When `config.enable_stage_a_roi_mode=True` and ROI count > `config.stage_a_min_roi_for_roi_mode`, Stage A SHALL sample ROIs (not panels).
2. Sample size: `max(1, int(total_work_items * config.roi_sample_fraction))`.
3. Seed SHALL be fixed to 42 for deterministic behavior.

---

### Stage B: Structure Factor Modifiers

**Purpose:** Optimize per-shell or per-reflection structure factor multipliers.

**Stage Name:** `"stage_b"`

**Modes:**

| Mode | Description | Optimizer |
|------|-------------|-----------|
| `"shell"` | Per-resolution-shell modifiers | LBFGS |
| `"per_reflection"` | Per-ASU-reflection modifiers | LBFGS (< 10k params) or Adam (≥ 10k params) |

**Optimized Parameters (Shell Mode):**

| Parameter | Parameterization | Description |
|-----------|-----------------|-------------|
| `shell_modifier_raw` | Softplus input | Per-shell F² multipliers. `softplus(raw) * 2` applied. |

**Optimized Parameters (Per-Reflection Mode):**

| Parameter | Parameterization | Description |
|-----------|-----------------|-------------|
| `log_modifiers` | Log-space | Per-ASU log-multipliers. `exp(log_modifier)` applied. |

**Inputs:**

| Input | Type | Source |
|-------|------|--------|
| `context` | `RefinementContext` | Engine inputs dict |
| `stage_a_telemetry` | `Dict` | Stage A output (frozen crystal params) |
| `stage_a_ctx` | `StageAContext` | Stage A warm cache |
| `canonical_baseline` | `Dict` | Stage A final state for parity check |

**Outputs:**

| Output | Type | Destination |
|--------|------|-------------|
| `telemetry` | `RefinementTelemetry` | Engine aggregation |
| `artifacts` | `StageBArtifacts` | Engine artifacts cache (shell_edges, asu_modifier_stats) |

**Normative Requirements:**

1. Stage B SHALL freeze Stage A crystal parameters (no gradient).
2. Stage B SHALL use Stage A's `canonical_baseline` to verify baseline parity at initialization.
3. Baseline parity check: If `|stage_b_initial_chi² - stage_a_chi²| / stage_a_chi² > 1e-3`, Stage B SHALL raise `RuntimeError` with actionable diff.
4. Stage B SHALL emit `stage_b_baseline_rel_diff` and `stage_b_baseline_abs_diff` in telemetry.
5. Shell mode: `n_shells` defaults to `config.stage_b_n_shells`.
6. Per-reflection mode: When ASU count ≥ `config.stage_b_optimizer_gate` (default: 10000), Stage B SHALL use Adam optimizer.
7. Stage B MAY fall back to shell mode if ASU mapping fails (crystal_symmetry unavailable).
8. When `config.stage_b_full_eval_on_cpu=True` and device is CUDA and ROI mode is disabled, Stage B SHALL route evaluations to CPU.

**Shell Computation:**

1. Shell indices computed from d-spacing: `d = 1 / |s|` where `s` is reciprocal space vector.
2. Shell edges evenly spaced in `1/d²` space for uniform volume shells.
3. Shell modifier: `modifier = softplus(shell_modifier_raw[shell_idx]) * 2`.
4. Applied to F² grid: `F_modified = F * sqrt(modifier)`.

**Per-Reflection Computation:**

1. ASU indices computed via `compute_hkl_asu_map(hkl_indices_grid, crystal_symmetry)`.
2. Log-modifier: `modifier = exp(log_modifiers[asu_idx])`.
3. Applied to F grid: `F_modified = F * modifier`.

---

### Stage C: Detector Distance Refinement

**Purpose:** Optimize detector panel distances from sample.

**Stage Name:** `"stage_c"`

**Optimized Parameters:**

| Parameter | Parameterization | Description |
|-----------|-----------------|-------------|
| `distance_offset_raw` | Tanh-bounded | Per-panel distance offset. `tanh(raw) * max_delta` applied. |

**Inputs:**

| Input | Type | Source |
|-------|------|--------|
| `context` | `RefinementContext` | Engine inputs dict |
| `stage_a_telemetry` | `Dict` | Stage A output (frozen crystal params) |
| `stage_a_ctx` | `StageAContext` | Stage A warm cache |
| `baseline_detector` | dxtbx Detector | From context (distance reference) |

**Outputs:**

| Output | Type | Destination |
|--------|------|-------------|
| `telemetry` | `RefinementTelemetry` | Engine aggregation |
| `artifacts` | `StageCArtifacts` | Engine artifacts cache (bragg_full tensor) |

**Normative Requirements:**

1. Stage C SHALL freeze Stage A crystal parameters (no gradient).
2. Stage C SHALL use baseline detector distances as reference point.
3. Distance delta clamped: `delta_mm = tanh(distance_offset_raw) * config.stage_c_max_distance_delta_mm`.
4. Final distance: `distance_mm = baseline_distance_mm + delta_mm`.
5. Stage C SHALL retarget Stage A cached detectors and simulators via `_retarget_stage_a_detectors`.
6. Stage C MUST maintain autograd graph through distance offsets (no `.item()` conversion in gradient path).
7. Stage C SHALL emit `distance_offset_mm` per panel in telemetry.

**Warm Cache Retargeting:**

1. When Stage A warm cache is available, Stage C SHALL reuse cached detector models and simulators.
2. Retargeting mutates `StageAContext` in place: updates `detector_configs`, `detector_models`, `simulators`.
3. When ROI cache exists, ROI entry simulators SHALL also be retargeted.
4. Crystal model pointers are preserved to maintain HKL grid references.

---

## Data Flow Contracts (Normative)

### Context Types

#### RefinementContext

**Purpose:** Shared refinement state across all stages.

**Fields:**

| Field | Type | Required | Contract |
|-------|------|----------|----------|
| `refinement_inputs` | `RefinementInputs` | Yes | Contains target, loss_mask, panel_slices, trusted_mask, sigma_readout. |
| `detector` | dxtbx Detector | Yes | Panel geometry. |
| `beam` | dxtbx Beam | Yes | Wavelength, polarization, direction. |
| `crystal` | dxtbx Crystal | Yes | Unit cell, orientation. |
| `hkl_grid` | `torch.Tensor` | Yes | Structure factor grid `[h, k, l]`. |
| `hkl_metadata` | `Dict` | Yes | Grid dimensions, `has_halo` flag. MUST contain `'has_halo'` key. |
| `baseline_crystal` | dxtbx Crystal | No | For misset extraction in Stage A. |
| `baseline_detector` | dxtbx Detector | No | For Stage C distance offsets. |
| `asu_map` | `torch.Tensor` | No | Pre-computed ASU mapping for Stage B per-reflection mode. |

**Validation:**

| Condition | Behavior |
|-----------|----------|
| `hkl_grid` not `torch.Tensor` | SHALL raise `ValueError` with message containing "must be torch.Tensor" |
| `hkl_metadata` missing `'has_halo'` | SHALL raise `ValueError` with message containing "missing required key 'has_halo'" |
| `asu_map` shape mismatch | SHALL raise `ValueError` with both shapes in message |

#### JobContext

**Purpose:** Job-level metadata and calibration state.

**Fields:**

| Field | Type | Required | Contract |
|-------|------|----------|----------|
| `cli_args` | Namespace | Yes | CLI parser output. |
| `dataload` | DataLoad | Yes | Experiment, detector, beam, crystal. |
| `sigma_provenance` | `str` | Yes | MUST be non-empty. |
| `sigma_reference_value` | `float` | Yes | MUST be `> 0`. |
| `refinement_config` | RefinementConfig | Yes | Device, dtype, stage flags. |
| `hkl_metadata` | `Dict` | Yes | MUST contain `'has_halo'` key. |
| `spot_scale_override` | `float` | No | Default: `1.0`. MUST be `> 0`. |
| `hkl_source` | `str` | No | MUST be `"refined"` or `"raw"`. Default: `"raw"`. |

**Validation:**

| Condition | Behavior |
|-----------|----------|
| `sigma_reference_value <= 0` | SHALL raise `ValueError` with message containing "strictly positive" |
| `sigma_provenance` empty | SHALL raise `ValueError` with message containing "non-empty" |
| `spot_scale_override <= 0` | SHALL raise `ValueError` with message containing "strictly positive" |
| `hkl_source` not in `["refined", "raw"]` | SHALL raise `ValueError` with valid options |

### Inter-Stage Data Flow

| From | To | Data | Contract |
|------|-----|------|----------|
| Engine | Stage A | `context` | `RefinementContext` instance in `inputs['context']` |
| Stage A | Stage B | `stage_a_telemetry` | Dict with `chi_squared`, cell params, misset, `log_scale` |
| Stage A | Stage B | `stage_a_ctx` | `StageAContext` warm cache (optional) |
| Stage A | Stage B | `canonical_baseline` | Dict with final Stage A state |
| Stage A | Stage C | `stage_a_telemetry` | Same as Stage B |
| Stage A | Stage C | `stage_a_ctx` | Same as Stage B |
| Stage B | Stage C | `stage_b_telemetry` | Dict with shell/ASU modifiers (optional) |

### Telemetry Schema

All stages SHALL emit telemetry conforming to `RefinementTelemetry`:

**Required Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `optimizer` | `str` | Optimizer name (`"LBFGS"` or `"Adam"`) |
| `stage` | `str` | Stage name (`"A"`, `"B"`, `"C"`) |
| `status` | `str` | `"ok"`, `"early_stop"`, `"rollback"`, or `"error"` |
| `message` | `str` | Status description |
| `chi_squared_best` | `Tuple[float, int]` | Best chi² and iteration |
| `masked_mse_best` | `Tuple[float, int]` | Best MSE and iteration |
| `param_deltas` | `Dict[str, float]` | Final parameter changes |

**Optional Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `chi_squared_trace_sample` | `List[float]` | Chi² per closure on sampled subset |
| `chi_squared_trace_full` | `List[Tuple[int, float]]` | Chi² per validation on full set |
| `variance_floor_clamp_fraction` | `float` | Fraction of pixels where floor engaged |
| `stage_type` | `str` | Stage identifier |
| `mode` | `str` | Stage mode variant |

---

## Stage Ordering (Normative)

1. Stage A MUST execute before Stage B (Stage B depends on frozen Stage A parameters).
2. Stage A MUST execute before Stage C (Stage C depends on frozen Stage A parameters).
3. Stage B MAY execute before Stage C, or Stage B MAY be skipped entirely.
4. Engine protocol string: `"+".join(sorted(executed_stages))` (e.g., `"stage_a+stage_b+stage_c"`).

**Supported Configurations:**

| Configuration | Stages | Protocol String |
|--------------|--------|-----------------|
| Stage A only | `[StageA()]` | `"stage_a"` |
| Stage A + B | `[StageA(), StageB()]` | `"stage_a+stage_b"` |
| Stage A + C | `[StageA(), StageC()]` | `"stage_a+stage_c"` |
| Full pipeline | `[StageA(), StageB(), StageC()]` | `"stage_a+stage_b+stage_c"` |

---

## Configuration Precedence (Normative)

When configuration can come from multiple sources:

```
1. Explicit CLI argument (highest precedence)
2. Calibration metadata (torch_config.json)
3. Context-provided values
4. RefinementConfig defaults (lowest precedence)
```

Conflicts at the same precedence level SHALL raise an error.

---

## Checkpointing (Informative)

### Checkpoint Locations

Checkpoints MAY be saved after:
- Stage A completion — Crystal parameters, warm cache state
- Stage B completion — Shell modifiers, ASU modifiers
- Stage C completion — Distance offsets, final Bragg tensor

### Artifacts

Each stage MAY emit artifacts via `StageResult.artifacts`:

| Stage | Artifact Type | Contents |
|-------|--------------|----------|
| Stage A | `StageAArtifacts` | `stage_a_ctx`, `context_schema_version` |
| Stage B | `StageBArtifacts` | `shell_edges`, `n_asu_unique`, `asu_modifier_stats` |
| Stage C | `StageCArtifacts` | `bragg_full` tensor |

Engine caches artifacts in `engine.artifacts[stage.name]`.

---

## References (Informative)

- `spec-db-core.md` — Core data types, variance model
- `spec-db-runtime.md` — Execution requirements
- `spec-db-interfaces.md` — CLI/API for invoking pipeline
