"""Simple test for FastAPI Deep Research streaming endpoint."""

import json
import os
from pprint import pprint

from dotenv import load_dotenv

load_dotenv()

import requests

API_BASE = os.getenv("FASTAPI_BASE_URL", "http://localhost:8000")
print(f"🌐 API Base URL: {API_BASE}", flush=True)

request_data = {
    "messages": [
        {
            "role": "user",
            "content": "What are the latest developments in metformin for diabetes treatment?",
        }
    ],
    "config": {
        "allow_clarification": False,
        "max_researcher_iterations": 1,
        "apiKeys": {"OPENAI_API_KEY": "sk",
                    "TAVILY_API_KEY": "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"},
        "search_api": "tavily",
        "apiBaseUrl": {"OPENAI_API_BASE_URL": "https://api.openai.com/v1"},
        "summarization_model": "openai:gpt-4o-mini",
        "research_model": "openai:gpt-4o-mini",
        "compression_model": "openai:gpt-4o-mini",
        "final_report_model": "openai:gpt-4o-mini",
    },
}

print("📤 Sending request to streaming endpoint...", flush=True)
response = requests.post(
    f"{API_BASE}/v1/research/stream",
    json=request_data,
    stream=True,
    timeout=300,
)
print(f"📥 Response received, status: {response.status_code}", flush=True)

if not response.ok:
    print(f"❌ Error: {response.status_code}")
    print(response.text)
else:
    print(f"✅ Response OK, status: {response.status_code}")
    print("📡 Starting to stream events...\n")
    
    # Write streaming events to a markdown file
    output_path = "stream_output.md"
    with open(output_path, "w", encoding="utf-8") as md_file:
        md_file.write("# Streaming Research Output\n\n")
        event_index = 0
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            if line.startswith("data: "):
                event_index += 1
                try:
                    event_json = json.loads(line[6:])  # strip "data: "
                    event_type = event_json.get("event", "unknown")
                    print(f"📨 Event {event_index}: {event_type}")
                    
                    # Write each event as a markdown section with a JSON code block
                    md_file.write(f"## Event {event_index}\n\n")
                    md_file.write("```json\n")
                    md_file.write(json.dumps(event_json, indent=2))
                    md_file.write("\n```\n\n")
                except json.JSONDecodeError as e:
                    error_msg = f"**Failed to parse JSON for event {event_index}: {e}**\n\n"
                    print(f"⚠️  {error_msg}")
                    md_file.write(error_msg)
    
    print(f"\n✅ Streaming complete! Wrote {event_index} events to {output_path}")
