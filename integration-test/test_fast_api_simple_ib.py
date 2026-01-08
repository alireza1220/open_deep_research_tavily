"""Simple test for FastAPI Deep Research streaming endpoint."""

import json
import os
from pprint import pprint

from dotenv import load_dotenv

load_dotenv()

import requests

API_BASE = os.getenv("FASTAPI_BASE_URL", "http://localhost:8000")
print(API_BASE)

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
        "apiKeys": {"OPENAI_API_KEY": "sk-_74oWR7B_Iw7MOYzpCuuGA"},
        "apiBaseUrl": {"OPENAI_API_BASE_URL": "http://models.ai.nant.com/v1"},
        "summarization_model": "openai:Llama-4-Maverick",
        "research_model": "openai:Llama-4-Maverick",
        "compression_model": "openai:Llama-4-Maverick",
        "final_report_model": "openai:Llama-4-Maverick",
    },
}

response = requests.post(
    f"{API_BASE}/v1/research/stream",
    json=request_data,
    stream=True,
    timeout=300,
)

if not response.ok:
    print(f"Error: {response.status_code}")
    print(response.text)
else:
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
                    # Write each event as a markdown section with a JSON code block
                    md_file.write(f"## Event {event_index}\n\n")
                    md_file.write("```json\n")
                    md_file.write(json.dumps(event_json, indent=2))
                    md_file.write("\n```\n\n")
                except json.JSONDecodeError as e:
                    md_file.write(
                        f"**Failed to parse JSON for event {event_index}: {e}**\n\n"
                    )
