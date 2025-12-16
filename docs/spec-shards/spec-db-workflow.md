# spec-db-workflow.md — Workflow Specification (Normative)

<!--
Template: Pipeline and data flow requirements.
-->

---

## Overview (Normative)

- **Purpose:** Define processing pipeline stages and data flow.
- **Scope:** Stage ordering, stage contracts, data transformations.
- **Status:** Active.

---

## Pipeline Overview (Normative)

```
[Stage 1: Input] → [Stage 2: Process] → [Stage 3: Validate] → [Stage 4: Output]
```

Stages SHALL execute in the order specified. Skipping stages is NOT permitted unless explicitly allowed.

---

## Stage Definitions (Normative)

### Stage 1: [Stage Name]

**Purpose:** [What this stage does]

**Inputs:**
| Input | Type | Source |
|-------|------|--------|
| [input1] | [Type] | [Where it comes from] |

**Outputs:**
| Output | Type | Destination |
|--------|------|-------------|
| [output1] | [Type] | [Where it goes] |

**Requirements:**
1. [Requirement that MUST be satisfied]
2. [Requirement that MUST be satisfied]

**Validation:**
- [What is validated before proceeding]

---

### Stage 2: [Stage Name]

**Purpose:** [What this stage does]

**Inputs:**
| Input | Type | Source |
|-------|------|--------|
| [input1] | [Type] | Stage 1 output |

**Outputs:**
| Output | Type | Destination |
|--------|------|-------------|
| [output1] | [Type] | Stage 3 |

**Requirements:**
1. [Requirement]

---

### Stage 3: [Stage Name]

<!-- Continue pattern for each stage -->

---

## Data Flow Contracts (Normative)

### Inter-Stage Data

| From | To | Data | Contract |
|------|-----|------|----------|
| Stage 1 | Stage 2 | [Data name] | [Type, shape, constraints] |
| Stage 2 | Stage 3 | [Data name] | [Type, shape, constraints] |

### Data Transformation Rules

1. [Transformation rule]
2. [Transformation rule]

---

## Configuration Precedence (Normative)

When configuration can come from multiple sources:

```
1. Explicit parameter (highest precedence)
2. Configuration file
3. Environment variable
4. Default value (lowest precedence)
```

Conflicts at the same precedence level SHALL raise an error.

---

## Checkpointing (Informative)

### Checkpoint Locations

Checkpoints MAY be saved after:
- [Stage N] — [What state is captured]

### Checkpoint Format

[Description of checkpoint format if applicable]

---

## References (Informative)

- `spec-db-core.md` — Core data types
- `spec-db-runtime.md` — Execution requirements
- `spec-db-interfaces.md` — CLI/API for invoking pipeline
