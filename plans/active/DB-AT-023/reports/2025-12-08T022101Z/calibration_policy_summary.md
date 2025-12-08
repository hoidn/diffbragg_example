# DB-AT-023 Phase A3 — Calibration Policy Summary

**Initiative**: DB-AT-023 (Calibration Policy Guard — ADU vs Photons)
**Phase**: A3 — Calibration Policy Summary
**Date**: 2025-12-08T02:21:01Z
**Normative Sources**:
- `docs/spec-db-workflow.md:19-47` (Calibration Policy)
- `docs/architecture.md:165-178` (Calibration ladder architecture)
- `docs/config_crosswalk.md:1-100` (Parameter mapping)

---

## Executive Summary

This document summarizes the calibration policy requirements for DB-AT-023 (Calibration Policy Guard), extracting normative requirements from spec-db-workflow.md and identifying Phase B implementation scope.

**Key Policy Points**:
1. A run SHALL choose a **single unit mode** (ADU or photon)
2. When `--adu-per-photon` is provided, targets/sigma SHALL be converted at ingest
3. Calibration precedence follows a strict ladder (torch_config → CLI → external_lookup → MTZ → defaults)
4. Conflicting calibration values SHALL cause the run to fail (no silent overrides)

---

## ADU vs Photon Mode (spec-db-workflow.md:19-21, 35)

### When `--adu-per-photon` is PROVIDED:

```
target_photon = target_adu / adu_per_photon
sigma_readout_photon = sigma_readout_adu / adu_per_photon
sigma_floor_photon = sigma_floor_adu / adu_per_photon
```

- **unit_mode**: `"photon"`
- **gain**: `adu_per_photon` value
- **spot_scale application**: applies directly (no sqrt)
- **Telemetry**: MUST record `unit_mode` and `gain`

### When `--adu-per-photon` is ABSENT:

- **target**: remains in ADU
- **unit_mode**: `"ADU"`
- **gain**: `1.0` (implicit)
- **spot_scale application**: uses `sqrt(spot_scale_override)` post-sim with `log_scale` as delta
- **Telemetry**: MUST record `unit_mode=ADU`

### Normative Conversion Sequence (spec-db-workflow.md:47)

1. Ingest metadata, decide unit_mode/gain
2. Apply gain if needed to target/sigma*
3. Resolve calibration payload via precedence
4. Build HKL grid (refined preferred, else raw; fail if refined requested but missing)
5. Construct configs/context with calibration (`log_scale_baseline = log(sqrt(spot_scale_override))` in ADU mode, `0` in photon mode)
6. Apply variance model `V = max(I_model + sigma_readout^2, sigma_floor^2)`
7. Emit full telemetry

---

## Calibration Precedence Ladder (spec-db-workflow.md:34)

**Priority order** (highest to lowest):

| Tier | Source | Description |
|------|--------|-------------|
| 1 | `torch_config` | JSON config file (if provided via `--config`) |
| 2 | CLI overrides | Command-line flags (e.g., `--adu-per-photon`, `--sigma-floor`) |
| 3 | `external_lookup` | DIALS imageset metadata (sigma tiles, calibration) |
| 4 | Refined MTZ metadata | Per-reflection calibration from refinement |
| 5 | Raw MTZ defaults | Initial MTZ file metadata |
| 6 | Hardcoded defaults | Legacy fallback values |

### Conflict Resolution

When `torch_config` AND CLI both define the same field AND disagree:
- **Action**: Run SHALL fail with a clear error
- **Rationale**: No silent overrides allowed (spec-db-workflow.md:34)

Fields affected by conflict resolution:
- `gain` / `adu_per_photon`
- `sigma_floor`
- `spot_scale_override`
- `beam_flux` / `beam_exposure`
- `beamsize_mm`
- `N_cells`

---

## Required Calibration Fields (spec-db-workflow.md:39-45)

### MUST be provided (Spec-DB conformance):

| Field | Source Options | Notes |
|-------|----------------|-------|
| `spot_scale_override` | torch_config | Typically via calibration JSON |
| `sigma_floor` | CLI or config | Instrument defaults allowed only when surfaced in telemetry |
| `sigma_readout` | Canonical ladder (spec-db-core.md) | map → scalar → external tiles → error |

### SHOULD be provided:

| Field | Source Options | Notes |
|-------|----------------|-------|
| `beam_flux` | Calibration config | If absent, use documented fallbacks + record provenance |
| `beam_exposure` | Calibration config | If absent, use documented fallbacks + record provenance |

### MAY default:

| Field | Default | Notes |
|-------|---------|-------|
| `beamsize_mm` | `None` | Effective value MUST be recorded |
| `N_cells` | `1` | Effective value MUST be recorded |

---

## Sigma Sourcing Ladder (spec-db-core.md, spec-db-workflow.md:36-37)

**Canonical ladder** (spec-db-core.md §Variance inputs):

1. **Map** (per-pixel sigma_readout tensor)
2. **Scalar** (single sigma_readout value)
3. **External tiles** (embedded in DIALS imageset external_lookup)
4. **Error** (fail if none found)

