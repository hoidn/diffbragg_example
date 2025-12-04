# Phase C.2/C.3 Documentation Updates — ARCH-PROBE-FREEZE-001

**Loop**: Ralph (2026-01-01T010000Z)
**Mode**: Docs
**Action Type**: implementation_ready
**Decision Status**: localized
**Initiative Type**: architecture

## Problem & SPEC/ARCH Alignment

With Phase C.1 complete (enforcement test `tests/architecture/test_probe_contracts.py` delivered and passing), Phase C.2/C.3 required baking the enforcement guard into governance docs so CI/planning tooling can cite canonical sources.

**ARCH Contracts**:
- `prompts/supervisor.md:272-314` — Owner: Supervisor prompt (Galph); must reference the enforcement test, allowlist workflow, and shim expectations so future loops treat the guard as decision-carrying policy.
- `docs/findings.md` — Owner: Knowledge Base Ledger; must capture PROBE-FREEZE-001 as a decision-carrying finding with references to test + plan + Problems Ledger directive.

**Spec Alignment**: Per `input.md:21-22`, this loop implements documentation-only updates with no code changes. Both deliverables align with ARCH-PROBE-FREEZE-001 Phase C governance requirements.

## Search & Existing Implementation Summary

**Supervisor prompt (`prompts/supervisor.md:272-287`)**:
- Current state: diagnostic_script_policy section existed with thin wrapper rule + growth caps, but lacked explicit references to the mechanical enforcement test.
- Pattern: XML-formatted policy sections within the supervisor prompt.

**Findings ledger (`docs/findings.md:1-92`)**:
- Current state: 91 entries in markdown table format (ID | Date | Tags | Summary | Source | Status).
- Pattern: Single-line table rows with pipe-delimited fields; long summaries wrap naturally in markdown.
- Last entry before this loop: `REFINE-008` (line 91).

**Enforcement test (`tests/architecture/test_probe_contracts.py`)**:
- Delivered in Phase C.1 (2025-12-31T010000Z).
- Two test cases: `test_plan_bin_growth_cap` (400 LOC cap + allowlist) and `test_probe_shims_delegate_to_owner_clis` (AST-based delegation guard).
- Already documented in `docs/TESTING_GUIDE.md:255-320`.

## Code Analysis Performed

No code analysis required — this is a documentation-only loop per `input.md:2` (Mode: Docs).

**File inspections**:
- `prompts/supervisor.md:272-287` — Confirmed XML section structure and identified insertion point for enforcement guard bullets.
- `docs/findings.md:1-92` — Confirmed table format and identified insertion point after `REFINE-008` (line 91).
- `docs/TESTING_GUIDE.md:255-320` — Confirmed existing documentation of the enforcement test (provides wording parity baseline).

## Changes Made

### 1. `prompts/supervisor.md:272-314` — Expanded diagnostic_script_policy

Added four new bullet sections to `<diagnostic_script_policy>`:

**Enforcement guard** (lines 288-291):
- Describes `tests/architecture/test_probe_contracts.py` and its two test cases.
- Cites the 400 LOC cap enforcement via `GROWTH_CAP_EXCEPTIONS` allowlist.
- Documents shim delegation validation (AST-based guard for Phase B shims).

**Allowlist maintenance** (lines 293-294):
- Workflow: add entries with plan ID + cleanup intent, remove once refactored.
- Rationale: explicit allowlist prevents silent cap bypasses.

**Shim expectations** (lines 296-301):
- Acceptable structure: imports + optional `sys.path` + `if __name__` delegation.
- Forbidden: function/class definitions.

**Artifacts policy when tests fail** (lines 303-307):
- `test_plan_bin_growth_cap` failure: refactor to thin wrapper OR promote to `scripts/tools/`.
- `test_probe_shims_delegate_to_owner_clis` failure: remove definitions, migrate logic to owner modules.

**References** (lines 309-313):
- Cross-references to enforcement test, TESTING_GUIDE.md, findings.md, and plan implementation.md.

**Wording parity**: Aligned with `docs/TESTING_GUIDE.md:255-320` to ensure consistent guidance across docs.

### 2. `docs/findings.md:92` — Added PROBE-FREEZE-001 Entry

Inserted new table row after `REFINE-008` (line 91):

