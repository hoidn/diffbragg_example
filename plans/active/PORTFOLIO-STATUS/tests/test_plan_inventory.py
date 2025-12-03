"""Unit tests for plan_inventory.py script.

Hermetic tests that use temporary directories and do not rely on repo data.
Tests bucket logic, rollup report generation, and config file handling.

Per CLAUDE.md: Tests must be hermetic (tmp_path fixtures, no reliance on repo data).
"""

import json
import pytest
from pathlib import Path
import sys

# Add parent dir to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "bin"))

import plan_inventory
from plan_inventory import (
    PlanEntry,
    compute_bucket,
    load_rollup_config,
    parse_fix_plan_ids,
    inventory_plans,
    write_rollup_report,
    resolve_rollup_config,
)


class TestBucketLogic:
    """Test bucket classification per classification.md rules."""

    def test_active_missing_bucket(self):
        """Plans with implementation but not in fix_plan → active_missing."""
        entry = PlanEntry(
            id="TEST-001",
            in_fix_plan=False,
            has_implementation=True,
            last_report="2025-12-05T120000Z",
            status_hint="Active"
        )
        assert compute_bucket(entry) == "active_missing"

    def test_archive_ready_bucket_with_archive_hint(self):
        """Plans with 'archive' in status_hint → archive_ready."""
        entry = PlanEntry(
            id="TEST-002",
            in_fix_plan=False,
            has_implementation=True,
            last_report=None,
            status_hint="Ready for archive"
        )
        assert compute_bucket(entry) == "archive_ready"

    def test_archive_ready_bucket_with_duplicate_hint(self):
        """Plans with 'duplicate' in status_hint → archive_ready."""
        entry = PlanEntry(
            id="TEST-003",
            in_fix_plan=False,
            has_implementation=True,
            last_report=None,
            status_hint="Duplicate of TEST-001"
        )
        assert compute_bucket(entry) == "archive_ready"

    def test_missing_plan_bucket(self):
        """Plans without implementation.md → missing_plan."""
        entry = PlanEntry(
            id="TEST-004",
            in_fix_plan=False,
            has_implementation=False,
            last_report=None,
            status_hint=None
        )
        assert compute_bucket(entry) == "missing_plan"

    def test_tracked_bucket(self):
        """Plans already in fix_plan → tracked."""
        entry = PlanEntry(
            id="TEST-005",
            in_fix_plan=True,
            has_implementation=True,
            last_report="2025-12-05T120000Z",
            status_hint="in_progress"
        )
        assert compute_bucket(entry) == "tracked"


class TestRollupConfig:
    """Test rollup config loading and handling."""

    def test_load_rollup_config_valid(self, tmp_path):
        """Load valid rollup config JSON."""
        config_path = tmp_path / "rollups.json"
        config_data = {
            "ROLLUP-A": ["PLAN-1", "PLAN-2"],
            "ROLLUP-B": ["PLAN-3"]
        }
        config_path.write_text(json.dumps(config_data))

        loaded = load_rollup_config(config_path)
        assert loaded == config_data

    def test_load_rollup_config_missing_file(self, tmp_path):
        """Missing config file returns empty dict."""
        config_path = tmp_path / "nonexistent.json"
        loaded = load_rollup_config(config_path)
        assert loaded == {}


class TestResolveRollupConfig:
    """Test automation guard rollup config resolution."""

    def test_user_supplied_path(self, tmp_path):
        cfg = tmp_path / "rollups.json"
        cfg.write_text("{}")
        path, auto = resolve_rollup_config(cfg)
        assert path == cfg
        assert not auto

    def test_auto_default_path(self, tmp_path, monkeypatch):
        cfg = tmp_path / "auto_rollups.json"
        cfg.write_text("{}")
        monkeypatch.setattr(plan_inventory, "DEFAULT_ROLLUP_CONFIG", cfg)
        path, auto = resolve_rollup_config(None)
        assert path == cfg
        assert auto

    def test_missing_default_path_errors(self, tmp_path, monkeypatch):
        missing = tmp_path / "missing_rollups.json"
        monkeypatch.setattr(plan_inventory, "DEFAULT_ROLLUP_CONFIG", missing)
        with pytest.raises(FileNotFoundError):
            resolve_rollup_config(None)

    def test_missing_user_path_errors(self, tmp_path):
        bad = tmp_path / "does_not_exist.json"
        with pytest.raises(FileNotFoundError):
            resolve_rollup_config(bad)

    def test_load_rollup_config_invalid_json(self, tmp_path):
        """Invalid JSON returns empty dict."""
        config_path = tmp_path / "bad.json"
        config_path.write_text("{ invalid json }")
        loaded = load_rollup_config(config_path)
        assert loaded == {}


