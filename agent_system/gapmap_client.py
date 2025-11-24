"""
GAP-map API Client

Provides access to the GAP-map database of open important problems in science and technology.
https://www.gap-map.org/

The GAP-map catalogs:
- Research gaps: Open problems and challenges across scientific fields
- Capabilities: Foundational technologies/approaches that could address gaps
- Resources: Papers, datasets, and tools related to capabilities
- Fields: Research disciplines (computation, chemistry, biology, etc.)
"""

import requests
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


BASE_URL = "https://www.gap-map.org/data"


@dataclass
class Gap:
    """Represents a research gap/open problem."""
    id: str
    name: str
    slug: str
    description: str
    field: Dict[str, str]  # {id, name}
    foundational_capabilities: List[str]  # capability IDs
    tags: List[str]


@dataclass
class Capability:
    """Represents a foundational capability/approach."""
    id: str
    name: str
    slug: str
    description: str
    gaps: List[str]  # gap IDs this addresses
    resources: List[str]  # resource IDs
    tags: List[str]


@dataclass
class Resource:
    """Represents a resource (paper, tool, dataset)."""
    id: str
    title: str
    url: Optional[str]
    summary: Optional[str]
    types: List[str]  # e.g., ["Publication", "Dataset"]


class GapMapClient:
    """Client for GAP-map API."""

    def __init__(self):
        """Initialize the client."""
        self._cache = {}

    def _fetch(self, endpoint: str) -> Any:
        """Fetch data from GAP-map API with caching."""
        if endpoint in self._cache:
            return self._cache[endpoint]

        url = f"{BASE_URL}/{endpoint}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        self._cache[endpoint] = data
        return data

    def get_all_gaps(self) -> List[Dict]:
        """Get all research gaps."""
        data = self._fetch("gaps.json")
        # API returns list directly for individual endpoints
        return data if isinstance(data, list) else data.get("gaps", [])

    def get_all_capabilities(self) -> List[Dict]:
        """Get all foundational capabilities."""
        data = self._fetch("capabilities.json")
        return data if isinstance(data, list) else data.get("capabilities", [])

    def get_all_resources(self) -> List[Dict]:
        """Get all resources."""
        data = self._fetch("resources.json")
        return data if isinstance(data, list) else data.get("resources", [])

    def get_all_fields(self) -> List[Dict]:
        """Get all research fields."""
        data = self._fetch("fields.json")
        return data if isinstance(data, list) else data.get("fields", [])

    def search_gaps(self, query: str, field: Optional[str] = None) -> List[Dict]:
        """
        Search for gaps by keyword.

        Args:
            query: Search term (searches name and description)
            field: Optional field name to filter by (e.g., "Computation", "Chemistry")

        Returns:
            List of matching gaps
        """
        gaps = self.get_all_gaps()
        query_lower = query.lower()

        results = []
        for gap in gaps:
            # Check if query matches name or description
            name_match = query_lower in gap.get("name", "").lower()
            desc_match = query_lower in gap.get("description", "").lower()

            # Check field filter
            field_match = True
            if field:
                gap_field = gap.get("field", {}).get("name", "")
                field_match = field.lower() in gap_field.lower()

            if (name_match or desc_match) and field_match:
                results.append(gap)

        return results

    def get_gap_by_id(self, gap_id: str) -> Optional[Dict]:
        """Get a specific gap by ID."""
        gaps = self.get_all_gaps()
        for gap in gaps:
            if gap.get("id") == gap_id:
                return gap
        return None

    def get_capabilities_for_gap(self, gap_id: str) -> List[Dict]:
        """
        Get all capabilities that could address a specific gap.

        Args:
            gap_id: ID of the gap

        Returns:
            List of capabilities
        """
        gap = self.get_gap_by_id(gap_id)
        if not gap:
            return []

        capability_ids = gap.get("foundationalCapabilities", [])
        capabilities = self.get_all_capabilities()

        return [
            cap for cap in capabilities
            if cap.get("id") in capability_ids
        ]

    def get_resources_for_capability(self, capability_id: str) -> List[Dict]:
        """
        Get all resources related to a capability.

        Args:
            capability_id: ID of the capability

        Returns:
            List of resources
        """
        capabilities = self.get_all_capabilities()
        capability = next((c for c in capabilities if c.get("id") == capability_id), None)

        if not capability:
            return []

        resource_ids = capability.get("resources", [])
        resources = self.get_all_resources()

        return [
            res for res in resources
            if res.get("id") in resource_ids
        ]

    def find_related_approaches(self, problem_description: str) -> Dict[str, Any]:
        """
        Find gaps, capabilities, and resources related to a problem description.

        Args:
            problem_description: Description of the problem to explore

        Returns:
            Dict with:
                - matched_gaps: List of relevant gaps
                - capabilities: Dict mapping gap IDs to their capabilities
                - resources: Dict mapping capability IDs to their resources
        """
        # Search for relevant gaps
        gaps = self.search_gaps(problem_description)

        result = {
            "matched_gaps": gaps,
            "capabilities": {},
            "resources": {}
        }

        # Get capabilities for each gap
        for gap in gaps[:5]:  # Limit to top 5 to avoid too much data
            gap_id = gap["id"]
            caps = self.get_capabilities_for_gap(gap_id)
            result["capabilities"][gap_id] = caps

            # Get resources for each capability
            for cap in caps[:3]:  # Limit to top 3 capabilities per gap
                cap_id = cap["id"]
                resources = self.get_resources_for_capability(cap_id)
                result["resources"][cap_id] = resources

        return result

    def format_gap_summary(self, gap: Dict) -> str:
        """Format a gap as a readable summary."""
        field_name = gap.get("field", {}).get("name", "Unknown field")
        tags = gap.get("tags", [])
        tags_str = f" [{', '.join(tags)}]" if tags else ""

        return f"""
**{gap['name']}** ({field_name}){tags_str}

{gap['description']}

ID: {gap['id']}
Capabilities: {len(gap.get('foundationalCapabilities', []))} foundational approaches
"""

    def format_capability_summary(self, capability: Dict) -> str:
        """Format a capability as a readable summary."""
        tags = capability.get("tags", [])
        tags_str = f" [{', '.join(tags)}]" if tags else ""

        return f"""
**{capability['name']}**{tags_str}

{capability['description']}

ID: {capability['id']}
Addresses {len(capability.get('gaps', []))} gaps
Resources: {len(capability.get('resources', []))} available
"""

    def format_resource_summary(self, resource: Dict) -> str:
        """Format a resource as a readable summary."""
        types = resource.get("types", [])
        types_str = f" ({', '.join(types)})" if types else ""
        url = resource.get("url", "")
        url_str = f"\nURL: {url}" if url else ""

        summary = resource.get("summary", "No summary available")

        return f"""
**{resource['title']}**{types_str}

{summary}{url_str}
"""


if __name__ == "__main__":
    # Quick test
    client = GapMapClient()
    gaps = client.get_all_gaps()
    print(f"✓ GAP-map client works! Fetched {len(gaps)} research gaps")

    # Show a sample
    if gaps:
        print(f"\nSample gap:")
        print(client.format_gap_summary(gaps[0]))
