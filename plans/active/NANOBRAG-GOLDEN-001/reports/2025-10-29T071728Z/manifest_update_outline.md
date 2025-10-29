# Manifest Update Outline

Current manifest dataset_name: simple_cubic_fallback

## Proposed Fields
- `datasets`: expand to list Diptych entries with `kind` (ROI|panel), `panel_index`, `filename`, `sha256_placeholder`.
- `provenance`: add `diffbragg_capture` and `torch_capture` sub-sections with command logs and git SHAs.
- `roi_catalog`: document bbox coordinates and ROI id ordering for parity harness alignment.
- `spec_version`: bump to indicate hybrid ROI/full-panel compliance requirements.

## Verification Hooks
- Update parity_loader fixtures to validate ROI-to-panel mapping and bbox integrity.
- Embed checksum verification for both ROI and panel files using existing loader utilities.

All new text will cite docs/spec-db-conformance.md:23-26 and docs/spec-db-tracing.md:15-60 when implemented.
