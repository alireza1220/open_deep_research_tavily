"""Pydantic schemas for FastAPI request and response models."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from open_deep_research.configuration import Configuration, MCPConfig, SearchAPI


class Message(BaseModel):
    """OpenAI-compatible message format."""

    role: str = Field(description="Message role (user, assistant, system)")
    content: str = Field(description="Message content")


class ResearchRequest(BaseModel):
    """Request schema for research endpoint."""

    messages: List[Message] = Field(
        description="List of messages in OpenAI-compatible format"
    )
    config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional configuration overrides. All Configuration fields are supported.",
    )


class ResearchResponse(BaseModel):
    """Response schema for research endpoint."""

    final_report: str = Field(description="Final research report")
    messages: List[Dict[str, Any]] = Field(
        description="List of messages from the research process"
    )
    notes: List[str] = Field(
        default_factory=list, description="Research notes and findings"
    )
    research_brief: Optional[str] = Field(
        default=None, description="Research brief/question"
    )
    status: str = Field(
        description="Status of the research (completed, clarification_needed, error)"
    )


class StreamEvent(BaseModel):
    """Server-Sent Events format for streaming responses."""

    event: str = Field(description="Event type (e.g., 'progress', 'complete', 'error')")
    data: Dict[str, Any] = Field(description="Event data payload")


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = Field(default="healthy", description="Service status")
    version: str = Field(description="API version")

