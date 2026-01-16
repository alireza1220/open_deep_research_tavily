"""Main LangGraph implementation for the Deep Research agent."""

import asyncio
from typing import Literal

from langchain.chat_models import init_chat_model
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    filter_messages,
    get_buffer_string,
)
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from open_deep_research.configuration import (
    Configuration,
    SearchAPI,
)
from open_deep_research.prompts import (
    clarify_with_user_instructions,
    compress_research_simple_human_message,
    compress_research_system_prompt,
    final_report_generation_prompt,
    lead_researcher_prompt,
    research_system_prompt,
    transform_messages_into_research_topic_prompt,
)
from open_deep_research.state import (
    AgentInputState,
    AgentState,
    ClarifyWithUser,
    ConductResearch,
    ResearchComplete,
    ResearcherOutputState,
    ResearcherState,
    ResearchQuestion,
    SupervisorState,
)
from open_deep_research.utils import (
    anthropic_websearch_called,
    get_all_tools,
    get_api_key_for_model,
    get_base_url_for_model,
    get_config_value,
    get_model_token_limit,
    get_notes_from_tool_calls,
    get_today_str,
    is_token_limit_exceeded,
    openai_websearch_called,
    remove_up_to_last_ai_message,
    think_tool,
)

# Initialize a configurable model that we will use throughout the agent
configurable_model = init_chat_model(
    configurable_fields=("model", "max_tokens", "api_key", "base_url"),
)

async def clarify_with_user(state: AgentState, config: RunnableConfig) -> Command[Literal["write_research_brief", "__end__"]]:
    """Analyze user messages and ask clarifying questions if the research scope is unclear.
    
    This function determines whether the user's request needs clarification before proceeding
    with research. If clarification is disabled or not needed, it proceeds directly to research.
    
    Args:
        state: Current agent state containing user messages
        config: Runtime configuration with model settings and preferences
        
    Returns:
        Command to either end with a clarifying question or proceed to research brief
    """
    # Step 1: Check if clarification is enabled in configuration
    configurable = Configuration.from_runnable_config(config)
    if not configurable.allow_clarification:
        # Skip clarification step and proceed directly to research
        return Command(goto="write_research_brief")
    
    # Step 2: Prepare the model for structured clarification analysis
    messages = state["messages"]
    model_config = {
        "model": configurable.research_model,
        "max_tokens": configurable.research_model_max_tokens,
        "api_key": get_api_key_for_model(configurable.research_model, config),
        "base_url": get_base_url_for_model(configurable.research_model, config),
        "tags": ["langsmith:nostream"]
    }
    
    # Configure model with structured output and retry logic
    clarification_model = (
        configurable_model
        .with_structured_output(ClarifyWithUser)
        .with_retry(stop_after_attempt=configurable.max_structured_output_retries)
        .with_config(model_config)
    )
    
    # Step 3: Analyze whether clarification is needed
    prompt_content = clarify_with_user_instructions.format(
        messages=get_buffer_string(messages), 
        date=get_today_str()
    )
    response = await clarification_model.ainvoke([HumanMessage(content=prompt_content)])
    
    # Step 4: Route based on clarification analysis
    if response.need_clarification:
        # End with clarifying question for user
        return Command(
            goto=END, 
            update={"messages": [AIMessage(content=response.question)]}
        )
    else:
        # Proceed to research with verification message
        return Command(
            goto="write_research_brief", 
            update={"messages": [AIMessage(content=response.verification)]}
        )


async def write_research_brief(state: AgentState, config: RunnableConfig) -> Command[Literal["research_supervisor"]]:
    """Transform user messages into a structured research brief and initialize supervisor.
    
    This function analyzes the user's messages and generates a focused research brief
    that will guide the research supervisor. It also sets up the initial supervisor
    context with appropriate prompts and instructions.
    
    Args:
        state: Current agent state containing user messages
        config: Runtime configuration with model settings
        
    Returns:
        Command to proceed to research supervisor with initialized context
    """
    # Step 1: Set up the research model for structured output
    configurable = Configuration.from_runnable_config(config)
    research_model_config = {
        "model": configurable.research_model,
        "max_tokens": configurable.research_model_max_tokens,
        "api_key": get_api_key_for_model(configurable.research_model, config),
        "base_url": get_base_url_for_model(configurable.research_model, config),
        "tags": ["langsmith:nostream"]
    }
    
    # Configure model for structured research question generation
    research_model = (
        configurable_model
        .with_structured_output(ResearchQuestion)
        .with_retry(stop_after_attempt=configurable.max_structured_output_retries)
        .with_config(research_model_config)
    )
    
    # Step 2: Generate structured research brief from user messages
    prompt_content = transform_messages_into_research_topic_prompt.format(
        messages=get_buffer_string(state.get("messages", [])),
        date=get_today_str()
    )
    response = await research_model.ainvoke([HumanMessage(content=prompt_content)])
    
    # Step 3: Initialize supervisor with research brief and instructions
    supervisor_system_prompt = lead_researcher_prompt.format(
        date=get_today_str(),
        max_concurrent_research_units=configurable.max_concurrent_research_units,
        max_researcher_iterations=configurable.max_researcher_iterations
    )
    
    return Command(
        goto="research_supervisor", 
        update={
            "research_brief": response.research_brief,
            "supervisor_messages": {
                "type": "override",
                "value": [
                    SystemMessage(content=supervisor_system_prompt),
                    HumanMessage(content=response.research_brief)
                ]
            }
        }
    )


