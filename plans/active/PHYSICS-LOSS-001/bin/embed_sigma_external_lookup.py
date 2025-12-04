#!/usr/bin/env python3
"""
Legacy compatibility shim for sigma metadata embedding.

This script delegates to the canonical owner module dbex.tools.embed_sigma_external_lookup.
Preserved for backward compatibility with existing automation and documentation references.

New users should invoke the tool directly:
    python -m dbex.tools.embed_sigma_external_lookup [args]

Architecture Context: ARCH-PROBE-FREEZE-001 — Probe Freeze & Logging Consolidation
Canonical Owner: dbex/tools/embed_sigma_external_lookup.py
"""

from __future__ import annotations

if __name__ == "__main__":
    from dbex.tools.embed_sigma_external_lookup import main
    main()
