### Turn Summary
Hardened the plan inventory guard by documenting the required `--rollup-config` command, auto-loading the canonical rollups.json in plan_inventory.py, and expanding its pytest suite so the guard now fails fast when the config is missing.
Regenerated the inventory under 2025-12-06T094500Z with the new guard (56 plans total, 22 tracked, 32 active_missing, 2 missing_plan) and refreshed docs/fix_plan.md + implementation.md with the latest counts and Phase C status; archive hygiene for ARCH-REFRACTOR-001 confirmed.
Next: author the FINDINGS-LEDGER-002 implementation stub, hook it into docs/fix_plan.md, and rerun the inventory so the missing-plan bucket drops back to one.
Artifacts: plans/active/PORTFOLIO-STATUS/reports/2025-12-06T094500Z/ (inventory.json, inventory_missing.md, rollup_report.md, pytest_plan_inventory.log)
