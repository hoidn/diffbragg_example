# Phase B.1 Planning Notes — Consumer Mapping

**Initiative:** FINDINGS-LEDGER-002
**Date:** 2025-12-07T060000Z
**Phase:** B.1 (Map Consumers)

---

## Objective

Map Active findings from `docs/findings.md` (74 entries per Phase A.2 inventory) to their fix-plan consumers (initiatives, roll-ups, test selectors) to establish bidirectional crosslinks between the knowledge base and active work.

---

## Methodology

1. **Input artifacts:**
   - `docs/findings.md` — knowledge base ledger (86 total findings, 74 Active)
   - `docs/fix_plan.md` — fix-plan ledger (Tier 0–4 + detailed initiative sections)
   - Phase A.2 inventory: `plans/active/FINDINGS-LEDGER-002/reports/2025-12-03T120250Z/findings_inventory.json`

2. **Consumer extraction:**
   - Wrote `map_consumers.py` script to grep `fix_plan.md` for each Active finding ID
   - Extracted initiative IDs from matching lines via regex `\[([A-Z\-0-9]+)\]`
   - Deduplicated consumers per finding and stored in `consumer_map.json`

3. **Classification:**
   - **Pattern findings**: General constraints governing multiple initiatives (e.g., GEOMETRY-*, RUNTIME-001, TESTING-*)
   - **Blocker findings**: Specific bugs or missing functionality blocking progress (e.g., DIAG-UNIT-001, REFINE-010/015, PERF-WARM-011)

---

## Results Summary

| Metric | Count | Percentage |
|--------|-------|------------|
| Total Active Findings | 74 | 100% |
| Findings with Consumers | 9 | 12.2% |
| Orphaned Findings | 64 | 86.5% |
| Pattern Findings (est.) | ~40 | ~54% |
| Blocker Findings (est.) | ~34 | ~46% |

**Key findings WITH consumers:**
- CONFORMANCE-001 → ARCH-IMPL-CONFORMANCE-001, RECOMMENDED (lifecycle decision)
- REFINE-001 → ARCH-REFINE-001, TORCH-REFINE-CLEANUP-001
- SCALE-001 → MAP-SCALE-SYNC-001
- REFINE-007 → PERF-WARM-SIM-001 (2 references)
- REFINE-012 → PERF-WARM-SIM-001
- CONVERGENCE-001 → TORCH-GEOMETRY-SYNC-001
- PHYSICS-LOSS-001, SCALE-008, SCALE-009 → various Attempts History references

---

## Why 86% Are Orphaned

### Root Causes

1. **Implicit governance**: Pattern findings (GEOMETRY-*, CONFIG-*, TESTING-*, RUNTIME-001, DIAGNOSTICS-001, MASKING-001, PARITY-001) establish normative behaviors that govern **all** initiatives but aren't explicitly cited in fix-plan initiative titles or status lines.

2. **Ledger structure mismatch**:
   - Fix-plan Attempts History cites findings inline (e.g., "per REFINE-007", "addresses SCALE-008") but initiative summaries don't always include finding IDs in searchable format.
   - Roll-up initiative descriptions (e.g., TORCH-REFINE-CLEANUP-001, MAP-SCALE-SYNC-001) aggregate multiple sub-plans but don't explicitly list their governing findings.

3. **Plan-local references**:
   - Findings referenced in `plans/active/<initiative>/implementation.md` or `reports/*.md` won't appear in top-level fix_plan.md grep.
   - Example: GEOMETRY-004 governs TORCH-GEOMETRY-UB-REALIGN-001 but citation lives in plan-local docs.

4. **Completed/archived work**:
   - Findings like CLI-001/002, CONFIG-002/003, REFINE-014 may govern past work that's now archived or folded into "done" initiatives (ARCH-REFINE-001, ARCH-IMPL-CONFORMANCE-001).
   - Once code changes land and tests pass, finding references may persist only in Attempts History rather than active initiative tracking.

5. **Missing roll-up initiatives**:
   - Clusters of related findings lack a unifying initiative:
     - PERF-WARM-001 through PERF-WARM-013 (12 findings) → should map to PERF-WARM-SIM-001 but only 3 are cited
     - REFINE-002/003/006/008/009/010/011/013/014/015/016 (11 findings) → should map to TORCH-REFINE-CLEANUP-001 but only REFINE-001 is cited
     - PHYSICS-LOSS-002/003/004/005 (4 findings) → no dedicated initiative
     - ARCH-STAGE-CTX-001/002 → no dedicated initiative tracking context consolidation

