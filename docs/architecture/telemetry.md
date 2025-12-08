# Telemetry Ownership Charter

**Status**: Active (ARCH-TELEMETRY-002 Phase A)
**Last Updated**: 2025-12-07
**Normative References**:
- `docs/spec-db-workflow.md` (telemetry requirements)
- `docs/spec-db-core.md` (variance model, chi-squared invariants)
- `docs/architecture/dbex/io/writer.idl.md` (HDF5 schema)
- `docs/architecture/dbex/refinement/interfaces.idl.md` (observer contracts)

---

## 1. Purpose

This charter establishes:
1. **Ownership**: Which modules own telemetry surfaces and their semantics
2. **Expansion Rules**: How new telemetry fields are added
3. **Semantics Deferral**: Where normative definitions live (Spec-DB, IDLs)
4. **Probe Freeze Policy**: Constraints on plan-local diagnostics

---

## 2. Primary Owners

### 2.1 Stage Telemetry Dataclasses (`dbex/refinement/interfaces.py`)

| Dataclass | Responsibility |
|-----------|----------------|
| `StageATelemetry` | Typed payload for Stage A (geometry/scale refinement) |
| `StageBTelemetry` | Typed payload for Stage B (shell modifiers, baseline parity) |
| `StageCTelemetry` | Typed payload for Stage C (detector refinement) |
| `StagePerfCounters` | Performance counters (closure evals, validation runs, timing, variance-floor stats) |
| `StageResult` | Aggregate container (stage, telemetry, perf_counters) |

**Key Attributes Owned**:
- Loss traces: `loss_trace_sample`, `loss_trace_full`, `best_loss_full`
- Chi-squared: `chi_squared_trace_sample`, `chi_squared_trace_full`, `chi_squared_best`
- Masked MSE: `masked_mse_trace_sample`, `masked_mse_trace_full`, `masked_mse_best`
- Perf counters: `closure_evals`, `validation_runs`, `forward_times_ms`
- Variance-floor: `variance_floor_clamped_pixels`, `variance_floor_masked_pixels`
- Stage A specific: `u_matrix_lifecycle_log`, `a_star_lifecycle_log`, `panel_loss_diag`
- Stage B specific: `stage_b_baseline_rel_diff/abs_diff/diff_path`

**Contract Reference**: `docs/architecture/dbex/refinement/interfaces.idl.md`

### 2.2 Stage Collectors (`dbex/refinement/telemetry_collectors.py`)

| Collector | Responsibility |
|-----------|----------------|
| `StageATelemetryCollector` | Observer impl for Stage A; wraps `StageATelemetryState` |
| `StageBTelemetryCollector` | Observer impl for Stage B; wraps `StageBTelemetryState` |
| `StageCTelemetryCollector` | Observer impl for Stage C; wraps `StageCTelemetryState` |

Collectors implement the `RefinementObserver` protocol (interfaces.py:36):
- `on_step(iteration, loss, metrics)` - per-closure telemetry
- `on_validation(scope, chi2, payload)` - full-validation telemetry
- `finalize() -> StageResult` - construct typed result

### 2.3 Writer (`dbex/io/writer.py`)

**Responsibility**: Serialize telemetry to HDF5 `/torch_diagnostics` schema

**Does NOT own** telemetry semantics; consumes typed `StageResult` and produces HDF5 attributes/datasets.

**Contract Reference**: `docs/architecture/dbex/io/writer.idl.md`

---

## 3. Secondary/Diagnostic Owners

### 3.1 Baseline Metrics (`dbex/refinement/telemetry_baseline.py`)

**Function**: `collect_stage_a_baseline_metrics()`

**Purpose**: Production-grade baseline metrics for Stage A parity diagnostics

**Consumer**: `StageAArtifacts.baseline_metrics` (opt-in via `config.enable_stage_a_baseline_metrics`)

**Not a primary telemetry surface** - used for parity debugging, not core refinement output.

### 3.2 Stage Artifacts (`dbex/refinement/artifacts.py`)

| Artifact | Fields |
|----------|--------|
| `StageAArtifacts` | `baseline_metrics` (schema v1, optional) |
| `StageBArtifacts` | `stage_b_baseline_rel_diff/abs_diff/diff_path` |

Artifacts carry stage-specific metadata not in the core telemetry traces.

### 3.3 Mapping Calibration (`dbex/vis/mapping.py`)

**Fields**: `log_scale_baseline_source` in calibration/diagnostics dicts

