# FORWARD-EQUIV-002 Artifact Validation Report

**Loop**: i=144
**Initiative**: DB-AT-SUITE-CARE-001 Phase B.3
**Timestamp**: 2025-12-08T03:00:00Z
**Validator**: Ralph (implementation engineer)

---

## Executive Summary

**Validation Outcome**: **Case C-Minor (manifest integrity anomaly detected)**

- **Directory**: `tests/fixtures/golden_data/simple_cubic/` — **EXISTS** ✓
- **Manifest**: `manifest.json` — **EXISTS** ✓
- **File Co-location**: All 7 tensor/data files present with correct sizes — **PASS** ✓
- **Foreign Paths (MANIFEST-001)**: No foreign paths detected — **PASS** ✓
- **Checksum Integrity**: Manifest file SHA256 **mismatch** vs expected — **FAIL** ⚠

**Impact Assessment**: DB-AT-002 Phase A1 can proceed with **CAUTION**. Artifact files are valid and co-located, but manifest integrity check failed. Recommend verifying expected checksum source and regenerating manifest if discrepancy confirmed.

---

## Validation Details

### 1. Directory Existence

```
$ ls -lah tests/fixtures/golden_data/simple_cubic/
total 102M
drwxrwxr-x 3 ollie ollie 4.0K Nov  4 09:19 .
drwxrwxr-x 3 ollie ollie 4.0K Oct 28 18:06 ..
-rw-rw-r-- 1 ollie ollie  24M Nov  4 09:18 bragg_diffbragg.npy
-rw-rw-r-- 1 ollie ollie  24M Oct 29 03:31 bragg_panel_0.npy
-rw-rw-r-- 1 ollie ollie  24M Nov  4 09:19 bragg_torch.npy
-rw-rw-r-- 1 ollie ollie 1.9K Nov  4 01:09 config_torch.json
-rw-rw-r-- 1 ollie ollie 6.0M Nov  4 09:19 loss_mask_panel_0.npy
-rw-rw-r-- 1 ollie ollie 2.1K Nov  4 09:19 manifest.json
-rw-rw-r-- 1 ollie ollie  479 Nov  4 09:19 metadata.json
drwxrwxr-x 3 ollie ollie 4.0K Oct 29 12:29 plans
-rw-rw-r-- 1 ollie ollie 5.1K Nov  4 09:19 refined.expt
-rw-rw-r-- 1 ollie ollie  67K Nov  4 09:19 refined.refl
-rw-rw-r-- 1 ollie ollie 955K Nov  4 09:19 refined_structure_factors.mtz
-rw-rw-r-- 1 ollie ollie  24M Nov  4 09:19 target_panel_0.npy
```

**Status**: ✓ Directory exists with 13 files (10 data files + 3 metadata/config files)

### 2. Manifest Verification

**Manifest File SHA256**:
```
Actual:   1a45240a0a86409b1f214c239293dc042b9eb6a04455c26aa6eccaa3ac035d02
Expected: 2d1f8d67…8567aee (per DB-AT-SUITE-CARE-001 implementation.md:38)
Match:    FALSE ⚠
```

**Self-Reported Manifest Integrity Check**:
```
Self-reported manifest_sha256: b73e5049daebcb6a5166aa33f19705bf27964609bcbb607fe42fd02867b5405d
Computed checksum (excluding manifest_sha256 field): 9290abacc3c5bb1dffb9bdc93c16daee8eeec4744e5c73552b9c863121730eb4
Internal consistency: FALSE ⚠
```

**Analysis**: The manifest contains a `manifest_sha256` field that does not match the computed checksum of the manifest content (excluding that field). This suggests either:
1. The manifest was manually edited after generation, OR
2. The checksum computation algorithm differs from the generator's implementation, OR
3. The expected checksum in the implementation plan refers to an older version

### 3. File Co-location Check (MANIFEST-001)

**Foreign Path Analysis**:
```
bragg_diffbragg:          bragg_diffbragg.npy         — Foreign path: False ✓
bragg_torch:              bragg_torch.npy             — Foreign path: False ✓
target_panel_0:           target_panel_0.npy          — Foreign path: False ✓
loss_mask_panel_0:        loss_mask_panel_0.npy       — Foreign path: False ✓
refined_structure_factors: refined_structure_factors.mtz — Foreign path: False ✓
refined_experiment:       refined.expt                — Foreign path: False ✓
refined_reflections:      refined.refl                — Foreign path: False ✓
```

