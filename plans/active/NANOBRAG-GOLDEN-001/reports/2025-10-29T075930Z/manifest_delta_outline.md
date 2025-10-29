# Manifest Delta Outline

- Current dataset_name: simple_cubic_fallback

## Planned Changes
- Replace fallback dataset name with canonical identifier (e.g., `nanoBragg_canonical_v1`).
- Introduce `datasets` array entries for `panel` and `roi` payloads with SHA256 placeholders.
- Add `roi_catalog` reference pointing to roi_bbox_catalog.json (docs/spec-db-core.md:20-33 alignment).
- Expand `provenance` with DiffBragg/torch command logs, git SHAs, and environment tags per POLICY-001.

## Verification Hooks
- Update parity_loader to validate checksums and ROI ordering.
- Ensure docs/spec-db-conformance.md:23-26 thresholds are testable via pytest fixtures.

## Follow-up
- After canonical tensors exist, compute SHA256 hashes and refresh metadata.json accordingly.
