# FastAPI Endpoint Setup Guide

## Overview

The FastAPI endpoint provides a REST API interface to the Deep Research agent. It supports both synchronous and streaming research requests, with optional ngrok tunnel support for public access.

## Prerequisites

1. **Install Dependencies**: Ensure all dependencies are installed:
   ```bash
   uv sync
   ```

2. **Environment Variables**: Set up your `.env` file with required API keys:
   - `OPENAI_API_KEY` (or other model API keys)
   - `TAVILY_API_KEY` (if using Tavily search)
   - Other model-specific API keys as needed

## Starting the Server

### Basic Usage (Local Only)

Start the FastAPI server on the default port (8000):

```bash
python -m open_deep_research.main
```

Or using uvicorn directly:

```bash
uvicorn open_deep_research.api:app --port 8000
```

### With Custom Port

Set the port via environment variable or command-line argument:

```bash
# Using environment variable
PORT=8080 python -m open_deep_research.main

# Using command-line argument
python -m open_deep_research.main --port 8080
```

### With Ngrok Tunnel (Public Access)

To expose the API publicly via ngrok:

```bash
python -m open_deep_research.main --ngrok
```

**Note**: This requires `pyngrok` to be installed. If not installed, you'll see an error message with installation instructions.

The output will show:
```
============================================================
ngrok tunnel created successfully!
Public URL: https://xxxx-xx-xx-xx-xx.ngrok.io
Local URL: http://localhost:8000
============================================================
```

### Development Mode (Auto-reload)

For development with auto-reload:

```bash
python -m open_deep_research.main --reload
```

Or using uvicorn:

```bash
uvicorn open_deep_research.api:app --reload --port 8000
```

## API Endpoints

### Health Check

Check if the API is running:

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "0.0.16"
}
```

### Synchronous Research

Execute a research request and wait for the complete result:

```bash
curl -X POST http://localhost:8000/v1/research \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "Research the latest developments in quantum computing"
      }
    ]
  }'
```

**Response:**
```json
{
  "final_report": "# Research Report: Quantum Computing...",
  "messages": [
    {"role": "user", "content": "Research..."},
    {"role": "assistant", "content": "# Research Report..."}
  ],
  "notes": ["Note 1", "Note 2"],
  "research_brief": "Research question here",
  "status": "completed"
}
```

### Research with Custom Configuration

You can override configuration options in the request:

```bash
curl -X POST http://localhost:8000/v1/research \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "Research AI developments"
      }
    ],
    "config": {
      "research_model": "openai:gpt-4.1",
      "allow_clarification": false,
      "max_researcher_iterations": 4,
      "search_api": "tavily"
    }
  }'
```

**Available Configuration Options:**

- `research_model`: Model for conducting research (e.g., "openai:gpt-4.1")
- `research_model_max_tokens`: Maximum tokens for research model
- `compression_model`: Model for compressing research findings
- `compression_model_max_tokens`: Maximum tokens for compression model
- `final_report_model`: Model for writing final report
- `final_report_model_max_tokens`: Maximum tokens for final report
- `search_api`: Search API to use ("tavily", "openai", "anthropic", "none")
- `allow_clarification`: Whether to ask clarifying questions (boolean)
- `max_researcher_iterations`: Maximum research iterations (1-10)
- `max_concurrent_research_units`: Maximum concurrent research units (1-20)
- `max_react_tool_calls`: Maximum tool calling iterations (1-30)
- `mcp_config`: MCP server configuration (optional)
- `mcp_prompt`: MCP tool instructions (optional)

### Streaming Research

Stream research progress in real-time using Server-Sent Events (SSE):

```bash
curl -X POST http://localhost:8000/v1/research/stream \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "Research quantum computing"
      }
    ]
  }'
```

**Response Format (SSE):**
```
data: {"event": "progress", "data": {"nodes": ["clarify_with_user"], "has_final_report": false}}

data: {"event": "progress", "data": {"nodes": ["write_research_brief"], "has_final_report": false}}

data: {"event": "complete", "data": {"final_report": "...", "messages": [...], "notes": [...], "research_brief": "..."}}

data: {"event": "end", "data": {"message": "Stream completed"}}
```

**Event Types:**
- `progress`: Research is in progress (includes node names)
- `complete`: Research completed (includes full results)
- `end`: Stream ended
- `error`: Error occurred (includes error message)

## Python Client Example

```python
import requests

API_BASE = "http://localhost:8000"

# Health check
response = requests.get(f"{API_BASE}/health")
print(response.json())

# Synchronous research
response = requests.post(
    f"{API_BASE}/v1/research",
    json={
        "messages": [
            {"role": "user", "content": "Research quantum computing"}
        ]
    },
    timeout=300
)
result = response.json()
print(f"Status: {result['status']}")
print(f"Report: {result['final_report'][:200]}...")

# Streaming research
response = requests.post(
    f"{API_BASE}/v1/research/stream",
    json={
        "messages": [
            {"role": "user", "content": "Research AI"}
        ]
    },
    stream=True,
    timeout=600
)

for line in response.iter_lines():
    if line:
        line_str = line.decode('utf-8')
        if line_str.startswith('data: '):
            import json
            event = json.loads(line_str[6:])
            print(f"Event: {event['event']}")
            if event['event'] == 'complete':
                print(f"Report: {event['data']['final_report'][:200]}...")
```

## Integration Testing

Run the integration tests:

```bash
python integration-test/test_fastapi_endpoint.py
```

Or with custom URL:

```bash
FASTAPI_BASE_URL=http://localhost:8000 python integration-test/test_fastapi_endpoint.py
```

## API Documentation

Once the server is running, you can access interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Coexistence with LangGraph Server

The FastAPI server can run alongside the LangGraph server:

- **FastAPI Server**: Port 8000 (default)
- **LangGraph Server**: Port 2024 (default)

Both servers use the same underlying `deep_researcher` graph, so you can use either interface:

```bash
# Terminal 1: Start LangGraph server (for development/testing)
uvx --refresh --from "langgraph-cli[inmem]" --with-editable . --python 3.11 langgraph dev --allow-blocking

# Terminal 2: Start FastAPI server (for production API)
python -m open_deep_research.main
```

## Troubleshooting

### Port Already in Use

If port 8000 is already in use:

```bash
# Use a different port
PORT=8080 python -m open_deep_research.main
```

### Ngrok Not Working

If ngrok fails:

1. Ensure `pyngrok` is installed: `pip install pyngrok`
2. Check if ngrok is authenticated: `ngrok config check`
3. Try without ngrok first to verify the server works

### Research Timeout

Research requests can take several minutes. Increase timeout:

```python
response = requests.post(url, json=data, timeout=600)  # 10 minutes
```

### Import Errors

If you see import errors:

```bash
# Reinstall dependencies
uv sync

# Or install FastAPI dependencies explicitly
pip install fastapi uvicorn[standard] pyngrok
```

## Production Deployment

For production deployment:

1. Use a production ASGI server like `gunicorn` with `uvicorn` workers:
   ```bash
   gunicorn open_deep_research.api:app -w 4 -k uvicorn.workers.UvicornWorker
   ```

2. Set up proper authentication (not included by default)

3. Use environment variables for configuration

4. Set up proper logging and monitoring

5. Consider using a reverse proxy (nginx, Traefik) for SSL termination

## Next Steps

- See [API_USAGE_GUIDE.md](API_USAGE_GUIDE.md) for LangGraph server usage
- See [SETUP_AND_ARCHITECTURE.md](SETUP_AND_ARCHITECTURE.md) for architecture details

