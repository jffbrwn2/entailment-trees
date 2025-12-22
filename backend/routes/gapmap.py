"""Gap Map API endpoints."""

from fastapi import APIRouter, HTTPException

from backend.models import GenerateHypothesisRequest
from backend.services import get_gapmap_client, get_openrouter_client

router = APIRouter(prefix="/api/gapmap", tags=["gapmap"])


@router.get("/gaps")
async def get_gapmap_gaps():
    """Get all research gaps from Gap Map."""
    try:
        client = get_gapmap_client()
        gaps = client.get_all_gaps()
        return gaps
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch gaps: {str(e)}")


@router.get("/capabilities")
async def get_gapmap_capabilities():
    """Get all capabilities from Gap Map."""
    try:
        client = get_gapmap_client()
        capabilities = client.get_all_capabilities()
        return capabilities
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch capabilities: {str(e)}")


@router.get("/fields")
async def get_gapmap_fields():
    """Get all fields from Gap Map for filtering."""
    try:
        client = get_gapmap_client()
        fields = client.get_all_fields()
        return fields
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch fields: {str(e)}")


@router.get("/resources")
async def get_gapmap_resources():
    """Get all resources from Gap Map."""
    try:
        client = get_gapmap_client()
        resources = client.get_all_resources()
        return resources
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch resources: {str(e)}")


@router.post("/generate-hypothesis")
async def generate_capability_hypothesis(request: GenerateHypothesisRequest):
    """Generate a hypothesis using Claude via OpenRouter."""
    # Build fallback first in case API fails
    if request.mode == "gap_only" and request.gap_name:
        fallback = f"It is possible to address {request.gap_name}"
    elif request.mode == "capability_only" and request.capability_name:
        fallback = f"{request.capability_name} can be applied to solve problems"
    else:
        fallback = f"{request.capability_name} can be used to address {request.gap_name}"

    # Try to get OpenRouter client - may fail if no API key
    try:
        openrouter_client = get_openrouter_client()
    except ValueError as e:
        print(f"[GAPMAP] OpenRouter client init failed: {e}", flush=True)
        return {"hypothesis": fallback, "error": str(e)}

    if request.mode == "gap_only" and request.gap_name:
        # Generate hypothesis for a gap (problem to be solved)
        prompt = f"""Convert this research gap into a clear, testable hypothesis about how it could be solved.

Research Gap: {request.gap_name}
{request.gap_description or ''}

Write a single hypothesis statement that proposes a specific approach to address this gap.
Be specific and concise. Output only the hypothesis statement, nothing else."""
    elif request.mode == "capability_only" and request.capability_name:
        # Generate hypothesis for a capability (technique/approach)
        prompt = f"""Convert this capability into a clear, testable hypothesis about what it could achieve.

Capability: {request.capability_name}
{request.capability_description or ''}

Write a single hypothesis statement that proposes a specific application of this capability.
Be specific and concise. Output only the hypothesis statement, nothing else."""
    else:
        # Generate hypothesis connecting capability to gap
        prompt = f"""Convert this capability and research gap into a clear, testable hypothesis claim.

Capability: {request.capability_name}
{request.capability_description or ''}

Research Gap: {request.gap_name}
{request.gap_description or ''}

Write a single hypothesis statement that proposes how this capability could address this gap.
Be specific and concise. Output only the hypothesis statement, nothing else."""

    try:
        hypothesis = await openrouter_client.chat(
            messages=[{"role": "user", "content": prompt}],
            model="anthropic/claude-opus-4.5",
        )
        return {"hypothesis": hypothesis.strip()}
    except Exception as e:
        print(f"[GAPMAP] OpenRouter chat failed: {e}", flush=True)
        return {"hypothesis": fallback, "error": str(e)}


@router.get("/gaps/{gap_id}/capabilities")
async def get_capabilities_for_gap(gap_id: str):
    """Get capabilities that address a specific gap."""
    try:
        client = get_gapmap_client()
        capabilities = client.get_capabilities_for_gap(gap_id)
        return capabilities
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch capabilities for gap: {str(e)}")


@router.get("/capabilities/{capability_id}/gaps")
async def get_gaps_for_capability(capability_id: str):
    """Get gaps that a capability addresses."""
    try:
        client = get_gapmap_client()
        gaps = client.get_all_gaps()

        # Find gaps that have this capability in their foundationalCapabilities
        # (Gap Map data has gaps -> capabilities, not capabilities -> gaps)
        matching_gaps = [
            g for g in gaps
            if capability_id in g.get("foundationalCapabilities", [])
        ]

        return matching_gaps
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch gaps for capability: {str(e)}")
