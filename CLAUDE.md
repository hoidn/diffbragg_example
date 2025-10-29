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

See: `CLAUDE.md` for full rules, FSM, artifact policy, and required reading.

