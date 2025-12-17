# Specification Conventions

This document defines the standards for behavioral specifications in this project.
Use it to evaluate whether existing specs meet quality requirements and to guide
improvements when they don't.

**Purpose:** Reference standard (not a prompt)
**Scope:** All specification documents in `docs/spec-shards/` and `docs/spec*.md`
**Version:** 1.0

---

## Table of Contents

1. [Normative Language](#1-normative-language)
2. [Document Structure](#2-document-structure)
3. [Content Requirements](#3-content-requirements)
4. [Quality Criteria](#4-quality-criteria)
5. [Cross-Referencing](#5-cross-referencing)
6. [Domain Contracts](#6-domain-contracts)
7. [Acceptance Tests](#7-acceptance-tests)
8. [Evaluation Checklist](#8-evaluation-checklist)

---

## 1. Normative Language

All specifications MUST use RFC 2119 keywords consistently.

### Required Keywords

| Keyword | Meaning | Use For |
|---------|---------|---------|
| **SHALL** | Absolute requirement | Behavior that MUST occur exactly as stated |
| **SHALL NOT** | Absolute prohibition | Behavior that MUST NOT occur |
| **MUST** | Invariant | Property that cannot be violated |
| **MUST NOT** | Invariant prohibition | State that must never exist |
| **SHOULD** | Strong recommendation | Default behavior with justified exceptions |
| **SHOULD NOT** | Strong discouragement | Behavior to avoid unless justified |
| **MAY** | Optional | Implementation choice |

### Prohibited Phrasing

Do not use these; replace with RFC 2119 equivalents:

| Avoid | Replace With |
|-------|--------------|
| "will", "is", "does" | SHALL |
| "cannot", "won't" | SHALL NOT / MUST NOT |
| "can", "might" | MAY |
| "should" (lowercase) | SHOULD (uppercase) |

### Voice Requirements

- Use active voice: "Function X SHALL return Y" (not "Y is returned by X")
- Identify the subject: "The implementation SHALL..." or "Parameter X SHALL..."
- Avoid ambiguous subjects: "It should work" → "The parser SHALL accept..."

---

## 2. Document Structure

### Shard Organization

Specifications are organized into shards by concern:

| Shard | Purpose |
|-------|---------|
| `spec-db.md` | Index of all shards; terminology glossary |
| `spec-db-core.md` | Data types, domain model, mathematical foundations |
| `spec-db-workflow.md` | Processing pipeline, stages, sequencing |
| `spec-db-interfaces.md` | CLI, API, input/output formats |
| `spec-db-runtime.md` | Environment, determinism, resource management |
| `spec-db-conformance.md` | Acceptance tests, thresholds, validation |
| `spec-db-tracing.md` | Instrumentation, debug output, trace schemas |
| `spec-db-vis.md` | Visualization, diagnostics, report formats |

### Section Hierarchy

Each shard SHOULD follow this structure:

```markdown
# [Shard Title] — [Category] Specification (Normative)

<!--
Metadata: extraction source, iteration, confidence
-->

---

## Overview (Normative)

- **Purpose:** [One sentence]
- **Scope:** [What this shard covers]
- **Status:** Active | Draft | Deprecated

---

## [Major Section] (Normative|Informative)

### [Subsection]

[Content organized by topic]

---

## References (Informative)

- Cross-references to related shards
- External standards citations
```

### Section Labels

- **(Normative)** — Contains binding requirements (SHALL/MUST statements)
- **(Informative)** — Context, rationale, examples (no binding requirements)

---

## 3. Content Requirements

### 3.1 Data Type Specifications

Every public data type MUST include:

```markdown
### [TypeName]

**Definition:** [One sentence describing what this type represents]

**Fields:**

| Field | Type | Required | Contract |
|-------|------|----------|----------|
| `field_name` | `exact_type` | Yes/No | SHALL [constraint]. Default: [value]. |

**Invariants:**
1. [Property that MUST always hold]
2. [Relationship between fields]

**Construction:**
- [How instances are created, validation performed]
```

**Checklist:**
- [ ] All fields listed with exact types (`float`, not "number")
- [ ] Required vs optional clearly marked
- [ ] Defaults specified for optional fields
- [ ] Value constraints explicit (ranges, enums, patterns)
- [ ] Cross-field invariants stated
- [ ] Units specified where applicable

### 3.2 Computation Specifications

Every public function/method MUST include:

```markdown
### [function_name]

**Purpose:** [One sentence: what this computes/produces]

**Signature:** `result = function_name(param1, param2, ...)`

**Inputs:**

| Parameter | Type | Contract |
|-----------|------|----------|
| `param1` | `type` | SHALL [constraint]. Default: [value]. Units: [unit]. |

**Output:**
- Returns `type` of shape `[dimensions]`.
- [Property guarantees: normalized, sorted, bounded, etc.]

**Behavior:**
1. [Step-by-step observable behavior]
2. [Not implementation details]

**Error Conditions:**

| Condition | Behavior |
|-----------|----------|
| `param1 < 0` | SHALL raise `ValueError` with message containing "param1" |
```

**Checklist:**
- [ ] All parameters documented with exact types
- [ ] Valid ranges/constraints specified
- [ ] Units specified where applicable
- [ ] Return type and shape explicit
- [ ] Output properties guaranteed (bounds, dtype, etc.)
- [ ] All error conditions enumerated
- [ ] Exception types specified
- [ ] Error message patterns specified

### 3.3 Workflow/Pipeline Specifications

Multi-step processes MUST include:

```markdown
### [WorkflowName]

**Purpose:** [What this workflow accomplishes]

**Stages:**

1. **[Stage Name]**
   - **Input:** [what it receives, types, constraints]
   - **Process:** [observable transformation]
   - **Output:** [what it produces]
   - **Invariant:** [what MUST be true after this stage]

2. **[Next Stage]**
   - **Precondition:** [what previous stage guarantees]
   - ...

**Error Handling:**
- If Stage N fails: [effect on previous stages' outputs]
- Recovery behavior: [if any]

**Cross-References:**
- Stage 1 uses types from `spec-db-core.md § [Section]`
```

**Checklist:**
- [ ] All stages enumerated in order
- [ ] Input/output for each stage explicit
- [ ] Stage invariants (postconditions) stated
- [ ] Error propagation behavior defined
- [ ] Dependencies between stages clear

### 3.4 Interface Specifications

CLI and API interfaces MUST include:

```markdown
### [Command/Endpoint]

**Synopsis:**
```bash
command --flag VALUE [--optional VALUE]
```

**Arguments:**

| Argument | Type | Required | Contract |
|----------|------|----------|----------|
| `--flag` | `type` | Yes | SHALL [constraint]. |

**Precedence:** (when multiple sources)
1. CLI argument (highest)
2. Config file
3. Environment variable
4. Default (lowest)

**Exit Codes:**

| Code | Meaning | Condition |
|------|---------|-----------|
| 0 | Success | Normal completion |
| 1 | Error | [Specific condition] |

**Output Format:**
- [Schema, structure, content guarantees]
```

---

## 4. Quality Criteria

### 4.1 Verifiability

**Every normative statement MUST be testable.**

Ask: "How would I write a test for this statement?"

| Quality | Example |
|---------|---------|
| **Good** | "Output values SHALL be in range `[0.0, 1.0]`" |
| **Bad** | "Output should be reasonable" |
| **Good** | "SHALL raise `ValueError` with message containing 'threshold'" |
| **Bad** | "Errors should be handled appropriately" |
| **Good** | "Processing time SHALL be < 100ms for inputs < 1MB" |
| **Bad** | "Should be efficient" |

### 4.2 Precision

**Types, ranges, and constraints MUST be explicit.**

| Requirement | Good | Bad |
|-------------|------|-----|
| Types | `float64`, `np.ndarray[float32]` | "a number", "array" |
| Ranges | `SHALL be in [0, 100]` | "should be small" |
| Shapes | `shape [N, H, W]` where N = batch | "appropriate dimensions" |
| Units | "in millimeters", "in radians" | (implicit) |

### 4.3 Behavior vs Implementation

**Specify observable behavior, NOT implementation details.**

| Specify (Behavior) | Avoid (Implementation) |
|--------------------|------------------------|
| Input/output contracts | Algorithm choice |
| Error conditions | Internal data structures |
| State changes visible to callers | Variable names |
| Ordering guarantees | Performance (unless guaranteed) |
| Numerical precision guarantees | Code organization |

**Test:** Could someone reimplement this differently and still satisfy the spec?
If the spec forces a particular implementation, it's over-specified.

### 4.4 Accuracy

During bootstrapping: **Implementation is ground truth.**

- If spec and code differ, the spec is wrong
- No aspirational statements ("should eventually...")
- No invented behaviors (only what code actually does)
- Re-read implementation after drafting spec

### 4.5 Prohibited Language

Never use vague terms in normative statements:

- "reasonable", "appropriate", "proper", "suitable"
- "efficient", "fast", "performant" (without metric)
- "correctly", "properly", "well" (without definition)
- "etc.", "and so on", "similar" (be exhaustive)
- "generally", "usually", "typically" (be precise)

---

## 5. Cross-Referencing

### 5.1 Shard Index

All shards MUST be listed in `spec-db.md` with:
- Shard name and path
- One-line purpose
- Status (Active/Draft/Deprecated)

### 5.2 Cross-Reference Format

```markdown
See `spec-db-core.md` § Variance Model
Per `spec-db-workflow.md` § Stage A
As defined in `spec-db-interfaces.md` § CLI Arguments
```

### 5.3 Terminology

- **Define terms on first use** in each shard, or reference definition
- **Use consistent terminology** across shards (check spec-db.md glossary)
- **Add new terms** to spec-db.md terminology section
- **No undefined terms** in normative statements

### 5.4 Cross-Reference Validity

All cross-references MUST:
- Point to existing files
- Reference existing section headings
- Be updated when targets move/rename

---

## 6. Domain Contracts

Beyond input/output contracts, specs MUST capture domain-level requirements.

### 6.1 Mathematical Invariants

Relationships that must hold regardless of input:

```markdown
### [Invariant Name]

**Statement:** At [condition], [quantity] SHALL equal [expression].

**Tolerance:** ε ≤ [value] (e.g., 1e-12)

**Rationale:** [Why this invariant matters]

**Verification:** [How to test this]
```

**Examples:**
- Zero-point behavior: "At zero parameters, U(0) SHALL equal U₀"
- Decompositions: "A* SHALL equal U @ B"
- Conservation: "sum(weights) SHALL equal 1.0"
- Bounds: "variance SHALL be ≥ σ_floor²"

### 6.2 Conventions

Choices that must be consistent across implementations:

```markdown
### [Convention Name]

**Statement:** [Quantity] SHALL use [convention], consistent with [standard].

**External Standard:** [DIALS, dxtbx, PDB, etc.]

**Rationale:** [Why this convention]

**Error Behavior:** If input violates convention, SHALL [behavior].
```

**Categories:**
- **Coordinate conventions:** axis ordering, handedness, origin location
- **Index conventions:** 0-based vs 1-based, (row,col) vs (x,y)
- **Polarity conventions:** True=include vs True=exclude, sign of vectors
- **Unit conventions:** mm vs m, degrees vs radians, ADU vs photons

### 6.3 Acceptance Thresholds

Numeric criteria for correctness:

```markdown
### [Threshold Name]

**Metric:** [What is measured]

**Threshold:** [metric] SHALL be [comparison] [value]

**Provenance:** (per test_X.py:L42) | (per prior spec) | (domain requirement)

**Rationale:** [Why this threshold value]

**Failure Implication:** If not met, indicates [problem].
```

---

## 7. Acceptance Tests

The conformance shard (`spec-db-conformance.md`) MUST define acceptance tests.

### 7.1 Test Definition Format

```markdown
### [Test-ID]: [Descriptive Name]

**Purpose:** [What domain property this validates]

**Tier:** 1 (required) | 2 (standard) | 3 (extended)

**Setup:**
- Dataset: [path or description]
- Configuration: [key parameters]
- Baseline: [golden data or reference, if applicable]

**Execution:**
```bash
pytest tests/acceptance/test_[id].py -v
```

**Acceptance Criteria:**

| Criterion | Threshold | Rationale |
|-----------|-----------|-----------|
| [Metric 1] | [comparison] [value] | [Why this threshold] |

**Spec References:**
- `spec-db-core.md` § [Section] — [What requirement is validated]
```

### 7.2 Threshold Requirements

Every acceptance test MUST have:
- **Explicit numeric thresholds** (not "should pass")
- **Provenance** (where threshold comes from)
- **Rationale** (why this value)
- **Spec traceability** (which requirement it validates)

### 7.3 Test Tiers

| Tier | Name | Requirement |
|------|------|-------------|
| 1 | Required | MUST pass for any conforming implementation |
| 2 | Standard | SHOULD pass; exceptions require justification |
| 3 | Extended | MAY pass; tests edge cases or performance |

---

## 8. Evaluation Checklist

Use this checklist to evaluate whether a spec meets conventions.

### 8.1 Per-Statement Checklist

For each normative statement:

- [ ] Uses RFC 2119 keyword (SHALL/MUST/SHOULD/MAY)
- [ ] Active voice with clear subject
- [ ] Testable (can describe concrete test)
- [ ] Precise (explicit types, ranges, values)
- [ ] No vague language
- [ ] Accurate (matches implementation)

### 8.2 Per-Section Checklist

For each specification section:

- [ ] Follows appropriate template (data type / computation / workflow / interface)
- [ ] All parameters/fields documented
- [ ] Types explicit (not "number" but "float64")
- [ ] Constraints explicit (not "small" but "< 100")
- [ ] Units specified where applicable
- [ ] Error conditions enumerated
- [ ] Cross-references valid

### 8.3 Per-Shard Checklist

For each specification shard:

- [ ] Listed in spec-db.md index
- [ ] Has Overview section with Purpose/Scope/Status
- [ ] Sections labeled (Normative) or (Informative)
- [ ] Terms defined or referenced on first use
- [ ] Cross-references point to existing targets
- [ ] No undefined terminology in normative statements

### 8.4 Domain Completeness Checklist

For the specification set as a whole:

- [ ] All domain concepts from prior specs covered
- [ ] Mathematical invariants stated with tolerances
- [ ] Zero-point behaviors defined
- [ ] Conventions documented with external standards
- [ ] Acceptance thresholds have provenance
- [ ] Cross-cutting concerns addressed (tracing, vis, parity)

### 8.5 Scoring Thresholds

| Dimension | Threshold | Measurement |
|-----------|-----------|-------------|
| Coverage | ≥ 80% | Specified behaviors / total behaviors |
| Accuracy | ≥ 85% | Accurate clauses / total clauses |
| Consistency | ≥ 90% | 100 - (issues × 5) |
| Domain Completeness | ≥ 75% | Specified concepts / total concepts |

---

## Appendix A: Quick Reference Card

### RFC 2119 Keywords
```
SHALL      = absolute requirement
SHALL NOT  = absolute prohibition
MUST       = invariant (always true)
MUST NOT   = invariant prohibition
SHOULD     = strong recommendation
SHOULD NOT = strong discouragement
MAY        = optional
```

### Cross-Reference Format
```
See `spec-db-[shard].md` § [Section Name]
```

### Template Quick Reference

**Data Type:**
```
### TypeName
**Definition:** ...
**Fields:** | Field | Type | Required | Contract |
**Invariants:** 1. ...
```

**Computation:**
```
### function_name
**Purpose:** ...
**Signature:** ...
**Inputs:** | Parameter | Type | Contract |
**Output:** ...
**Error Conditions:** | Condition | Behavior |
```

**Acceptance Test:**
```
### TEST-ID: Name
**Purpose:** ...
**Tier:** 1|2|3
**Acceptance Criteria:** | Criterion | Threshold | Rationale |
**Spec References:** ...
```

---

## Appendix B: Common Deficiencies

| Deficiency | Example | Fix |
|------------|---------|-----|
| Missing RFC 2119 | "returns a tensor" | "SHALL return a tensor" |
| Vague constraint | "should be small" | "SHALL be < 100" |
| Implicit type | "takes an array" | "takes `np.ndarray[float32]`" |
| Missing units | "distance parameter" | "distance in millimeters" |
| No error spec | (errors not mentioned) | "SHALL raise ValueError if..." |
| Untestable | "handles errors properly" | "SHALL raise X with message Y" |
| Missing invariant | (decomposition in code) | "A* SHALL equal U @ B" |
| Missing threshold | "correlation should be good" | "correlation SHALL be ≥ 0.2" |
| Broken cross-ref | "see § Foo" (doesn't exist) | Update or remove reference |

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-XX-XX | Initial version extracted from spec_writer.md and spec_reviewer.md |
