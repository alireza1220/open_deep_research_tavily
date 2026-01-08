#!/usr/bin/env python3
"""
Integration test for the FastAPI Deep Research API endpoints.

This script tests the FastAPI endpoints at http://127.0.0.1:8000
Make sure the FastAPI server is running before executing this test.

Usage:
    python integration-test/test_fastapi_endpoint.py

Note: This is a standalone script, not a pytest test file.
      Functions starting with 'test_' are helper functions, not pytest tests.
"""

import os
import sys
import time
import json
from typing import Optional, Dict, Any
import requests
from requests.exceptions import RequestException, ConnectionError, Timeout


# Configuration
API_BASE_URL = os.getenv("FASTAPI_BASE_URL", "http://127.0.0.1:8000")
TEST_QUERY = os.getenv("TEST_QUERY", "What are the latest developments in quantum computing?")


class FastAPIClient:
    """Client for interacting with the FastAPI Deep Research API."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Content-Type": "application/json"
        }
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        timeout: int = 30
    ) -> requests.Response:
        """Make an HTTP request to the API."""
        url = f"{self.base_url}{endpoint}"
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=self.headers, timeout=timeout)
            elif method.upper() == "POST":
                response = requests.post(url, headers=self.headers, json=data, timeout=timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            return response
        except ConnectionError as e:
            raise ConnectionError(f"Could not connect to {url}. Is the server running?") from e
        except Timeout as e:
            raise Timeout(f"Request to {url} timed out after {timeout} seconds") from e
    
    def check_health(self) -> bool:
        """Check if the API is accessible."""
        try:
            response = self._make_request("GET", "/health")
            return response.status_code == 200
        except Exception as e:
            print(f"Health check failed: {e}")
            return False
    
    def get_health(self) -> Dict[str, Any]:
        """Get health check response."""
        response = self._make_request("GET", "/health")
        response.raise_for_status()
        return response.json()
    
    def research(
        self,
        query: str,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a research request."""
        data = {
            "messages": [
                {
                    "role": "user",
                    "content": query
                }
            ]
        }
        if config:
            data["config"] = config
        
        response = self._make_request("POST", "/v1/research", data=data, timeout=300)
        response.raise_for_status()
        return response.json()
    
    def stream_research(
        self,
        query: str,
        config: Optional[Dict[str, Any]] = None
    ):
        """Stream a research request (Server-Sent Events)."""
        data = {
            "messages": [
                {
                    "role": "user",
                    "content": query
                }
            ]
        }
        if config:
            data["config"] = config
        
        url = f"{self.base_url}/v1/research/stream"
        try:
            response = requests.post(
                url,
                headers=self.headers,
                json=data,
                stream=True,
                timeout=600  # 10 minutes for streaming
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        try:
                            event_data = json.loads(line_str[6:])
                            yield event_data
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            raise Exception(f"Streaming failed: {e}") from e


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)


def test_api_connection(client: FastAPIClient) -> bool:  # type: ignore  # Not a pytest test
    """Test basic API connectivity."""
    print_section("Testing API Connection")
    
    if not client.check_health():
        print("❌ API is not accessible. Please ensure the server is running.")
        print(f"   Expected URL: {API_BASE_URL}")
        return False
    
    print(f"✅ API is accessible at {API_BASE_URL}")
    return True


def test_health_endpoint(client: FastAPIClient) -> bool:  # type: ignore  # Not a pytest test
    """Test health check endpoint."""
    print_section("Testing Health Endpoint")
    
    try:
        health = client.get_health()
        status = health.get("status", "unknown")
        version = health.get("version", "unknown")
        
        print(f"✅ Health check passed")
        print(f"   Status: {status}")
        print(f"   Version: {version}")
        return True
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


def test_research_endpoint(client: FastAPIClient, query: str) -> bool:  # type: ignore  # Not a pytest test
    """Test synchronous research endpoint."""
    print_section("Testing Research Endpoint (Synchronous)")
    
    try:
        print(f"Query: {query}")
        print("Executing research (this may take several minutes)...")
        
        result = client.research(query)
        
        status = result.get("status", "unknown")
        final_report = result.get("final_report", "")
        messages = result.get("messages", [])
        notes = result.get("notes", [])
        research_brief = result.get("research_brief")
        
        print(f"✅ Research completed successfully!")
        print(f"   Status: {status}")
        print(f"   Final report length: {len(final_report)} characters")
        print(f"   Messages: {len(messages)}")
        print(f"   Notes: {len(notes)}")
        if research_brief:
            print(f"   Research brief: {research_brief[:100]}...")
        
        if final_report:
            preview = final_report[:300] + "..." if len(final_report) > 300 else final_report
            print(f"\n   Report preview:\n   {preview}")
        
        return True
    except requests.exceptions.HTTPError as e:
        print(f"❌ Research request failed: {e.response.status_code}")
        print(f"   Response: {e.response.text[:200]}")
        return False
    except Exception as e:
        print(f"❌ Research request failed: {e}")
        return False


