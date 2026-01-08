#!/bin/bash
# Example curl command for testing the streaming research endpoint

API_BASE="${FASTAPI_BASE_URL:-http://localhost:8000}"

curl -X POST "${API_BASE}/v1/research/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "What are the latest developments in metformin for diabetes treatment?"
      }
    ],
    "config": {
      "allow_clarification": false,
      "max_researcher_iterations": 1,
        "apiKeys": {"OPENAI_API_KEY": "sk-_74oWR7B_Iw7MOYzpCuuGA"},
        "apiBaseUrl": {"OPENAI_API_BASE_URL": "http://models.ai.nant.com/v1"},
        "summarization_model": "openai:Llama-4-Maverick",
        "research_model": "openai:Llama-4-Maverick",
        "compression_model": "openai:Llama-4-Maverick",
        "final_report_model": "openai:Llama-4-Maverick"
    }
  }' \
  --no-buffer

