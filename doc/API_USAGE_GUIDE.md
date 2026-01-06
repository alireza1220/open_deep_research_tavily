# API Usage Guide

## Overview

The Open Deep Research API is served via LangGraph Server at `http://127.0.0.1:2024`. This API provides access to the Deep Researcher agent, which performs comprehensive research on topics and generates detailed reports.

## Starting the Server

Before making API calls, you need to start the LangGraph server:

```bash
# Install dependencies and start the LangGraph server
uvx --refresh --from "langgraph-cli[inmem]" --with-editable . --python 3.11 langgraph dev --allow-blocking
```

Once started, the server will be available at:
- **API Base URL**: `http://127.0.0.1:2024`
- **API Documentation**: `http://127.0.0.1:2024/docs` (OpenAPI/Swagger UI)
- **Studio UI**: `https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024`

## Available Endpoints

### Core Endpoints

- **`GET /docs`** - Interactive API documentation (Swagger UI)
- **`GET /openapi.json`** - OpenAPI specification
- **`POST /assistants`** - Create or manage assistants
- **`GET /assistants`** - List available assistants
- **`GET /assistants/{assistant_id}`** - Get assistant details
- **`POST /threads`** - Create a new conversation thread
- **`GET /threads/{thread_id}`** - Get thread details
- **`POST /runs`** - Execute a run (non-streaming)
- **`POST /runs/stream`** - Execute a run with streaming responses
- **`GET /runs/{run_id}`** - Get run status and results
- **`GET /runs/{run_id}/stream`** - Stream run updates
- **`POST /mcp`** - Model Context Protocol endpoint (if enabled)

## Authentication

The API uses Supabase-based JWT authentication. Include the JWT token in the Authorization header:

```
Authorization: Bearer <JWT_TOKEN>
```

**Note**: Authentication configuration is set via environment variables in `.env`:
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_KEY` - Your Supabase API key

If authentication is not configured, some endpoints may be accessible without authentication (check the `/docs` endpoint for current requirements).

## Making API Calls

### 1. View API Documentation

The easiest way to explore the API is through the interactive Swagger UI:

```bash
# Open in browser
open http://127.0.0.1:2024/docs

# Or use curl
curl http://127.0.0.1:2024/docs
```

### 2. List Available Assistants

First, check what assistants are available:

```bash
curl -X GET http://127.0.0.1:2024/assistants \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

**Response:**
```json
{
  "assistants": [
    {
      "assistant_id": "assistant-id-here",
      "name": "Deep Researcher",
      "config": {...}
    }
  ]
}
```

### 3. Create a Thread

A thread represents a conversation session:

```bash
curl -X POST http://127.0.0.1:2024/threads \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

**Response:**
```json
{
  "thread_id": "thread-abc123",
  "created_at": "2024-01-01T00:00:00Z"
}
```

### 4. Execute a Research Run (Streaming)

Execute a research task with streaming responses:

```bash
curl -X POST http://127.0.0.1:2024/runs/stream \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "thread-abc123",
    "assistant_id": "assistant-id-here",
    "input": {
      "messages": [
        {
          "role": "user",
          "content": "Research the latest developments in quantum computing"
        }
      ]
    }
  }'
```

**Response:** Server-Sent Events (SSE) stream with incremental updates

### 5. Execute a Research Run (Non-Streaming)

For synchronous execution:

```bash
curl -X POST http://127.0.0.1:2024/runs \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "thread-abc123",
    "assistant_id": "assistant-id-here",
    "input": {
      "messages": [
        {
          "role": "user",
          "content": "Research the latest developments in quantum computing"
        }
      ]
    }
  }'
```

**Response:**
```json
{
  "run_id": "run-xyz789",
  "status": "pending",
  "thread_id": "thread-abc123"
}
```

### 6. Check Run Status

Poll for run completion:

```bash
curl -X GET http://127.0.0.1:2024/runs/run-xyz789 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

