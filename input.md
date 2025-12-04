Summary: Document the probe-freeze enforcement guard so the diagnostic script policy and findings ledger cite the new architecture test.
Mode: Docs
ActionType: implementation_ready
DecisionStatus: localized
InitiativeType: architecture
Focus: ARCH-PROBE-FREEZE-001 — Probe Freeze & Logging Consolidation
Branch: integration
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' pytest -vv tests/architecture/test_probe_contracts.py | tee plans/active/ARCH-PROBE-FREEZE-001/reports/2026-01-01T010000Z/pytest_probe_contracts.log
Artifacts: plans/active/ARCH-PROBE-FREEZE-001/reports/2026-01-01T010000Z/
Findings Applied (Mandatory): No relevant findings — this loop authors the PROBE-FREEZE-001 entry tying the guard to policy.
Pointers:
  - plans/active/ARCH-PROBE-FREEZE-001/implementation.md:66-90 — Phase C.2/C.3 tasks outlining the required prompt + findings updates.
  - docs/fix_plan.md:836-866 — Attempts history + new 2026-01-01 planning note for the policy/finding hooks.
  - prompts/supervisor.md:254-309 — Current scriptization/diagnostic script policy text that must reference the enforcement test.
  - docs/TESTING_GUIDE.md:255-320 — Section already describing `tests/architecture/test_probe_contracts.py` (use for wording parity).
ARCH Contracts (mandatory):
  - prompts/supervisor.md:254-309 — Owner: Supervisor prompt (Galph); failure type: architecture conformance (policy does not yet cite the enforcement test or allowlist maintenance).
  - docs/architecture/data_telemetry_flow.md:42-118 — Owner: dbex.refinement telemetry/logging APIs; failure type: implementation bug (without policy hooks, plan scripts revert to shadow pipelines instead of using owner telemetry).
Do Now (hard validity contract)
1. Implement: `prompts/supervisor.md::diagnostic_script_policy` — expand this section to cite `tests/architecture/test_probe_contracts.py`, describe the 400 LOC growth-cap/allowlist workflow, list the shim scripts that must remain thin wrappers, and clarify artifact expectations when the test fails. Keep language in sync with docs/TESTING_GUIDE.md.
2. Implement: `docs/findings.md::PROBE-FREEZE-001` — add a new table row documenting the probe-freeze enforcement guard (tags: architecture, diagnostics). Reference `tests/architecture/test_probe_contracts.py`, `prompts/supervisor.md` §10, and the ARCH-PROBE-FREEZE-001 plan so future loops treat the guard as decision-carrying evidence.
3. Implement: Capture and attach the pytest log proving `tests/architecture/test_probe_contracts.py` still passes after the doc updates (command in Mapped tests). Store the log under the artifacts directory and mention it in summary.md.
Forbidden This Loop:
  - no edits to plan-local probe scripts or allowlist entries; documentation-only scope.
  - no new instrumentation or telemetry toggles outside the owner modules referenced above.
Mapped tests are mandatory; rerun until passing:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' pytest -vv tests/architecture/test_probe_contracts.py | tee plans/active/ARCH-PROBE-FREEZE-001/reports/2026-01-01T010000Z/pytest_probe_contracts.log
How-To Map:
  1. Update `prompts/supervisor.md` diagnostic script policy text per Do Now #1; ensure bullets explicitly mention the new pytest guard, allowlist maintenance, and shim expectations.
  2. Extend `docs/findings.md` with the PROBE-FREEZE-001 entry capturing owner responsibility, enforcement test, and plan references; keep table formatting consistent.
  3. Create `plans/active/ARCH-PROBE-FREEZE-001/reports/2026-01-01T010000Z/summary.md`, document the doc changes, then run the mapped pytest command and save the log in the same directory.
Pitfalls To Avoid:
  - Do not modify the `GROWTH_CAP_EXCEPTIONS` allowlist or shim list in the test file; this loop is documentation-only.
  - Keep prompt wording tightly aligned with docs/TESTING_GUIDE.md to avoid conflicting guidance.
  - Ensure the new finding references concrete files/lines (prompt + test) so the ledger stays actionable.
  - Maintain ASCII formatting in prompts/supervisor.md (angle-bracket XML sections must remain valid).
  - Reference the Problems Ledger directive when summarizing artifacts; this loop services that open issue.
If Blocked: Document the issue in `plans/active/ARCH-PROBE-FREEZE-001/reports/2026-01-01T010000Z/blockers.md`, update docs/fix_plan.md Attempts History with evidence, and notify Galph only after attaching the failing pytest log plus notes on the unresolved policy text.
