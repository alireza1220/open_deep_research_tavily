"""FastAPI application and endpoints for Deep Research API."""

from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from open_deep_research.configuration import Configuration
from open_deep_research.deep_researcher import deep_researcher
from open_deep_research.schemas import (
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
        try:
            # Convert messages to LangChain format
            langchain_messages = convert_messages_to_langchain(
                [msg.dict() for msg in request.messages]
            )
            
            # Build configuration
            config = build_config(request.config)
            
            # Stream events from the deep researcher graph in updates mode
            # This gives us incremental state updates rather than full state each time
            final_state = {}
            async for event in deep_researcher.astream(
                {"messages": langchain_messages},
                config=config if config else None,
                stream_mode="updates",
            ):
                # LangGraph streams updates as dict with node names as keys
                # Each value is the state update from that node
                event_type = "progress"
                event_data = {}
                
                if isinstance(event, dict):
                    # Update final_state with the latest updates
                    for node_name, node_update in event.items():
                        if isinstance(node_update, dict):
                            final_state.update(node_update)
                    
                    # Check if we have a final report (completion)
                    if "final_report" in final_state:
                        event_type = "complete"
                        event_data = {
                            "final_report": final_state.get("final_report", ""),
                            "messages": convert_langchain_to_dict(
                                final_state.get("messages", [])
                            ),
                            "notes": final_state.get("notes", []),
                            "research_brief": final_state.get("research_brief"),
                        }
                    else:
                        # Progress update - send node information
                        event_data = {
                            "nodes": list(event.keys()),
                            "has_final_report": "final_report" in final_state,
                        }
                
                # Create SSE event
                stream_event = StreamEvent(event=event_type, data=event_data)
                
                # Format as SSE
                yield f"data: {stream_event.model_dump_json()}\n\n"
            
            # Send final completion event with full state
            if final_state.get("final_report"):
                completion_event = StreamEvent(
                    event="complete",
                    data={
                        "final_report": final_state.get("final_report", ""),
                        "messages": convert_langchain_to_dict(
                            final_state.get("messages", [])
                        ),
                        "notes": final_state.get("notes", []),
                        "research_brief": final_state.get("research_brief"),
                    },
                )
            else:
                completion_event = StreamEvent(
                    event="end",
                    data={"message": "Stream completed"},
                )
            yield f"data: {completion_event.model_dump_json()}\n\n"
        
        except Exception as e:
            # Send error event
            error_event = StreamEvent(
                event="error",
                data={"error": str(e)},
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

