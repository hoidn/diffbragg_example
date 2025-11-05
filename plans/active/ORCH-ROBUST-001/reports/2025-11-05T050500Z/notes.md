Title: Galph robustness tweak — doc/meta whitelist includes Git meta files
Date: 2025-11-05T05:05:00Z
Change:
- Adjusted supervisor default `--autocommit-whitelist` to add `.gitignore`, `.gitmodules`, `.gitattributes` so supervisor-initiated repo‑hygiene edits do not self‑fail the loop.
Files:
- scripts/orchestration/supervisor.py (argument default string)
- scripts/orchestration/README.md (document the whitelist)
Rebuild: none (Python script; no compilation)
Validation plan:
- With a dirty `.gitignore`, end-of-loop doc auto‑commit should stage+commit it and not mark `post_ok=False`.
- Prior failure signature in logs/integration/galph/iter-00090_20251105_044435.log should not reoccur.
Environment tag: orch-robust-docmeta-20251105
