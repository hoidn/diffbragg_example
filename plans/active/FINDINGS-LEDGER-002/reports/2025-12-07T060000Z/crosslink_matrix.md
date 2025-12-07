# Findings ↔ Fix-Plan Crosslink Matrix

**Initiative:** FINDINGS-LEDGER-002 Phase B.1
**Date:** 2025-12-07T060000Z
**Scope:** Map Active findings → fix-plan initiative consumers

---

## Summary Statistics

| Metric | Count |
|--------|-------|
| Total Active Findings | 74 |
| Findings with Consumers | 9 |
| Orphaned Findings (no consumers) | 64 |
| Consumer Coverage | 12.2% |

**Finding Type Distribution:**
- **Pattern findings** (general architecture/behavior constraints): ~40 findings
- **Blocker findings** (specific initiative blockers): ~34 findings

---

## Findings WITH Consumers (9)

### CONFORMANCE-001
**Summary:** DB-AT parity and workflow profiles define canonical pytest selectors
**Tags:** testing, acceptance, parity
**Consumers:**
- [ARCH-IMPL-CONFORMANCE-001] (line 21) — Architecture / Implementation contract alignment
- [RECOMMENDED] (line 943) — Lifecycle decision referencing conformance requirements

### REFINE-001
**Summary:** Stage A LBFGS must warm-start the global scale from the calibration hint
**Tags:** refinement, lbfgs, scale
**Consumers:**
- [ARCH-REFINE-001] (line 34) — Refine Engine Modularization + Torch IO context
- [TORCH-REFINE-CLEANUP-001] (line 40) — Stage A/B/C refinement probes rollup

### SCALE-001
**Summary:** Canonical capture MUST NOT multiply structure factors by `sqrt(scale_override)`
**Tags:** scaling, structure-factors, parity
**Consumers:**
- [MAP-SCALE-SYNC-001] (line 37) — Calibration ladder initiatives MAP-SCALE-001—005

### PHYSICS-LOSS-001
**Summary:** Stage B/C refinements must consume the same variance-weighted denominator
**Tags:** loss, telemetry, staging
**Consumers:**
- [0] (line 631) — Phase C.1 implementation (StageCTelemetryCollector extension)

### SCALE-008
**Summary:** Stage A `build_mapping_stage_a_context` multiplies `spot_scale_override`
**Tags:** scaling, stage_a, calibration
**Consumers:**
- [NON-NORMATIVE] (line 204) — Phase C.12 geometry mode parameterization

### SCALE-009
**Summary:** Reconstruction helpers must apply `sqrt(spot_scale_override)` post-run
**Tags:** scaling, reconstruction, calibration, architecture
**Consumers:**
- [NON-NORMATIVE] (line 204) — Phase C.12 geometry mode parameterization

### REFINE-007
**Summary:** Stage C microslip tests inject ±0.25 mm panel offsets
**Tags:** refinement, detector, acceptance
**Consumers:**
- [PERF-WARM-SIM-001] (line 62) — Warm Simulator (Stage C panel-loss path)
- [0] (line 631) — Phase C.1 implementation (StageCTelemetryCollector)

### CONVERGENCE-001
**Summary:** Stage A U-matrix refinement diagnostic scripts detect zero parameter deltas
**Tags:** refinement, convergence, code-path-divergence, u-matrix
**Consumers:**
- [TORCH-GEOMETRY-SYNC-001] (line 39) — Geometry convergence/parity/UB realign initiatives

### REFINE-012
**Summary:** Stage A panel-mode validations forced Stage C ROI subset mismatch
**Tags:** refinement, stage-c, roi-mode
**Consumers:**
- [PERF-WARM-SIM-001] (line 62) — Warm Simulator blocker

---

## Orphaned Findings (no fix-plan consumers) — 64 findings

