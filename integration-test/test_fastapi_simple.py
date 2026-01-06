#!/usr/bin/env python3
"""Simple test for FastAPI Deep Research endpoints."""

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

def test_research():
    """Test research endpoint with a drug-related query."""
    request_data = {
        "messages": [{"role": "user", "content": "What are the latest developments in metformin for diabetes treatment?"}],
        "config": {
            "allow_clarification": False,
            "max_researcher_iterations": 1,
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
    print(f"\n✅ Research endpoint passed (status: {data['status']})")

if __name__ == "__main__":
    print(f"Testing FastAPI at {API_BASE}\n")
    test_health()
    test_research()
    print("\n✅ All tests passed!")

