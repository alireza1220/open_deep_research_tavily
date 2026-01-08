#!/usr/bin/env python3
"""
Test file demonstrating how to use API base URLs from configuration instead of .env.

This example shows how to pass apiBaseUrl in the config dictionary when making
requests to the Deep Research API, bypassing the need for environment variables.

Usage:
    # Set the environment variables to enable config-based base URLs and API keys
    export GET_API_BASE_URL_FROM_CONFIG=true
    export GET_API_KEYS_FROM_CONFIG=true
    
    # Run the test
    python integration-test/test_config_base_url.py
"""

import os
from pprint import pprint

import requests

# Set environment variables to enable config-based base URLs and API keys
os.environ["GET_API_BASE_URL_FROM_CONFIG"] = "true"
os.environ["GET_API_KEYS_FROM_CONFIG"] = "true"

API_BASE = os.getenv("FASTAPI_BASE_URL", "http://localhost:8000")


def test_research_with_config_base_url():
    """Test research endpoint using apiBaseUrl from configuration."""
    request_data = {
        "messages": [
            {
                "role": "user",
                "content": "What are the latest developments in quantum computing?"
            }
        ],
        "config": {
            "allow_clarification": False,
            "max_researcher_iterations": 1,
            # API keys from config (requires GET_API_KEYS_FROM_CONFIG=true)
            "apiKeys": {
                "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", "your-openai-api-key-here"),
            },
            # API base URLs from config (requires GET_API_BASE_URL_FROM_CONFIG=true)
            "apiBaseUrl": {
                "OPENAI_API_BASE_URL": os.getenv("OPENAI_API_BASE_URL", "https://api.openai.com/v1"),
            },
            # Model configuration
            "summarization_model": "openai:gpt-4o-mini",
            "research_model": "openai:gpt-4o-mini",
        }
    }
    
    print("\n📤 Request with apiBaseUrl in config:")
    print("=" * 80)
    pprint(request_data)
    print("=" * 80)
    
    print("\n🔧 Configuration Notes:")
    print("- GET_API_BASE_URL_FROM_CONFIG=true (set in this script)")
    print("- GET_API_KEYS_FROM_CONFIG=true (set in this script)")
    print("- apiKeys.OPENAI_API_KEY will be used instead of OPENAI_API_KEY env var")
    print("- apiBaseUrl.OPENAI_API_BASE_URL will be used instead of OPENAI_API_BASE_URL env var")
    print("- This allows using different API keys and base URLs per request without changing environment")
    
    try:
        response = requests.post(
            f"{API_BASE}/v1/research",
            json=request_data,
            timeout=120
        )
        
        if response.status_code == 200:
            data = response.json()
            print("\n📥 Response:")
            print("=" * 80)
            pprint(data)
            print("=" * 80)
            print(f"\n✅ Research endpoint passed (status: {data.get('status', 'unknown')})")
        else:
            print(f"\n❌ Request failed with status {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Could not connect to {API_BASE}")
        print("Make sure the FastAPI server is running.")
    except Exception as e:
        print(f"\n❌ Error: {e}")


def test_get_base_url_function():
    """Test the get_base_url_for_model function directly."""
    from langchain_core.runnables import RunnableConfig
    from open_deep_research.utils import get_base_url_for_model
    
    print("\n🧪 Testing get_base_url_for_model function:")
    print("=" * 80)
    
    # Test with config-based base URL
    config: RunnableConfig = {
        "configurable": {
            "apiBaseUrl": {
                "OPENAI_API_BASE_URL": "https://custom.openai.com/v1",
                "ANTHROPIC_API_BASE_URL": "https://custom.anthropic.com/v1",
            }
        }
    }
    
    os.environ["GET_API_BASE_URL_FROM_CONFIG"] = "true"
    os.environ["GET_API_KEYS_FROM_CONFIG"] = "true"
    
    # Test OpenAI model
    openai_url = get_base_url_for_model("openai:gpt-4o-mini", config)
    print(f"OpenAI base URL: {openai_url}")
    assert openai_url == "https://custom.openai.com/v1", f"Expected custom URL, got {openai_url}"
    
    # Test Anthropic model
    anthropic_url = get_base_url_for_model("anthropic:claude-3-5-sonnet", config)
    print(f"Anthropic base URL: {anthropic_url}")
    assert anthropic_url == "https://custom.anthropic.com/v1", f"Expected custom URL, got {anthropic_url}"
    
    # Test with environment variable fallback
    os.environ["GET_API_BASE_URL_FROM_CONFIG"] = "false"
    os.environ["OPENAI_API_BASE_URL"] = "https://env.openai.com/v1"
    
    env_url = get_base_url_for_model("openai:gpt-4o-mini", config)
    print(f"OpenAI base URL (from env): {env_url}")
    assert env_url == "https://env.openai.com/v1", f"Expected env URL, got {env_url}"
    
    print("\n✅ All function tests passed!")


if __name__ == "__main__":
    print("Testing API Base URL Configuration")
    print("=" * 80)
    
    # Test the function directly
    test_get_base_url_function()
    
    # Test with actual API call (if server is running)
    print("\n" + "=" * 80)
    print("Testing with actual API call:")
    test_research_with_config_base_url()
    
    print("\n" + "=" * 80)
    print("✅ All tests completed!")

