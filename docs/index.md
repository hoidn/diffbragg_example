# DBEX Documentation Hub

This index provides a concise map of the project documentation and key code pointers so you can quickly find what you need.

Status note
- The Spec DB shards and CLI flags (e.g., `--backend`, `--device`, `--adu-per-photon`, `--nabc`) target the planned PyTorch backend (`nanobrag_torch`). They are not yet implemented in the current CLI. Use `python -m dbex.refine_one` for now (see `dbex/refine_one.py`).

## Quick Start

### [README](../README.md) — Project Overview
Description: High‑level intro with environment setup, data acquisition, and how to run the legacy DiffBragg workflow.  
Keywords: setup, overview, environment, quickstart  
Use this when: First time setting up DBEX and running the provided single‑image optimization benchmark.

### Current CLI: `dbex.refine_one` (legacy)
Description: Main entry point for the DiffBragg workflow; parses `.expt/.refl/.mtz` paths and writes HDF5 ROI outputs.  
Keywords: CLI, DiffBragg, refinement, HDF5  
Use this when: Running the current pipeline end‑to‑end. See code: `dbex/refine_one.py`.

### ROI Viewer: `dbex.look`
Description: Interactive viewer for ROI triptychs (Data | Model), paginated with keyboard navigation.  
Keywords: visualization, ROI, HDF5, inspection  
Use this when: Inspecting fit quality and ROI scores from a refinement run. See code: `dbex/look.py`.

## Operational Ledgers

### [Knowledge Base Ledger](findings.md)
Description: Persistent record of architectural findings, runtime guardrails, and parity lessons for the torch integration.  
Keywords: findings, guardrails, lessons  
Use this when: Planning a loop or checking prior art before touching simulator/bridge code.

### [Fix Plan Ledger](fix_plan.md)
Description: Master task list for the torch backend rollout, including dependencies, exit criteria, and Attempts History.  
Keywords: fix-plan, ledger, attempts-history  
Use this when: Selecting the next loop focus and recording artifacts.

## Specifications (Spec DB)

### [Spec Index](spec-db.md)
Description: Canonical list of Spec DB shards (core, runtime, workflow, interfaces, conformance, tracing).  
Keywords: spec, index, contract  
Use this when: Locating the authoritative spec shard for a topic.

### [Core](spec-db-core.md)
Description: Physics/geometry units, data contracts (arrays, masks, ROI semantics) and simulator expectations.  
Keywords: units, geometry, data‑contracts, masks  
Use this when: Implementing or validating core simulator/array semantics.

### [Runtime](spec-db-runtime.md)
Description: PyTorch execution guardrails (vectorization, device/dtype neutrality, compile caching, determinism).  
Keywords: runtime, torch.compile, determinism  
Use this when: Building/refactoring the torch backend or debugging performance.

### [Workflow](spec-db-workflow.md)
Description: End‑to‑end pipeline from ingestion → background → masking → calibration → simulation → loss → staging.  
Keywords: pipeline, masking, calibration, staging  
Use this when: Mapping data flow or aligning staging across implementations.

### [Interfaces](spec-db-interfaces.md)
Description: CLI/API surface and precedence rules for the planned torch backend (flags like `--backend`, `--device`).  
Keywords: CLI, API, precedence  
Use this when: Designing or consuming the torch CLI/API. For now, use `dbex.refine_one`.

### [Conformance](spec-db-conformance.md)
Description: Acceptance tests (DB‑AT‑XXX) and conformance profiles; placeholders until torch backend lands.  
Keywords: acceptance‑tests, parity, gradcheck  
Use this when: Planning validation and parity coverage.

### [Tracing](spec-db-tracing.md)
Description: Tracing/instrumentation requirements and parity workflow for first‑divergence debugging.  
Keywords: tracing, diagnostics, parity  
Use this when: Investigating physics discrepancies or adding trace hooks.

## APIs and Crosswalks

### [Configuration Crosswalk](config_crosswalk.md)
Description: Mapping between DIALS/dxtbx/simtbx inputs, DiffBragg concepts, and `nanobrag_torch` configs/params.  
Keywords: mapping, detector, beam, crystal, masks  
Use this when: Bridging Experiment metadata to simulator configs.

### [DIALS API](dials_api.md)
Description: Reflection table schema, bbox conventions, and mask formats relevant to ROI/background.  
Keywords: reflections, bbox, masks  
Use this when: Interpreting `.refl` columns and slicing ROIs correctly.

### [dxtbx API](dxtbx_api.md)
Description: Detector/Beam/Crystal/Scan fields used to populate simulator configs.  
Keywords: detector, beam, crystal, geometry  
Use this when: Extracting geometry and wavelength/polarization metadata.

### [simtbx/diffBragg Utilities](simtbx_api.md)
Description: Image loading, ROI/background helpers, and MTZ handling used by `dbex`.  
Keywords: image_data_from_expt, background, MTZ  
Use this when: Running or modifying ROI/background estimation.

### [nanobrag_torch API](nanobrag_api.md)
Description: Integration‑oriented guide for Detector/Crystal/Beam configs, simulator runtime, and HKL IO.  
Keywords: torch, simulator, DetectorConfig, CrystalConfig  
Use this when: Implementing the torch backend (planned).

## Architecture and Plans

### [Architecture Overview](architecture.md)
Description: System context, ADRs, data flow, and proposed module layout for the torch integration.  
Keywords: ADRs, data‑flow, modules  
Use this when: Understanding the planned design and integration boundaries.

