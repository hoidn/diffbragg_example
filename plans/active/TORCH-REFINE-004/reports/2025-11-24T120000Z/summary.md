### Turn Summary
Analyzed Ralph's Phase 8 blockers: identified two bugs in Stage B wrapper preventing E2E per-reflection validation.
Bug #1 (shell regression): wrapper uppercases optimizer_type but tests expect lowercase; fix removes `.upper()` at line 411.
Bug #2 (per-reflection KeyError): custom attributes added AFTER to_dict() serialization instead of BEFORE, causing Stage C extraction failure; fix adds attributes to dataclass before serialization matching nanobrag_refinement.py pattern.
Next: Ralph applies two-line fix (optimizer case + attribute timing), validates with 4-step protocol (compilation, Phase 6 regression, shell smoke, per-reflection smoke).
Artifacts: plans/active/TORCH-REFINE-004/reports/2025-11-24T120000Z/ (phase_8_blocker_analysis.md comprehensive root cause, input.md fix specification)
