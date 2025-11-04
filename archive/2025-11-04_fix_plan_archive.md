# DBEX Fix Plan — Archived Initiatives (2025-11-04)

This archive compacts the main fix plan by moving fully completed initiatives out of `docs/fix_plan.md`. Each entry provides a short summary and cross‑references to artifacts and specs. For full Attempts History details before this housekeeping, consult repository history prior to 2025-11-04.

Archive created: 2025-11-04
Origin: docs/fix_plan.md (housekeeping >50 KB rule)

## Archived Items (Status: done)

### [ORCH-ROBUST-001] Supervisor robustness to submodule pointer drift
- Scope: Orchestration hardening around submodule gitlinks and hygiene.
- Artifacts: plans/active/HARDEN-SUBMODULE-ROBUSTNESS/reports/<timestamp>/
- Notes: Implemented robust gitlink detection and single‑retry scrub.

### [NANOBRAG-GOLDEN-001] Replace fallback DB-AT-001 golden dataset
- Scope: Canonical nanoBragg2 dataset + manifest/metadata; parity harness alignment.
- Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/<timestamp>/
- Notes: Achieved strong DB_AT_001 parity; added checksum guard in tests.

### [NANOBRAG-BACKEND-002] Replace CLI torch backend stub with nanobrag_torch simulator
- Scope: Promote real `nanobrag_torch` config/models; integrate Simulator per panel; apply √(spot_scale_override).
- Artifacts: plans/active/NANOBRAG-BACKEND-002/reports/<timestamp>/
- Notes: Backend parity validated against canonical fixtures.

### [PARITY-HARNESS-002] Implement DB-AT parity harness tests
- Scope: Parity harness utilities and selectors; artifact logging.
- Artifacts: plans/active/PARITY-HARNESS-002/reports/<timestamp>/

### [TORCH-BRIDGE-001] Bridge DataLoad to `nanobrag_torch`
- Scope: Detector/Beam/Crystal config hydration; tensor/mask preparation.
- Artifacts: plans/active/TORCH-BRIDGE-001/reports/<timestamp>/

### [TORCH-RUNTIME-002] Author torch runtime checklist + testing harness seed
- Scope: Runtime guards (compile, determinism, device/dtype neutrality) and test seeds.
- Artifacts: plans/active/TORCH-RUNTIME-002/reports/<timestamp>/

### [TORCH-CLI-003] Wire torch backend flag into CLI
- Scope: `--backend {diffbragg,nanobrag}` and diagnostics plumbing.
- Artifacts: plans/active/TORCH-CLI-003/reports/<timestamp>/

### [DOC-HARDEN-001] Harden key docs with prescriptive guardrails
- Scope: Spec/arch/testing docs clarity and guardrails.
- Artifacts: plans/active/DOC-HARDEN-001/reports/<timestamp>/

### [FORWARD-EQUIV-001] Forward equivalence smoke validation
- Scope: DiffBragg vs torch forward comparison (no refinement), ROI metrics.
- Artifacts: plans/active/FORWARD-EQUIV-001/reports/<timestamp>/

### [FORWARD-EQUIV-002] Promote forward equivalence smoke to canonical parity
- Scope: Canonicalization of forward‑equivalence thresholds and artifacts.
- Artifacts: plans/active/FORWARD-EQUIV-002/reports/<timestamp>/

### [DB-AT-010] Gradient correctness guard
- Scope: Masked loss + gradcheck across key parameters; environment guards.
- Artifacts: plans/active/DB-AT-010/reports/<timestamp>/

### [RUNTIME-VEC-001] Source weighting runtime guard
- Scope: Equal‑weight rule validation; vectorization runtime conformance.
- Artifacts: plans/active/RUNTIME-VEC-001/reports/<timestamp>/

### [DB-AT-002] Determinism selector scaffold
- Scope: Same‑seed bitwise; diff‑seed independence; CPU constraints.
- Artifacts: plans/active/DB-AT-002/reports/<timestamp>/

### [DB-AT-020] Reflection ingestion sanity
- Scope: ROI bbox semantics and panel alignment checks.
- Artifacts: plans/active/DB-AT-020/reports/<timestamp>/

### [DB-AT-021] Mask semantics guard
- Scope: Trusted mask polarity/shape and simulator/loss mask alignment.
- Artifacts: plans/active/DB-AT-021/reports/<timestamp>/

### [DB-AT-022] Background sentinel guard
- Scope: −1 sentinel handling around ROIs; guard enforcement.
- Artifacts: plans/active/DB-AT-022/reports/<timestamp>/

### [DB-AT-023] Calibration policy guard
- Scope: ADU↔photons policy and global scale expectations.
- Artifacts: plans/active/DB-AT-023/reports/<timestamp>/

### [DB-AT-024] Mapping consistency guard
- Scope: Zero‑iteration forward mapping metrics and thresholds.
- Artifacts: plans/active/DB-AT-024/reports/<timestamp>/

### [FINDINGS-LEDGER-002] Extend knowledge base with torch experiment lessons
- Scope: Durable findings updates with path:line anchors.
- Artifacts: plans/active/FINDINGS-LEDGER-002/reports/<timestamp>/

### [DOC-RUNTIME-004] Restore `docs/pytorch_runtime_checklist.md`
- Scope: Runtime checklist restoration and alignment with tests.
- Artifacts: plans/active/DOC-RUNTIME-004/reports/<timestamp>/

## Notes
- Cross‑references: specs in docs/spec-db-*.md, architecture guidance in docs/architecture.md and plans/nanobrag_integration_plan.md.
- Artifacts: Each initiative’s reports directory contains logs, metrics, and pytest outputs referenced by the ledger at completion time.
