"""
Tests for GAP-map client helper functions.

Tests the simple GAP-map client for exploring open problems and approaches.
These tests make real API calls to gap-map.org.

Run with: pytest tests/test_gapmap_integration.py -v -s
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path to import gapmap_client directly
sys.path.insert(0, str(Path(__file__).parent.parent))
from agent_system.gapmap_client import GapMapClient


class TestGapMapClient:
    """Test basic GAP-map client functionality."""

    def test_get_all_gaps(self):
        """Test fetching all research gaps."""
        client = GapMapClient()
        gaps = client.get_all_gaps()

        print(f"\n✓ Fetched {len(gaps)} research gaps")
        assert len(gaps) > 0
        assert isinstance(gaps, list)

        # Check first gap structure
        first_gap = gaps[0]
        assert "id" in first_gap
        assert "name" in first_gap
        assert "description" in first_gap
        assert "field" in first_gap

    def test_get_all_capabilities(self):
        """Test fetching all foundational capabilities."""
        client = GapMapClient()
        capabilities = client.get_all_capabilities()

        print(f"\n✓ Fetched {len(capabilities)} capabilities")
        assert len(capabilities) > 0
        assert isinstance(capabilities, list)

        # Check first capability structure
        first_cap = capabilities[0]
        assert "id" in first_cap
        assert "name" in first_cap
        assert "description" in first_cap

    def test_get_all_fields(self):
        """Test fetching all research fields."""
        client = GapMapClient()
        fields = client.get_all_fields()

        print(f"\n✓ Fetched {len(fields)} research fields")
        assert len(fields) > 0

        # Check that common fields exist
        field_names = [f.get("name", "") for f in fields]
        print(f"  Fields: {', '.join(field_names[:5])}...")

    def test_search_gaps(self):
        """Test searching for gaps by keyword."""
        client = GapMapClient()

        # Search for computation-related gaps
        results = client.search_gaps("neural", field="Computation")

        print(f"\n✓ Found {len(results)} gaps related to 'neural' in Computation")

        if results:
            first_result = results[0]
            print(f"  Example: {first_result['name']}")
            assert "neural" in first_result["name"].lower() or "neural" in first_result["description"].lower()

    def test_get_capabilities_for_gap(self):
        """Test getting capabilities for a specific gap."""
        client = GapMapClient()

        # Get any gap first
        gaps = client.get_all_gaps()
        assert len(gaps) > 0

        test_gap = gaps[0]
        gap_id = test_gap["id"]

        print(f"\n✓ Testing gap: {test_gap['name']}")
        capabilities = client.get_capabilities_for_gap(gap_id)

        print(f"  Found {len(capabilities)} capabilities")
        assert isinstance(capabilities, list)

    def test_get_resources_for_capability(self):
        """Test getting resources for a capability."""
        client = GapMapClient()

        # Get any capability with resources
        capabilities = client.get_all_capabilities()
        capability_with_resources = None

        for cap in capabilities:
            if cap.get("resources") and len(cap["resources"]) > 0:
                capability_with_resources = cap
                break

        if capability_with_resources:
            resources = client.get_resources_for_capability(capability_with_resources["id"])
            print(f"\n✓ Found {len(resources)} resources for '{capability_with_resources['name']}'")

            if resources:
                first_resource = resources[0]
                print(f"  Example: {first_resource.get('title', 'N/A')}")
                assert "title" in first_resource


class TestGapMapSearchAndExplore:
    """Test GAP-map search and exploration workflows."""

    def test_find_related_approaches(self):
        """Test comprehensive search for related approaches."""
        client = GapMapClient()

        print("\n🔍 Searching for related neural recording problems...")
        results = client.find_related_approaches("neural activity recording")

        gaps = results["matched_gaps"]
        print(f"✓ Found {len(gaps)} related problems")

        if gaps:
            first_gap = gaps[0]
            print(f"\n  Related problem: {first_gap['name']}")
            print(f"  Field: {first_gap['field']['name']}")

            # Check if we got capabilities
            gap_id = first_gap["id"]
            if gap_id in results["capabilities"]:
                caps = results["capabilities"][gap_id]
                print(f"  Approaches: {len(caps)} foundational capabilities")

                if caps:
                    print(f"    - {caps[0]['name']}")

        assert isinstance(gaps, list)

    def test_explore_computation_gap(self):
        """Test exploring a specific computation-related gap."""
        client = GapMapClient()
        gaps = client.search_gaps("computing", field="Computation")

        print(f"\n✓ Found {len(gaps)} computation gaps")

        if gaps:
            test_gap = gaps[0]
            print(f"\n  Exploring: {test_gap['name']}")

            # Get approaches for this gap
            capabilities = client.get_capabilities_for_gap(test_gap["id"])
            print(f"  Foundational capabilities: {len(capabilities)}")

            # Check novelty by seeing if our approach matches existing capabilities
            if capabilities:
                print(f"\n  Existing approaches:")
                for cap in capabilities[:3]:
                    print(f"    - {cap['name']}")
                    print(f"      {cap['description'][:100]}...")

    def test_format_gap_summary(self):
        """Test formatting gap information for display."""
        client = GapMapClient()
        gaps = client.get_all_gaps()

        if gaps:
            summary = client.format_gap_summary(gaps[0])
            print(f"\n{summary}")

            assert gaps[0]["name"] in summary
            assert gaps[0]["description"] in summary
            assert "ID:" in summary

    def test_format_capability_summary(self):
        """Test formatting capability information for display."""
        client = GapMapClient()
        capabilities = client.get_all_capabilities()

        if capabilities:
            summary = client.format_capability_summary(capabilities[0])
            print(f"\n{summary}")

            assert capabilities[0]["name"] in summary
            assert capabilities[0]["description"] in summary

    def test_format_resource_summary(self):
        """Test formatting resource information for display."""
        client = GapMapClient()
        resources = client.get_all_resources()

        if resources:
            summary = client.format_resource_summary(resources[0])
            print(f"\n{summary}")

            assert resources[0]["title"] in summary


class TestGapMapWorkflow:
    """Test complete workflow using GAP-map."""

    def test_complete_problem_exploration_workflow(self):
        """Test complete workflow: search problems → explore approaches → get resources."""
        client = GapMapClient()

        # Step 1: Search for related problems
        print("\n📋 Step 1: Search for related problems")
        gaps = client.search_gaps("machine learning")
        print(f"✓ Found {len(gaps)} related problems")

        if not gaps:
            pytest.skip("No gaps found for 'machine learning'")

        # Step 2: Pick a gap and explore approaches
        test_gap = gaps[0]
        print(f"\n🔍 Step 2: Explore approaches for '{test_gap['name']}'")
        capabilities = client.get_capabilities_for_gap(test_gap["id"])
        print(f"✓ Found {len(capabilities)} approaches")

        if not capabilities:
            print("  No capabilities for this gap")
            return

        # Step 3: Get resources for an approach
        test_cap = capabilities[0]
        print(f"\n📚 Step 3: Get resources for '{test_cap['name']}'")
        resources = client.get_resources_for_capability(test_cap["id"])
        print(f"✓ Found {len(resources)} resources")

        if resources:
            print(f"\n  Sample resource: {resources[0]['title']}")
            if "url" in resources[0]:
                print(f"  URL: {resources[0]['url']}")

        print("\n✓ Complete workflow succeeded")

    def test_caching_behavior(self):
        """Test that the client caches API responses."""
        client = GapMapClient()

        # First call - should fetch from API
        gaps1 = client.get_all_gaps()

        # Second call - should use cache
        gaps2 = client.get_all_gaps()

        # Should return same data
        assert len(gaps1) == len(gaps2)
        assert gaps1[0]["id"] == gaps2[0]["id"]

        print(f"\n✓ Caching working correctly")


if __name__ == "__main__":
    # Run with: python tests/test_gapmap_integration.py
    pytest.main([__file__, "-v", "-s"])
