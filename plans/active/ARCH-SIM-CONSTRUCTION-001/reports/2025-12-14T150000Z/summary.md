### Turn Summary
Flagged the missing StageAContext hand-off as the reason reconstruction stays 9–30× below telemetry and updated the plan so DB-AT fixtures plus the baseline probe pull warm caches from StageAArtifacts instead of the removed `_stage_contexts` hook.
Logged the fix in docs/fix_plan.md + the implementation plan and queued a Do Now that patches both files, then reruns the probe and DB-AT-028/029 under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/` to prove reconstruction now matches Stage A telemetry before chasing further scale bugs.
Next: Ralph should implement the StageAArtifacts wiring, rerun the baseline probe, and re-execute the DB-AT selectors with the new artifact path to confirm masked means/chi² align with telemetry.
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/
