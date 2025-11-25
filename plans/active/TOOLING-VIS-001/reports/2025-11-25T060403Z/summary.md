### Turn Summary
Authored a ready-for-implementation Do Now to log sigma/HKL provenance in the mapping probe and Stage A smoke fixture, then compare metadata-sigma vs cli_override contexts before rerunning DB-AT-028/029.
Mapping baseline still shows ROI CC≈-0.04 with spot_scale_override≈3.18e17 on metadata-sigma despite CPU/GPU parity; the new plan targets sigma_source/HKL differences as the likely culprit.
Next: Ralph implements the provenance logging, runs both probe variants, and executes DB-AT-028/029 (metadata) capturing logs/JSONs.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T060403Z/ (input.md)
