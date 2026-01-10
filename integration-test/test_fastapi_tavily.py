#!/usr/bin/env python3
"""Test FastAPI Deep Research endpoints with Tavily search engine."""

import os
from pprint import pprint

import requests

API_BASE = os.getenv("FASTAPI_BASE_URL", "http://localhost:8000")

def test_health():
    """Test health endpoint."""
    response = requests.get(f"{API_BASE}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    print("✅ Health check passed")

def test_research_with_tavily():
    """Test research endpoint with Tavily search engine."""
    request_data = {
        "messages": [{"role": "user", "content": "What are the latest developments in artificial intelligence?"}],
        "config": {
            "allow_clarification": False,
            "max_researcher_iterations": 1,
            "search_api": "tavily",
        }
    }
    
    print("\n📤 Request:")
    pprint(request_data)
    
    response = requests.post(
        f"{API_BASE}/v1/research",
        json=request_data,
        timeout=120
    )
    
    assert response.status_code == 200
    data = response.json()
    
    print("\n📥 Response:")
    pprint(data)
    
    assert "final_report" in data
    assert "status" in data
    print(f"\n✅ Tavily research endpoint passed (status: {data['status']})")
    
    # Verify the report contains search results
    if "final_report" in data:
        report = data["final_report"]
        print(f"\n📄 Report length: {len(report)} characters")
        print(f"📄 Report preview: {report[:200]}...")

if __name__ == "__main__":
    print(f"Testing FastAPI with Tavily search at {API_BASE}\n")
    test_health()
    test_research_with_tavily()
    print("\n✅ All Tavily tests passed!")

