# spec-db-core.md — Core Domain Specification (Normative)

<!--
Template: Adapt for your project's core domain.
Replace [PLACEHOLDERS] with domain-specific content.
-->

---

## Overview (Normative)

- **Purpose:** Define fundamental domain concepts, units, and data contracts.
- **Scope:** Core types, unit systems, coordinate conventions, fundamental computations.
- **Status:** Active. All implementations MUST conform.

---

## Units and Conventions (Normative)

### Unit System

| Quantity | Unit | Symbol | Notes |
|----------|------|--------|-------|
| [Quantity 1] | [Unit] | [Symbol] | [Any constraints] |
| [Quantity 2] | [Unit] | [Symbol] | [Any constraints] |

**Rule:** All internal computations SHALL use the units specified above. Conversion to/from user-facing units SHALL occur only at I/O boundaries.

### Coordinate System

[Description of coordinate system conventions.]

- **Origin:** [Where is the origin]
- **Axes:** [X, Y, Z definitions]
- **Handedness:** [Left/right-handed]

### Indexing Convention

- Arrays SHALL use [0-indexed / 1-indexed] access.
- [Any other indexing conventions]

---

## Core Data Types (Normative)

### [DataType1]

**Definition:** [What this type represents]

**Fields:**

| Field | Type | Required | Contract |
|-------|------|----------|----------|
| `field1` | `[Type]` | Yes | [Valid values, constraints] |
| `field2` | `[Type]` | No | [Default behavior, constraints] |

**Invariants:**
1. [Invariant that MUST hold]
2. [Invariant that MUST hold]

### [DataType2]

**Definition:** [What this type represents]

**Fields:**

| Field | Type | Required | Contract |
|-------|------|----------|----------|
| `field1` | `[Type]` | Yes | [Valid values, constraints] |

---

## Fundamental Computations (Normative)

### [Computation Name]

**Purpose:** [What this computation produces]

**Formula:**
```
result = [mathematical formula]
```

**Inputs:**
- `[input1]` — [Type, units, constraints]
- `[input2]` — [Type, units, constraints]

**Output:**
- `[result]` — [Type, units, properties]

**Constraints:**
1. [Input constraint that MUST be satisfied]
2. [Output property that MUST hold]

---

## Validation Rules (Normative)

### Input Validation

1. [Input type] SHALL be validated for [condition] before processing.
2. Missing required inputs SHALL cause an error with descriptive message.
3. [Other validation rules]

### Output Validation

1. Outputs SHALL satisfy [property].
2. [Other output constraints]

---

## Error Conditions (Normative)

| Condition | Required Behavior |
|-----------|-------------------|
| [Condition 1] | SHALL raise [ErrorType] with message describing [what] |
| [Condition 2] | SHALL fail with [specific behavior] |

**No Silent Failures:** Implementations MUST NOT silently produce incorrect results. When requirements cannot be met, implementations SHALL fail explicitly.

---

## References (Informative)

- [External standard or paper]
- [Related specification]
- `spec-db-runtime.md` — Execution requirements
- `spec-db-workflow.md` — Processing pipeline