class TestInventoryPlans:
    """Test plan directory scanning and bucket assignment."""

    def test_inventory_with_buckets(self, tmp_path):
        """Inventory assigns buckets correctly."""
        plans_root = tmp_path / "plans"
        plans_root.mkdir()

        # Create active plan with implementation
        active_plan = plans_root / "ACTIVE-001"
        active_plan.mkdir()
        (active_plan / "implementation.md").write_text(
            "# Active Plan\n\nThis is a real active plan with sufficient content.\n\n**Status:** in_progress"
        )

        # Create archive-ready plan
        archive_plan = plans_root / "ARCHIVE-001"
        archive_plan.mkdir()
        (archive_plan / "implementation.md").write_text(
            "# Archive Candidate\n\nThis plan should be archived soon.\n\n**Status:** Ready for archive"
        )

        # Create missing plan (no implementation)
        missing_plan = plans_root / "MISSING-001"
        missing_plan.mkdir()

        # Fix plan has none of these
        fix_plan_ids = set()

        entries = inventory_plans(plans_root, fix_plan_ids)

        # Verify buckets
        entry_map = {e.id: e for e in entries}
        assert entry_map["ACTIVE-001"].bucket == "active_missing"
        assert entry_map["ARCHIVE-001"].bucket == "archive_ready"
        assert entry_map["MISSING-001"].bucket == "missing_plan"


class TestRollupReport:
    """Test rollup report generation."""

    def test_rollup_report_basic(self, tmp_path):
        """Generate rollup report with timestamp spans and coverage."""
        # Setup fake entries
        entries = [
            PlanEntry("PLAN-1", False, True, "2025-11-01T120000Z", None, "active_missing"),
            PlanEntry("PLAN-2", False, True, "2025-11-05T120000Z", None, "active_missing"),
            PlanEntry("PLAN-3", False, True, "2025-11-03T120000Z", None, "active_missing"),
        ]

        rollup_config = {
            "ROLLUP-A": ["PLAN-1", "PLAN-2"],
            "ROLLUP-B": ["PLAN-3"]
        }

        fix_plan_ids = {"ROLLUP-A"}  # ROLLUP-A has section, ROLLUP-B doesn't

        out_path = tmp_path / "rollup_report.md"
        write_rollup_report(rollup_config, entries, fix_plan_ids, out_path)

        content = out_path.read_text()

        # Verify structure
        assert "# Roll-Up Coverage Report" in content
        assert "## ROLLUP-A" in content
        assert "## ROLLUP-B" in content

        # Verify member lists
        assert "PLAN-1, PLAN-2" in content
        assert "PLAN-3" in content

        # Verify timestamp spans
        assert "2025-11-01T120000Z to 2025-11-05T120000Z" in content
        assert "2025-11-03T120000Z" in content

        # Verify coverage flags
        assert "✓ Section exists" in content  # ROLLUP-A
        assert "✗ Missing section" in content  # ROLLUP-B

    def test_rollup_report_missing_member_dirs(self, tmp_path):
        """Report shows missing member directories."""
        entries = [
            PlanEntry("PLAN-1", False, True, "2025-11-01T120000Z", None, "active_missing"),
        ]

        rollup_config = {
            "ROLLUP-X": ["PLAN-1", "PLAN-MISSING"]
        }

        fix_plan_ids = set()
        out_path = tmp_path / "rollup_report.md"
        write_rollup_report(rollup_config, entries, fix_plan_ids, out_path)

        content = out_path.read_text()
        assert "**Missing Member Directories:** PLAN-MISSING" in content

    def test_rollup_report_no_reports(self, tmp_path):
        """Handle roll-ups with no reports."""
        entries = [
            PlanEntry("PLAN-1", False, True, None, None, "active_missing"),
        ]

        rollup_config = {
            "ROLLUP-Y": ["PLAN-1"]
        }

        fix_plan_ids = set()
        out_path = tmp_path / "rollup_report.md"
        write_rollup_report(rollup_config, entries, fix_plan_ids, out_path)

        content = out_path.read_text()
        assert "**Last Report Span:** No reports found" in content


class TestFixPlanParsing:
    """Test fix_plan.md ID extraction."""

    def test_parse_fix_plan_ids(self, tmp_path):
        """Extract [PLAN-ID] patterns from markdown."""
        fix_plan = tmp_path / "fix_plan.md"
        fix_plan.write_text("""
# Fix Plan

## Active Initiatives

### [ARCH-REFACTOR-001] Refinement Engine
- Status: in_progress

### [DB-AT-SUITE-CARE-001] DB Acceptance Tests
- Status: pending

Some text mentioning [INLINE-REF-001] in a sentence.
        """)

        ids = parse_fix_plan_ids(fix_plan)
        assert "ARCH-REFACTOR-001" in ids
        assert "DB-AT-SUITE-CARE-001" in ids
        assert "INLINE-REF-001" in ids

    def test_parse_fix_plan_missing_file(self, tmp_path):
        """Missing fix_plan returns empty set."""
        fix_plan = tmp_path / "nonexistent.md"
        ids = parse_fix_plan_ids(fix_plan)
        assert ids == set()