async def supervisor(state: SupervisorState, config: RunnableConfig) -> Command[Literal["supervisor_tools"]]:
    """Lead research supervisor that plans research strategy and delegates to researchers.
    
    The supervisor analyzes the research brief and decides how to break down the research
    into manageable tasks. It can use think_tool for strategic planning, ConductResearch
    to delegate tasks to sub-researchers, or ResearchComplete when satisfied with findings.
    
    Args:
        state: Current supervisor state with messages and research context
        config: Runtime configuration with model settings
        
    Returns:
        Command to proceed to supervisor_tools for tool execution
    """
    # Step 1: Configure the supervisor model with available tools
    configurable = Configuration.from_runnable_config(config)
    research_model_config = {
        "model": configurable.research_model,
        "max_tokens": configurable.research_model_max_tokens,
        "api_key": get_api_key_for_model(configurable.research_model, config),
        "base_url": get_base_url_for_model(configurable.research_model, config),
        "tags": ["langsmith:nostream"]
    }
    
    # Available tools: research delegation, completion signaling, and strategic thinking
    lead_researcher_tools = [ConductResearch, ResearchComplete, think_tool]
    
    # Configure model with tools, retry logic, and model settings
    research_model = (
        configurable_model
        .bind_tools(lead_researcher_tools)
        .with_retry(stop_after_attempt=configurable.max_structured_output_retries)
        .with_config(research_model_config)
    )
    
    # Step 2: Generate supervisor response based on current context
    supervisor_messages = state.get("supervisor_messages", [])
    response = await research_model.ainvoke(supervisor_messages)
    
    # Step 3: Update state and proceed to tool execution
    return Command(
        goto="supervisor_tools",
        update={
            "supervisor_messages": [response],
            "research_iterations": state.get("research_iterations", 0) + 1
        }
    )

async def supervisor_tools(state: SupervisorState, config: RunnableConfig) -> Command[Literal["supervisor", "__end__"]]:
    """Execute tools called by the supervisor, including research delegation and strategic thinking.
    
    This function handles three types of supervisor tool calls:
    1. think_tool - Strategic reflection that continues the conversation
    2. ConductResearch - Delegates research tasks to sub-researchers
    3. ResearchComplete - Signals completion of research phase
    
    Args:
        state: Current supervisor state with messages and iteration count
        config: Runtime configuration with research limits and model settings
        
    Returns:
        Command to either continue supervision loop or end research phase
    """
    # Step 1: Extract current state and check exit conditions
    configurable = Configuration.from_runnable_config(config)
    supervisor_messages = state.get("supervisor_messages", [])
    research_iterations = state.get("research_iterations", 0)
    most_recent_message = supervisor_messages[-1]
    
    # Define exit criteria for research phase
    exceeded_allowed_iterations = research_iterations > configurable.max_researcher_iterations
    no_tool_calls = not most_recent_message.tool_calls
    research_complete_tool_call = any(
        tool_call["name"] == "ResearchComplete" 
        for tool_call in most_recent_message.tool_calls
    )
    
    # Exit if any termination condition is met
    if exceeded_allowed_iterations or no_tool_calls or research_complete_tool_call:
        return Command(
            goto=END,
            update={
                "notes": get_notes_from_tool_calls(supervisor_messages),
                "research_brief": state.get("research_brief", "")
            }
        )
    
    # Step 2: Process all tool calls together (both think_tool and ConductResearch)
    all_tool_messages = []
    update_payload = {"supervisor_messages": []}
    
    # Handle think_tool calls (strategic reflection)
    think_tool_calls = [
        tool_call for tool_call in most_recent_message.tool_calls 
        if tool_call["name"] == "think_tool"
    ]
    
    for tool_call in think_tool_calls:
        reflection_content = tool_call["args"]["reflection"]
        all_tool_messages.append(ToolMessage(
            content=f"Reflection recorded: {reflection_content}",
            name="think_tool",
            tool_call_id=tool_call["id"]
        ))
    
    # Handle ConductResearch calls (research delegation)
    conduct_research_calls = [
        tool_call for tool_call in most_recent_message.tool_calls 
        if tool_call["name"] == "ConductResearch"
    ]
    
    if conduct_research_calls:
        try:
            # Limit concurrent research units to prevent resource exhaustion
            allowed_conduct_research_calls = conduct_research_calls[:configurable.max_concurrent_research_units]
            overflow_conduct_research_calls = conduct_research_calls[configurable.max_concurrent_research_units:]
            
            # Execute research tasks in parallel
            research_tasks = [
                researcher_subgraph.ainvoke({
                    "researcher_messages": [
                        HumanMessage(content=tool_call["args"]["research_topic"])
                    ],
                    "research_topic": tool_call["args"]["research_topic"]
                }, config) 
                for tool_call in allowed_conduct_research_calls
            ]
            
            tool_results = await asyncio.gather(*research_tasks)
            
            # Create tool messages with research results
            for observation, tool_call in zip(tool_results, allowed_conduct_research_calls):
                all_tool_messages.append(ToolMessage(
                    content=observation.get("compressed_research", "Error synthesizing research report: Maximum retries exceeded"),
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"]
                ))
            
            # Handle overflow research calls with error messages
            for overflow_call in overflow_conduct_research_calls:
                all_tool_messages.append(ToolMessage(
                    content=f"Error: Did not run this research as you have already exceeded the maximum number of concurrent research units. Please try again with {configurable.max_concurrent_research_units} or fewer research units.",
                    name="ConductResearch",
                    tool_call_id=overflow_call["id"]
                ))
            
            # Aggregate raw notes from all research results
            raw_notes_concat = "\n".join([
                "\n".join(observation.get("raw_notes", [])) 
                for observation in tool_results
            ])
            
            if raw_notes_concat:
                update_payload["raw_notes"] = [raw_notes_concat]
                
        except Exception as e:
            # Handle research execution errors
            if is_token_limit_exceeded(e, configurable.research_model) or True:
                # Token limit exceeded or other error - end research phase
                return Command(
                    goto=END,
                    update={
                        "notes": get_notes_from_tool_calls(supervisor_messages),
                        "research_brief": state.get("research_brief", "")
                    }
                )
    
    # Step 3: Return command with all tool results
    update_payload["supervisor_messages"] = all_tool_messages
    return Command(
        goto="supervisor",
        update=update_payload
    ) 

