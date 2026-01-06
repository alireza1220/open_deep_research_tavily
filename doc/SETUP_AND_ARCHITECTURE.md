# Setup and Architecture Documentation

This document consolidates setup instructions, LangSmith evaluation findings, architecture recommendations, and API access information for the Open Deep Research project.

## Table of Contents

1. [Quick Start & Running the Application](#quick-start--running-the-application)
2. [LangSmith Evaluation](#langsmith-evaluation)
3. [Architecture Recommendations](#architecture-recommendations)
4. [API Server Comparison: LangGraph Server vs FastAPI](#api-server-comparison-langgraph-server-vs-fastapi)
5. [API Access](#api-access)
6. [Troubleshooting](#troubleshooting)

---

## Quick Start & Running the Application

### Prerequisites

- Python 3.11 (as specified in `langgraph.json`)
- `uv` package manager
- API keys for:
  - LLM providers (OpenAI, Anthropic, etc.)
  - Search APIs (Tavily, etc.)
  - Optional: LangSmith (for observability/tracing)

### Installation Steps

1. **Clone the repository and activate a virtual environment:**

```bash
git clone https://github.com/langchain-ai/open_deep_research.git
cd open_deep_research
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. **Install dependencies:**

```bash
uv sync
# or
uv pip install -r pyproject.toml
```

3. **Set up environment variables:**

Create a `.env` file in the project root with your API keys and configuration:

```bash
# If .env.example exists, copy it
cp .env.example .env

# Then edit .env with your configuration
```

Required environment variables typically include:
- `OPENAI_API_KEY` - For OpenAI models
- `TAVILY_API_KEY` - For Tavily search API
- `LANGSMITH_API_KEY` - Optional, for LangSmith tracing
- `LANGSMITH_PROJECT` - Optional, LangSmith project name
- `LANGSMITH_TRACING` - Optional, set to "true" to enable tracing

### Running the Application

**Start the LangGraph server:**

```bash
uvx --refresh --from "langgraph-cli[inmem]" --with-editable . --python 3.11 langgraph dev --allow-blocking
```

This command will:
- Install LangGraph CLI dependencies
- Start the LangGraph server on `http://127.0.0.1:2024`
- Open LangGraph Studio UI in your browser
- Make the API available for requests

### Access Points

Once the server is running, you can access:

- **API Endpoint**: `http://127.0.0.1:2024`
- **API Documentation**: `http://127.0.0.1:2024/docs` (OpenAPI/Swagger docs)
- **Studio UI**: `https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024`

### Configuration

The application supports various configuration options that can be set via:
- Environment variables in `.env` file
- LangGraph Studio UI (Manage Assistants tab)
- API requests with configuration parameters

Key configuration areas:
- **LLM Models**: Summarization, Research, Compression, Final Report models
- **Search API**: Tavily (default), DuckDuckGo, Exa, Azure Search, or MCP servers
- **Research Parameters**: Max iterations, concurrent units, content length limits
- **Clarification**: Enable/disable user clarification prompts

---

## LangSmith Evaluation

### Question 1: Can LangSmith be used for exposing endpoints?

**Answer: Partially, but not as the primary mechanism**

LangSmith is primarily an **observability and tracing platform**, not an endpoint exposure service. Here's what it offers:

#### What LangSmith Provides:

1. **Observability & Tracing**: LangSmith integrates with LangGraph to provide:
   - Request/response tracing
   - Performance monitoring
   - Cost tracking
   - Debugging capabilities
   - Run history and analytics

2. **MCP Endpoint**: LangSmith's Agent Server can expose LangGraph agents via the Model Context Protocol (MCP) at `/mcp`, but this is specialized for exposing agents as tools to MCP-compliant clients, not general REST API exposure.

3. **API for Run Data**: The endpoint you may see (`api.smith.langchain.com/runs/...`) is LangSmith's API for retrieving trace/run data, not for exposing your own application endpoints.

#### What LangSmith Does NOT Provide:

- General REST API endpoint exposure
- API gateway functionality
- Request routing or load balancing
- Primary HTTP server for your application

**Recommendation**: Use **FastAPI** (as planned) for exposing your DeepResearch endpoint. LangSmith can coexist for observability.

### Question 2: Is LangSmith proprietary?

**Answer: Yes, LangSmith is proprietary**

- **LangSmith Service**: The LangSmith SaaS platform and self-hosted server are proprietary software owned by LangChain.
- **SDK**: The `langsmith` Python SDK is open source (MIT license), but this only provides client libraries to interact with the proprietary service.
- **Current Usage**: Your project uses LangSmith for tracing (`LANGSMITH_TRACING=true`) and evaluation, which requires either:
  - SaaS subscription (proprietary cloud service)
  - Self-hosted deployment (still proprietary software)

### Question 3: Is LangSmith recommended for production?

**Answer: Yes, for observability/tracing; No, for endpoint exposure**

#### For Observability/Tracing (Recommended):

✅ **Advantages:**
- Widely used in production for LLM application monitoring
- Provides valuable debugging and performance insights
- Tracks token usage and costs
- Can be self-hosted for data privacy
- Integrates seamlessly with LangGraph
- Useful for evaluation and testing workflows

❌ **Considerations:**
- Proprietary software (vendor lock-in)
- Additional infrastructure/complexity if self-hosting
- SaaS option sends data to LangChain servers

#### For Endpoint Exposure (Not Recommended):

❌ **Not Suitable Because:**
- Not designed as an API gateway or endpoint server
- Use FastAPI or LangGraph Server for actual endpoint exposure
- The MCP endpoint is specialized for agent tool exposure, not general REST APIs

---

## Architecture Recommendations

### Recommended Architecture

**For Production:**
```
┌─────────────────┐
│   FastAPI       │  ← Primary endpoint exposure (REST API)
│   Server        │     - HTTP endpoints
│   (Port 8000)   │     - Authentication
│                 │     - Request/response handling
└────────┬────────┘
         │
         │ Calls internally
         │
         ├─────────────────┐
         │                 │
         ▼                 ▼
┌─────────────────┐  ┌──────────────┐
│  LangGraph      │  │  LangSmith   │  ← Optional observability
│  Deep Researcher│  │  (Optional)  │     - Tracing
│  (Graph)        │  │              │     - Monitoring
└─────────────────┘  └──────────────┘     - Evaluation
```

**For Development:**
```
┌─────────────────┐
│ LangGraph Server│  ← Development/testing
│   (Port 2024)   │     - Quick iteration
│                 │     - Studio UI access
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  LangGraph      │
│  Deep Researcher│
│  (Graph)        │
└─────────────────┘
```

**Note:** FastAPI calls the LangGraph graph directly (not through LangGraph Server). Both can coexist - use LangGraph Server for development and FastAPI for production.

### Component Roles

#### 1. FastAPI (Primary Endpoint Exposure)

**Purpose**: Expose HTTP REST API endpoints for the DeepResearch functionality

**Responsibilities**:
- Handle HTTP requests/responses
- Authentication and authorization
- Request validation (Pydantic schemas)
- Error handling and status codes
- Optional: Streaming responses
- Health check endpoint

**When to Use**:
- Production API exposure
- Integration with external systems (e.g., Open Web UI)
- Standard REST API requirements

#### 2. LangGraph (Agent Execution)

**Purpose**: Execute the DeepResearch agent graph logic

**Responsibilities**:
- Agent workflow orchestration
- State management
- Tool execution
- LLM interactions

**Current Setup**:
- Already configured in `langgraph.json`
- Graph definition: `./src/open_deep_research/deep_researcher.py:deep_researcher`
- Runs on port 2024 via LangGraph Server

#### 3. LangSmith (Optional Observability)

**Purpose**: Provide tracing, monitoring, and evaluation capabilities

**Responsibilities**:
- Request/response tracing
- Performance monitoring
- Cost tracking
- Debugging and analysis
- Evaluation workflows

**Configuration**:
- Enable via `LANGSMITH_TRACING=true` environment variable
- Set `LANGSMITH_PROJECT` for project organization
- Requires `LANGSMITH_API_KEY` for SaaS or self-hosted setup

**When to Use**:
- Development and debugging
- Production monitoring (if acceptable to use proprietary tool)
- Evaluation and testing workflows

### Coexistence Strategy

**FastAPI + LangGraph + LangSmith can all coexist:**

1. **FastAPI** handles HTTP endpoint exposure, authentication, request/response handling
2. **LangGraph** executes the DeepResearch graph logic (can be called from FastAPI)
3. **LangSmith** (optional) provides tracing, monitoring, and evaluation capabilities

**Implementation Approach**:
- FastAPI endpoints call LangGraph graph internally (directly, not through LangGraph Server)
- LangGraph automatically sends traces to LangSmith if enabled
- All components work independently but complement each other
- LangGraph Server remains available for development/testing with Studio UI

**Production vs Development:**

- **Production**: FastAPI server → LangGraph graph → LangSmith (optional)
- **Development**: LangGraph Server → LangGraph graph → LangSmith (optional)
- Both use the same LangGraph graph code, just different entry points

### Configuration Options

#### Making LangSmith Optional

To make LangSmith truly optional:

1. **Environment Variable Control**:
   ```bash
   # Enable LangSmith
   LANGSMITH_TRACING=true
   LANGSMITH_API_KEY=your_key
   LANGSMITH_PROJECT=your_project
   
   # Disable LangSmith (simply don't set these or set LANGSMITH_TRACING=false)
   ```

2. **Code-Level Checks**:
   - Check for LangSmith environment variables before initializing
   - Gracefully handle missing LangSmith configuration
   - Provide fallback behavior when LangSmith is unavailable

3. **Documentation**:
   - Clearly mark LangSmith as optional
   - Provide setup instructions for both with and without LangSmith
   - Explain benefits vs. trade-offs

---

## API Server Comparison: LangGraph Server vs FastAPI

When exposing the DeepResearch API, you have two main options: **LangGraph Server** (current setup) or **FastAPI** (recommended for production). This section compares both approaches to help you choose the right solution for your use case.

### Comparison Table

| Feature | LangGraph Server | FastAPI |
|---------|-----------------|---------|
| **Setup Complexity** | Low (built-in) | Medium (requires implementation) |
| **API Control** | Limited (LangGraph-defined endpoints) | Full control over API design |
| **Customization** | Limited | Extensive |
| **Authentication** | Supabase-based (hardcoded) | Flexible (API keys, JWT, OAuth, etc.) |
| **Error Handling** | Standard LangGraph responses | Custom error handling |
| **Middleware** | Limited | Full middleware support |
| **Rate Limiting** | Not built-in | Easy to add |
| **Logging/Monitoring** | Basic | Full control |
| **OpenAPI Docs** | Auto-generated | Auto-generated + customizable |
| **Streaming** | Built-in SSE | Built-in SSE + WebSocket |
| **Production Ready** | Good for development | Excellent for production |
| **LangGraph Studio UI** | ✅ Integrated | ❌ Not available |
| **Development Speed** | Fast (no code needed) | Requires implementation |

### LangGraph Server (Current: `http://127.0.0.1:2024`)

**Pros:**
- ✅ Already working and tested
- ✅ Zero configuration - just run `langgraph dev`
- ✅ Built-in OpenAPI documentation at `/docs`
- ✅ LangGraph Studio UI integration for debugging
- ✅ Thread/conversation management built-in
- ✅ Excellent for development and testing
- ✅ Automatic graph discovery and endpoint generation

**Cons:**
- ❌ Less control over API design and endpoints
- ❌ Limited customization options
- ❌ Authentication tied to Supabase (harder to change)
- ❌ Not ideal for production REST APIs
- ❌ Less flexible for custom business logic
- ❌ Harder to add custom middleware, rate limiting, etc.

**When to Use:**
- Development and testing
- Quick prototyping
- When you need LangGraph Studio UI
- Internal tools and demos
- When you don't need custom API design

### FastAPI (Recommended for Production)

**Pros:**
- ✅ Full control over API design and endpoints
- ✅ Industry-standard REST API patterns
- ✅ Flexible authentication (API keys, JWT, OAuth, etc.)
- ✅ Better error handling and validation
- ✅ Easy to add middleware, rate limiting, logging
- ✅ Production-ready (async, streaming, health checks)
- ✅ Can call LangGraph graph internally
- ✅ Better for Open Web UI integration
- ✅ Easier to add custom business logic
- ✅ Standard Python web framework (well-documented)

**Cons:**
- ❌ Requires implementation and code maintenance
- ❌ Need to manage LangGraph integration yourself
- ❌ No LangGraph Studio UI integration
- ❌ More setup time initially

**When to Use:**
- Production deployments
- Custom API requirements
- Integration with external systems (Open Web UI, etc.)
- Need custom authentication/authorization
- Need rate limiting, monitoring, custom middleware
- Standard REST API requirements

### Recommendation

**For Production:** Use **FastAPI** as the primary API layer because:
1. **Production Requirements**: Custom endpoints, authentication, error handling
2. **Flexibility**: Easier to add features, rate limiting, monitoring
3. **Standard Patterns**: Aligns with industry-standard REST API practices
4. **Future-Proof**: Ready for Open Web UI and other integrations

**For Development:** Keep **LangGraph Server** available because:
1. **Fast Iteration**: Quick testing without writing API code
2. **Studio UI**: Visual debugging and graph exploration
3. **Simplicity**: No additional code to maintain

### Implementation Strategy

Both approaches can coexist:

```
┌─────────────────────────────────────────────────────────┐
│                    Client Request                        │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│   FastAPI        │    │ LangGraph Server │
│   (Production)    │    │  (Development)   │
│   Port 8000      │    │   Port 2024      │
└────────┬─────────┘    └────────┬──────────┘
         │                       │
         │                       │
         └───────────┬───────────┘
                     │
                     ▼
         ┌─────────────────────┐
         │   LangGraph Graph    │
         │  (Deep Researcher)   │
         └─────────────────────┘
```

**How FastAPI Calls LangGraph:**

FastAPI endpoints can call the LangGraph graph directly (without going through LangGraph Server):

```python
from fastapi import FastAPI
from src.open_deep_research.deep_researcher import deep_researcher

app = FastAPI()

@app.post("/research")
async def research_endpoint(query: str):
    # Call LangGraph graph directly
    result = await deep_researcher.ainvoke({"messages": [{"role": "user", "content": query}]})
    return result
```

**Coexistence Approach:**

1. **Development**: Use LangGraph Server (`langgraph dev`) for quick testing and Studio UI
2. **Production**: Use FastAPI server that calls LangGraph graph internally
3. **Both can run simultaneously** on different ports if needed

**Migration Path:**

1. Start with LangGraph Server (current setup) ✅
2. Implement FastAPI endpoints alongside (calls same graph)
3. Test FastAPI endpoints thoroughly
4. Deploy FastAPI for production
5. Keep LangGraph Server for development/testing

---

## API Access

### LangGraph Server API

**Base URL**: `http://127.0.0.1:2024`

**Endpoints**:
- `/docs` - OpenAPI/Swagger documentation
- `/assistants` - Assistant management
- `/threads` - Thread/conversation management
- `/runs` - Run execution
- `/mcp` - Model Context Protocol endpoint (if enabled)

### Authentication

The current setup uses Supabase-based authentication (see `src/security/auth.py`):

- **Authorization Header**: `Bearer <JWT_TOKEN>`
- **Token Validation**: JWT tokens validated via Supabase
- **Configuration**: Set `SUPABASE_URL` and `SUPABASE_KEY` in `.env`

### Example API Usage

#### Using LangGraph SDK (Python):

```python
from langgraph_sdk import get_client

client = get_client(
    api_url="http://127.0.0.1:2024",
    api_key="your_api_key"  # If authentication required
)

# Create a thread
thread = client.threads.create()

# Stream a run
async for event in client.runs.stream(
    thread_id=thread["thread_id"],
    assistant_id="your_assistant_id",
    input={"messages": [{"role": "user", "content": "Research topic here"}]}
):
    print(event)
```

#### Using HTTP Requests:

```bash
# Get API documentation
curl http://127.0.0.1:2024/docs

# Create a thread
curl -X POST http://127.0.0.1:2024/threads \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"

# Stream a run
curl -X POST http://127.0.0.1:2024/runs/stream \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "thread_id_here",
    "assistant_id": "assistant_id_here",
    "input": {
      "messages": [{"role": "user", "content": "Research topic"}]
    }
  }'
```

### Integration with Open Web UI

Based on the FastAPI endpoint requirements (from todo #2), the goal is to integrate with Open Web UI:

**Requirements**:
- Async/await support for long-running research tasks
- Streaming response capability
- Standard REST API format
- Health check endpoint

**Implementation Notes**:
- Open Web UI will pick up the tool automatically
- Tool will async await the response
- Once response is received, it will stream the response to the user
- FastAPI implementation should support Server-Sent Events (SSE) or WebSocket for streaming

---

## Troubleshooting

### Common Issues

#### 1. Port Already in Use

**Error**: `Address already in use` or port 2024 unavailable

**Solution**:
```bash
# Check what's using port 2024
lsof -i :2024

# Kill the process if needed
kill -9 <PID>

# Or use a different port (if supported by langgraph config)
```

#### 2. Missing Dependencies

**Error**: Import errors or missing packages

**Solution**:
```bash
# Reinstall dependencies
uv sync

# Or reinstall from pyproject.toml
uv pip install -r pyproject.toml
```

#### 3. Environment Variables Not Loaded

**Error**: API key errors or configuration not found

**Solution**:
- Ensure `.env` file exists in project root
- Verify environment variables are set correctly
- Check that `langgraph.json` points to correct env file: `"env": "./.env"`
- Restart the server after changing `.env`

#### 4. LangSmith Connection Issues

**Error**: LangSmith tracing not working

**Solution**:
- Verify `LANGSMITH_API_KEY` is set correctly
- Check `LANGSMITH_PROJECT` is set
- Ensure `LANGSMITH_TRACING=true` if you want tracing enabled
- For self-hosted: Verify LangSmith server URL is correct
- Note: LangSmith is optional - application should work without it

#### 5. Python Version Mismatch

**Error**: Python version errors

**Solution**:
- Ensure Python 3.11 is installed and active
- Check virtual environment is activated
- Verify `langgraph.json` specifies correct Python version: `"python_version": "3.11"`

#### 6. Authentication Errors

**Error**: 401 Unauthorized or authentication failures

**Solution**:
- Verify Supabase credentials (`SUPABASE_URL`, `SUPABASE_KEY`) are set
- Check JWT token is valid and not expired
- Ensure `src/security/auth.py` is properly configured
- For development, you may need to disable auth temporarily

### Getting Help

- Check the [README.md](../README.md) for additional information
- Review LangGraph documentation: https://langchain-ai.github.io/langgraph/
- Check LangSmith documentation: https://docs.smith.langchain.com/
- Review project issues on GitHub

---

## Summary

### Key Takeaways

1. **Running the Application**:
   - Use `uvx --refresh --from "langgraph-cli[inmem]" --with-editable . --python 3.11 langgraph dev --allow-blocking`
   - Access API at `http://127.0.0.1:2024`
   - API docs at `http://127.0.0.1:2024/docs`

2. **LangSmith Evaluation**:
   - ✅ Use for observability/tracing (recommended if acceptable)
   - ❌ Don't use for endpoint exposure (use FastAPI instead)
   - ⚠️ Proprietary software (consider alternatives if needed)

3. **Architecture**:
   - **Production**: FastAPI for HTTP endpoint exposure (recommended)
   - **Development**: LangGraph Server for quick testing and Studio UI
   - LangGraph for agent execution (used by both)
   - LangSmith for optional observability
   - All can coexist harmoniously

4. **API Server Choice**:
   - ✅ **FastAPI**: Recommended for production deployments
   - ✅ **LangGraph Server**: Excellent for development and testing
   - Both call the same LangGraph graph internally
   - Choose based on your use case (see "API Server Comparison" section)

5. **Next Steps**:
   - Implement FastAPI endpoint for production (see todo #2)
   - Keep LangGraph Server for development/testing
   - Make LangSmith optional via environment variables
   - Document FastAPI integration once implemented

---

*Last updated: Based on evaluation and setup instructions as of January 2026*