### [Integration Plan](../plans/nanobrag_integration_plan.md)
Description: Phase‑by‑phase plan to replace the optimizer with `nanobrag_torch`, deliverables, and validation.  
Keywords: plan, milestones, deliverables  
Use this when: Executing integration work or reviewing scope/timeline.

## Testing & Validation

### [Testing Guide](TESTING_GUIDE.md)
Description: Canonical environment flags, smoke/acceptance selectors, and artifact policy for pytest runs.  
Keywords: testing, pytest, selectors  
Use this when: Running or authoring tests for parity, ingestion, or runtime guardrails.

### [Test Suite Index](development/TEST_SUITE_INDEX.md)
Description: Status table for DB-AT selectors and runtime regression tests.  
Keywords: test-index, parity, runtime  
Use this when: Checking which selectors exist and which remain to be authored.

## PyTorch Development

### [PyTorch Architecture Design](architecture/pytorch_design.md)
Description: Detailed design notes for vectorized tricubic interpolation, detector absorption, and source weighting in `nanobrag_torch`.  
Keywords: architecture, vectorization, tricubic, absorption  
Use this when: Implementing or reviewing PyTorch simulator internals for DBEX integration.

### [C-CLI to PyTorch Configuration Map](development/c_to_pytorch_config_map.md)
Description: Parameter-by-parameter mapping between legacy DiffBragg CLI flags and the PyTorch configuration objects.  
Keywords: configuration, parity, beam-center, pivot  
Use this when: Ensuring configuration parity before running C↔PyTorch comparisons or authoring tests.

### [PyTorch Testing Strategy](development/testing_strategy.md)
Description: Layered testing philosophy, golden data requirements, and canonical commands for PyTorch parity and gradcheck suites.  
Keywords: testing-strategy, gradcheck, parity  
Use this when: Planning or updating PyTorch tests, harnesses, and golden suites.

### [PyTorch Runtime Checklist](pytorch_runtime_checklist.md)
Description: Quick reference for vectorization, device/dtype neutrality, `torch.compile` hygiene, and source equal-weight rules.  
Keywords: runtime, torch.compile, vectorization  
Use this when: Auditing or implementing PyTorch simulator changes.

## Reports and Correspondence

### [Maintainer Responses](../reports/maintainer_responses.md)
Description: Consolidated answers from maintainers clarifying APIs and runtime behavior.  
Keywords: clarifications, API, performance  
Use this when: Confirming assumptions or resolving ambiguities.

### Requests to Upstreams
- [nanobrag API request](../reports/nanobrag_api_request.md) — Questions and integration needs.  
- [dxtbx mapping request](../reports/email_request_dxtbx_detector_beam_mapping.md) — Detector/beam mapping details.  
- [simtbx background/API request](../reports/email_request_simtbx_background_and_api.md) — ROI/background/MTZ interface.  
- [DIALS reflections/masks request](../reports/email_request_dials_reflections_and_masks.md) — Reflection schema, bbox, mask formats.  
Use this when: Looking for provenance of decisions or external confirmations.

## Core Modules (Code Pointers)

### `dbex/data_load.py`
Description: Loads MTZ (|F|), DIALS Experiment and Reflections; computes background and ROI metadata via simtbx.  
Keywords: ingestion, background, ROI  
Use this when: You need in‑memory data + ROI/bbox for refinement.

### `dbex/run_diffbragg.py`
Description: Legacy DiffBragg refinement pipeline (xtal → Fhkl → detector) with final forward model image.  
Keywords: DiffBragg, refinement, forward‑model  
Use this when: Running or inspecting the legacy refinement loop.

### `dbex/refine_one.py`
Description: CLI driver that invokes DiffBragg pipeline, scores ROIs, and writes HDF5 outputs.  
Keywords: CLI, HDF5, ROI‑scores  
Use this when: Executing the current end‑to‑end benchmark.

### `dbex/look.py`
Description: Interactive Matplotlib viewer for HDF5 ROI triptychs.  
Keywords: viewer, visualization, ROI  
Use this when: Visualizing model vs data per ROI.

## Agent and External Tools

### [CLAUDE Instructions](../CLAUDE.md)
Description: Agent guidance and external tool source paths (DIALS, dxtbx, simtbx) within this workspace.  
Keywords: agent, external-paths, guidance  
Use this when: Working as an AI agent or locating external tool trees.

### [Agent Workflow Rules](../AGENTS.md)
Description: Repository-scoped conventions for coding style, pytest usage, artifact routing, and ledger expectations (overrides apply per subtree).  
Keywords: agent-workflow, conventions, ledger  
Use this when: You need authoritative agent rules; remember deeper AGENTS.md files override shallower ones within their directory tree.

## Planning Templates

### [Implementation Plan Template](../plans/templates/implementation_plan.md)
Description: Phased plan template for multi-loop initiatives; includes checklist IDs to reference in `input.md`.  
Keywords: planning, phases, checklist  
Use this when: Creating or updating a persistent plan under `plans/active/<initiative-id>/implementation.md`.

### [Phase Checklist Template](../plans/templates/phase_checklist.md)
Description: Per-phase checklist structure with objectives, validation, and artifacts sections.  
Keywords: planning, phase, validation  
Use this when: Managing detailed tasks for a single phase and linking them into the implementation plan.

---

Last updated: 2025‑10‑28
