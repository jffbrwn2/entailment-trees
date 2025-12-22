"""Runtime settings and API key endpoints."""

from fastapi import APIRouter

from agent_system.runtime_settings import get_settings, update_settings
from agent_system.api_keys import get_api_key, set_api_key

from backend.models import UpdateSettingsRequest, SetApiKeysRequest

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/config/status")
async def get_config_status() -> dict:
    """Check if required API keys are configured."""
    return {
        "anthropic_key_set": bool(get_api_key("ANTHROPIC_API_KEY")),
        "openrouter_key_set": bool(get_api_key("OPENROUTER_API_KEY")),
    }


@router.post("/config/keys")
async def set_session_api_keys(request: SetApiKeysRequest) -> dict:
    """Set API keys for the current session (stored in memory only)."""
    if request.anthropic_key:
        set_api_key("ANTHROPIC_API_KEY", request.anthropic_key)
    if request.openrouter_key:
        set_api_key("OPENROUTER_API_KEY", request.openrouter_key)
    return {"status": "ok"}


@router.get("/settings")
async def get_runtime_settings() -> dict:
    """Get current runtime settings."""
    settings = get_settings()
    return settings.to_dict()


@router.put("/settings")
async def update_runtime_settings(request: UpdateSettingsRequest) -> dict:
    """Update runtime settings."""
    # Convert request to dict, filtering out None values
    data = {k: v for k, v in request.model_dump().items() if v is not None}
    settings = update_settings(data)
    return settings.to_dict()
