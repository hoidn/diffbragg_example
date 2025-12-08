# A2 — Spec Alignment

## Bbox Semantics

### Normative Requirements

**spec-db-core.md:22–26** (ROI bbox semantics):
- Bboxes SHALL be `(x0, x1, y0, y1)` with `x1`, `y1` exclusive
- Slice as `img[pid, y0:y1, x0:x1]`
- Exclusivity invariant: `x1 > x0` and `y1 > y0` (non-empty ROIs)
- Upper bounds SHALL be within panel dimensions (`x1 <= panel_width`, `y1 <= panel_height`)

**dials_api.md:8–10, 26** (reflection table schema):
- Reflection `bbox` column: `(x0, x1, y0, y1, z0, z1)` tuple
- For 2D stills ROI slicing, use first four values `(x0, x1, y0, y1)`
- Upper bounds `x1`/`y1` are exclusive (Python slice convention)

**architecture.md:122–123** (runtime guards):
- Bounds check ROI bboxes (exclusive upper bounds)
- Enforce panel index alignment across reflections, image stacks, and masks

### Test Expectations for DB-AT-020

The acceptance test SHALL validate:

1. **Bbox exclusivity**:
   - Every ROI bbox satisfies `x1 > x0` and `y1 > y0`
   - No zero-width or zero-height bboxes

2. **Bounds conformance**:
   - For each ROI with panel `pid` and bbox `(x0, x1, y0, y1)`:
     - `x1 <= detector[pid].get_image_size()[0]` (panel fast dimension)
     - `y1 <= detector[pid].get_image_size()[1]` (panel slow dimension)
     - `x0 >= 0` and `y0 >= 0`

3. **Slicing shape validation**:
   - `dl.data[pid, y0:y1, x0:x1].shape == (y1 - y0, x1 - x0)`
   - `dl.background_image[pid, y0:y1, x0:x1].shape == (y1 - y0, x1 - x0)`

## Panel Alignment Semantics

### Normative Requirements

**dials_api.md:11–12, 27** (panel alignment):
- Panel indices in reflection tables align with `image_data_from_expt(expt)` stack and simtbx ROI `panel_ids`
- Reflection `panel`, image stack panel axis, and detector index use the same ordering

**spec-db-core.md:20** (pixel arrays ordering):
- Pixel arrays and masks SHALL use `[panel, slow, fast]` ordering

**architecture.md:123** (panel index alignment):
- Enforce panel index alignment across reflections, image stacks, and masks

### Test Expectations for DB-AT-020

The acceptance test SHALL validate:

1. **Panel ID range**:
   - All `dl.pids` values fall within `[0, len(dl.detector))`
   - Panel IDs are integers (flex.size_t or torch.int64)

2. **Reflection table alignment**:
   - Reflection table `panel` column matches `dl.pids` ordering
   - Length of `dl.bboxes` equals length of `dl.pids` (ROI array sync)

3. **Panel ordering consistency**:
   - Panel indices used for slicing (`dl.data[pid, ...]`) align with detector panel indexing

## Mask Precedence

### Normative Requirements

**spec-db-core.md:32–34** (mask formats):
- DIALS trusted mask SHALL be tuple of `flex.bool` per panel (True=trusted) shaped `(slow, fast)`
- DiffBragg hot/bad masks are inverted; explicit inversion SHALL be documented

**MASKING-001 finding** (applied per input.md:30–32):
- Bbox/ROI logic must use canonical mask precedence: `trusted_mask ∩ ROI ∩ background >= 0`

### Test Expectations for DB-AT-020

Phase B tests will validate loss_mask construction; Phase A baseline probe (A3) will inspect mask application as implemented.

## Cross-references

- **SPEC**: `docs/spec-db-core.md:22–26` (bbox semantics), `docs/spec-db-core.md:20` (pixel ordering), `docs/spec-db-core.md:32–34` (masks)
- **SPEC**: `docs/dials_api.md:8–10` (reflection bbox schema), `docs/dials_api.md:26–27` (slicing and alignment)
- **ARCH**: `docs/architecture.md:122–123` (runtime guards, panel index alignment)
- **FINDINGS**: CONFORMANCE-001 (acceptance test patterns), MASKING-001 (mask handling contracts)

## Reconciliation Summary

All normative sources are aligned:
- Bbox exclusivity and bounds enforcement are consistent across spec-db-core.md, dials_api.md, and architecture.md
- Panel alignment semantics follow DIALS convention (`[panel, slow, fast]` ordering)
- Runtime guards in architecture.md reinforce spec-db-core.md bbox invariants
- No conflicts detected; DB-AT-020 Phase B test assertions can be authored directly from these requirements
