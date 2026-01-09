"""FastAPI application and endpoints for Deep Research API."""

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage, MessageLikeRepresentation, SystemMessage
from langchain_core.runnables import RunnableConfig

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from open_deep_research.configuration import Configuration
from open_deep_research.deep_researcher import deep_researcher
from open_deep_research.schemas import (
    Citation,
    EventData,
    HealthResponse,
    ResearchRequest,
    ResearchResponse,
    StreamEvent,
)

# Create FastAPI app
app = FastAPI(
    title="Open Deep Research API",
    description="API for conducting deep research using LangGraph agents",
    version="0.0.16",
)


def convert_messages_to_langchain(messages: list[dict[str, str]]) -> list[AIMessage | HumanMessage | SystemMessage]:
    """Convert OpenAI-compatible messages to LangChain messages."""
    langchain_messages = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        
        if role == "user":
            langchain_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            langchain_messages.append(AIMessage(content=content))
        elif role == "system":
            langchain_messages.append(SystemMessage(content=content))
        else:
            # Default to human message for unknown roles
            langchain_messages.append(HumanMessage(content=content))
    
    return langchain_messages


def convert_langchain_to_dict(messages: list[AIMessage | HumanMessage | SystemMessage]) -> list[dict[str, Any]]:
    """Convert LangChain messages to dictionary format."""
    result = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            result.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            result.append({"role": "assistant", "content": msg.content})
        elif isinstance(msg, SystemMessage):
            result.append({"role": "system", "content": msg.content})
        else:
            result.append({"role": "assistant", "content": str(msg.content)})
    return result


def build_config(config_dict: Optional[Dict[str, Any]]) -> RunnableConfig:
    """Build RunnableConfig from request config dictionary."""
    if not config_dict:
        return {}
    
    # Convert config_dict to Configuration object, then to RunnableConfig
    try:
        config_obj = Configuration(**config_dict)
        return {"configurable": config_dict}
    except Exception:
        # If validation fails, still pass it through (let LangGraph handle it)
        return {"configurable": config_dict}


def determine_status(state: Dict[str, Any]) -> str:
    """Determine the status of the research based on state."""
    # Check if final report exists - this indicates completion
    if state.get("final_report"):
        return "completed"
    
    # If no final report but we have messages, check if clarification is needed
    messages = state.get("messages", [])
    if messages:
        last_msg = messages[-1]
        # If last message is AI and no final_report, likely clarification needed
        if isinstance(last_msg, AIMessage):
            # Check if this looks like a clarification question
            content = str(last_msg.content)
            if "?" in content or "clarify" in content.lower():
                return "clarification_needed"
    
    # Default to completed (shouldn't normally reach here)
    return "completed"


def extract_citations_from_report(report: str) -> List[Citation]:
    """Extract citations from final_report by parsing markdown links and Sources section.
    
    Args:
        report: The final report text containing markdown links and/or Sources section
        
    Returns:
        List of Citation objects extracted from the report
    """
    if not report:
        return []
    
    citations = []
    seen_urls = set()
    
    # Pattern 1: Match markdown links: [Title](URL)
    markdown_link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    matches = re.finditer(markdown_link_pattern, report)
    
    for idx, match in enumerate(matches, start=1):
        title = match.group(1).strip()
        url = match.group(2).strip()
        
        # Validate URL
        if not url or not url.startswith(('http://', 'https://')):
            continue
        
        # Skip if we've already seen this URL
        if url in seen_urls:
            continue
            
        seen_urls.add(url)
        citations.append(Citation(
            link=url,
            title=title if title else None,
            index=idx
        ))
    
    # Pattern 2: Match Sources section format: [1] Title: URL or [1] URL
    # Look for Sources section (case-insensitive)
    sources_section_pattern = r'(?:###\s*)?Sources?:?\s*\n(.*?)(?=\n\n|\n#|$)'
    sources_match = re.search(sources_section_pattern, report, re.IGNORECASE | re.DOTALL)
    
    if sources_match:
        sources_text = sources_match.group(1)
        # Pattern for numbered citations: [1] Title: URL
        # This pattern matches: [number] followed by title (everything up to the last colon before URL), then URL
        numbered_citation_pattern = r'\[(\d+)\]\s*(.+?):\s*(https?://[^\s]+)'
        numbered_matches = re.finditer(numbered_citation_pattern, sources_text)
        
        for match in numbered_matches:
            index_num = int(match.group(1))
            title = match.group(2).strip() if match.group(2) else None
            url = match.group(3).strip()
            
            # Validate URL
            if not url or not url.startswith(('http://', 'https://')):
                continue
            
            # Skip if we've already seen this URL
            if url in seen_urls:
                continue
                
            seen_urls.add(url)
            citations.append(Citation(
                link=url,
                title=title,
                index=index_num
            ))
    
    # Sort by index if available, otherwise keep original order
    citations.sort(key=lambda c: c.index if c.index is not None else 9999)
    
    return citations