# Supervisor Subgraph Construction
# Creates the supervisor workflow that manages research delegation and coordination
supervisor_builder = StateGraph(SupervisorState, config_schema=Configuration)

# Add supervisor nodes for research management
supervisor_builder.add_node("supervisor", supervisor)           # Main supervisor logic
supervisor_builder.add_node("supervisor_tools", supervisor_tools)  # Tool execution handler

# Define supervisor workflow edges
supervisor_builder.add_edge(START, "supervisor")  # Entry point to supervisor

# Compile supervisor subgraph for use in main workflow
supervisor_subgraph = supervisor_builder.compile()

async def researcher(state: ResearcherState, config: RunnableConfig) -> Command[Literal["researcher_tools"]]:
    """Individual researcher that conducts focused research on specific topics.
    
    This researcher is given a specific research topic by the supervisor and uses
    available tools (search, think_tool, MCP tools) to gather comprehensive information.
    It can use think_tool for strategic planning between searches.
    
    Args:
        state: Current researcher state with messages and topic context
        config: Runtime configuration with model settings and tool availability
        
    Returns:
        Command to proceed to researcher_tools for tool execution
    """
    print(f"🔍 [researcher] Function called", flush=True)
    # Step 1: Load configuration and validate tool availability
    configurable = Configuration.from_runnable_config(config)
    print(f"🔍 [researcher] Configuration loaded, search_api: {get_config_value(configurable.search_api)}", flush=True)
    researcher_messages = state.get("researcher_messages", [])
    
    # Log search API configuration
    search_api_raw = get_config_value(configurable.search_api)
    print(f"🔍 Backend: Raw search_api config value: {search_api_raw}", flush=True)
    
    # Get all available research tools (search, MCP, think_tool)
    tools = await get_all_tools(config)
    if len(tools) == 0:
        raise ValueError(
            "No tools found to conduct research: Please configure either your "
            "search API or add MCP tools to your configuration."
        )
    
    # Step 2: Configure the researcher model with tools
    research_model_config = {
        "model": configurable.research_model,
        "max_tokens": configurable.research_model_max_tokens,
        "api_key": get_api_key_for_model(configurable.research_model, config),
        "base_url": get_base_url_for_model(configurable.research_model, config),
        "tags": ["langsmith:nostream"]
    }
    
    # Determine search tool name based on configured search API
    search_api = SearchAPI(get_config_value(configurable.search_api))
    print(f"🔍 Backend: Using search API: {search_api.value}", flush=True)
    
    if search_api == SearchAPI.TAVILY:
        search_tool_name = "tavily_search"
    elif search_api == SearchAPI.PERPLEXITY:
        search_tool_name = "perplexity_search"
    elif search_api == SearchAPI.ANTHROPIC:
        search_tool_name = "web_search"
    elif search_api == SearchAPI.OPENAI:
        search_tool_name = "web_search"
    else:
        search_tool_name = "web_search"  # Default fallback
    
    print(f"🔍 Backend: Search tool name for prompt: {search_tool_name}", flush=True)
    
    # Prepare system prompt with MCP context if available
    researcher_prompt = research_system_prompt.format(
        search_tool_name=search_tool_name,
        mcp_prompt=configurable.mcp_prompt or "", 
        date=get_today_str()
    )
    
    # Configure model with tools, retry logic, and settings
    research_model = (
        configurable_model
        .bind_tools(tools)
        .with_retry(stop_after_attempt=configurable.max_structured_output_retries)
        .with_config(research_model_config)
    )
    
    # Step 3: Generate researcher response with system context
    messages = [SystemMessage(content=researcher_prompt)] + researcher_messages
    response = await research_model.ainvoke(messages)
    
    # Step 4: Update state and proceed to tool execution
    return Command(
        goto="researcher_tools",
        update={
            "researcher_messages": [response],
            "tool_call_iterations": state.get("tool_call_iterations", 0) + 1
        }
    )