**Requirements**:
- Shapes MUST match target or run fails
- Legacy hardcoded defaults (e.g., ~3 ADU) are **non-conformant**
- The general calibration ladder SHALL NOT be used to invent sigma sources

---

## Architecture Contracts (input.md:56-70)

### ARCH-CONTRACT-CALIBRATION-001 (Calibration Precedence)
- **Doc**: `docs/spec-db-workflow.md:34`
- **Owner**: `dbex/refine_one.py`, `dbex/nanobrag_bridge.py::prepare_refinement_inputs`
- **Classification**: Implementation conforms (precedence ladder documented, no enforcement test yet)

### ARCH-CONTRACT-UNIT-MODE-001 (ADU vs Photon Mode)
- **Doc**: `docs/spec-db-workflow.md:35`
- **Owner**: `dbex/refine_one.py`, `dbex/data_load.py`
- **Classification**: Implementation partially exists (no `--adu-per-photon` CLI flag yet per DB-AT-023 Phase B1)

### ARCH-CONTRACT-SIGMA-001 (Sigma Sourcing)
- **Doc**: `docs/spec-db-workflow.md:36-37`
- **Owner**: `dbex/data_load.py::_resolve_sigma_readout`, `dbex/refinement/inputs.py`
- **Classification**: Implementation conforms (ladder implemented)

---

## Phase B Implementation Requirements

Based on this policy summary, Phase B must deliver:

### B1: CLI Extension (`--adu-per-photon`)

**Target file**: `dbex/refine_one.py::create_parser`

```python
parser.add_argument(
    "--adu-per-photon",
    type=float,
    default=None,
    help="ADU per photon gain factor. When provided, targets and sigma are converted to photons."
)
```

**Threading**: Value must flow to `DataLoad` and `prepare_refinement_inputs`

### B2: Photon Conversion in `prepare_refinement_inputs`

**Target file**: `dbex/nanobrag_bridge.py::prepare_refinement_inputs`

When `adu_per_photon > 0`:
1. Convert `target = target / adu_per_photon`
2. Convert `sigma_readout = sigma_readout / adu_per_photon` (if map/scalar)
3. Convert `sigma_floor = sigma_floor / adu_per_photon`
4. Set `unit_mode = "photon"`, `gain = adu_per_photon`

When `adu_per_photon` is None:
1. Keep `target` in ADU
2. Set `unit_mode = "ADU"`, `gain = 1.0`

**Telemetry provenance**: Surface `unit_mode` and `gain` in `/torch_diagnostics`

### B3: Test Fixtures

**Target file**: `tests/dbex/test_calibration_policy.py`

Required test cases:
1. `test_DB_AT_023_photon_conversion` — Verify conversion when `--adu-per-photon` provided
2. `test_DB_AT_023_adu_path` — Verify ADU mode preserves targets, global scale applied
3. `test_DB_AT_023_invalid_gain` — Verify guardrail for invalid/non-positive `adu_per_photon`
4. `test_DB_AT_023_precedence_conflict` — Verify failure when torch_config and CLI disagree

---

## Telemetry Requirements (spec-db-workflow.md:45)

`/torch_diagnostics` SHALL include:

| Field | Source | Required? |
|-------|--------|-----------|
| `unit_mode` | Decided at ingest | YES |
| `gain` | `adu_per_photon` or 1.0 | YES |
| `spot_scale_override` | torch_config or CLI | YES |
| `sigma_readout_source` | Ladder tier | YES |
| `sigma_floor` | CLI or config | YES |
| `beam_flux` / `beam_exposure` | Calibration config | SHOULD |
| `beamsize_mm` | Config or default | YES |
| `N_cells` | Config or default | YES |
| `calibration_source_flux` | Provenance | SHOULD |

---

## Geometry/Mask/ROI Invariants (spec-db-workflow.md:38)

Shared across backends:
- Arrays: `[panel, slow, fast]`
- Beam-centre swap per config_crosswalk
- Mask polarity: `True=trusted`
- ROI bboxes: `(x0, x1, y0, y1)` with x1/y1 exclusive
- Background sentinels (e.g., -1): MUST be masked consistently in loss/variance

---

## Common Pitfalls (docs/architecture.md:176-179)

### ADU ↔ Photons Conversion Drift
- **Symptom**: Global scale off by a large constant; parity tests fail uniformly
- **Cause**: Comparing ADU targets against photon-scaled simulator outputs (or vice-versa)
- **Guardrail**: Follow ADR-02 strictly. Never mix representations within a single run.

---

## Summary

DB-AT-023 Phase B must implement:
1. `--adu-per-photon` CLI flag with threading to `prepare_refinement_inputs`
2. Photon conversion logic with telemetry provenance
3. Conflict guardrail when torch_config and CLI disagree
4. Test fixtures covering conversion, ADU path, and guardrails

The calibration policy is well-documented in spec-db-workflow.md; Phase B implementation is primarily plumbing and enforcement.

---

## Artifacts

- `calibration_policy_summary.md` — This report
- Cross-references:
  - `docs/spec-db-workflow.md:19-47`
  - `docs/architecture.md:165-178`
  - `docs/config_crosswalk.md:1-100`