| Field | Content |
|-------|---------|
| **ID** | PROBE-FREEZE-001 |
| **Date** | 2026-01-01 |
| **Tags** | architecture, diagnostics |
| **Summary** | Probe Freeze & Logging Consolidation: Plan-local scripts under `plans/active/**/bin/*.py` MUST remain thin wrappers per `prompts/supervisor.md` §10 diagnostic_script_policy. Enforcement guard `tests/architecture/test_probe_contracts.py` mechanically validates: (a) `test_plan_bin_growth_cap` enforces 400 LOC cap with explicit `GROWTH_CAP_EXCEPTIONS` allowlist (13 legacy scripts documented by plan ID for cleanup traceability), (b) `test_probe_shims_delegate_to_owner_clis` asserts Phase B shims contain only imports + `if __name__` delegation to canonical `dbex.tools.*` owner modules. Allowlist maintenance: add entries with plan ID + cleanup intent, remove once refactored. Failure actions: refactor to thin wrapper (reduce LOC <400) OR promote to `scripts/tools/` under harness initiative with pytest coverage. When a plan-local script re-implements Stage/mapping/ROI/physics/refinement semantics, it MUST migrate to production owner APIs (dbex.refinement, dbex.tools, dbex.calibration) with telemetry hooks before extension. |
| **Source** | tests/architecture/test_probe_contracts.py, prompts/supervisor.md:272-314, plans/active/ARCH-PROBE-FREEZE-001/implementation.md, docs/TESTING_GUIDE.md:255-320 |
| **Status** | Active |

**Rationale**:
- Captures the probe-freeze enforcement guard as a decision-carrying finding.
- References concrete files/lines (prompt + test + plan) so the ledger stays actionable.
- Tags: `architecture` (structural policy), `diagnostics` (telemetry/instrumentation scope).
- Satisfies `input.md:22` requirement to "reference concrete files/lines" and TESTING-003 (selector compliance).

## Tests and Static Checks

### Pytest Execution

**Command**:
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' pytest -vv tests/architecture/test_probe_contracts.py
```

**Outcome**:
```
2 passed in 0.27s
```

**Test cases validated**:
1. `test_plan_bin_growth_cap` — PASSED
   - Validated 13 allowlisted scripts exceed 400 LOC.
   - Confirmed all other scripts comply with cap.
2. `test_probe_shims_delegate_to_owner_clis` — PASSED
   - Validated 3 Phase B shims (embed_sigma_external_lookup.py: 19 lines, compare_mapping_dataset_metrics.py: 39 lines, capture_smoke_calibration.py: 37 lines).
   - Confirmed no function/class definitions detected in shims.

**Log captured**: `plans/active/ARCH-PROBE-FREEZE-001/reports/2026-01-01T010000Z/pytest_probe_contracts.log`

### Static Checks

**N/A** — Mode: Docs, no code changes. Documentation updates do not require formatter/linter runs.

**XML Validation** (prompts/supervisor.md):
- Manually verified opening/closing tags: `<diagnostic_script_policy>` and `</diagnostic_script_policy>` remain balanced.
- Verified `<strong>`, `<code>` tags properly closed.
- No syntax errors introduced in XML-formatted prompt sections.

**Markdown Validation** (docs/findings.md):
- Table row formatting validated: pipe-delimited fields align with existing schema.
- No line breaks introduced in table cells (multi-line summary wrapped naturally).

## Docs & Ledgers Updates

### 1. Updated `prompts/supervisor.md:272-314`

**Section**: `<diagnostic_script_policy>`
**Changes**: Added 4 new bullet sections (enforcement guard, allowlist maintenance, shim expectations, artifacts policy, references).
**Line count**: +42 lines (lines 288-313 new content).
**Cross-references**:
- `tests/architecture/test_probe_contracts.py` (enforcement test)
- `docs/TESTING_GUIDE.md:255-320` (execution workflow)
- `docs/findings.md::PROBE-FREEZE-001` (decision-carrying finding)
- `plans/active/ARCH-PROBE-FREEZE-001/implementation.md` (Phase C guardrails)

**Wording parity**: Aligned with `docs/TESTING_GUIDE.md` to avoid conflicting guidance (per `input.md:35`).

### 2. Updated `docs/findings.md:92`

**Entry**: PROBE-FREEZE-001
**Tags**: architecture, diagnostics
**Sources**:
- `tests/architecture/test_probe_contracts.py` (enforcement guard)
- `prompts/supervisor.md:272-314` (policy text)
- `plans/active/ARCH-PROBE-FREEZE-001/implementation.md` (plan context)
- `docs/TESTING_GUIDE.md:255-320` (usage guidance)

**Formatting**: Single-line table row with pipe-delimited fields (consistent with existing entries).

### 3. No Updates to `docs/fix_plan.md`

**Rationale**: `docs/fix_plan.md:866` already documents this loop's planning note (2026-01-01T010000Z Phase C.2 planning). Attempts History will be updated in the commit message per the version control step below.

### 4. No Updates to Architecture Docs

**Rationale**: This loop services an existing architecture plan (ARCH-PROBE-FREEZE-001). No new ADRs or architecture docs required; the enforcement test + policy updates constitute the Phase C deliverable.

## Version Control

**Commit Message**:
```
ARCH-PROBE-FREEZE-001: Document probe-freeze guard (tests: test_probe_contracts.py)

