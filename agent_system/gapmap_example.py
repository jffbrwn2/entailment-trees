#!/usr/bin/env python3
"""
Example usage of GAP-map client helper functions.

GAP-map catalogs important open problems across scientific fields and
the foundational capabilities/approaches that could address them.

Simple helper module - no MCP overhead, just fetch and filter JSON.
"""

from gapmap_client import GapMapClient


def explore_problem(query: str, field: str = None):
    """
    Explore a research problem using GAP-map.

    Args:
        query: Problem description (e.g., "neural recording")
        field: Optional field filter (e.g., "Computation", "Biology")
    """
    client = GapMapClient()

    print(f"\n{'='*60}")
    print(f"Exploring: {query}")
    if field:
        print(f"Field: {field}")
    print(f"{'='*60}\n")

    # Find related gaps
    gaps = client.search_gaps(query, field=field)
    print(f"Found {len(gaps)} related open problems\n")

    # Show top 3 gaps with their approaches
    for i, gap in enumerate(gaps[:3], 1):
        print(f"{i}. {gap['name']} ({gap['field']['name']})")
        print(f"   {gap['description'][:150]}...\n")

        # Get approaches for this gap
        caps = client.get_capabilities_for_gap(gap["id"])
        if caps:
            print(f"   Foundational Capabilities ({len(caps)}):")
            for j, cap in enumerate(caps[:2], 1):
                print(f"   {j}. {cap['name']}")
                print(f"      {cap['description'][:100]}...")

                # Get resources
                resources = client.get_resources_for_capability(cap["id"])
                if resources:
                    print(f"      Resources: {len(resources)} papers/tools available")
        print()


def quick_search(query: str):
    """Quick search across all problems."""
    client = GapMapClient()
    results = client.find_related_approaches(query)

    print(f"\nQuick search for: {query}")
    print(f"Found {len(results['matched_gaps'])} related problems")

    for gap in results["matched_gaps"][:3]:
        print(f"  - {gap['name']} ({gap['field']['name']})")


if __name__ == "__main__":
    # Example 1: Explore neural recording problems
    explore_problem("neural recording", field="Biology")

    # Example 2: Explore quantum computing
    explore_problem("quantum computing", field="Computation")

    # Example 3: Quick search
    quick_search("machine learning hardware")
