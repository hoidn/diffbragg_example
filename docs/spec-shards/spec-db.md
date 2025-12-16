# Specification Database Index

<!--
Central index for all normative specification shards.
Specs use RFC-2119 keywords: SHALL, MUST, MUST NOT, SHOULD, MAY
-->

---

## Shard Inventory

| Shard | Focus | Status |
|-------|-------|--------|
| [spec-db-core.md](./spec-db-core.md) | Core domain: units, data contracts, fundamental requirements | Active |
| [spec-db-runtime.md](./spec-db-runtime.md) | Execution guardrails, environment, determinism | Active |
| [spec-db-workflow.md](./spec-db-workflow.md) | Pipeline stages, data flow, processing order | Active |
| [spec-db-interfaces.md](./spec-db-interfaces.md) | CLI/API surface, parameter precedence | Active |
| [spec-db-conformance.md](./spec-db-conformance.md) | Acceptance test definitions, thresholds | Active |

---

## How to Use Specs

### Reading Specs

- **Normative sections** — Requirements that implementations MUST follow
- **Informative sections** — Guidance, examples, rationale (not binding)
- **RFC-2119 keywords:**
  - `SHALL` / `MUST` — Required
  - `MUST NOT` — Prohibited
  - `SHOULD` — Recommended
  - `MAY` — Optional

### Citing Specs

Use section citations: `` `spec-db-core.md` §Section Name ``

Example: "Per `spec-db-core.md` §Units, all distances SHALL be in meters."

### Spec Precedence

When conflicts exist:
```
SPECS > ARCHITECTURE DOCS > IMPLEMENTATION
```

If implementation differs from spec, the spec is correct and implementation must be fixed.

---

## Adding New Specs

1. Create new shard file: `spec-db-[name].md`
2. Follow template structure (see any existing shard)
3. Mark sections as `(Normative)` or `(Informative)`
4. Add to this index
5. Cross-reference from related shards

---

## Established Terminology

### Core Domain (`spec-db-core.md`)

| Term | Definition | Canonical Shard |
|------|------------|-----------------|
| ImageData | Raw detector pixels shaped `[panel, slow, fast]` | `spec-db-core.md` §Core Data Types |
| TrustedMask | Boolean mask with `True=include` polarity | `spec-db-core.md` §Core Data Types |
| SigmaReadoutMap | Per-pixel calibrated readout noise tensor | `spec-db-core.md` §Core Data Types |
| Variance Model | `V = max(I_model + σ_rdout², σ_floor²)` | `spec-db-core.md` §Fundamental Computations |
| Chi-Squared Loss | `χ² = Σ[(I_model - I_obs)² / V]` over masked pixels | `spec-db-core.md` §Fundamental Computations |
| ADU | Analog-to-Digital Units (raw detector output) | `spec-db-core.md` §Units |
| adu_per_photon | Calibration gain for ADU→photon conversion | `spec-db-core.md` §Units |
| sigma_rdout | Readout noise (scalar or per-pixel) | `spec-db-core.md` §Core Data Types |
| sigma_floor | Variance floor guard (prevents infinite weights) | `spec-db-core.md` §Fundamental Computations |

### Workflow (`spec-db-workflow.md`)

| Term | Definition | Canonical Shard |
|------|------------|-----------------|
| RefinementEngine | Protocol-based engine executing ordered Stage objects | `spec-db-workflow.md` §Engine Contract |
| RefinementStage | Protocol interface for all refinement stages | `spec-db-workflow.md` §Engine Contract |
| RefinementContext | Shared refinement state across all stages | `spec-db-workflow.md` §Data Flow Contracts |
| JobContext | Job-level metadata and calibration state | `spec-db-workflow.md` §Data Flow Contracts |
| RefinementTelemetry | Telemetry schema emitted by all stages | `spec-db-workflow.md` §Telemetry Schema |
| Stage A | Crystal orientation and unit cell refinement (LBFGS) | `spec-db-workflow.md` §Stage Definitions |
| Stage B | Structure factor shell/per-reflection modifiers | `spec-db-workflow.md` §Stage Definitions |
| Stage C | Detector distance refinement (LBFGS) | `spec-db-workflow.md` §Stage Definitions |
| StageAContext | Warm cache for Stage A (detector models, simulators) | `spec-db-workflow.md` §Stage Definitions |
| canonical_baseline | Stage A final state snapshot for parity checks | `spec-db-workflow.md` §Stage Definitions |
| shell_modifier | Per-resolution-shell F² multiplier | `spec-db-workflow.md` §Stage B |
| ASU | Asymmetric unit (unique reflections in space group) | `spec-db-workflow.md` §Stage B |
| distance_offset_raw | Tanh-bounded detector distance delta | `spec-db-workflow.md` §Stage C |

### Interfaces (`spec-db-interfaces.md`)

| Term | Definition | Canonical Shard |
|------|------------|-----------------|
| dbex.refine_one | CLI entry point for single-experiment refinement | `spec-db-interfaces.md` §Command-Line Interface |
| backend | Refinement backend selector (`diffbragg` or `nanobrag`) | `spec-db-interfaces.md` §Backend Selection |
| torch_diagnostics | HDF5 group containing nanobrag backend telemetry | `spec-db-interfaces.md` §Output Formats |
| ROI Triptych | Per-ROI data/model/bragg/bg/variance dataset group | `spec-db-interfaces.md` §ROI Triptych Datasets |
| Parameter Precedence | CLI > calibration metadata > external_lookup > default | `spec-db-interfaces.md` §Parameter Precedence |
| Sigma Resolution | Priority order for sigma_readout source | `spec-db-interfaces.md` §Sigma Readout Resolution |
| write_torch_outputs | HDF5 writer API for torch backend outputs | `spec-db-interfaces.md` §Programmatic API |
| _resolve_sigma_readout | Sigma source resolution with provenance tracking | `spec-db-interfaces.md` §Programmatic API |

---

## Cross-References

- **Architecture:** `docs/architecture/` — How specs are implemented
- **Contracts:** `docs/architecture/contracts/` — Formal API signatures
- **Tests:** Acceptance tests validate spec conformance
