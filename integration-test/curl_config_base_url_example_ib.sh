#!/bin/bash
# Example curl command demonstrating how to use API base URLs from configuration
# instead of environment variables.
#
# This example shows how to pass apiBaseUrl and apiKeys in the config dictionary.
# The server must have GET_API_BASE_URL_FROM_CONFIG=true and GET_API_KEYS_FROM_CONFIG=true set to use this.
#
# Usage:
#   # Set environment variables to enable config-based base URLs and API keys (on server side)
#   export GET_API_BASE_URL_FROM_CONFIG=true
#   export GET_API_KEYS_FROM_CONFIG=true
#
#   # Run the curl command
#   bash integration-test/curl_config_base_url_example.sh

API_BASE="${FASTAPI_BASE_URL:-http://localhost:8000}"

curl -X POST "${API_BASE}/v1/research" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "What are the latest developments in quantum computing?"
      }
    ],
    "config": {
      "allow_clarification": false,
      "max_researcher_iterations": 1,
      "apiKeys": {
        "OPENAI_API_KEY": "sk-_74oWR7B_Iw7MOYzpCuuGA"
      },
      "apiBaseUrl": {
        "OPENAI_API_BASE_URL": "http://models.ai.nant.com/v1"
      },
      "summarization_model": "openai:Llama-4-Maverick",
      "research_model": "openai:Llama-4-Maverick",
      "compression_model": "openai:Llama-4-Maverick",
      "final_report_model": "openai:Llama-4-Maverick"
    }
  }'

echo ""