# Tool Execution Helper Function
async def execute_tool_safely(tool, args, config):
    """Safely execute a tool with error handling.
    
    For search tools (tavily_search, perplexity_search), ToolException will propagate
    to fail the research if the search API fails. For other tools, errors are caught
    and returned as error messages.
    """
    from langchain_core.tools import ToolException
    
    tool_name = getattr(tool, "name", "")
    print(f"🔍 [execute_tool_safely] Executing tool: {tool_name} with args: {str(args)[:200]}", flush=True)
    
    try:
        result = await tool.ainvoke(args, config)
        print(f"✅ [execute_tool_safely] Tool '{tool_name}' completed successfully", flush=True)
        return result
    except ToolException as e:
        # For search tools, let ToolException propagate to fail the research
        # Check if this is a search tool - check both tool.name and metadata
        tool_name = getattr(tool, "name", "")
        metadata_name = tool.metadata.get("name", "") if hasattr(tool, "metadata") and tool.metadata else ""
        is_search_tool = (
            tool_name in ["tavily_search", "perplexity_search", "web_search"] or
            metadata_name in ["tavily_search", "perplexity_search", "web_search"] or
            (hasattr(tool, "metadata") and tool.metadata and tool.metadata.get("type") == "search")
        )
        if is_search_tool:
            print(f"🚨 [execute_tool_safely] Search tool '{tool_name}' failed, failing research", flush=True)
            # Re-raise ToolException for search tools to fail the research
            raise
        # For other tools, return error message
        return f"Error executing tool: {str(e)}"
    except Exception as e:
        # Check if this is a search tool before handling error
        tool_name = getattr(tool, "name", "")
        metadata_name = tool.metadata.get("name", "") if hasattr(tool, "metadata") and tool.metadata else ""
        is_search_tool = (
            tool_name in ["tavily_search", "perplexity_search", "web_search"] or
            metadata_name in ["tavily_search", "perplexity_search", "web_search"] or
            (hasattr(tool, "metadata") and tool.metadata and tool.metadata.get("type") == "search")
        )
        
        if is_search_tool:
            # For search tools, wrap non-ToolException errors as ToolException
            error_msg = f"❌ Error executing search tool '{tool_name}': {str(e)}"
            print(f"🚨 [execute_tool_safely] {error_msg}", flush=True)
            raise ToolException(error_msg) from e
        
        # For non-search tools, return error as string
        print(f"⚠️  [execute_tool_safely] Non-search tool '{tool_name}' error: {str(e)}", flush=True)
        return f"Error executing tool: {str(e)}"