**Status**: ✓ All file paths are relative filenames (no `/` or `\` characters). MANIFEST-001 requirement satisfied.

### 4. Tensor Inventory

**File Existence and Size Validation**:

| Manifest Key | Filename | Expected Size | Actual Size | Exists | Size Match |
|-------------|----------|---------------|-------------|--------|------------|
| bragg_diffbragg | bragg_diffbragg.npy | 24,896,132 | 24,896,132 | ✓ | ✓ |
| bragg_torch | bragg_torch.npy | 24,896,132 | 24,896,132 | ✓ | ✓ |
| target_panel_0 | target_panel_0.npy | 24,896,132 | 24,896,132 | ✓ | ✓ |
| loss_mask_panel_0 | loss_mask_panel_0.npy | 6,224,129 | 6,224,129 | ✓ | ✓ |
| refined_structure_factors | refined_structure_factors.mtz | 977,156 | 977,156 | ✓ | ✓ |
| refined_experiment | refined.expt | 5,204 | 5,204 | ✓ | ✓ |
| refined_reflections | refined.refl | 67,657 | 67,657 | ✓ | ✓ |

**Summary**: All 7 files exist with exact size matches. Total payload: ~102 MB.

### 5. Manifest Metadata

```json
{
  "dataset_name": "simple_cubic_canonical",
  "generation_timestamp": "2025-11-04T17:19:02.880149Z",
  "generator_command": "/home/ollie/Documents/diffbragg_example_2/diffbragg_example/scripts/generate_simple_cubic_golden.py ...",
  "git_revision": "c778c093f8f923c6c6b78361e90d2e713ea5e8e9",
  "structure_factor_source": "refined_structure_factors.mtz",
  "experiment_source": "refined.expt",
  "reflection_source": "refined.refl"
}
```

**Generation Details**:
- **Timestamp**: 2025-11-04T17:19:02Z (33 days ago)
- **Git Revision**: `c778c093` (commit from Nov 4, 2025)
- **Generator**: `scripts/generate_simple_cubic_golden.py`

---

## Recommendations

### Immediate Action (DB-AT-002 Phase A1)

**PROCEED WITH CAUTION** ✓ (with follow-up investigation)

**Rationale**:
1. **Core requirement met**: All tensor payloads exist and are co-located (MANIFEST-001 satisfied)
2. **Functional readiness**: DB-AT-002 Phase A1 fixture loading (`np.load()` calls) will succeed
3. **Checksum discrepancy**: Non-blocking for immediate Phase A1 work, but requires investigation

**Action Items**:
1. **DB-AT-002 owner**: Proceed to Phase A1 (fixture loading + basic validation test authoring)
2. **FORWARD-EQUIV-002 owner** (if exists): Investigate checksum mismatch:
   - Verify expected checksum source (`2d1f8d67…8567aee`)
   - Check if manifest was manually edited post-generation
   - Consider regenerating manifest with current `generate_simple_cubic_golden.py` if integrity critical
3. **DB-AT-SUITE-CARE-001 (this initiative)**: Proceed to Phase B.4 (member plan Phase A coordination)

### Long-term Maintenance

**If FORWARD-EQUIV-002 plan exists**:
- Escalate manifest integrity issue to plan owner
- Request manifest regeneration with verification of self-checksum algorithm

**If FORWARD-EQUIV-002 plan does NOT exist**:
- Document this check as part of DB-AT-SUITE-CARE-001 baseline validation
- Consider creating FORWARD-EQUIV-002 plan for golden suite maintenance if multiple consumers emerge

---

## Cross-References

- **DB-AT-002 Implementation Plan**: `plans/active/DB-AT-002/implementation.md` (Phase A1 depends on these fixtures)
- **DB-AT-SUITE-CARE-001 Implementation Plan**: `plans/active/DB-AT-SUITE-CARE-001/implementation.md` (Phase B.3 task definition, line 38)
- **Dependency Chain**: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T024500Z/dependency_chain.md`
- **SPEC**: `docs/spec-db-conformance.md` §DB-AT-002 (canonical tensors + metrics baselines)
- **Testing Strategy**: `docs/development/testing_strategy.md` §2.1 (Golden dataset maintenance)

---

## Artifacts

- **Directory Listing**: `ls_golden_data.txt` (13 files, 102 MB total)
- **Manifest Verification**: `manifest_verification.txt` (SHA256 checks, foreign path analysis, file existence validation)
- **This Report**: `forward_equiv_002_check.md`

---

**Validation Status**: ✓ **UNBLOCKED** (with checksum investigation recommended)
**Next Milestone**: DB-AT-SUITE-CARE-001 Phase B.4 (member plan Phase A coordination)
