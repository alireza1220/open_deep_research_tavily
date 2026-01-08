"""Pydantic schemas for FastAPI request and response models."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from open_deep_research.configuration import Configuration, MCPConfig, SearchAPI


class Citation(BaseModel):
    """Citation model for references in research reports."""
    
    link: str = Field(description="URL of the citation")
    title: Optional[str] = Field(default=None, description="Title of the source")
    index: Optional[int] = Field(default=None, description="Citation number/index if applicable")


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


class EventData(BaseModel):
    """Unified event data payload for stream events."""
    
    final_report: Optional[str] = Field(default=None, description="Final research report")
    final_report_without_citations: Optional[str] = Field(
        default=None, 
        description="Final report with markdown links and citation numbers stripped"
    )
    citations: Optional[List[Citation]] = Field(
        default=None, 
        description="List of citations extracted from the final report"
    )
    messages: Optional[List[Dict[str, str]]] = Field(
        default=None, 
        description="List of messages from the research process"
    )
    notes: Optional[List[str]] = Field(
        default=None, 
        description="Research notes and findings"
    )
    research_brief: Optional[str] = Field(
        default=None, 
        description="Research brief/question"
    )
    nodes: Optional[List[str]] = Field(
        default=None, 
        description="Active node names in the research graph"
    )
    progress_message: Optional[str] = Field(
        default=None, 
        description="Human-readable progress description"
    )
    has_final_report: Optional[bool] = Field(
        default=None, 
        description="Whether a final report has been generated"
    )
    started_time: Optional[str] = Field(
        default=None, 
        description="ISO 8601 timestamp when research started"
    )
    ended_time: Optional[str] = Field(
        default=None, 
        description="ISO 8601 timestamp when research ended"
    )
    duration: Optional[float] = Field(
        default=None, 
        description="Duration of research in seconds"
    )
    visited_websites: Optional[int] = Field(
        default=None, 
        description="Count of unique URLs from citations"
    )
    searches_occurred: Optional[int] = Field(
        default=None, 
        description="Count of search operations performed"
    )
    configuration: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Configuration used for this research call"
    )
    error_message: Optional[str] = Field(
        default=None, 
        description="Error message if an error occurred"
    )
    stats: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Additional statistics for this research"
    )


class StreamEvent(BaseModel):
    """Server-Sent Events format for streaming responses."""

    event: str = Field(description="Event type (e.g., 'progress', 'complete', 'error')")
    data: EventData = Field(description="Event data payload")


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = Field(default="healthy", description="Service status")
    version: str = Field(description="API version")