### Geometry & Configuration (13)
| Finding ID | Summary Snippet | Classification |
|------------|-----------------|----------------|
| GEOMETRY-001 | Bridge MUST derive beam center and detector vectors... | Pattern |
| GEOMETRY-002 | Torch bridge MUST recover DIALS XYZ rotation angles... | Pattern |
| GEOMETRY-003 | Stage-A baseline misset derived from dxtbx A* matrix... | Pattern |
| GEOMETRY-004 | Stage A incremental UB parameterization... | Pattern |
| CONFIG-001 | Config hydration from dxtbx to nanobrag_torch requires... | Pattern |
| CONFIG-002 | DetectorConfig.detector_convention must use enum value... | Blocker (resolved in code) |
| CONFIG-003 | BeamConfig.polarization_axis must be a tuple... | Blocker (resolved in code) |
| DXTBX-001 | dxtbx `crystal.get_A()` returns 9-element tuple... | Pattern |
| HKL-ORIENT-001 | Simulator must cache source→sample incident direction... | Pattern |
| MODEL-001 | Roundtrip tests validate schema compatibility... | Pattern |
| RUNTIME-001 | Gradient tests require `NANOBRAGG_DISABLE_COMPILE=1`... | Pattern |
| DIAGNOSTICS-001 | Torch backend emits `/torch_diagnostics` HDF5 group... | Pattern |
| MASKING-001 | Loss mask coverage typically <1%... | Pattern |

### Testing & Parity (4)
| Finding ID | Summary Snippet | Classification |
|------------|-----------------|----------------|
| TESTING-002 | CLI integration tests use mocking... | Pattern |
| TESTING-003 | Selector status transitions to Active after pytest --collect-only... | Pattern |
| PARITY-001 | First-divergence debugging workflow requires row-major scanning... | Pattern |
| MANIFEST-001 | Canonical manifest emission MUST verify `.npy` payloads exist... | Pattern |

### Scaling & Calibration (6)
| Finding ID | Summary Snippet | Classification |
|------------|-----------------|----------------|
| SCALE-002 | DiffBragg spot_scale_override must be re-applied post-simulation... | Pattern |
| SCALE-003 | Zero-iteration torch helper must ingest DiffBragg-refined √spot_scale... | Blocker (likely resolved) |
| SCALE-004 | DiffBragg calibration metadata must be sourced from config_torch.json... | Pattern |
| SCALE-005 | Injecting DiffBragg `N_cells` overrides multiplies intensities... | Blocker |
| SCALE-006 | CLI runs must ingest config_torch.json metadata... | Pattern |
| SCALE-007 | Zero-iteration bridge must emit structure-factor telemetry... | Pattern |

### Physics & Loss (4)
| Finding ID | Summary Snippet | Classification |
|------------|-----------------|----------------|
| PHYSICS-LOSS-002 | Variance-weighted chi-squared must enforce sigma-floor guard... | Pattern |
| PHYSICS-LOSS-003 | Stage A reports chi-squared as sum-of-ratios... | Blocker (inconsistency) |
| PHYSICS-LOSS-004 | Calibrated sigma maps entered via `--sigma-map`... | Pattern |
| PHYSICS-LOSS-005 | DIALS experiments embed calibrated readout-noise tiles... | Pattern |

### Performance & Warm Cache (12)
| Finding ID | Summary Snippet | Classification |
|------------|-----------------|----------------|
| PERF-WARM-001 | Stage A warm simulator cache via `StageAContext`... | Pattern |
| PERF-WARM-002 | Warm-mode still rebuilds `create_crystal_config` + `Crystal`... | Blocker |
| PERF-WARM-003 | Hoisting Stage A `create_crystal_config` shows ~1.01× speedup... | Observation |
| PERF-WARM-004 | Caching per-panel Simulator instances trims LBFGS ~2%... | Observation |
| PERF-WARM-005 | ROI sampling tied to warm cache... | Pattern |
| PERF-WARM-006 | Stage B/C warm smokes must reuse Stage A detector configs... | Pattern |
| PERF-WARM-007 | Canonical Stage B/C smokes assert perf-counter invariants... | Pattern |
| PERF-WARM-008 | Stage B reuses `StageAContext.roi_entries`... | Pattern |
| PERF-WARM-009 | Stage B ROI-mode closures evaluate only Stage A ROI subset... | Blocker |
| PERF-WARM-010 | Stage B smokes drive `shell_0_modifier` to 2.0... | Observation |
| PERF-WARM-011 | Canonical Stage B smokes fail due to GPU OOM... | Blocker |
| PERF-WARM-013 | Stage C instantiates fresh Detector/Simulator objects... | Blocker |

