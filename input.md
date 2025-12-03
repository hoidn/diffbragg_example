# Input for Ralph — ARCH-LAZY-IMPORTS-001 Phase C Process-Noise Sweep

## Summary
Clean up historical ticket references and process noise from docstrings/comments, replacing them with normative spec/finding citations.

## Mode
Docs

## InitiativeType
architecture

## Focus
ARCH-LAZY-IMPORTS-001 — Lazy imports / process-noise hygiene

## Branch
integration

## Mapped tests
none — documentation-only loop

## Artifacts
`plans/active/ARCH-LAZY-IMPORTS-001/reports/2025-12-05T000500Z/`

## Do Now

**Scope**: Process-noise cleanup across geometry/physics/Stage modules now that eager-import work (Phase B.3) is complete.

**Tasks**:
1. **Audit docstrings and comments** in the following modules for historical ticket references (e.g., "Issue #123", "JIRA-456", "TODO from 2024-06 sprint"):
   - `dbex/geometry/crystallography.py`
   - `dbex/physics/forward.py`
   - `dbex/physics/loss.py`
   - `dbex/refinement/stage_a_utils.py`
   - `dbex/refinement/hkl_utils.py`
   - `dbex/refinement/stage_a.py`
   - `dbex/refinement/stage_b.py`
   - `dbex/refinement/stage_c.py`

2. **Replace ticket/process references** with normative spec/finding citations where applicable:
   - Example: `# TODO: fix baseline bug (issue #789)` → `# Baseline logic per docs/spec-db-core.md §Calibration Metadata`
   - Example: `# Workaround for JIRA-456 matrix singularity` → `# Matrix derivation per GEOMETRY-001 finding`
   - Example: `# From 2024-11 refactor meeting notes` → Remove or replace with spec citation

3. **Document cleanup summary**:
   - Count of references replaced per module
   - List any references that cannot be mapped to specs/findings (flag for future triage)
   - Save audit results to `plans/active/ARCH-LAZY-IMPORTS-001/reports/2025-12-05T000500Z/process_noise_audit.md`

4. **Validation**: Run `rg -n "TODO|FIXME|JIRA|Issue #|ticket" dbex/{geometry,physics,refinement}/*.py` after cleanup to verify no low-value process references remain

**Expected Metrics**:
- 8 modules scanned
- ~10-30 docstring/comment updates (estimate based on typical process noise density)
- Net ~0 LOC (comment-only changes)

## How-To Map

**Audit**:
```bash
cd /home/ollie/Documents/diffbragg_example
rg -n "TODO|FIXME|JIRA|Issue #|ticket|meeting notes|sprint" \
  dbex/geometry/crystallography.py \
  dbex/physics/forward.py \
  dbex/physics/loss.py \
  dbex/refinement/stage_a_utils.py \
  dbex/refinement/hkl_utils.py \
  dbex/refinement/stage_a.py \
  dbex/refinement/stage_b.py \
  dbex/refinement/stage_c.py \
  > plans/active/ARCH-LAZY-IMPORTS-001/reports/2025-12-05T000500Z/process_noise_raw.txt
```

**Cleanup Strategy**:
- For each hit, inspect context and determine:
  1. Can it be replaced with a spec/finding citation? (do so)
  2. Is it a valid TODO describing missing spec coverage? (keep, but reword to reference the gap)
  3. Is it low-value process noise? (delete)

**Post-Cleanup Verification**:
```bash
rg -n "TODO|FIXME|JIRA|Issue #|ticket" dbex/{geometry,physics,refinement}/*.py \
  > plans/active/ARCH-LAZY-IMPORTS-001/reports/2025-12-05T000500Z/remaining_noise.txt
```

## Pitfalls To Avoid

1. **Do NOT remove valid spec-gap TODOs**: If a TODO describes missing normative behavior (e.g., "TODO: implement per-ASU variance floor per spec §67 when available"), keep it but reword to cite the spec section explicitly.

2. **Do NOT change substantive logic**: This is a documentation-only loop; only update docstrings/comments, not code.

3. **Do NOT invent spec citations**: If a comment refers to behavior not documented in specs/findings, flag it in `process_noise_audit.md` for future triage instead of inventing a citation.

4. **Preserve attribution**: If a comment includes valuable context about why a workaround exists (e.g., "Detector transform convention differs from DIALS; see GEOMETRY-003"), keep the context but upgrade the citation to the finding.

5. **Initiative type constraint**: architecture initiatives change structure/documentation, not external behavior. Ensure no semantic changes to docstrings that describe user-facing API contracts.

## If Blocked

If you encounter:
- **Uncertainty about spec mapping**: Flag the comment in `process_noise_audit.md` with a note "Cannot map to spec; recommend future triage" instead of deleting or changing it.
- **Substantive logic questions**: Do not attempt to resolve them; flag for future bugfix/spec-change initiative.

Log the block reason in `plans/active/ARCH-LAZY-IMPORTS-001/reports/2025-12-05T000500Z/blocked_notes.md` and return control to supervisor.

## Findings Applied (Mandatory)

- ARCH-ENGINE-002: Lazy-import staging rules and eager-import precedent for module-scope dependencies
- ARCH-LAZY-IMPORTS-001 Phase B.3 completion: Stage A/B/C/physics/geometry modules now have eager imports; process noise is the remaining hygiene work

No additional findings directly constrain docstring cleanup, but general principle: prefer normative spec citations over historical process artifacts.

## Pointers

- **Spec Index**: `docs/spec-db.md`
- **Spec Core**: `docs/spec-db-core.md` (geometry, variance, calibration)
- **Spec Runtime**: `docs/spec-db-runtime.md` (torch guardrails)
- **Spec Workflow**: `docs/spec-db-workflow.md` (pipeline, telemetry)
- **Findings**: `docs/findings.md` (GEOMETRY-001/003, PHYSICS-LOSS-001/003, ARCH-ENGINE-002, etc.)
- **Initiative Plan**: `plans/active/ARCH-LAZY-IMPORTS-001/implementation.md` (Phase C checklist lines 95-100)
- **Fix Plan Row**: `docs/fix_plan.md` lines 224-245

## Next Up (optional)

If you complete the process-noise sweep faster than expected:
1. Run `wc -c docs/fix_plan.md` to check ledger size
2. If >70 kB, recommend archiving old attempts to `docs/fix_plan_archive.md` in next loop

## Doc Sync Plan (Conditional)

Not applicable — no new tests authored this loop.

## Normative Math/Physics

Not applicable — this is a documentation cleanup loop with no math/physics changes.
