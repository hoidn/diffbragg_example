# spec-db-runtime.md — Runtime Specification (Normative)

<!--
Template: Runtime execution requirements.
Covers environment, determinism, device handling.
-->

---

## Overview (Normative)

- **Purpose:** Define execution environment requirements and runtime behavior.
- **Scope:** Environment setup, determinism, device/dtype handling, resource management.
- **Status:** Active.

---

## Environment Requirements (Normative)

### Required Environment Variables

| Variable | Purpose | Required Value |
|----------|---------|----------------|
| [VAR_NAME] | [What it controls] | [Value or "must be set"] |

### Python Version

- Implementations SHALL support Python [version range].

### Dependencies

- Required dependencies are specified in `pyproject.toml`.
- Implementations SHALL NOT require dependencies not listed there.

---

## Determinism (Normative)

### Reproducibility Requirements

1. Given identical inputs and configuration, implementations SHALL produce identical outputs.
2. Random number generators SHALL be seeded explicitly when randomness is used.

### Non-Deterministic Operations

When non-deterministic operations are unavoidable:
1. They SHALL be documented in the function contract.
2. A deterministic alternative SHOULD be provided where possible.

### PyTorch Determinism (if applicable)

```python
# For deterministic execution:
torch.use_deterministic_algorithms(True)
torch.manual_seed(seed)
```

---

## Device Handling (Normative)

### Device Neutrality

1. Code SHALL NOT hardcode device (CPU/GPU).
2. Device SHALL be configurable via parameter or configuration.
3. All tensors in a computation SHALL be on the same device.

### Dtype Handling

1. Implementations SHALL support float32 and float64.
2. Dtype SHALL be preserved through computations unless explicitly converted.
3. Dtype mismatches SHALL raise explicit errors.

---

## Resource Management (Normative)

### Memory

1. Large intermediate results SHOULD be released when no longer needed.
2. Memory-intensive operations SHALL support batching where applicable.

### File Handles

1. File handles SHALL be properly closed after use.
2. Context managers (`with` statements) SHALL be used for file operations.

---

## Error Handling (Normative)

### Error Messages

1. Error messages SHALL include sufficient context for diagnosis.
2. Error messages SHALL identify the specific input or condition that caused the error.

### Exception Types

| Condition | Exception Type |
|-----------|----------------|
| Invalid input type | `TypeError` |
| Invalid input value | `ValueError` |
| Missing required input | `ValueError` |
| Runtime failure | `RuntimeError` |
| Configuration error | `ConfigurationError` (if defined) |

---

## Logging (Informative)

### Log Levels

- `DEBUG` — Detailed diagnostic information
- `INFO` — Confirmation of normal operation
- `WARNING` — Something unexpected but handled
- `ERROR` — Failure that prevented operation

### Log Content

Logs SHOULD include:
- Timestamp
- Operation being performed
- Relevant parameter values (excluding sensitive data)

---

## References (Informative)

- `spec-db-core.md` — Core domain requirements
- `spec-db-workflow.md` — Processing pipeline
