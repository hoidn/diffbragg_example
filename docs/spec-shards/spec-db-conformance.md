# spec-db-conformance.md — Conformance Specification (Normative)

<!--
Template: Acceptance test definitions and conformance requirements.
-->

---

## Overview (Normative)

- **Purpose:** Define acceptance tests that validate spec conformance.
- **Scope:** Test definitions, acceptance thresholds, conformance profiles.
- **Status:** Active.

---

## Conformance Profiles (Normative)

### Profile: Standard

**Requirements:** All tests in Tier 1 and Tier 2 MUST pass.

### Profile: Minimal

**Requirements:** All tests in Tier 1 MUST pass.

---

## Acceptance Test Index

| Test ID | Description | Tier | Threshold |
|---------|-------------|------|-----------|
| AT-001 | [Brief description] | 1 | [Pass criterion] |
| AT-002 | [Brief description] | 1 | [Pass criterion] |
| AT-003 | [Brief description] | 2 | [Pass criterion] |

---

## Test Definitions (Normative)

### AT-001: [Test Name]

**Purpose:** [What this test validates]

**Tier:** 1 (Required for all profiles)

**Setup:**
```bash
# Setup commands or description
```

**Execution:**
```bash
pytest tests/acceptance/test_at_001.py -v
```

**Acceptance Criteria:**
1. [Measurable criterion] — Threshold: [value]
2. [Measurable criterion] — Threshold: [value]

**Spec References:**
- `spec-db-core.md` §[Section] — [What requirement is validated]

---

### AT-002: [Test Name]

**Purpose:** [What this test validates]

**Tier:** 1

**Setup:**
[Setup description]

**Execution:**
```bash
pytest tests/acceptance/test_at_002.py -v
```

**Acceptance Criteria:**
1. [Criterion] — Threshold: [value]

**Spec References:**
- `spec-db-*.md` §[Section]

---

### AT-003: [Test Name]

**Purpose:** [What this test validates]

**Tier:** 2

<!-- Continue pattern -->

---

## Threshold Definitions (Normative)

### Numerical Thresholds

| Metric | Threshold | Rationale |
|--------|-----------|-----------|
| [Metric 1] | [value] | [Why this threshold] |
| [Metric 2] | [value] | [Why this threshold] |

### Comparison Tolerances

- Absolute tolerance: [value]
- Relative tolerance: [value]

---

## Test Artifacts (Normative)

### Required Artifacts

Each acceptance test SHALL produce:
1. Pass/fail status
2. Measured values for each criterion
3. [Other required artifacts]

### Artifact Location

```
tests/acceptance/artifacts/
└── [test_id]/
    ├── results.json
    └── [other artifacts]
```

---

## Running Conformance Tests

### Full Suite

```bash
pytest tests/acceptance/ -v --tb=short
```

### By Tier

```bash
# Tier 1 only
pytest tests/acceptance/ -v -m "tier1"

# Tier 2 only
pytest tests/acceptance/ -v -m "tier2"
```

### By Profile

```bash
# Standard profile
pytest tests/acceptance/ -v -m "standard"

# Minimal profile
pytest tests/acceptance/ -v -m "minimal"
```

---

## References (Informative)

- `spec-db-core.md` — Core requirements being tested
- `spec-db-runtime.md` — Runtime requirements being tested
- `docs/development/testing_strategy.md` — Overall testing approach