def strip_citations_from_report(report: str) -> str:
    """Strip markdown links, citation numbers, and Sources section from the final report.
    
    Args:
        report: The final report text
        
    Returns:
        Report with markdown links [Title](URL), citation numbers [1], [2], and Sources section removed
    """
    if not report:
        return ""
    
    # Remove Sources section first (before processing citations)
    # Matches: ### Sources, ## Sources, # Sources, Sources: etc. and everything after until end
    # This pattern handles various formats and removes the entire Sources section
    sources_pattern = r'(?:###?\s*)?Sources?:?\s*\n.*$'
    report = re.sub(sources_pattern, '', report, flags=re.IGNORECASE | re.DOTALL | re.MULTILINE)
    
    # Remove markdown links: [Title](URL) -> Title
    report = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', report)
    
    # Remove citation numbers like [1], [2], etc. that appear standalone
    # This matches [number] that's not part of a markdown link
    report = re.sub(r'\[(\d+)\]', '', report)
    
    # Clean up any trailing whitespace or extra newlines
    report = report.rstrip()
    
    return report


def normalize_notes(notes: Any) -> List[str]:
    """Normalize notes from state, handling both list and override dict formats.
    
    Args:
        notes: Notes from state, can be List[str] or {"type": "override", "value": []}
        
    Returns:
        Normalized list of strings
    """
    if isinstance(notes, dict) and notes.get("type") == "override":
        return notes.get("value", [])
    elif isinstance(notes, list):
        return notes
    else:
        return []


def extract_urls_from_messages(messages: List[MessageLikeRepresentation]) -> Set[str]:
    """Extract URLs from tool call results in messages.
    
    Args:
        messages: List of LangChain messages
        
    Returns:
        Set of unique URLs found in tool call results
    """
    urls = set()
    
    for msg in messages:
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            # Check tool call results for URLs
            for tool_call in msg.tool_calls:
                if isinstance(tool_call, dict):
                    result = tool_call.get('result', '')
                    if isinstance(result, str):
                        # Look for URLs in the result text
                        url_pattern = r'https?://[^\s\)]+'
                        found_urls = re.findall(url_pattern, result)
                        urls.update(found_urls)
    
    return urls


def get_progress_message(node_names: List[str], has_final_report: bool) -> str:
    """Generate a human-readable progress message based on current nodes.
    
    Args:
        node_names: List of active node names
        has_final_report: Whether final report has been generated
        
    Returns:
        Human-readable progress message
    """
    if has_final_report:
        return "All completed - drafting the final version"
    
    node_messages = {
        "clarify_with_user": "Checking whether clarifying questions are needed",
        "write_research_brief": "Completed briefing, now working on supervisor agent",
        "research_supervisor": "Conducting research",
        "researcher": "Gathering information",
        "compress_research": "Compressing research findings",
        "write_final_report": "Writing final report"
    }
    
    for node in node_names:
        if node in node_messages:
            return node_messages[node]
    
    if node_names:
        return f"Processing: {', '.join(node_names)}"
    
    return "Starting research"


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="healthy", version="0.0.16")


@app.post("/v1/research", response_model=ResearchResponse)
async def research(request: ResearchRequest) -> ResearchResponse:
    """Main research endpoint for synchronous research execution."""
    try:
        # Convert messages to LangChain format
        langchain_messages = convert_messages_to_langchain(
            [msg.dict() for msg in request.messages]
        )
        
        # Build configuration
        config = build_config(request.config)
        
        # Invoke the deep researcher graph
        result = await deep_researcher.ainvoke(
            {"messages": langchain_messages},
            config=config if config else None,
        )
        
        # Determine status
        status = determine_status(result)
        
        # Convert messages back to dict format
        response_messages = convert_langchain_to_dict(result.get("messages", []))
        
        # Build response
        return ResearchResponse(
            final_report=result.get("final_report", ""),
            messages=response_messages,
            notes=result.get("notes", []),
            research_brief=result.get("research_brief"),
            status=status,
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Research execution failed: {str(e)}",
        )


