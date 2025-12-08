# Input for Ralph (Loop i=178)

## Summary
Execute TORCH-CLI-BRIDGE-ROLLUP-001 Phase A — Member Plan Reality Check and Inventory.

## BindingForRalph
- **ActionType:** evidence_collection
- **DecisionStatus:** exploring
- **InitiativeType:** roll-up

## SupervisorMode
Docs (roll-up inventory and roadmap drafting — no production code changes)

## Focus
TORCH-CLI-BRIDGE-ROLLUP-001 — CLI & Bridge Infrastructure Roll-up — Phase A (Member Plan Inventory)

## Branch
integration

## Mapped Tests
- None — this is an evidence-collection/docs-only loop; validation deferred to Phase B

## Artifacts
`plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/reports/2025-12-08T073000Z/`

## Findings Applied (Mandatory)
- **PROBE-FREEZE-001** (Plan-local probe policy): No new persistent scripts; use existing tests and inline Python only
  - Adherence: Evidence collection only; no new bin/ scripts
- **DIAGNOSTICS-001** (Diagnostic artifact expectations): Artifacts follow established JSON/markdown patterns
  - Adherence: Artifacts routed to `reports/2025-12-08T073000Z/`
- No other findings directly applicable to this inventory task

## Pointers
- Roll-up entry: `docs/fix_plan.md` lines 405-422
- Member plan TORCH-BRIDGE-001: `plans/active/TORCH-BRIDGE-001/implementation.md` (Phase A-C done, Phase D pending)
- Member plan TORCH-CLI-003: `plans/active/TORCH-CLI-003/implementation.md`
- Member plan TORCH-CLI-004: `plans/active/TORCH-CLI-004/implementation.md` (all phases pending)
- Exit criteria: `docs/fix_plan.md` lines 412-416

---

## ARCH Contracts (mandatory)
- **Environment Freeze**: No package installs; read-only evidence collection
  - Owner: CLAUDE.md
  - Classification: Roll-up Phase A — inventory and reality check only

---

## Do Now

**Focus:** TORCH-CLI-BRIDGE-ROLLUP-001 Phase A — Member Plan Inventory

**Implement:** `plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/implementation.md::phase_a_inventory`

**Validating Pytest Selector:** None (evidence-collection loop)

### Background
TORCH-CLI-BRIDGE-ROLLUP-001 depends on REPORT-NANOBRAG-STATUS-001 (output schema), which is now **done**. The roll-up covers 3 member plans:
1. **TORCH-BRIDGE-001** (Bridge DataLoad to nanobrag_torch): Phase A-C complete, Phase D (closeout) pending
2. **TORCH-CLI-003** (implementation.md exists)
3. **TORCH-CLI-004** (Torch diagnostics ROI score coercion): All phases pending

The roll-up `implementation.md` is currently a stub. This Phase A builds the real roadmap.

### Phase A Tasks

#### A1 — Member Plan Reality Check
For each member plan, verify:
- Current implementation.md status vs reality
- Which phases are truly complete (check if tests pass, code exists)
- Which phases are pending/blocked

Member plans to audit:
1. `plans/active/TORCH-BRIDGE-001/implementation.md` — Phase A-C marked complete; Phase D (D1-D4) pending closeout
2. `plans/active/TORCH-CLI-003/implementation.md` — Status unknown, read and assess
3. `plans/active/TORCH-CLI-004/implementation.md` — All phases pending per implementation.md

#### A2 — Inventory Remaining Work
Compile a work breakdown:
- Count remaining tasks across all member plans
- Identify dependencies between member plans
- Estimate scope (docs-only vs code changes)

Output: `member_plan_inventory.md` with:
- Table of member plans with status/remaining phases
- Dependency graph (if any)
- Total remaining task count

#### A3 — Draft Roll-up Roadmap
Create a roadmap for the roll-up:
- Sequence member plan closeouts (TORCH-BRIDGE-001 Phase D first if quickest)
- Identify which exit criteria (EC1-EC4) each member plan addresses
- Note any blockers or prerequisites

Output: `roadmap_draft.md` with:
- Phased approach for roll-up completion
- Exit criteria mapping to member plans
- Estimated loop count per phase

#### A4 — Update Roll-up implementation.md
Replace the stub `plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/implementation.md` with a real plan:
- Phase A: Member Plan Inventory (this loop)
- Phase B: TORCH-BRIDGE-001 closeout
- Phase C: TORCH-CLI-003 completion
- Phase D: TORCH-CLI-004 completion
- Phase E: Roll-up closure

#### A5 — Author Summary
Create `reports/2025-12-08T073000Z/summary.md` with:
- Member plan status overview
- Key findings from reality check
- Recommended next focus (likely TORCH-BRIDGE-001 Phase D)

---

## How-To Map

```bash
# Set environment
cd /home/ollie/Documents/diffbragg_example
export ARTIFACT_DIR=plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/reports/2025-12-08T073000Z

# A1: Read member plan implementation.md files
# Use Read tool on:
#   - plans/active/TORCH-BRIDGE-001/implementation.md
#   - plans/active/TORCH-CLI-003/implementation.md
#   - plans/active/TORCH-CLI-004/implementation.md

# A2: Check test status for TORCH-BRIDGE-001 (completed phases)
# Optional: verify tests still pass
KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only tests/dbex/test_nanobrag_bridge.py tests/dbex/test_nanobrag_bridge_configs.py tests/dbex/test_nanobrag_smoke.py 2>&1 | head -30

# A3-A5: Create artifacts using Write tool
```

---

## Forbidden This Loop
- **No production code changes** — Inventory/docs only
- **No package installs** — Environment Freeze
- **No new persistent scripts** — Use inline Python per PROBE-FREEZE-001

## Pitfalls To Avoid
1. **Don't run full test suites** — Only collect-only or targeted verification
2. **Don't modify member plan implementation.md files** — Only read and inventory
3. **Focus on reality check** — Verify claimed status matches actual state
4. **Cross-reference fix_plan.md** — Ensure ledger consistency

## If Blocked
If member plan files are missing:
1. Document the gap in `reports/2025-12-08T073000Z/error.md`
2. Recommend creating missing implementation.md files as Phase B prerequisite
3. Note limitation in summary

---

## Exit Criteria Validation (Phase A)

| Criterion | Expected | Validation |
|-----------|----------|------------|
| Member plan inventory | All 3 plans audited | member_plan_inventory.md |
| Roadmap drafted | Phased approach documented | roadmap_draft.md |
| Roll-up implementation.md | Stub replaced with real plan | implementation.md diff |
| Summary authored | Phase A closure | summary.md |

---

## Output Artifacts Expected

1. `plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/reports/2025-12-08T073000Z/member_plan_inventory.md`
2. `plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/reports/2025-12-08T073000Z/roadmap_draft.md`
3. `plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/reports/2025-12-08T073000Z/summary.md`
4. Updated `plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/implementation.md`

---

## Implement Target
`plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/implementation.md::phase_a_inventory` (docs update)

## Validating Pytest Selectors
None — evidence-collection loop

---

## Next Up (optional)
If Phase A completes successfully:
- Proceed to Phase B: TORCH-BRIDGE-001 Phase D closeout (D1-D4: re-run tests, update ledgers, registry sync)
- TORCH-BRIDGE-001 Phase D is docs-heavy and quickest path to partial roll-up progress