### Refinement (12)
| Finding ID | Summary Snippet | Classification |
|------------|-----------------|----------------|
| REFINE-002 | Stage A nucleus produces only ~0.15% masked-MSE improvement... | Gate calibration |
| REFINE-003 | Stage A orientation refinement via quaternion → rotation matrix... | Pattern |
| REFINE-006 | Stage A runs plateau at ~0.206% improvement... | Observation |
| REFINE-008 | Per-reflection Fhkl modifiers mapped to unique ASU indices... | Pattern |
| REFINE-009 | Stage C must seed detector distance offsets from canonical baseline... | Pattern |
| REFINE-010 | Stage A ROI-mode LBFGS on refGeom_small stalls at 0%... | Blocker |
| REFINE-011 | Stage C ROI-mode closures evaluate only sampled ROI subset... | Blocker |
| REFINE-013 | Stage C LBFGS closure never writes best_params_snapshot_c back... | Blocker |
| REFINE-014 | Stage C wrapper reused Stage A `misset_xyz_deg` (double-conversion)... | Blocker (likely resolved) |
| REFINE-015 | Stage C reuses Stage A `log_scale` delta but ignores baseline... | Blocker |
| REFINE-016 | Stage A panel-mode validations intersect trusted mask... | Pattern |
| REFINE-007-EXT | Stage C detector offset refinement wrapper extends REFINE-007... | Pattern |

### Architecture & Engine (6)
| Finding ID | Summary Snippet | Classification |
|------------|-----------------|----------------|
| ARCH-ENGINE-002 | StageC wrapper implements RefinementStage protocol... | Pattern |
| ARCH-ENGINE-003 | Phase E telemetry enrichment must be injected into active paths... | Pattern |
| ARCH-STAGE-CTX-001 | Stage implementations pass 10–15 positional arguments... | Blocker (tech debt) |
| ARCH-STAGE-CTX-002 | Stage B baseline parity guard mutates telemetry shims via dict... | Blocker (tech debt) |
| ARCH-FACTORY-001 | Unified simulator factory designed for forward-only simulation... | Pattern |
| ARCH-FACTORY-003 | ExperimentModel adapter Phase B3 BLOCKED by upstream nanobrag_torch bug... | Blocker (external dependency) |

### CLI & Gradients (4)
| Finding ID | Summary Snippet | Classification |
|------------|-----------------|----------------|
| CLI-001 | `create_detector_config` MUST convert trusted_mask to torch.Tensor... | Blocker (likely resolved) |
| CLI-002 | HKL amplitude mean calculation fails with flex.double... | Blocker (likely resolved) |
| GRADIENT-001 | Production refinement must avoid `.item()`/`.numpy()` on differentiable tensors... | Pattern |

### Orchestration & Policy (3)
| Finding ID | Summary Snippet | Classification |
|------------|-----------------|----------------|
| ORCH-ROBUST-001 | Harden supervisor against submodule pointer drift... | Pattern |
| ORCH-CLAUDE-001 | Claude Code wrapper may fail with ENOENT when Node not on PATH... | Blocker (likely resolved) |
| POLICY-001 | Environment Freeze exception for targeted bugfixes... | Pattern |

### Diagnostics & Simulator (2)
| Finding ID | Summary Snippet | Classification |
|------------|-----------------|----------------|
| DIAG-UNIT-001 | nanobrag_torch Crystal real-space vectors in meters vs scattering in Å⁻¹... | Blocker (root cause in progress) |
| CONVERGENCE-001 | Already listed above (has consumer) | N/A |