@app.post("/v1/research/stream")
async def research_stream(request: ResearchRequest) -> StreamingResponse:
    """Streaming research endpoint using Server-Sent Events (SSE)."""
    
    async def generate_stream():
        """Generate SSE stream events."""
        started_time = datetime.now(timezone.utc).isoformat()
        searches_occurred = 0
        final_state = {}
        config_dict = request.config if request.config else {}
        
        try:
            # Convert messages to LangChain format
            langchain_messages = convert_messages_to_langchain(
                [msg.dict() for msg in request.messages]
            )
            
            # Build configuration
            config = build_config(request.config)
            
            # Stream events from the deep researcher graph in updates mode
            # This gives us incremental state updates rather than full state each time
            async for event in deep_researcher.astream(
                {"messages": langchain_messages},
                config=config if config else None,
                stream_mode="updates",
            ):
                # LangGraph streams updates as dict with node names as keys
                # Each value is the state update from that node
                event_type = "progress"
                
                if isinstance(event, dict):
                    # Update final_state with the latest updates
                    for node_name, node_update in event.items():
                        if isinstance(node_update, dict):
                            final_state.update(node_update)
                            
                            # Track search operations from messages
                            if node_name in ["researcher", "research_supervisor", "supervisor_tools"]:
                                messages = node_update.get("messages", [])
                                for msg in messages:
                                    # Check if message has tool_calls attribute (AIMessage)
                                    if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
                                        for tool_call in msg.tool_calls:
                                            tool_name = tool_call.get("name", "") if isinstance(tool_call, dict) else getattr(tool_call, "name", "")
                                            if tool_name and ("search" in tool_name.lower() or "tavily" in tool_name.lower()):
                                                searches_occurred += 1
                    
                    # Check if we have a final report (completion)
                    has_final_report = "final_report" in final_state
                    node_names = list(event.keys()) if isinstance(event, dict) else []
                    
                    if has_final_report:
                        event_type = "complete"
                        final_report = final_state.get("final_report", "")
                        
                        # Extract citations from final report
                        citations = extract_citations_from_report(final_report)
                        
                        # Generate report without citations
                        final_report_without_citations = strip_citations_from_report(final_report)
                        
                        # Normalize notes
                        notes = normalize_notes(final_state.get("notes", []))
                        
                        # Count visited websites from citations
                        visited_websites = len(citations)
                        
                        # Convert messages
                        messages = convert_langchain_to_dict(
                            final_state.get("messages", [])
                        )
                        
                        # Generate progress message
                        progress_message = get_progress_message(node_names, has_final_report)
                        
                        event_data = EventData(
                            final_report=final_report,
                            final_report_without_citations=final_report_without_citations,
                            citations=citations if citations else None,
                            messages=messages if messages else None,
                            notes=notes if notes else None,
                            research_brief=final_state.get("research_brief"),
                            nodes=node_names if node_names else None,
                            progress_message=progress_message,
                            has_final_report=True,
                            started_time=started_time,
                            visited_websites=visited_websites,
                            searches_occurred=searches_occurred,
                            configuration=config_dict if config_dict else None,
                        )
                    else:
                        # Progress update - send node information
                        progress_message = get_progress_message(node_names, False)
                        
                        # Include research_brief if it's available (after write_research_brief node)
                        research_brief = final_state.get("research_brief")
                        
                        event_data = EventData(
                            nodes=node_names if node_names else None,
                            has_final_report=False,
                            progress_message=progress_message,
                            research_brief=research_brief if research_brief else None,
                            started_time=started_time,
                            searches_occurred=searches_occurred,
                            configuration=config_dict if config_dict else None,
                        )
                
                else:
                    # Fallback for non-dict events
                    event_data = EventData(
                        started_time=started_time,
                        searches_occurred=searches_occurred,
                        configuration=config_dict if config_dict else None,
                    )
                
                # Create SSE event
                stream_event = StreamEvent(event=event_type, data=event_data)
                
                # Format as SSE
                yield f"data: {stream_event.model_dump_json()}\n\n"
            
            # Send final completion event with full state
            ended_time = datetime.now(timezone.utc).isoformat()
            start_dt = datetime.fromisoformat(started_time.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(ended_time.replace('Z', '+00:00'))
            duration = (end_dt - start_dt).total_seconds()
            
            if final_state.get("final_report"):
                final_report = final_state.get("final_report", "")
                citations = extract_citations_from_report(final_report)
                final_report_without_citations = strip_citations_from_report(final_report)
                notes = normalize_notes(final_state.get("notes", []))
                messages = convert_langchain_to_dict(final_state.get("messages", []))
                
                completion_event = StreamEvent(
                    event="complete",
                    data=EventData(
                        final_report=final_report,
                        final_report_without_citations=final_report_without_citations,
                        citations=citations if citations else None,
                        messages=messages if messages else None,
                        notes=notes if notes else None,
                        research_brief=final_state.get("research_brief"),
                        has_final_report=True,
                        started_time=started_time,
                        ended_time=ended_time,
                        duration=duration,
                        visited_websites=len(citations),
                        searches_occurred=searches_occurred,
                        configuration=config_dict if config_dict else None,
                    ),
                )
            else:
                completion_event = StreamEvent(
                    event="end",
                    data=EventData(
                        started_time=started_time,
                        ended_time=ended_time,
                        duration=duration,
                        searches_occurred=searches_occurred,
                        configuration=config_dict if config_dict else None,
                    ),
                )
            yield f"data: {completion_event.model_dump_json()}\n\n"
        
        except Exception as e:
            # Send error event
            ended_time = datetime.now(timezone.utc).isoformat()
            start_dt = datetime.fromisoformat(started_time.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(ended_time.replace('Z', '+00:00'))
            duration = (end_dt - start_dt).total_seconds()
            
            error_event = StreamEvent(
                event="error",
                data=EventData(
                    error_message=str(e),
                    started_time=started_time,
                    ended_time=ended_time,
                    duration=duration,
                    searches_occurred=searches_occurred,
                    configuration=config_dict if config_dict else None,
                ),
            )
            yield f"data: {error_event.model_dump_json()}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@app.exception_handler(422)
async def validation_exception_handler(request: Request, exc: Exception):
    """Handle validation errors."""
    return JSONResponse(
        status_code=422,
        content={"detail": f"Validation error: {str(exc)}"},
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    """Handle internal server errors."""
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
    )