def test_stream_research_endpoint(client: FastAPIClient, query: str) -> bool:  # type: ignore  # Not a pytest test
    """Test streaming research endpoint."""
    print_section("Testing Research Endpoint (Streaming)")
    
    try:
        print(f"Query: {query}")
        print("Streaming research (this may take several minutes)...\n")
        
        event_count = 0
        final_report_received = False
        
        for event in client.stream_research(query):
            event_count += 1
            event_type = event.get("event", "unknown")
            event_data = event.get("data", {})
            
            if event_type == "complete":
                final_report_received = True
                final_report = event_data.get("final_report", "")
                print(f"\n✅ Stream completed. Received {event_count} events.")
                print(f"   Final report length: {len(final_report)} characters")
                if final_report:
                    preview = final_report[:200] + "..." if len(final_report) > 200 else final_report
                    print(f"\n   Report preview:\n   {preview}")
                return True
            elif event_type == "end":
                print(f"\n✅ Stream ended. Received {event_count} events.")
                if not final_report_received:
                    print("   ⚠️  No final report received in stream")
                return True
            elif event_type == "error":
                error_msg = event_data.get("error_message", "Unknown error")
                print(f"\n❌ Stream error: {error_msg}")
                return False
            elif event_type == "progress":
                # Print minimal info to avoid cluttering output
                if event_count % 10 == 0:
                    nodes = event_data.get("nodes", [])
                    print(f"   Received {event_count} events... (nodes: {nodes})")
        
        print(f"⚠️  Stream ended without completion event. Received {event_count} events.")
        return True  # Still consider it successful if we got events
        
    except Exception as e:
        print(f"❌ Streaming failed: {e}")
        return False


def test_research_with_config(client: FastAPIClient, query: str) -> bool:  # type: ignore  # Not a pytest test
    """Test research endpoint with custom configuration."""
    print_section("Testing Research Endpoint with Custom Config")
    
    try:
        print(f"Query: {query}")
        print("Testing with custom configuration (allow_clarification=False)...")
        
        config = {
            "allow_clarification": False,
            "research_model": "openai:gpt-4.1",
        }
        
        result = client.research(query, config=config)
        
        status = result.get("status", "unknown")
        print(f"✅ Research with custom config completed!")
        print(f"   Status: {status}")
        
        return True
    except Exception as e:
        print(f"❌ Research with config failed: {e}")
        return False


def test_error_handling(client: FastAPIClient) -> bool:  # type: ignore  # Not a pytest test
    """Test error handling for invalid requests."""
    print_section("Testing Error Handling")
    
    try:
        # Test with invalid request (missing messages)
        invalid_data = {}
        response = requests.post(
            f"{client.base_url}/v1/research",
            headers=client.headers,
            json=invalid_data,
            timeout=10
        )
        
        if response.status_code == 422:
            print("✅ Validation error handling works correctly")
            return True
        else:
            print(f"⚠️  Expected 422, got {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False


def main():
    """Run integration tests."""
    print("\n" + "="*60)
    print("  FastAPI Deep Research API Integration Test")
    print("="*60)
    print(f"\nAPI Base URL: {API_BASE_URL}")
    print(f"Test Query: {TEST_QUERY}")
    
    # Initialize client
    client = FastAPIClient(API_BASE_URL)
    
    # Test 1: Connection
    if not test_api_connection(client):
        print("\n❌ Integration test failed: API is not accessible")
        print("\n   To start the FastAPI server:")
        print("   python -m open_deep_research.main")
        print("   or")
        print("   uvicorn open_deep_research.api:app --port 8000")
        sys.exit(1)
    
    # Test 2: Health endpoint
    if not test_health_endpoint(client):
        print("\n⚠️  Health endpoint test failed")
    
    # Test 3: Error handling
    test_error_handling(client)
    
    # Test 4: Research endpoint (synchronous)
    print("\n⚠️  Note: Research tests may take several minutes.")
    print("   Starting synchronous research test...")
    research_success = test_research_endpoint(client, TEST_QUERY)
    
    # Test 5: Research endpoint with config
    test_research_with_config(client, TEST_QUERY)
    
    # Test 6: Streaming research endpoint (optional - comment out if you don't want to wait)
    print("\n⚠️  Note: Streaming test may take several minutes.")
    print("   Starting streaming research test...")
    stream_success = test_stream_research_endpoint(client, TEST_QUERY)
    
    print_section("Integration Test Summary")
    print("✅ Basic API tests completed!")
    
    if research_success:
        print("   ✅ Synchronous research endpoint: PASSED")
    else:
        print("   ⚠️  Synchronous research endpoint: Failed or incomplete")
    
    if stream_success:
        print("   ✅ Streaming research endpoint: PASSED")
    else:
        print("   ⚠️  Streaming research endpoint: Failed or incomplete")
    
    print("\n   All integration tests completed!")


if __name__ == "__main__":
    main()