---

## Consumer Coverage Analysis

### High-Impact Findings (Pattern + Blocker Intersection)

**These findings should have explicit consumers but are orphaned:**

| Finding ID | Type | Why It Needs a Consumer | Recommended Consumer |
|------------|------|-------------------------|----------------------|
| GEOMETRY-001 | Pattern | Governs all bridge mapping logic | TORCH-GEOMETRY-SYNC-001 or new [BRIDGE-GOVERNANCE-001] |
| GEOMETRY-002 | Pattern | Governs DIALS rotation angle inversion | TORCH-GEOMETRY-SYNC-001 |
| GEOMETRY-003 | Pattern | Stage A baseline misset derivation | TORCH-GEOMETRY-SYNC-001 |
| GEOMETRY-004 | Pattern | Stage A UB parameterization | TORCH-GEOMETRY-UB-REALIGN-001 (via TORCH-GEOMETRY-SYNC-001) |
| CONFIG-001 | Pattern | Governs all dxtbx→nanobrag hydration | New [BRIDGE-GOVERNANCE-001] or NANOBRAG-GOLDEN-001 |
| RUNTIME-001 | Pattern | Gradient test environment requirements | RUNTIME-VEC-001 or new [TESTING-HARNESS-001] |
| TESTING-003 | Pattern | Selector activation protocol | DB-AT-SUITE-CARE-001 or TESTING-GUIDE maintenance |
| PARITY-001 | Pattern | First-divergence debugging workflow | FORWARD-EQUIV-COVERAGE-001 or new [PARITY-TOOLING-001] |
| PHYSICS-LOSS-002 | Blocker | Sigma-floor guard enforcement | New [PHYSICS-LOSS-CONSISTENCY] |
| PHYSICS-LOSS-003 | Blocker | Stage A vs B/C chi-squared inconsistency | New [PHYSICS-LOSS-CONSISTENCY] |
| PHYSICS-LOSS-004 | Pattern | CLI sigma-map ingestion contract | New [PHYSICS-LOSS-CONSISTENCY] |
| PHYSICS-LOSS-005 | Pattern | DIALS external_lookup harvest spec | New [PHYSICS-LOSS-CONSISTENCY] |
| PERF-WARM-002 | Blocker | Warm-mode still rebuilds crystal configs | PERF-WARM-SIM-001 (should be explicit in ledger) |
| PERF-WARM-009 | Blocker | Stage B ROI-mode evaluates wrong subset | PERF-WARM-SIM-001 (should be explicit in ledger) |
| PERF-WARM-011 | Blocker | Stage B GPU OOM on panel mode | PERF-WARM-SIM-001 (should be explicit in ledger) |
| PERF-WARM-013 | Blocker | Stage C instantiates fresh simulators | PERF-WARM-SIM-001 (should be explicit in ledger) |
| REFINE-002 | Gate | Stage A nucleus improvement threshold | TORCH-REFINE-CLEANUP-001 (should be explicit) |
| REFINE-003 | Pattern | Stage A orientation refinement contract | TORCH-REFINE-CLEANUP-001 (should be explicit) |
| REFINE-010 | Blocker | Stage A ROI-mode LBFGS stalls | ARCH-REFINE-001 or TORCH-REFINE-CLEANUP-001 |
| REFINE-011 | Blocker | Stage C ROI-mode subset mismatch | PERF-WARM-SIM-001 (related to REFINE-012) |
| REFINE-013 | Blocker | Stage C best_params_snapshot never written back | ARCH-REFINE-001 or PERF-WARM-SIM-001 |
| REFINE-015 | Blocker | Stage C ignores calibrated log_scale baseline | ARCH-REFINE-001 or PERF-WARM-SIM-001 |
| REFINE-016 | Pattern | Stage A panel-mode trusted mask intersection | ARCH-REFINE-001 |
| ARCH-STAGE-CTX-001 | Blocker | Stage implementations pass 10–15 positional args | New [ARCH-STAGE-CONTEXT-CONSOLIDATION] |
| ARCH-STAGE-CTX-002 | Blocker | Stage B mutates telemetry shims via dict | New [ARCH-STAGE-CONTEXT-CONSOLIDATION] |
| SCALE-002 | Pattern | Global post-simulation factor application | MAP-SCALE-SYNC-001 (should be explicit) |
| SCALE-003 | Blocker | Zero-iteration helper must ingest refined amplitudes | MAP-SCALE-SYNC-001 (should be explicit) |
| SCALE-005 | Blocker | N_cells injection multiplies intensities ~3.2e5× | MAP-SCALE-SYNC-001 (should be explicit) or ARCH-SIM-CONSTRUCTION-001 |
| SCALE-006 | Pattern | CLI must ingest config_torch.json metadata | MAP-SCALE-SYNC-001 (should be explicit) |
| DIAG-UNIT-001 | Blocker | nanobrag_torch Crystal units mismatch (meters vs Å⁻¹) | ARCH-SIM-CONSTRUCTION-001 or DIAG-NANOBRAGG-OVERSAMPLE-001 |

