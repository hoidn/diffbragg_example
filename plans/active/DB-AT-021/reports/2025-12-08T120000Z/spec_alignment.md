# DB-AT-021 Phase A2: Spec Alignment (Mask Polarity Semantics)

**Initiative**: DB-AT-021 (Mask Semantics Guard)
**Phase**: A2 — Spec Alignment Across 3 Docs
**Date**: 2025-12-08T12:00:00Z
**Objective**: Reconcile mask polarity semantics across spec-db-core.md, dials_api.md, and architecture.md

---

## Executive Summary

**Status**: ✅ ALIGNED — No conflicts detected

All three docs consistently define:
1. **Trusted mask polarity**: `True=trusted, False=untrusted` (DIALS convention)
2. **Loss mask construction**: `loss_mask = (background >= 0) ∧ trusted_mask`
3. **Canonical owner**: `dbex.refinement.inputs.prepare_refinement_inputs` constructs loss_mask
4. **Simulator mask**: Uses DIALS polarity directly (1=include); no inversion required for `nanobrag_torch` path

---

## Document Cross-Reference

### 1. spec-db-core.md (Normative)

**Section**: Lines 33-38, 123-125
**Key Rules**:

- **Mask format** (line 34):
  > DIALS trusted mask SHALL be a tuple of `flex.bool` per panel (True=trusted) shaped `(slow, fast)`.

- **Loss mask construction** (line 124):
  > The loss SHALL be computed only where `(background >= 0) ∧ trusted_mask`, and invalid pixels SHALL NOT contribute to the gradient.

- **Sigma constraint** (line 38):
  > `sigma_readout` values SHALL be strictly positive and finite on all trusted pixels. Zero or NaN sigma is non-compliant.

**Takeaway**: spec-db-core.md establishes normative polarity (True=trusted) and loss mask formula. Background sentinel is `-1` (line 124: `background >= 0` excludes sentinel pixels).

---

### 2. dials_api.md (DIALS External Interface)

**Section**: Lines 15-23
**Key Rules**:

- **Trusted mask format** (lines 16-18):
  > DIALS tooling can generate "trusted" masks per panel based on detector metadata (trusted range, gain, saturation).
  > DiffBragg expects a pickled DIALS mask file (tuple of flex.bool per panel) at `prm.roi.hotpixel_mask`.
  > During ROI gathering, this "trusted" mask is inverted to a "hot/bad" mask for rejection counts.

- **Shapes** (lines 22-23):
  > Masks and images are `[panel, slow, fast]`; ensure panel count and per-panel shapes match the detector.

**Takeaway**: dials_api.md documents DIALS external contract (True=trusted) and notes DiffBragg's internal inversion for legacy hot/bad pixel counting. This inversion is **NOT** applicable to `nanobrag_torch` path (confirmed via architecture.md below).

---

### 3. architecture.md (DBEX Implementation)

**Section**: Lines 52-62, 103-105
**Key Rules**:

- **Mask materialization** (lines 52-54):
  > Bridge → build per-panel DetectorConfig [...] materialize tensors:
  >   - `trusted_mask_tensor` from DIALS pickled mask (True=trusted),

- **Loss mask construction** (line 57):
  > Loss = masked MSE over `(bg_mask_tensor & trusted_mask_tensor)`.

- **ADR-07: Mask Polarity and Loss Mask** (lines 103-105):
  > Use DIALS trusted mask (True=include) directly in simulator; define loss mask as `(background >= 0) & trusted_mask`.

**Takeaway**: architecture.md confirms DIALS polarity is used directly for both simulator and loss mask (no inversion). `bg_mask_tensor = (background >= 0)` aligns with spec-db-core.md sentinel semantics.

---

## spec-db-conformance.md (Acceptance Criteria)

**Section**: Lines 58-61, 116, 194, 197
**DB-AT-021 Acceptance Test**:

- **Setup** (lines 59-60):
  > load DIALS trusted mask; convert to simulator mask; verify mask/loss application on sample ROIs.

- **Expectation** (line 60-61):
  > simulator zeros masked pixels post-compute; loss excludes masked/background-invalid pixels.

**Canonical Mapping Checklist** (line 116):
  > Trusted mask polarity True=trusted; background sentinel −1 outside ROIs; loss mask `(background >= 0) ∧ trusted_mask`.

**prepare_refinement_inputs Contract** (lines 194, 197):
  > - Construct `loss_mask = (background_image >= 0) ∧ trusted_mask`.
  > - Zero out `target` and `sigma_readout` where `loss_mask` is False.