async def researcher_tools(state: ResearcherState, config: RunnableConfig) -> Command[Literal["researcher", "compress_research"]]:
    """Execute tools called by the researcher, including search tools and strategic thinking.
    
    This function handles various types of researcher tool calls:
    1. think_tool - Strategic reflection that continues the research conversation
    2. Search tools (tavily_search, web_search) - Information gathering
    3. MCP tools - External tool integrations
    4. ResearchComplete - Signals completion of individual research task
    
    Args:
        state: Current researcher state with messages and iteration count
        config: Runtime configuration with research limits and tool settings
        
    Returns:
        Command to either continue research loop or proceed to compression
    """
    print(f"🔍 [researcher_tools] Function called", flush=True)
    # Step 1: Extract current state and check early exit conditions
    configurable = Configuration.from_runnable_config(config)
    print(f"🔍 [researcher_tools] Configuration loaded", flush=True)
    researcher_messages = state.get("researcher_messages", [])
    most_recent_message = researcher_messages[-1]
    
    # Early exit if no tool calls were made (including native web search)
    has_tool_calls = bool(most_recent_message.tool_calls)
    has_native_search = (
        openai_websearch_called(most_recent_message) or 
        anthropic_websearch_called(most_recent_message)
    )
    
    print(f"🔍 [researcher_tools] has_tool_calls: {has_tool_calls}, has_native_search: {has_native_search}", flush=True)
    if has_tool_calls:
        print(f"🔍 [researcher_tools] Tool calls found: {[tc.get('name', 'unknown') for tc in most_recent_message.tool_calls]}", flush=True)
    else:
        print(f"🔍 [researcher_tools] No tool calls - checking message type: {type(most_recent_message)}", flush=True)
        if hasattr(most_recent_message, 'content'):
            print(f"🔍 [researcher_tools] Message content preview: {str(most_recent_message.content)[:200]}", flush=True)
    
    if not has_tool_calls and not has_native_search:
        # Check if search API is configured - if so, we should require at least one search
        search_api = SearchAPI(get_config_value(configurable.search_api))
        if search_api != SearchAPI.NONE:
            error_msg = (
                f"Research failed: Search API '{search_api.value}' is configured but no search was performed. "
                f"The research completed without conducting any searches, which is required for deep research."
            )
            print(f"🚨 [researcher_tools] {error_msg}", flush=True)
            from langchain_core.tools import ToolException
            raise ToolException(error_msg)
        return Command(goto="compress_research")
    
    # Step 2: Handle other tool calls (search, MCP tools, etc.)
    tools = await get_all_tools(config)
    tools_by_name = {}
    for tool in tools:
        # Get tool name - check both .name attribute and metadata
        tool_name = None
        if hasattr(tool, "name"):
            tool_name = tool.name
        elif isinstance(tool, dict):
            tool_name = tool.get("name", "web_search")
        else:
            tool_name = getattr(tool, "name", "web_search")
        
        tools_by_name[tool_name] = tool
        # Also add metadata name if different
        if hasattr(tool, "metadata") and tool.metadata:
            metadata_name = tool.metadata.get("name")
            if metadata_name and metadata_name != tool_name:
                tools_by_name[metadata_name] = tool
    
    # Debug: Log available tools
    available_tool_names = list(tools_by_name.keys())
    print(f"🔍 [researcher_tools] Available tools: {available_tool_names}", flush=True)
    
    # Execute all tool calls in parallel
    tool_calls = most_recent_message.tool_calls
    print(f"🔍 [researcher_tools] Tool calls requested: {[tc['name'] for tc in tool_calls]}", flush=True)
    
    # Check if perplexity_search is in available tools
    if "perplexity_search" in available_tool_names:
        print(f"✅ [researcher_tools] perplexity_search tool is available", flush=True)
    else:
        print(f"⚠️  [researcher_tools] perplexity_search tool NOT found in available tools!", flush=True)
    
    print(f"🔍 [researcher_tools] Preparing to execute {len(tool_calls)} tool calls", flush=True)
    
    # Validate all tools exist before executing
    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        if tool_name not in tools_by_name:
            error_msg = f"Tool '{tool_name}' not found in available tools: {list(tools_by_name.keys())}"
            print(f"🚨 [researcher_tools] {error_msg}", flush=True)
            from langchain_core.tools import ToolException
            raise ToolException(error_msg)
        print(f"🔍 [researcher_tools] Found tool '{tool_name}' in tools_by_name, preparing to execute", flush=True)
    
    tool_execution_tasks = [
        execute_tool_safely(tools_by_name[tool_call["name"]], tool_call["args"], config) 
        for tool_call in tool_calls
    ]
    print(f"🔍 [researcher_tools] Created {len(tool_execution_tasks)} execution tasks, starting gather...", flush=True)
    
    # Gather results - check for ToolException from search tools
    from langchain_core.tools import ToolException
    
    def _extract_tool_exception(exc: Exception) -> ToolException | None:
        """Extract ToolException from exception chain, including ExceptionGroup."""
        if isinstance(exc, ToolException):
            return exc
        # Handle ExceptionGroup (Python 3.11+)
        if hasattr(exc, "exceptions"):
            for sub_exc in exc.exceptions:
                if found := _extract_tool_exception(sub_exc):
                    return found
        return None
    
    try:
        # Use return_exceptions=False so ToolException propagates immediately
        observations = await asyncio.gather(*tool_execution_tasks, return_exceptions=False)
    except Exception as e:
        # Check if this is a ToolException from a search tool
        tool_exc = _extract_tool_exception(e)
        if tool_exc:
            # If a search tool fails, fail the entire research IMMEDIATELY
            error_msg = f"Research failed: {str(tool_exc)}"
            print(f"🚨 [researcher_tools] {error_msg}", flush=True)
            # Raise exception to stop graph execution immediately
            # The API endpoint will catch this and send an error event
            raise RuntimeError(error_msg) from tool_exc
        # Re-raise other exceptions
        raise
    
    # Create tool messages from execution results
    tool_outputs = [
        ToolMessage(
            content=observation,
            name=tool_call["name"],
            tool_call_id=tool_call["id"]
        ) 
        for observation, tool_call in zip(observations, tool_calls)
    ]
    
    # CRITICAL VALIDATION: If search API is configured, ensure search tool was actually called
    search_api = SearchAPI(get_config_value(configurable.search_api))
    if search_api in [SearchAPI.TAVILY, SearchAPI.PERPLEXITY]:
        # Check if any of the executed tool calls were search tools
        search_tool_names = ["tavily_search", "perplexity_search"]
        tool_names_called = [tc["name"] for tc in tool_calls]
        search_tool_called = any(name in tool_names_called for name in search_tool_names)
        
        print(f"🔍 [researcher_tools] Search API configured: {search_api.value}", flush=True)
        print(f"🔍 [researcher_tools] Tool names called: {tool_names_called}", flush=True)
        print(f"🔍 [researcher_tools] Search tool called: {search_tool_called}", flush=True)
        
        if not search_tool_called:
            # Build a clearer error message that distinguishes between search tools and other tools
            search_tool_name = 'tavily_search' if search_api == SearchAPI.TAVILY else 'perplexity_search'
            other_tools = [name for name in tool_names_called if name not in ["tavily_search", "perplexity_search"]]
            other_tools_str = ", ".join(other_tools) if other_tools else "none"
            
            # Collect tool responses for debugging - use tool_outputs which have the actual content
            tool_responses = []
            for tool_output, tool_call in zip(tool_outputs, tool_calls):
                tool_name = tool_call["name"]
                # Get content from ToolMessage object
                content = tool_output.content if hasattr(tool_output, 'content') else str(tool_output)
                # Truncate to 500 chars for readability but show more than before
                response_preview = str(content)[:500] if content else "None"
                tool_responses.append(f"{tool_name}: {response_preview}")
            
            tool_responses_str = " | ".join(tool_responses) if tool_responses else "No tool responses"
            
            # Print tool responses separately for better visibility
            print(f"🔍 [researcher_tools] Tool response: {tool_responses_str}", flush=True)
            
            error_msg = (
                f"Research failed: Search API '{search_api.value}' is configured but the required search tool "
                f"({search_tool_name}) was not called. "
                f"Other tools called: {other_tools_str}. "
                f"Tool response: {tool_responses_str}. "
                f"The research must call the search tool ({search_tool_name}) to perform deep research, "
                f"even if other tools like 'think_tool' are also used."
            )
            print(f"🚨 [researcher_tools] {error_msg}", flush=True)
            from langchain_core.tools import ToolException
            raise ToolException(error_msg)
    
    # Step 3: Check late exit conditions (after processing tools)
    exceeded_iterations = state.get("tool_call_iterations", 0) >= configurable.max_react_tool_calls
    research_complete_called = any(
        tool_call["name"] == "ResearchComplete" 
        for tool_call in most_recent_message.tool_calls
    )
    
    if exceeded_iterations or research_complete_called:
        # End research and proceed to compression
        return Command(
            goto="compress_research",
            update={"researcher_messages": tool_outputs}
        )
    
    # Continue research loop with tool results
    return Command(
        goto="researcher",
        update={"researcher_messages": tool_outputs}
    )

