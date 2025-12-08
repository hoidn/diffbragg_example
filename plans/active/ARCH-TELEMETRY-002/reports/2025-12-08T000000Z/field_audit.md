# ARCH-TELEMETRY-002 Phase C.1: Field Audit Report

**Created**: 2025-12-08T000000Z
**Author**: Ralph (Implementation Engineer)
**Purpose**: Audit telemetry fields for usage; identify deprecation candidates

---

## Methodology

Searched for each telemetry field from the Phase A inventory across:
1. Spec-DB documents (`docs/spec-db-*.md`)
2. Test files (`tests/`)
3. Data Dependency Manifest (`docs/data_dependency_manifest.md`)
4. Active plan artifacts (`plans/active/`)

---

## Field Status Summary

### Actively Used Fields (No Action Required)

| Field | Spec-DB | Tests | Manifest | Plans | Verdict |
|-------|---------|-------|----------|-------|---------|
| `stage_b_baseline_rel_diff` | N/A | test_stage_b_cpu_fallback.py, test_torch_refine_smoke.py | Yes | ARCH-REFINE-001 | **In Use** |
| `stage_b_baseline_abs_diff` | N/A | test_stage_b_cpu_fallback.py, test_torch_refine_smoke.py | Yes | ARCH-REFINE-001 | **In Use** |
| `variance_floor_clamped_pixels` | spec-db-conformance.md | test_stage_a_smoke_parity.py, test_stage_a_mapping_equiv.py | Yes | TOOLING-VIS-001 | **In Use** |
| `variance_floor_masked_pixels` | spec-db-conformance.md | test_stage_a_smoke_parity.py, test_stage_a_mapping_equiv.py | Yes | TOOLING-VIS-001 | **In Use** |
| `canonical_detector_distances_mm` | N/A | test_refine_one_cli.py, test_torch_refine_smoke.py | Yes | N/A | **In Use** |
| `log_scale_baseline_source` | N/A | test_stage_a_smoke_parity.py | Yes | ARCH-SIM-CONSTRUCTION-001 | **In Use** |
| `loss_trace_sample/full` | spec-db-conformance.md | test_refine_one_cli.py | Yes | Multiple | **In Use** |
| `chi_squared_trace_*` | spec-db-conformance.md | test_refine_one_cli.py | Yes | Multiple | **In Use** |
| `masked_mse_trace_*` | N/A | test_refine_one_cli.py | Yes | Multiple | **In Use** |

### Plan-Local Diagnostic Fields (Active Plan Consumer)

| Field | Tests | Active Plan | Verdict |
|-------|-------|-------------|---------|
| `u_matrix_lifecycle_log` | None | TORCH-GEOMETRY-CONVERGENCE-001 | **Plan-local diagnostic** |
| `a_star_lifecycle_log` | None | TORCH-GEOMETRY-CONVERGENCE-001 | **Plan-local diagnostic** |

**Note**: These fields are NOT serialized to HDF5 (`dbex/io/writer.py` does not emit them). They are internal state used for convergence diagnostics during the TORCH-GEOMETRY-CONVERGENCE-001 initiative. Per PROBE-FREEZE-001, they are legitimate plan-local diagnostics. No deprecation action required while the plan is active.

### Internal-Use Fields (No Test Consumer - Monitor for Deprecation)

| Field | Spec-DB | Tests | Manifest | Plans | Verdict |
|-------|---------|-------|----------|-------|---------|
| `panel_loss_diag` | No | No | No | No | **Future deprecation candidate** |

**Evidence**:
- `grep -r "panel_loss_diag" tests/` -> No matches
- `grep -r "panel_loss_diag" docs/spec-db-*.md` -> No matches
- Only found in: charter (telemetry.md), archive (fix_plan_archive.md), implementation code

**Recommendation**: Document as internal diagnostic. If still unused after TORCH-GEOMETRY-* initiatives close, consider deprecation in future telemetry cleanup.

---

## Conclusion

**Exit Criterion 2 Status**: All primary telemetry fields are in active use.

- No fields are completely unused
- `panel_loss_diag` is a candidate for future cleanup (internal-use only, no test/spec consumers)
- `u_matrix_lifecycle_log` and `a_star_lifecycle_log` serve TORCH-GEOMETRY-CONVERGENCE-001 (plan-local diagnostics per PROBE-FREEZE-001)

**Action**: Mark EC2 as "all fields in use — no deprecation needed; `panel_loss_diag` identified as future cleanup candidate."

---

## Grep Commands Executed

```bash
# Lifecycle logs
grep -r "u_matrix_lifecycle|a_star_lifecycle" docs/spec-db-*.md  # No matches
grep -r "u_matrix_lifecycle|a_star_lifecycle" tests/             # No matches
grep -r "u_matrix_lifecycle|a_star_lifecycle" docs/data_dependency_manifest.md  # No matches
# Found in: interfaces.py, context.py, telemetry_collectors.py, stage_a.py, telemetry.md

# panel_loss_diag
grep -r "panel_loss_diag" tests/              # No matches
grep -r "panel_loss_diag" docs/spec-db-*.md   # No matches
# Found in: telemetry.md, fix_plan_archive.md, implementation code

# Stage B baseline (widely used)
grep -r "stage_b_baseline_rel_diff" .  # 22 files

# Variance floor (widely used)
grep -r "variance_floor_clamped_pixels" .  # 29 files
```

---

## Cross-References

- Telemetry Inventory: `reports/2025-12-07T215000Z/telemetry_inventory.md`
- Charter: `docs/architecture/telemetry.md`
- Probe Freeze Policy: PROBE-FREEZE-001 in `docs/findings.md`
