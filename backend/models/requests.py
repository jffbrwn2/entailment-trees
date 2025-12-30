"""Pydantic request and response models."""

from typing import Optional
from pydantic import BaseModel


class CreateApproachRequest(BaseModel):
    """Request to create a new approach."""
    name: str
    hypothesis: str
    description: Optional[str] = ""


class ChatRequest(BaseModel):
    """Request to send a chat message."""
    message: str
    approach_name: Optional[str] = None


class ApproachInfo(BaseModel):
    """Information about an approach."""
    name: str
    folder: str
    description: str
    last_updated: str
    num_claims: int
    num_implications: int


class GenerateNameRequest(BaseModel):
    """Request to generate an approach name from a hypothesis."""
    hypothesis: str


class ResumeSessionRequest(BaseModel):
    """Request to resume a specific conversation."""
    conversation_filename: str


class AutoStartRequest(BaseModel):
    """Request to start auto mode."""
    model: str = "google/gemini-2.5-pro-preview"


class AutoInterjectRequest(BaseModel):
    """Request for user to interject during auto mode."""
    message: str
    target: Optional[str] = None  # 'auto' | 'core' | None


class UpdateSettingsRequest(BaseModel):
    """Request to update runtime settings."""
    chatModel: Optional[str] = None
    evaluatorModel: Optional[str] = None
    entailmentModel: Optional[str] = None
    autoModel: Optional[str] = None
    edisonToolsEnabled: Optional[bool] = None
    gapMapToolsEnabled: Optional[bool] = None


class SetApiKeysRequest(BaseModel):
    """Request to set API keys for the session."""
    anthropic_key: Optional[str] = None
    openrouter_key: Optional[str] = None


class GenerateHypothesisRequest(BaseModel):
    """Request to generate a hypothesis from capability and gap."""
    capability_name: Optional[str] = None
    capability_description: Optional[str] = None
    gap_name: Optional[str] = None
    gap_description: Optional[str] = None
    mode: str = "capability_gap"  # "capability_gap" or "gap_only"