async def compress_research(state: ResearcherState, config: RunnableConfig):
    """Compress and synthesize research findings into a concise, structured summary.
    
    This function takes all the research findings, tool outputs, and AI messages from
    a researcher's work and distills them into a clean, comprehensive summary while
    preserving all important information and findings.
    
    Args:
        state: Current researcher state with accumulated research messages
        config: Runtime configuration with compression model settings
        
    Returns:
        Dictionary containing compressed research summary and raw notes
    """
    # Step 1: Configure the compression model
    configurable = Configuration.from_runnable_config(config)
    
    print(f"🔍 [compress_research] Function called - starting validation", flush=True)
    
    # CRITICAL VALIDATION: Check if search tool was called during entire research session
    search_api = SearchAPI(get_config_value(configurable.search_api))
    if search_api in [SearchAPI.TAVILY, SearchAPI.PERPLEXITY]:
        researcher_messages = state.get("researcher_messages", [])
        search_tool_names = ["tavily_search", "perplexity_search"]
        
        # Check all messages for search tool calls
        search_tool_called = False
        all_tool_names_called = []
        for msg in researcher_messages:
            if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    tool_name = tool_call.get("name", "") if isinstance(tool_call, dict) else getattr(tool_call, "name", "")
                    if tool_name:
                        all_tool_names_called.append(tool_name)
                        if tool_name in search_tool_names:
                            search_tool_called = True
                            print(f"✅ [compress_research] Found search tool call: {tool_name}", flush=True)
        
        print(f"🔍 [compress_research] Search API configured: {search_api.value}", flush=True)
        print(f"🔍 [compress_research] All tool names called during research: {all_tool_names_called}", flush=True)
        print(f"🔍 [compress_research] Search tool called: {search_tool_called}", flush=True)
        
        if not search_tool_called:
            error_msg = (
                f"Research failed: Search API '{search_api.value}' is configured but the required search tool "
                f"({'tavily_search' if search_api == SearchAPI.TAVILY else 'perplexity_search'}) was never called during the research session. "
                f"Tools called: {all_tool_names_called}. "
                f"The research must call the search tool to perform deep research."
            )
            print(f"🚨 [compress_research] {error_msg}", flush=True)
            from langchain_core.tools import ToolException
            raise ToolException(error_msg)
    synthesizer_model = configurable_model.with_config({
        "model": configurable.compression_model,
        "max_tokens": configurable.compression_model_max_tokens,
        "api_key": get_api_key_for_model(configurable.compression_model, config),
        "base_url": get_base_url_for_model(configurable.compression_model, config),
        "tags": ["langsmith:nostream"]
    })
    
    # Step 2: Prepare messages for compression
    researcher_messages = state.get("researcher_messages", [])
    
    # Add instruction to switch from research mode to compression mode
    researcher_messages.append(HumanMessage(content=compress_research_simple_human_message))
    
    # Step 3: Attempt compression with retry logic for token limit issues
    synthesis_attempts = 0
    max_attempts = 3
    
    while synthesis_attempts < max_attempts:
        try:
            # Create system prompt focused on compression task
            compression_prompt = compress_research_system_prompt.format(date=get_today_str())
            messages = [SystemMessage(content=compression_prompt)] + researcher_messages
            
            # Execute compression
            response = await synthesizer_model.ainvoke(messages)
            
            # Extract raw notes from all tool and AI messages
            raw_notes_content = "\n".join([
                str(message.content) 
                for message in filter_messages(researcher_messages, include_types=["tool", "ai"])
            ])
            
            # Return successful compression result
            return {
                "compressed_research": str(response.content),
                "raw_notes": [raw_notes_content]
            }
            
        except Exception as e:
            synthesis_attempts += 1
            
            # Handle token limit exceeded by removing older messages
            if is_token_limit_exceeded(e, configurable.research_model):
                researcher_messages = remove_up_to_last_ai_message(researcher_messages)
                continue
            
            # For other errors, continue retrying
            continue
    
    # Step 4: Return error result if all attempts failed
    raw_notes_content = "\n".join([
        str(message.content) 
        for message in filter_messages(researcher_messages, include_types=["tool", "ai"])
    ])
    
    return {
        "compressed_research": "Error synthesizing research report: Maximum retries exceeded",
        "raw_notes": [raw_notes_content]
    }