Phase C.2/C.3 — Expanded prompts/supervisor.md diagnostic_script_policy
to cite tests/architecture/test_probe_contracts.py enforcement guard,
allowlist maintenance workflow, shim delegation expectations, and failure
artifacts. Added PROBE-FREEZE-001 to docs/findings.md with references to
test + prompt + plan so future loops treat the 400 LOC cap and thin-wrapper
rule as decision-carrying policy.

Validation: tests/architecture/test_probe_contracts.py (2/2 PASSED in 0.27s)
- test_plan_bin_growth_cap: 13 allowlisted scripts validated, all others compliant
- test_probe_shims_delegate_to_owner_clis: 3 Phase B shims validated (no definitions)

Files touched:
- prompts/supervisor.md (+42 lines: enforcement guard, allowlist workflow, shim expectations, references)
- docs/findings.md (+1 entry: PROBE-FREEZE-001 with test/prompt/plan sources)

Artifacts: plans/active/ARCH-PROBE-FREEZE-001/reports/2026-01-01T010000Z/
- pytest_probe_contracts.log (2 passed in 0.27s)
- summary.md (this document)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Files to commit**:
- `prompts/supervisor.md` (documentation update)
- `docs/findings.md` (new PROBE-FREEZE-001 entry)
- `plans/active/ARCH-PROBE-FREEZE-001/reports/2026-01-01T010000Z/pytest_probe_contracts.log` (test evidence)
- `plans/active/ARCH-PROBE-FREEZE-001/reports/2026-01-01T010000Z/summary.md` (this document)

## Next Step

**Phase C.2/C.3 Exit Criteria Satisfied**:
- ✅ `prompts/supervisor.md::diagnostic_script_policy` expanded with explicit reference to `test_probe_contracts.py`, allowlist workflow, shim roster, and artifact expectations.
- ✅ `docs/findings.md::PROBE-FREEZE-001` added, documenting the enforcement guard with concrete file:line references.
- ✅ Pytest log captured proving enforcement test still passes after doc updates (2/2 PASSED in 0.27s).
- ✅ Wording parity maintained with `docs/TESTING_GUIDE.md` to avoid conflicting guidance.
- ✅ ASCII formatting preserved in `prompts/supervisor.md` (XML tags balanced).

**Completion Status**: Phase C.2/C.3 complete. Documentation-only scope per `input.md:24-26` (no edits to plan-local scripts, no new instrumentation, no telemetry toggles).

**Next Action for Galph**:
1. Review this summary.md + pytest log to confirm policy/finding hooks satisfy the Problems Ledger directive ("Freeze plan-local probe scripts…").
2. If satisfied, mark ARCH-PROBE-FREEZE-001 Phase C complete in `docs/fix_plan.md` Attempts History.
3. If additional governance hooks are needed (e.g., CI integration, pre-commit hook), schedule follow-up loop under a new harness initiative.

---

### Turn Summary

Documented the probe-freeze enforcement guard in governance docs (prompts/supervisor.md + docs/findings.md). Expanded diagnostic_script_policy with enforcement test references, allowlist maintenance workflow, shim expectations, and failure artifacts. Added PROBE-FREEZE-001 finding with test/prompt/plan sources. Validated enforcement test (2/2 PASSED in 0.27s). No code changes per Docs mode. Next: Galph review + Phase C close-out.

Artifacts: `plans/active/ARCH-PROBE-FREEZE-001/reports/2026-01-01T010000Z/pytest_probe_contracts.log`, `summary.md`
