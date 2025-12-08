# AGENTS.md (root)

This repository’s authoritative agent operating guide is `CLAUDE.md`.

Key policy: Environment Freeze — the runtime is pre-provisioned and MUST NOT be modified during loops. Do not install or upgrade packages; treat missing imports as blockers and record them in `docs/fix_plan.md`.

**Exception**: Targeted bugfixes to locally available source code are permitted when blocking critical paths:
- Scope: Patches to source trees under the workspace (e.g., `simtbx_project/`, vendored dependencies)
- Requirements:
  1. Save patch file (`.patch` or `.diff`) in the loop's artifacts directory
  2. Document rebuild commands and any dependencies used
  3. Test the fix resolves the blocking issue
  4. Update `docs/findings.md` with patch details and rationale
  5. Tag environment state (e.g., "simtbx-patched-diffbraggCUDA708")
- Rationale: Blocking bugs in local source prevent progress; targeted fixes with documentation maintain reproducibility without external package churn

Quick router:
- prompts/supervisor.md (supervisor rules), prompts/main.md (engineer loop)
- docs/index.md (docs hub), docs/TESTING_GUIDE.md (pytest selectors), docs/fix_plan.md (ledger), prompts/fsm_analysis.md (FSM)

Simulator import note (nanobrag_torch)
- The `nanobrag_torch` package imported by DBEX comes from the editable install under `/home/ollie/Documents/nanoBragg/src/nanobrag_torch`, not from the vendored `src/nanobrag-torch` tree inside this repository.
- Treat `/home/ollie/Documents/nanoBragg` as the authoritative runtime source for `nanobrag_torch` when reasoning about behavior. Under Environment Freeze, edits to that tree count as environment-level changes and MUST follow the same exception rules as other external dependencies (patch file, rebuild commands, findings entry, environment tag), not be assumed to take effect just by touching `src/nanobrag-torch` in this repo.