**Not a standalone telemetry surface** - embedded in calibration metadata flow.

---

## 4. Semantics Deferral

Telemetry semantics are defined by external specifications:

| Semantics | Normative Source |
|-----------|------------------|
| Variance-weighted chi-squared | `docs/spec-db-core.md` §Objective Function |
| Variance model (sigma_floor) | `docs/spec-db-core.md` §86-90 |
| Stage pipeline requirements | `docs/spec-db-workflow.md` §Calibration |
| HDF5 schema stability | `docs/findings.md` DIAGNOSTICS-001 |
| Physics loss invariants | `docs/findings.md` PHYSICS-LOSS-001/003 |

**This charter does NOT define** new physics or loss semantics. It documents ownership and expansion rules for existing telemetry infrastructure.

---

## 5. Expansion Rules

New production telemetry fields MUST follow this process:

### 5.1 Requirements

1. **Spec Update**: If the field reflects new physics/semantics, update `docs/spec-db-*.md` first
2. **IDL Definition**: Add field to relevant IDL contract (`interfaces.idl.md` or `writer.idl.md`)
3. **Dataclass Update**: Add field to appropriate `Stage*Telemetry` dataclass in `interfaces.py`
4. **Collector Wiring**: Update `Stage*TelemetryCollector` callbacks to populate the field
5. **Writer Support**: If serialized to HDF5, update `writer.py` and `writer.idl.md`
6. **Enforcement Test**: Add test under `tests/architecture/` verifying field presence/schema

### 5.2 Charter Update

After adding new telemetry:
1. Update telemetry inventory (`plans/active/ARCH-TELEMETRY-002/reports/.../telemetry_inventory.md`)
2. Update this charter's §2 or §3 if ownership changes
3. Record in `docs/findings.md` if establishing a new pattern

### 5.3 Prohibited

- Adding production telemetry fields without IDL definition
- Changing telemetry semantics under `bugfix/perf` initiative type
- Plan-local scripts emitting new production schemas (PROBE-FREEZE-001)

---

## 6. Probe Freeze Policy (PROBE-FREEZE-001)

Per `prompts/supervisor.md::diagnostic_script_policy` and `tests/architecture/test_probe_contracts.py`:

### Allowed

- Plan-local scripts consuming existing telemetry surfaces
- Temporary diagnostic probes in `archive/plans/*/bin/` that read production telemetry
- Test fixtures asserting on existing schema fields

### Prohibited

- Plan-local scripts creating new production telemetry schemas
- New `/torch_diagnostics` attributes without charter/IDL update
- Telemetry dict mutations in production code (ARCH-STAGE-CTX-002)

### Enforcement

- `tests/architecture/test_probe_contracts.py` validates probe constraints
- Supervisor rejects initiatives that add production telemetry without charter compliance

---

## 7. Consumer Guidance

### For Test Authors

- Import typed dataclasses from `dbex.refinement.interfaces`
- Assert on dataclass fields, not dict keys
- Use `StageResult.to_legacy_dict()` only for HDF5 schema compatibility tests

### For Probe Writers

- Read telemetry from HDF5 `/torch_diagnostics` group or `StageResult` objects
- Do NOT add new attributes to telemetry dicts in probe code
- Use existing telemetry surfaces; request charter update if new fields needed

### For Engine/Stage Authors

- Use `Stage*TelemetryCollector` observer pattern for telemetry emission
- Do NOT mutate telemetry dicts directly (ARCH-STAGE-CTX-002)
- Emit typed `StageResult` via `collector.finalize()`

---

## 8. Related Documents

| Document | Purpose |
|----------|---------|
| `docs/spec-db-workflow.md` | Pipeline and telemetry requirements |
| `docs/spec-db-core.md` | Physics and variance model |
| `docs/architecture/dbex/io/writer.idl.md` | HDF5 schema contract |
| `docs/architecture/dbex/refinement/interfaces.idl.md` | Observer and dataclass contracts |
| `docs/findings.md` | Telemetry-related findings (PHYSICS-LOSS-001, DIAGNOSTICS-001) |
| `docs/data_dependency_manifest.md` | Telemetry data dependencies (see §Telemetry) |
| `tests/architecture/test_probe_contracts.py` | Probe freeze enforcement |

---

## 9. Change Log

- **2025-12-07 (ARCH-TELEMETRY-002 Phase A.1)**: Initial charter authored; documents existing ownership, establishes expansion rules and probe freeze policy
