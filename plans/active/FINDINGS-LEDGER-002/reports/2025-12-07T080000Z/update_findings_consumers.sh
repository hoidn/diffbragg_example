#!/bin/bash
# Script to add "**Consumers:**" metadata to findings.md entries
# Phase B.2 of FINDINGS-LEDGER-002

set -e

FINDINGS_FILE="docs/findings.md"

# Backup
cp "$FINDINGS_FILE" "$FINDINGS_FILE.backup"

# Function to add consumer to a finding's Summary column
add_consumer() {
    local finding_id="$1"
    local consumer="$2"

    # Use sed to find the line with the finding ID and append the consumer to the Summary column
    # The Summary is in column 4 (after ID, Date, Tags)
    # We'll add " **Consumers:** $consumer" before the closing | of the Summary column

    sed -i "/^| $finding_id |/ s/| Active \$/| Active **Consumers:** $consumer |/" "$FINDINGS_FILE"
    sed -i "/^| $finding_id |/ s/| Resolved \$/| Resolved **Consumers:** $consumer |/" "$FINDINGS_FILE"
    sed -i "/^| $finding_id |/ s/| Deferred \$/| Deferred **Consumers:** $consumer |/" "$FINDINGS_FILE"
}

echo "Adding consumer metadata to findings.md..."

# TORCH-REFINE-CLEANUP-001 consumers
for finding in REFINE-001 REFINE-002 REFINE-003 REFINE-006 REFINE-009 REFINE-010 GRADIENT-001 REFINE-016; do
    add_consumer "$finding" "TORCH-REFINE-CLEANUP-001"
done

# MAP-SCALE-SYNC-001 consumers
for finding in SCALE-001 SCALE-002 SCALE-003 SCALE-004 SCALE-005 SCALE-006 SCALE-007; do
    add_consumer "$finding" "MAP-SCALE-SYNC-001"
done

# PERF-WARM-SIM-001 consumers
for finding in PERF-WARM-{001..013} REFINE-007 REFINE-011 REFINE-012; do
    add_consumer "$finding" "PERF-WARM-SIM-001"
done

# TORCH-GEOMETRY-SYNC-001 consumers
for finding in GEOMETRY-001 GEOMETRY-002 GEOMETRY-003 GEOMETRY-004 CONFIG-001 DXTBX-001 HKL-ORIENT-001 CONVERGENCE-001; do
    add_consumer "$finding" "TORCH-GEOMETRY-SYNC-001"
done

# PHYSICS-LOSS-CONSISTENCY consumers
for finding in PHYSICS-LOSS-{001..005}; do
    add_consumer "$finding" "PHYSICS-LOSS-CONSISTENCY"
done

# ARCH-REFACTOR-001 consumers
for finding in REFINE-001 ARCH-ENGINE-002 ARCH-ENGINE-003 ARCH-FACTORY-001 ARCH-FACTORY-003; do
    add_consumer "$finding" "ARCH-REFACTOR-001"
done

# ARCH-STAGE-CONTEXT-CONSOLIDATION consumers
for finding in ARCH-STAGE-CTX-001 ARCH-STAGE-CTX-002; do
    add_consumer "$finding" "ARCH-STAGE-CONTEXT-CONSOLIDATION"
done

# DB-AT-SUITE-CARE-001 consumers
for finding in TESTING-003 RUNTIME-001 DIAGNOSTICS-001 MASKING-001; do
    add_consumer "$finding" "DB-AT-SUITE-CARE-001"
done

# FORWARD-EQUIV-COVERAGE-001 consumers
for finding in PARITY-001 MANIFEST-001; do
    add_consumer "$finding" "FORWARD-EQUIV-COVERAGE-001"
done

# ARCH-IMPL-CONFORMANCE-001 consumer (already linked)
add_consumer "CONFORMANCE-001" "ARCH-IMPL-CONFORMANCE-001"

# TORCH-API-ALIGN-001 consumer (retrospective)
add_consumer "MODEL-001" "TORCH-API-ALIGN-001"

echo "Consumer metadata added to $(grep -c 'Consumers:' "$FINDINGS_FILE") findings"
echo "Backup saved to $FINDINGS_FILE.backup"