**Response:**
```json
{
  "run_id": "run-xyz789",
  "status": "success",
  "thread_id": "thread-abc123",
  "output": {
    "messages": [
      {
        "role": "assistant",
        "content": "# Research Report: Quantum Computing Developments\n\n..."
      }
    ]
  }
}
```

## Python SDK Usage

Using the LangGraph SDK provides a more convenient interface:

```python
from langgraph_sdk import get_client

# Initialize client
client = get_client(
    api_url="http://127.0.0.1:2024",
    api_key="your_api_key"  # Optional, if authentication required
)

# Create a thread
thread = client.threads.create()
print(f"Thread ID: {thread['thread_id']}")

# List assistants
assistants = client.assistants.list()
assistant_id = assistants['assistants'][0]['assistant_id']

# Stream a research run
async for event in client.runs.stream(
    thread_id=thread["thread_id"],
    assistant_id=assistant_id,
    input={
        "messages": [
            {
                "role": "user",
                "content": "Research the latest developments in quantum computing"
            }
        ]
    }
):
    print(f"Event: {event}")
    # Process streaming events
    # Event types: "thread", "run", "step", "end"
```

## JavaScript/TypeScript Usage

Using fetch API:

```javascript
const API_BASE = 'http://127.0.0.1:2024';
const AUTH_TOKEN = 'YOUR_TOKEN';

// Create a thread
async function createThread() {
  const response = await fetch(`${API_BASE}/threads`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${AUTH_TOKEN}`,
      'Content-Type': 'application/json'
    }
  });
  return await response.json();
}

// Stream a run
async function streamRun(threadId, assistantId, query) {
  const response = await fetch(`${API_BASE}/runs/stream`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${AUTH_TOKEN}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      thread_id: threadId,
      assistant_id: assistantId,
      input: {
        messages: [
          {
            role: 'user',
            content: query
          }
        ]
      }
    })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');
    
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));
        console.log('Event:', data);
      }
    }
  }
}

// Usage
(async () => {
  const thread = await createThread();
  const assistants = await fetch(`${API_BASE}/assistants`, {
    headers: { 'Authorization': `Bearer ${AUTH_TOKEN}` }
  }).then(r => r.json());
  
  await streamRun(
    thread.thread_id,
    assistants.assistants[0].assistant_id,
    'Research quantum computing'
  );
})();
```

## Python Requests Example

Using the `requests` library:

```python
import requests
import json

API_BASE = "http://127.0.0.1:2024"
AUTH_TOKEN = "YOUR_TOKEN"

headers = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}

# Create a thread
thread_response = requests.post(
    f"{API_BASE}/threads",
    headers=headers
)
thread = thread_response.json()
thread_id = thread["thread_id"]

# List assistants
assistants_response = requests.get(
    f"{API_BASE}/assistants",
    headers=headers
)
assistants = assistants_response.json()
assistant_id = assistants["assistants"][0]["assistant_id"]

# Execute a run
run_response = requests.post(
    f"{API_BASE}/runs",
    headers=headers,
    json={
        "thread_id": thread_id,
        "assistant_id": assistant_id,
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": "Research the latest developments in quantum computing"
                }
            ]
        }
    }
)
run = run_response.json()
print(f"Run ID: {run['run_id']}, Status: {run['status']}")

# Poll for completion
import time
while True:
    status_response = requests.get(
        f"{API_BASE}/runs/{run['run_id']}",
        headers=headers
    )
    status = status_response.json()
    
    if status["status"] in ["success", "error"]:
        print(f"Final status: {status['status']}")
        if status["status"] == "success":
            print(f"Output: {status.get('output', {})}")
        break
    
    time.sleep(2)  # Poll every 2 seconds
