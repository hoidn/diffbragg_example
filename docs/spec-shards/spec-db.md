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

## Cross-References

- **Architecture:** `docs/architecture/` — How specs are implemented
- **Contracts:** `docs/architecture/contracts/` — Formal API signatures
- **Tests:** Acceptance tests validate spec conformance