---

## Phase B.2 Strategy

### Objective
Update both `docs/findings.md` AND `docs/fix_plan.md` to establish reciprocal links.

### Tasks

#### 1. Update fix_plan.md Initiative Descriptions

For each roll-up/initiative with orphaned findings, add explicit "Governed By" or "Findings" line:

**Example (TORCH-REFINE-CLEANUP-001):**
```markdown
- [TORCH-REFINE-CLEANUP-001] (Stage A/B/C refinement probes TORCH-REFINE-001/002/002D/002E/003) — **pending**.
  - **Governed by:** REFINE-001, REFINE-002, REFINE-003, REFINE-006, REFINE-010
  - Ledger entry will consolidate their status and dependencies...
```

**Example (MAP-SCALE-SYNC-001):**
```markdown
- [MAP-SCALE-SYNC-001] (Calibration ladder initiatives MAP-SCALE-001—005) — **pending**.
  - **Governed by:** SCALE-001, SCALE-002, SCALE-003, SCALE-004, SCALE-005, SCALE-006, SCALE-007
  - Plans live under `plans/active/MAP-SCALE-00X/`...
```

**Example (PERF-WARM-SIM-001):**
```markdown
- [PERF-WARM-SIM-001] (Warm Simulator) — **blocked**.
  - **Governed by:** PERF-WARM-001 through PERF-WARM-013, REFINE-007, REFINE-011, REFINE-012
  - Full-detector telemetry shows Stage C panel-loss path diverges...
```

**Example (New initiative — PHYSICS-LOSS-CONSISTENCY):**
```markdown
### Tier 1: Core Physics & Stability
- [PHYSICS-LOSS-CONSISTENCY] (Physics Loss Function Alignment) — **pending**.
  - **Governed by:** PHYSICS-LOSS-001, PHYSICS-LOSS-002, PHYSICS-LOSS-003, PHYSICS-LOSS-004, PHYSICS-LOSS-005
  - **Goal:** Align Stage A/B/C chi-squared computation, enforce sigma-floor guard, unify sigma-map ingestion, harvest DIALS external_lookup metadata.
  - **Exit Criteria:** All stages use identical variance-weighted denominator, telemetry persists chi_squared + masked_mse, sigma-floor enforcement validated via unit tests.
```

**Example (New initiative — ARCH-STAGE-CONTEXT-CONSOLIDATION):**
```markdown
### Tier 2: Architectural Maturity
- [ARCH-STAGE-CONTEXT-CONSOLIDATION] (Stage Context Parameter Consolidation) — **pending**.
  - **Governed by:** ARCH-STAGE-CTX-001, ARCH-STAGE-CTX-002
  - **Depends on:** ARCH-REFACTOR-001 (Phases A-C complete)
  - **Goal:** Replace 10–15 positional arguments with typed context dataclasses, eliminate telemetry dict mutations in Stage B baseline parity guard.
  - **Exit Criteria:** Stage helpers accept single `context` parameter, telemetry updates use dataclass property assignment, enforcement test validates context immutability.
```

#### 2. Update findings.md with Consumer Metadata

Add "Consumers" field to each finding entry (or expand Summary to include it):