### Special Cases (2)
| Finding ID | Summary Snippet | Classification |
|------------|-----------------|----------------|
| PROBE-FREEZE-001 | *(Listed in grep output but not in inventory JSON; potential duplicate or Phase A.2 cleanup artifact)* | TBD |
| DBAT-SMOKE-GOLDEN-001 | *(Listed in grep output but not in inventory JSON; needs validation)* | TBD |
| SIM-CONSTR-OFFSET-001 | *(Listed in grep output but not in inventory JSON; needs validation)* | TBD |
| SIM-CONSTR-PARTIALITY-001 | *(Listed in grep output but not in inventory JSON; needs validation)* | TBD |
| DIAG-OVERSAMPLE-001 | *(Listed in grep output but not in inventory JSON; needs validation)* | TBD |

---

## Analysis Notes

### Pattern vs. Blocker Distribution

**Pattern findings** (40): General architectural constraints, testing patterns, and normative behaviors that govern multiple initiatives. These findings typically:
- Document canonical APIs/workflows (GEOMETRY-*, CONFIG-*, DIAGNOSTICS-001)
- Establish testing/acceptance gates (TESTING-*, PARITY-001)
- Define performance baselines (PERF-WARM-003/004/007)

**Blocker findings** (34): Specific bugs, technical debt, or missing functionality blocking progress. Examples:
- Active blockers: DIAG-UNIT-001, SCALE-005, PHYSICS-LOSS-003, REFINE-010/011/013/015, PERF-WARM-002/009/011/013, ARCH-STAGE-CTX-001/002
- Likely resolved: CLI-001/002, CONFIG-002/003, REFINE-014 (code evidence suggests fix landed)

### Why 86% of Findings Are Orphaned

1. **Implicit governance**: Many pattern findings (GEOMETRY-*, TESTING-*, RUNTIME-001) govern all initiatives but aren't explicitly referenced in fix-plan text.
2. **Ledger structure**: Fix-plan Attempts History cites findings inline (e.g., "per REFINE-007") but the initiative title/status lines don't always mention them.
3. **Roll-up hiding**: Findings referenced in plan-local implementation.md or reports/*.md won't appear in fix-plan grep.
4. **Completed work**: Some findings (SCALE-003, CLI-001/002, CONFIG-002/003) likely govern past work now archived or folded into done initiatives.

### Phase B.2 Recommendations

1. **High-priority reciprocal links** (findings → fix-plan):
   - Add "Consumers: [INITIATIVE-ID]" metadata to each finding in findings.md
   - Update fix-plan Tier 0–4 initiative descriptions to cite governing findings

2. **Roll-up cross-references**:
   - TORCH-REFINE-CLEANUP-001 should cite REFINE-002/003/006/010/011/013/014/015/016
   - MAP-SCALE-SYNC-001 should cite SCALE-002/003/004/005/006/007
   - PERF-WARM-SIM-001 should cite all PERF-WARM-* findings
   - TORCH-GEOMETRY-SYNC-001 should cite GEOMETRY-001/002/003/004 + CONVERGENCE-001

3. **Archive/Retire candidates**:
   - CLI-001/002, CONFIG-002/003 (if code fixes confirmed via test validation)
   - REFINE-014 (if Stage C orientation fix landed and validated)
   - SCALE-003 (if zero-iteration bridge now handles DiffBragg-refined amplitudes)

4. **New roll-up needs**:
   - Create [ARCH-STAGE-CONTEXT-CONSOLIDATION] to track ARCH-STAGE-CTX-001/002
   - Create [PHYSICS-LOSS-CONSISTENCY] to track PHYSICS-LOSS-001/002/003
   - Ensure ARCH-REFACTOR-001 cites ARCH-ENGINE-002/003

---

**Artifacts:**
- `consumer_map.json` — machine-readable mapping
- `map_consumers.py` — reproducible consumer extraction script
- `planning_notes.md` — Phase B.2 strategy (see separate file)