# Researcher Subgraph Construction
# Creates individual researcher workflow for conducting focused research on specific topics
researcher_builder = StateGraph(
    ResearcherState, 
    output=ResearcherOutputState, 
    config_schema=Configuration
)

# Add researcher nodes for research execution and compression
researcher_builder.add_node("researcher", researcher)                 # Main researcher logic
researcher_builder.add_node("researcher_tools", researcher_tools)     # Tool execution handler
researcher_builder.add_node("compress_research", compress_research)   # Research compression

# Define researcher workflow edges
researcher_builder.add_edge(START, "researcher")           # Entry point to researcher
researcher_builder.add_edge("compress_research", END)      # Exit point after compression

# Compile researcher subgraph for parallel execution by supervisor
researcher_subgraph = researcher_builder.compile()

def extract_urls_from_text(text: str) -> list[str]:
    """Extract all URLs from text using multiple patterns.
    
    Args:
        text: Text to search for URLs
        
    Returns:
        List of unique URLs found in the text
    """
    import re
    urls = set()
    
    if not text:
        return []
    
    # Pattern 1: URLs after "URL: " (from Perplexity/Tavily formatted output)
    # This pattern handles: "URL: https://example.com" or "URL:https://example.com"
    pattern1 = r'URL:\s*(https?://[^\s\n\r<>"\'()]+)'
    matches = re.finditer(pattern1, text, re.IGNORECASE | re.MULTILINE)
    for match in matches:
        url = match.group(1).strip().rstrip('.,;:')
        # Clean up any trailing characters that might have been captured
        url = re.sub(r'[.,;:]+$', '', url)
        if url and len(url) > 10:
            urls.add(url)
    
    # Pattern 2: Markdown links [Title](URL)
    pattern2 = r'\[([^\]]+)\]\((https?://[^)]+)\)'
    matches = re.finditer(pattern2, text)
    for match in matches:
        url = match.group(2).strip().rstrip('.,;:')
        if url and len(url) > 10:
            urls.add(url)
    
    # Pattern 3: Standalone URLs (http:// or https://)
    # More restrictive to avoid false positives
    pattern3 = r'(https?://[^\s\n\r<>"\'()\[\]]+[^\s\n\r<>"\'()\[\].,;:])'
    matches = re.finditer(pattern3, text)
    for match in matches:
        url = match.group(1).strip().rstrip('.,;:')
        # Filter out URLs that are clearly incomplete or malformed
        # Must have a domain (contain a dot) and be reasonably long
        if url and len(url) > 10 and '.' in url and not url.endswith('...'):
            # Exclude common false positives
            if not any(excluded in url.lower() for excluded in ['example.com', 'placeholder', 'test.com']):
                urls.add(url)
    
    # Normalize URLs (remove trailing slashes for deduplication, but preserve original)
    normalized_urls = {}
    for url in urls:
        # Normalize for comparison: lowercase, remove trailing slash
        normalized = url.lower().rstrip('/')
        # Keep the original URL (preferring https over http if both exist)
        if normalized not in normalized_urls:
            normalized_urls[normalized] = url
        elif url.startswith('https://') and not normalized_urls[normalized].startswith('https://'):
            # Prefer https version
            normalized_urls[normalized] = url
    
    return list(normalized_urls.values())