**Takeaway**: spec-db-conformance.md codifies DB-AT-021 as enforcement for mask polarity alignment and loss mask construction per spec-db-core.md normative rules.

---

## Alignment Summary

| Aspect | spec-db-core.md | dials_api.md | architecture.md | spec-db-conformance.md |
|--------|----------------|--------------|-----------------|------------------------|
| **Trusted polarity** | True=trusted (line 34) | True=trusted (line 16) | True=trusted (line 54) | True=trusted (line 116) |
| **Loss mask formula** | `(background >= 0) ∧ trusted_mask` (line 124) | (not specified; external API doc) | `(bg_mask_tensor & trusted_mask_tensor)` (line 57) | `(background >= 0) ∧ trusted_mask` (line 116, 194) |
| **Background sentinel** | `-1` outside ROIs (line 124 implication) | (not specified) | `-1` sentinel (ADR-07, line 105) | `−1` outside ROIs (line 116) |
| **Inversion required?** | No (direct polarity) | No for `nanobrag_torch`; Yes for legacy DiffBragg hot/bad counts | No (direct polarity, line 61) | No (direct polarity) |
| **Canonical owner** | (not specified; implementation detail) | (not specified) | `prepare_refinement_inputs` (line 57 context) | `prepare_refinement_inputs` (line 192-197) |

---

## ARCH-CONTRACT-MASKING-001 (Canonical Owner Documentation)

**Owner module/API**: `dbex.refinement.inputs.prepare_refinement_inputs`

**Contract**:
1. **Input**: `trusted_mask` (DIALS polarity: True=trusted), `background_image` (with `-1` sentinel outside ROIs)
2. **Output**: `loss_mask = (background_image >= 0) ∧ trusted_mask`
3. **Side effects**: Zero out `target` and `sigma_readout` where `loss_mask` is False
4. **Invariant**: Loss mask construction MUST follow spec-db-core.md:124 normative formula

**Forbidden duplicates**:
- Alternative `loss_mask` construction logic in:
  - Stage A/B/C refinement helpers
  - Test harness (except for test fixtures validating `prepare_refinement_inputs` itself)
  - Plan-local diagnostic scripts

**Enforcement**: DB-AT-021 Phase B will author `tests/dbex/test_mask_semantics.py::TestDB_AT_021_MaskSemantics` to validate:
1. `prepare_refinement_inputs` constructs loss_mask per normative formula
2. No duplicates exist in production paths
3. Simulator receives trusted_mask with correct polarity (True=trusted)

---

## Conflict Analysis

**No conflicts detected**. All four docs (spec-db-core, dials_api, architecture, spec-db-conformance) agree on:
- Polarity: True=trusted
- Loss mask: `(background >= 0) ∧ trusted_mask`
- No inversion for `nanobrag_torch` simulator path

**Note on dials_api.md inversion remark** (line 19):
> During ROI gathering, this "trusted" mask is inverted to a "hot/bad" mask for rejection counts.

This refers to legacy DiffBragg internal bookkeeping (hot/bad pixel counts for telemetry), NOT the `nanobrag_torch` forward/loss paths. The inversion is:
- **Scope**: Diagnostic rejection counts only
- **Not applicable**: Simulator mask (`DetectorConfig.mask_array`), loss mask construction, gradient paths

---

## Recommendations for Phase B

1. **Test polarity**:
   - Load `747_mask.pkl` via `DataLoad`
   - Assert `trusted_mask.dtype == bool`
   - Verify sample trusted pixel (True) and untrusted pixel (False)
   - Confirm no polarity inversion in `prepare_refinement_inputs`

2. **Test loss_mask construction**:
   - Mock or fixture: `background_image` with sentinel `-1` in some regions
   - Call `prepare_refinement_inputs`
   - Assert `loss_mask[i,j] == True` where `(background[i,j] >= 0) and trusted_mask[i,j]`
   - Assert `loss_mask[i,j] == False` where `(background[i,j] == -1) or not trusted_mask[i,j]`

3. **Test simulator mask**:
   - Extract `DetectorConfig.mask_array` (if accessible via bridge)
   - Verify 1=include (trusted), 0=exclude (untrusted)
   - Confirm no polarity flip vs DIALS input

4. **Conformance check**:
   - Search for duplicate loss_mask construction logic
   - If found, flag as ARCH-CONTRACT-MASKING-001 violation
   - Escalate to architecture type if consolidation required

---

## Status: ✅ A2 COMPLETE

**Next**: Proceed to Phase A3 (Baseline Probe)