**Example (GEOMETRY-001):**
```markdown
| GEOMETRY-001 | 2025-10-28 | geometry, detector, dxtbx | Bridge MUST derive beam center and detector vectors exactly per dxtbx mapping; reject non-square pixel pitch. **Consumers:** TORCH-GEOMETRY-SYNC-001 (bridge governance). | docs/spec-db-core.md:35 | Active |
```

**Example (REFINE-010):**
```markdown
| REFINE-010 | 2025-12-01 | refinement, stage-a, roi-mode | Stage A ROI-mode LBFGS on refGeom_small (29 ROIs) stalls at 0% improvement even with `roi_sample_fraction=1.0`. **Consumers:** TORCH-REFINE-CLEANUP-001 (Stage A nucleus work), ARCH-REFACTOR-001 (ROI-mode debugging). | plans/active/ARCH-REFINE-001/reports/2025-12-01T105500Z/stage_c_stage_a_probe_cli.json, docs/spec-db-workflow.md:116-128 | Active |
```

*(Alternatively, add a separate "Consumers" column to the findings.md table, but this may require reformatting the entire ledger.)*

#### 3. Create Missing Roll-up Initiatives

Add these to fix_plan.md Tier 1 or Tier 2:

- **[PHYSICS-LOSS-CONSISTENCY]** — Align loss computation across Stage A/B/C (PHYSICS-LOSS-001/002/003/004/005)
- **[ARCH-STAGE-CONTEXT-CONSOLIDATION]** — Consolidate positional args into typed contexts (ARCH-STAGE-CTX-001/002)
- **[BRIDGE-GOVERNANCE-001]** (optional) — Centralize dxtbx→nanobrag config hydration patterns (GEOMETRY-001/002/003/004, CONFIG-001)
- **[PARITY-TOOLING-001]** (optional) — Standardize first-divergence debugging workflow (PARITY-001, DIAGNOSTICS-001)

#### 4. Archive/Retire Candidates (Phase B.3)

Validate and retire findings where code fixes are confirmed:

| Finding ID | Validation Method | Target Status |
|------------|-------------------|---------------|
| CLI-001 | Run `pytest tests/dbex/test_refine_one_cli.py -k mask` | Resolved if passing |
| CLI-002 | Run `pytest tests/dbex/test_refine_one_cli.py -k telemetry` | Resolved if passing |
| CONFIG-002 | Run `pytest tests/dbex/test_nanobrag_bridge_configs.py -k convention` | Resolved if passing |
| CONFIG-003 | Run `pytest tests/dbex/test_nanobrag_bridge_configs.py -k polarization` | Resolved if passing |
| REFINE-014 | Check `dbex/refinement/stage_c.py` for misset_xyz conversion fix | Resolved if fixed |
| SCALE-003 | Check `dbex/nanobrag_bridge.py` for refined amplitude ingestion | Resolved if implemented |

---

## Validation Metrics for Phase B.2

**Success criteria:**
1. **Consumer coverage ≥80%**: At least 59 of 74 Active findings have explicit consumer references in fix_plan.md
2. **Reciprocal links**: Each cited finding includes "Consumers: [INITIATIVE-ID]" metadata in findings.md
3. **Roll-up completeness**: All major finding clusters (PERF-WARM-*, REFINE-*, SCALE-*, PHYSICS-LOSS-*, GEOMETRY-*) map to documented initiatives
4. **Artifact validation**: `crosslink_matrix.md` updated with Phase B.2 changes, consumer_map.json regenerated to confirm ≥80% coverage

---

## Blockers & Risks

**None identified for Phase B.1.** Phase B.2 execution will require:
- Write access to `docs/findings.md` and `docs/fix_plan.md` (coordinate via git pull --rebase)
- Validation passes for archive/retire candidates (may require running pytest selectors)
- Supervisor approval for new roll-up initiatives (PHYSICS-LOSS-CONSISTENCY, ARCH-STAGE-CONTEXT-CONSOLIDATION)

---

## Artifacts

- `consumer_map.json` — machine-readable finding → consumer mapping (74 entries, 9 with consumers)
- `crosslink_matrix.md` — Phase B.1 consumer analysis (this report's companion)
- `map_consumers.py` — reproducible consumer extraction script
- `planning_notes.md` — this document (Phase B.2 strategy)