async def final_report_generation(state: AgentState, config: RunnableConfig):
    """Generate the final comprehensive research report with retry logic for token limits.
    
    This function takes all collected research findings and synthesizes them into a 
    well-structured, comprehensive final report using the configured report generation model.
    
    Args:
        state: Agent state containing research findings and context
        config: Runtime configuration with model settings and API keys
        
    Returns:
        Dictionary containing the final report and cleared state
    """
    # Step 1: Extract research findings and prepare state cleanup
    notes = state.get("notes", [])
    cleared_state = {"notes": {"type": "override", "value": []}}
    findings = "\n".join(notes)
    
    # Step 1.5: Extract URLs from findings and messages
    messages_text = get_buffer_string(state.get("messages", []))
    all_text = findings + "\n\n" + messages_text
    
    # Extract URLs separately from findings and messages to debug
    urls_from_findings = extract_urls_from_text(findings)
    urls_from_messages = extract_urls_from_text(messages_text)
    extracted_urls = extract_urls_from_text(all_text)
    
    # Debug: Print URL extraction results
    print(f"🔗 [final_report_generation] URL extraction results:", flush=True)
    print(f"🔗 [final_report_generation]   URLs from findings: {len(urls_from_findings)}", flush=True)
    print(f"🔗 [final_report_generation]   URLs from messages: {len(urls_from_messages)}", flush=True)
    print(f"🔗 [final_report_generation]   Total unique URLs: {len(extracted_urls)}", flush=True)
    if extracted_urls:
        print(f"🔗 [final_report_generation]   Sample URLs (first 5):", flush=True)
        for i, url in enumerate(extracted_urls[:5], 1):
            print(f"🔗 [final_report_generation]     [{i}] {url}", flush=True)
    
    # Format URLs as a numbered list for the prompt
    if extracted_urls:
        available_sources = "\n".join([f"[{i+1}] {url}" for i, url in enumerate(extracted_urls)])
        print(f"🔗 [final_report_generation] Formatted {len(extracted_urls)} URLs for Available Sources section", flush=True)
    else:
        available_sources = "No URLs found in research findings."
        print(f"⚠️  [final_report_generation] WARNING: No URLs found in research findings or messages!", flush=True)
        print(f"⚠️  [final_report_generation] Findings length: {len(findings)} chars", flush=True)
        print(f"⚠️  [final_report_generation] Messages length: {len(messages_text)} chars", flush=True)
    
    # Step 2: Configure the final report generation model
    configurable = Configuration.from_runnable_config(config)
    writer_model_config = {
        "model": configurable.final_report_model,
        "max_tokens": configurable.final_report_model_max_tokens,
        "api_key": get_api_key_for_model(configurable.final_report_model, config),
        "base_url": get_base_url_for_model(configurable.final_report_model, config),
        "tags": ["langsmith:nostream"]
    }
    
    # Step 3: Attempt report generation with token limit retry logic
    max_retries = 3
    current_retry = 0
    findings_token_limit = None
    
    while current_retry <= max_retries:
        try:
            # Create comprehensive prompt with all research context
            final_report_prompt = final_report_generation_prompt.format(
                research_brief=state.get("research_brief", ""),
                messages=messages_text,
                findings=findings,
                available_sources=available_sources,
                date=get_today_str()
            )
            
            # Generate the final report
            final_report = await configurable_model.with_config(writer_model_config).ainvoke([
                HumanMessage(content=final_report_prompt)
            ])
            
            # Return successful report generation
            return {
                "final_report": final_report.content, 
                "messages": [final_report],
                **cleared_state
            }
            
        except Exception as e:
            # Handle token limit exceeded errors with progressive truncation
            if is_token_limit_exceeded(e, configurable.final_report_model):
                current_retry += 1
                
                if current_retry == 1:
                    # First retry: determine initial truncation limit
                    model_token_limit = get_model_token_limit(configurable.final_report_model)
                    if not model_token_limit:
                        return {
                            "final_report": f"Error generating final report: Token limit exceeded, however, we could not determine the model's maximum context length. Please update the model map in deep_researcher/utils.py with this information. {e}",
                            "messages": [AIMessage(content="Report generation failed due to token limits")],
                            **cleared_state
                        }
                    # Use 4x token limit as character approximation for truncation
                    findings_token_limit = model_token_limit * 4
                else:
                    # Subsequent retries: reduce by 10% each time
                    findings_token_limit = int(findings_token_limit * 0.9)
                
                # Truncate findings and retry
                findings = findings[:findings_token_limit]
                continue
            else:
                # Non-token-limit error: return error immediately
                return {
                    "final_report": f"Error generating final report: {e}",
                    "messages": [AIMessage(content="Report generation failed due to an error")],
                    **cleared_state
                }
    
    # Step 4: Return failure result if all retries exhausted
    return {
        "final_report": "Error generating final report: Maximum retries exceeded",
        "messages": [AIMessage(content="Report generation failed after maximum retries")],
        **cleared_state
    }

# Main Deep Researcher Graph Construction
# Creates the complete deep research workflow from user input to final report
deep_researcher_builder = StateGraph(
    AgentState, 
    input=AgentInputState, 
    config_schema=Configuration
)

# Add main workflow nodes for the complete research process
deep_researcher_builder.add_node("clarify_with_user", clarify_with_user)           # User clarification phase
deep_researcher_builder.add_node("write_research_brief", write_research_brief)     # Research planning phase
deep_researcher_builder.add_node("research_supervisor", supervisor_subgraph)       # Research execution phase
deep_researcher_builder.add_node("final_report_generation", final_report_generation)  # Report generation phase

# Define main workflow edges for sequential execution
deep_researcher_builder.add_edge(START, "clarify_with_user")                       # Entry point
deep_researcher_builder.add_edge("research_supervisor", "final_report_generation") # Research to report
deep_researcher_builder.add_edge("final_report_generation", END)                   # Final exit point

# Compile the complete deep researcher workflow
deep_researcher = deep_researcher_builder.compile()