```

## Request/Response Format

### Input Format

The `input` field in run requests should contain a `messages` array following the chat message format:

```json
{
  "messages": [
    {
      "role": "user",
      "content": "Your research question here"
    }
  ]
}
```

### Output Format

Successful runs return messages in the thread:

```json
{
  "messages": [
    {
      "role": "user",
      "content": "Research question"
    },
    {
      "role": "assistant",
      "content": "# Research Report\n\n[Detailed research report content]"
    }
  ]
}
```

## Configuration Options

You can configure the Deep Researcher behavior through assistant configuration. Common options include:

- **LLM Models**: Summarization, Research, Compression, Final Report models
- **Search API**: Tavily (default), DuckDuckGo, Exa, Azure Search, or MCP servers
- **Research Parameters**: Max iterations, concurrent units, content length limits
- **Clarification**: Enable/disable user clarification prompts

Configuration can be set:
1. Via environment variables in `.env`
2. Through the LangGraph Studio UI (Manage Assistants tab)
3. Via API requests when creating/updating assistants

## Error Handling

The API returns standard HTTP status codes:

- **200 OK** - Successful request
- **201 Created** - Resource created successfully
- **400 Bad Request** - Invalid request format
- **401 Unauthorized** - Missing or invalid authentication
- **404 Not Found** - Resource not found
- **500 Internal Server Error** - Server error

Error responses follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

## Example: Complete Research Workflow

Here's a complete example workflow:

```python
import requests
import time

API_BASE = "http://127.0.0.1:2024"
AUTH_TOKEN = "YOUR_TOKEN"

headers = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}

# Step 1: Get available assistants
assistants = requests.get(f"{API_BASE}/assistants", headers=headers).json()
assistant_id = assistants["assistants"][0]["assistant_id"]

# Step 2: Create a thread
thread = requests.post(f"{API_BASE}/threads", headers=headers).json()
thread_id = thread["thread_id"]

# Step 3: Start a research run
run = requests.post(
    f"{API_BASE}/runs",
    headers=headers,
    json={
        "thread_id": thread_id,
        "assistant_id": assistant_id,
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": "Research the impact of AI on healthcare"
                }
            ]
        }
    }
).json()

print(f"Started run: {run['run_id']}")

# Step 4: Poll for completion
while True:
    status = requests.get(
        f"{API_BASE}/runs/{run['run_id']}",
        headers=headers
    ).json()
    
    print(f"Status: {status['status']}")
    
    if status["status"] == "success":
        # Step 5: Get the final thread with results
        final_thread = requests.get(
            f"{API_BASE}/threads/{thread_id}",
            headers=headers
        ).json()
        
        # Extract the research report
        for message in final_thread.get("messages", []):
            if message["role"] == "assistant":
                print("\n" + "="*50)
                print("RESEARCH REPORT")
                print("="*50)
                print(message["content"])
        break
    elif status["status"] == "error":
        print(f"Error: {status.get('error', 'Unknown error')}")
        break
    
    time.sleep(2)
```

## Troubleshooting

### Server Not Running

If you get connection errors, ensure the server is running:

```bash
# Check if server is running
curl http://127.0.0.1:2024/docs

# If not, start it
uvx --refresh --from "langgraph-cli[inmem]" --with-editable . --python 3.11 langgraph dev --allow-blocking
```

### Port Already in Use

If port 2024 is already in use:

```bash
# Check what's using the port
lsof -i :2024

# Kill the process if needed
kill -9 <PID>
```

### Authentication Errors

If you get 401 Unauthorized errors:

1. Check that your `.env` file has `SUPABASE_URL` and `SUPABASE_KEY` set
2. Verify your JWT token is valid
3. Check the `/docs` endpoint to see if authentication is required for your endpoint

### Long-Running Requests

Research tasks can take several minutes. For long-running requests:

- Use the streaming endpoint (`/runs/stream`) to get incremental updates
- Set appropriate timeouts in your HTTP client
- Consider using async/await patterns for better resource management

## Additional Resources

- **API Documentation**: Visit `http://127.0.0.1:2024/docs` for interactive API exploration
- **LangGraph Documentation**: https://langchain-ai.github.io/langgraph/
- **Project README**: See `README.md` for setup and configuration details
- **Architecture Documentation**: See `doc/SETUP_AND_ARCHITECTURE.md` for system architecture

