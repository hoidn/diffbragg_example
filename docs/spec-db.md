# Specification Database Index

<!--
Central index for all normative specification shards.
Specs use RFC-2119 keywords: SHALL, MUST, MUST NOT, SHOULD, MAY
-->

---

## Shard Inventory

| Shard | Focus | Status |
|-------|-------|--------|
| [spec-db-core.md](./spec-shards/spec-db-core.md) | Core domain: units, data contracts, fundamental requirements | Pending |
| [spec-db-runtime.md](./spec-shards/spec-db-runtime.md) | Execution guardrails, environment, determinism | Pending |
| [spec-db-workflow.md](./spec-shards/spec-db-workflow.md) | Pipeline stages, data flow, processing order | Pending |
| [spec-db-interfaces.md](./spec-shards/spec-db-interfaces.md) | CLI/API surface, parameter precedence | Pending |
| [spec-db-conformance.md](./spec-shards/spec-db-conformance.md) | Acceptance test definitions, thresholds | Pending |

---

## How to Use Specs

### Reading Specs

- **Normative sections** - Requirements that implementations MUST follow
- **Informative sections** - Guidance, examples, rationale (not binding)
- **RFC-2119 keywords:**
  - `SHALL` / `MUST` - Required
  - `MUST NOT` - Prohibited
  - `SHOULD` - Recommended
  - `MAY` - Optional

### Citing Specs

Use section citations: `` `spec-db-core.md` Section Name ``

Example: "Per `spec-db-core.md` Units, all distances SHALL be in meters."

### Spec Precedence

During Bootstrap (extracting specs from implementation):
```
IMPLEMENTATION > TEMPLATES > EXISTING SPECS
```

After Bootstrap Complete:
```
SPECS > ARCHITECTURE DOCS > IMPLEMENTATION
```

---

## Adding New Specs

1. Create new shard file: `spec-shards/spec-db-[name].md`
2. Follow template structure (see ~/Documents/project-templates/docs/spec-shards/)
3. Mark sections as `(Normative)` or `(Informative)`
4. Add to this index
5. Cross-reference from related shards

---

## Cross-References

- **Architecture:** `docs/architecture/` - How specs are implemented
- **Contracts:** `docs/architecture/dbex/` - IDL-style API contracts
- **Tests:** Acceptance tests validate spec conformance

---

## Bootstrap Status

Phase: **Inventory** (iteration 0)
State file: `sync/spec_bootstrap_state.json`

Thresholds:
- Coverage: 80%
- Accuracy: 85%
- Consistency: 90%
