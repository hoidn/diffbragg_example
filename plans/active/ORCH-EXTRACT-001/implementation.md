# Implementation Plan: Orchestration Submodule Extraction

## Initiative
- ID: ORCH-EXTRACT-001
- Title: Extract orchestration scripts to reusable Git submodule
- Owner: ollie
- Spec Owner: N/A (infrastructure, not science code)
- Status: in_progress

## Goals
- Enable reuse of galph/ralph orchestration across multiple projects
- Remove project-specific and user-specific hardcoding
- Establish configuration convention (`orchestration.yaml`) for portability
- Preserve Environment Freeze compliance (submodule updates = code changes, not env changes)

## Phases Overview
- Phase A — Decouple: Remove hardcoded paths, add config loader
- Phase B — Extract: Create standalone repo, convert to submodule
- Phase C — Validate: Test in second project, document conventions

## Exit Criteria
1. `scripts/orchestration/` is a git submodule pointing to standalone repo
2. No `/home/ollie/` or other user-specific paths in codebase
3. All project-specific paths read from `orchestration.yaml`
4. Self-references use `Path(__file__)` instead of hardcoded paths
5. Second consumer project successfully runs galph/ralph loops
6. README documents configuration schema and submodule usage

## Compliance Matrix (Mandatory)
- [ ] **Policy:** Environment Freeze — submodule changes are code changes (permitted)
- [ ] **Policy:** No pip installs during agent loops

## Architecture / Interfaces

**Key Data Types:**
```
OrchConfig {
  prompts_dir: Path
  supervisor_prompt: str
  state_file: Path
  doc_whitelist: list[str]
  tracked_output_globs: list[str]
  findings_file: Path
  input_file: Path
  logs_dir: Path
  tmp_dir: Path
}
```

**Boundary Definitions:**
```
[Consumer Project]
    └── orchestration.yaml (config)
    └── scripts/orchestration/ (submodule)
            └── config.py (loader)
            └── supervisor.py (reads config)
            └── loop.py (reads config)
            └── ...
```

**Data Flow:**
1. Scripts start → `load_config()` searches upward for `orchestration.yaml`
2. Config merged with defaults → paths resolved relative to project root
3. Scripts operate using configured paths

## Context Priming (read before edits)
- Primary docs: `scripts/orchestration/README.md`
- Files to modify: `supervisor.py`, `loop.py`, `check_input.py`, `plan_lint.py`
- New file: `config.py`

---

## Phase A — Decouple

### Objectives
- Remove all hardcoded project-specific and user-specific paths
- Implement config loader with sensible defaults
- Fix self-references to use `Path(__file__)`

### Checklist
- [x] A0: **Nucleus / Test-first gate:** Run existing orchestration locally, capture working baseline
- [x] A1: Create `config.py` with `load_config()`, `find_config()`, `stream_to_text_script()`
- [x] A2: Refactor `supervisor.py` — replace hardcoded paths with config lookups
  - `/home/ollie/.claude/...` → `claude_cli_default()` (searches repo-local, home-local, PATH)
  - `docs/fix_plan.md` etc. → `cfg.doc_whitelist`
  - `prompts/supervisor.md` → `cfg.prompts_dir / cfg.supervisor_prompt`
  - `scripts/orchestration/claude_stream_to_text.py` → `stream_to_text_script()`
- [x] A3: Refactor `loop.py` — same pattern as A2
- [x] A4: Refactor `check_input.py` — use `cfg.findings_file`, `cfg.input_file`
- [x] A5: Refactor `plan_lint.py` — use `cfg.input_file`
- [x] A6: Create `orchestration.yaml` for DBEX with current paths (no behavior change)
- [x] A7: Test orchestration still works with config file present (imports + syntax verified)

### Dependency Analysis
- **Touched Modules:** `supervisor.py`, `loop.py`, `check_input.py`, `plan_lint.py`
- **Circular Import Risks:** None — `config.py` has no internal imports
- **State Migration:** None — config is read-only at startup

### Notes & Risks
- Risk: YAML parsing adds `pyyaml` dependency
  - Mitigation: Fall back to stdlib `json` or keep yaml optional with graceful degradation
- Risk: Config file not found silently uses defaults, may surprise users
  - Mitigation: Log warning when no config found and using defaults

---

## Phase B — Extract

### Objectives
- Create standalone git repository for orchestration
- Convert in-tree directory to submodule
- Establish versioning strategy

### Checklist
- [ ] B1: Create `~/repos/orchestration` (or preferred location)
- [ ] B2: Copy decoupled scripts to new repo, init git
- [ ] B3: Add minimal `README.md` documenting config schema
- [ ] B4: Push to remote (GitHub/GitLab)
- [ ] B5: In DBEX: `git rm -r scripts/orchestration` (preserve history)
- [ ] B6: In DBEX: `git submodule add <remote-url> scripts/orchestration`
- [ ] B7: Commit and verify `git clone --recurse-submodules` works
- [ ] B8: Update DBEX `CLAUDE.md` to note submodule

### Notes & Risks
- Risk: Forgetting `--recurse-submodules` on clone leaves empty directory
  - Mitigation: Add pre-commit hook or CI check; document prominently
- Risk: Submodule pointer drift causes "dirty" status
  - Mitigation: Existing `_submodule_scrub()` in supervisor.py handles this

---

## Phase C — Validate

### Objectives
- Prove multi-project reuse works
- Document conventions for new consumers
- Establish update workflow

### Checklist
- [ ] C1: Add submodule to second project (e.g., another DBEX-like repo or test repo)
- [ ] C2: Create `orchestration.yaml` for second project with different paths
- [ ] C3: Run galph/ralph loop in second project, verify success
- [ ] C4: Test submodule update workflow:
  - Make change in orchestration repo
  - Pull update in consumer: `git submodule update --remote`
  - Verify both projects still work
- [ ] C5: Write comprehensive README covering:
  - Installation (submodule add)
  - Configuration schema
  - CLI flags that override config
  - Troubleshooting (common issues)
- [ ] C6: Optional: Add `orchestration.schema.json` for IDE autocomplete

### Validation & Artifacts
- Tests: Manual loop execution in both projects
- Artifacts: `plans/active/ORCH-EXTRACT-001/reports/` — loop logs from both projects

### Notes & Risks
- Risk: Config schema evolves, old consumers break
  - Mitigation: Semantic versioning on orchestration repo; document breaking changes
- Risk: Different projects need conflicting features
  - Mitigation: Use CLI flags for project-specific overrides; keep config minimal

---

## Artifacts Index
- Reports root: `plans/active/ORCH-EXTRACT-001/reports/`
- Config schema: `orchestration.yaml` (created)
- Standalone repo: TBD (e.g., `github.com/ollie/orchestration`)
