# Integration Tests

This directory contains integration tests for the Open Deep Research API.

## Prerequisites

1. **Start the LangGraph Server**: Before running the tests, ensure the server is running:
   ```bash
   uvx --refresh --from "langgraph-cli[inmem]" --with-editable . --python 3.11 langgraph dev --allow-blocking
   ```

2. **Install Dependencies**: The test uses the `requests` library which should already be installed:
   ```bash
   uv sync
   ```

## Running the Tests

### Basic Usage

Run the integration test:

```bash
python integration-test/test_api.py
```

### With Environment Variables

You can customize the test behavior using environment variables:

```bash
# Set custom API URL (default: http://127.0.0.1:2024)
export API_BASE_URL="http://127.0.0.1:2024"

# Set Supabase JWT token (if required)
# Note: This is Supabase authentication, NOT LangSmith
# Get token from your Supabase project after setting SUPABASE_URL and SUPABASE_KEY in .env
export AUTH_TOKEN="your_supabase_jwt_token_here"

# Set custom test query
export TEST_QUERY="What are the latest developments in AI?"

# Run the test
python integration-test/test_api.py
```

## What the Tests Do

The integration test script (`test_api.py`) performs the following tests:

1. **API Connection Test**: Verifies the API is accessible
2. **List Assistants**: Retrieves available assistants
3. **Create Thread**: Creates a new conversation thread
4. **Create Run**: Starts a research run with a test query
5. **Poll Run Status** (optional): Polls for run completion (disabled by default)
6. **Stream Run** (optional): Tests streaming responses (disabled by default)

## Test Output

The test will print:
- ✅ Success indicators for passing tests
- ❌ Error messages for failing tests
- ⚠️  Warnings for non-critical issues
- Status updates during long-running operations

## Example Output

```
============================================================
  Open Deep Research API Integration Test
============================================================

API Base URL: http://127.0.0.1:2024
Authentication: Disabled
Test Query: What are the latest developments in quantum computing?

============================================================
  Testing API Connection
============================================================
✅ API is accessible at http://127.0.0.1:2024

============================================================
  Testing List Assistants
============================================================
✅ Found 1 assistant(s):
   1. Deep Researcher (ID: assistant-123)

============================================================
  Testing Create Thread
============================================================
✅ Created thread: thread-abc123

============================================================
  Testing Create Run
============================================================
Query: What are the latest developments in quantum computing?
✅ Created run: run-xyz789
   Status: pending

============================================================
  Integration Test Summary
============================================================
✅ Basic API tests completed successfully!
   Thread ID: thread-abc123
   Run ID: run-xyz789
```

## Troubleshooting

### Connection Errors

If you see connection errors:
- Ensure the LangGraph server is running
- Check that the API_BASE_URL is correct
- Verify the server is accessible: `curl http://127.0.0.1:2024/docs`

### Authentication Errors

If you get 401 Unauthorized errors:
- **Authentication Type**: The API uses **Supabase JWT authentication** (NOT LangSmith)
- Set `SUPABASE_URL` and `SUPABASE_KEY` in your `.env` file
- Get a JWT token from your Supabase project
- Set the `AUTH_TOKEN` environment variable with the Supabase JWT token
- **Alternative**: Use LangGraph Studio UI (no authentication required)
- **Note**: LangSmith is only used for tracing/observability, not authentication

### Timeout Errors

Research runs can take several minutes. If you enable polling or streaming tests:
- Increase timeout values in the code if needed
- Be patient - research tasks are computationally intensive

## Customizing Tests

You can modify `test_api.py` to:
- Add more test cases
- Test specific endpoints
- Customize timeout values
- Enable/disable polling and streaming tests
- Add assertions for specific response formats

## Continuous Integration

For CI/CD pipelines, you might want to:
- Set shorter timeouts for faster feedback
- Skip long-running tests (polling/streaming)
- Use mock responses for certain endpoints
- Add retry logic for flaky network conditions

