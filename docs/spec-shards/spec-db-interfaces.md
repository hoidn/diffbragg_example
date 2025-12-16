# spec-db-interfaces.md — Interface Specification (Normative)

<!--
Template: CLI and API surface requirements.
-->

---

## Overview (Normative)

- **Purpose:** Define CLI and API interfaces.
- **Scope:** Command-line interface, programmatic API, parameter handling.
- **Status:** Active.

---

## Command-Line Interface (Normative)

### Primary Commands

| Command | Purpose | Required Args |
|---------|---------|---------------|
| `[command1]` | [What it does] | `--arg1`, `--arg2` |
| `[command2]` | [What it does] | `--arg1` |

### Global Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--verbose` | flag | false | Enable verbose output |
| `--config` | path | None | Configuration file path |

### Command: [command1]

```bash
[tool] [command1] --required-arg VALUE [--optional-arg VALUE]
```

**Required Arguments:**

| Argument | Type | Description |
|----------|------|-------------|
| `--required-arg` | [type] | [What it specifies] |

**Optional Arguments:**

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--optional-arg` | [type] | [default] | [What it specifies] |

**Exit Codes:**
- `0` — Success
- `1` — General error
- `2` — Invalid arguments

---

## Programmatic API (Normative)

### Entry Points

| Function | Purpose | Module |
|----------|---------|--------|
| `main_function()` | [Primary entry point] | `package.module` |
| `helper_function()` | [Secondary function] | `package.module` |

### API Contracts

See `docs/architecture/contracts/` for detailed API signatures.

---

## Parameter Handling (Normative)

### Precedence

When a parameter can be specified multiple ways:

```
1. CLI argument (highest)
2. Configuration file
3. Environment variable
4. Programmatic default
5. Hardcoded default (lowest)
```

### Validation

1. All parameters SHALL be validated before use.
2. Invalid parameters SHALL cause immediate, descriptive errors.
3. Type coercion SHALL be explicit, not implicit.

### Required vs Optional

- Required parameters: Missing value SHALL cause error.
- Optional parameters: Missing value SHALL use documented default.

---

## Output Formats (Normative)

### Standard Output

| Format | Extension | When Used |
|--------|-----------|-----------|
| [Format 1] | `.ext` | [Condition] |
| [Format 2] | `.ext` | [Condition] |

### Output Schema

[Description of output format/schema]

---

## Error Reporting (Normative)

### Error Message Format

```
Error: [Brief description]
  Context: [Relevant details]
  Suggestion: [How to fix]
```

### Verbosity Levels

| Level | Content |
|-------|---------|
| Default | Error messages only |
| `--verbose` | Progress and warnings |
| `--debug` | Detailed diagnostics |

---

## References (Informative)

- `spec-db-core.md` — Core data types accepted by interfaces
- `spec-db-workflow.md` — Pipeline invoked by commands
- `spec-db-conformance.md` — Tests validating interface behavior
