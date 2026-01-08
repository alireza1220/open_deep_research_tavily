#!/usr/bin/env python3
"""Simple test for FastAPI Deep Research streaming endpoint."""

import json
import os
from pprint import pprint

import requests

API_BASE = os.getenv("FASTAPI_BASE_URL", "http://localhost:8000")


def test_stream():
    """Test streaming research endpoint."""
    request_data = {
        "messages": [{"role": "user", "content": "What are the latest developments in metformin for diabetes treatment?"}],
        "config": {
            "allow_clarification": False,
            "max_researcher_iterations": 1,
        }
    }
    
    print("\n📤 Request:")
    pprint(request_data)
    print("\n📡 Streaming response...\n")
    
    response = requests.post(
        f"{API_BASE}/v1/research/stream",
        json=request_data,
        stream=True,
        timeout=300
    )
    
    assert response.status_code == 200
    content_type = response.headers.get("content-type", "")
    assert "text/event-stream" in content_type or "event-stream" in content_type, f"Expected text/event-stream, got {content_type}"
    
    event_count = 0
    progress_events = []
    complete_event = None
    error_event = None
    
    # Parse SSE stream
    for line in response.iter_lines(decode_unicode=True):
        if not line:
            continue
        
        if line.startswith("data: "):
            data_str = line[6:]  # Remove "data: " prefix
            try:
                event_data = json.loads(data_str)
                event_count += 1
                
                # Validate event structure
                assert "event" in event_data, "Event missing 'event' field"
                assert "data" in event_data, "Event missing 'data' field"
                
                event_type = event_data["event"]
                data = event_data["data"]
                
                # Validate EventData structure (all fields should be Optional)
                assert isinstance(data, dict), "Event data should be a dictionary"
                
                # Print event header
                print(f"\n{'='*80}")
                print(f"  [{event_count}] Event Type: {event_type.upper()}")
                print(f"{'='*80}")
                
                # Check that data has EventData fields (at least some should be present)
                if event_type == "progress":
                    progress_events.append(event_data)
                    print(f"  📍 Nodes: {data.get('nodes', []) or 'None'}")
                    print(f"  📊 Has Final Report: {data.get('has_final_report', False)}")
                    print(f"  💬 Progress Message: {data.get('progress_message', 'None') or 'None'}")
                    print(f"  ⏰ Started Time: {data.get('started_time', 'None') or 'None'}")
                    print(f"  🔍 Searches Occurred: {data.get('searches_occurred', 0) or 0}")
                    if data.get("configuration"):
                        print(f"  ⚙️  Configuration: {list(data['configuration'].keys())}")
                    else:
                        print(f"  ⚙️  Configuration: None")
                    
                    # Validate progress event fields
                    if "nodes" in data:
                        assert isinstance(data["nodes"], list) or data["nodes"] is None
                    if "has_final_report" in data:
                        assert isinstance(data["has_final_report"], bool) or data["has_final_report"] is None
                    if "progress_message" in data:
                        assert isinstance(data["progress_message"], str) or data["progress_message"] is None
                    if "started_time" in data:
                        assert isinstance(data["started_time"], str) or data["started_time"] is None
                    if "searches_occurred" in data:
                        assert isinstance(data["searches_occurred"], (int, type(None)))
                    if "configuration" in data:
                        assert isinstance(data["configuration"], dict) or data["configuration"] is None
                
                elif event_type == "complete":
                    complete_event = event_data
                    print(f"  ✅ Complete Event")
                    print(f"\n  📄 Final Report:")
                    final_report = data.get('final_report', '') or ''
                    print(f"     Length: {len(final_report)} chars")
                    if final_report:
                        preview = final_report[:200] + "..." if len(final_report) > 200 else final_report
                        print(f"     Preview: {preview}")
                    
                    final_report_no_cites = data.get('final_report_without_citations', '') or ''
                    if final_report_no_cites:
                        print(f"  📄 Final Report (No Citations):")
                        print(f"     Length: {len(final_report_no_cites)} chars")
                    
                    citations = data.get('citations', []) or []
                    print(f"\n  🔗 Citations: {len(citations)}")
                    if citations:
                        for i, citation in enumerate(citations[:5], 1):  # Show first 5
                            title = citation.get('title', 'No title') or 'No title'
                            link = citation.get('link', '') or ''
                            index = citation.get('index', '') or ''
                            print(f"     [{index}] {title[:50]}: {link[:60]}...")
                        if len(citations) > 5:
                            print(f"     ... and {len(citations) - 5} more")
                    
                    print(f"\n  📊 Statistics:")
                    print(f"     Visited Websites: {data.get('visited_websites', 0) or 0}")
                    print(f"     Searches Occurred: {data.get('searches_occurred', 0) or 0}")
                    print(f"     Duration: {data.get('duration', 0) or 0:.2f}s")
                    
                    print(f"\n  ⏰ Timing:")
                    print(f"     Started: {data.get('started_time', 'None') or 'None'}")
                    print(f"     Ended: {data.get('ended_time', 'None') or 'None'}")
                    
                    messages = data.get('messages', []) or []
                    print(f"\n  💬 Messages: {len(messages)}")
                    if messages:
                        for i, msg in enumerate(messages[:3], 1):  # Show first 3
                            role = msg.get('role', 'unknown')
                            content = msg.get('content', '') or ''
                            content_preview = content[:80] + "..." if len(content) > 80 else content
                            print(f"     [{i}] {role}: {content_preview}")
                        if len(messages) > 3:
                            print(f"     ... and {len(messages) - 3} more")
                    
                    notes = data.get('notes', []) or []
                    print(f"\n  📝 Notes: {len(notes)}")
                    if notes:
                        for i, note in enumerate(notes[:3], 1):  # Show first 3
                            note_preview = note[:80] + "..." if len(note) > 80 else note
                            print(f"     [{i}] {note_preview}")
                        if len(notes) > 3:
                            print(f"     ... and {len(notes) - 3} more")
                    
                    research_brief = data.get('research_brief', '') or ''
                    if research_brief:
                        print(f"\n  📋 Research Brief:")
                        brief_preview = research_brief[:150] + "..." if len(research_brief) > 150 else research_brief
                        print(f"     {brief_preview}")
                    
                    if data.get("configuration"):
                        print(f"\n  ⚙️  Configuration: {list(data['configuration'].keys())}")
                    
                    # Validate complete event fields
                    assert "final_report" in data or data.get("final_report") is None
                    if citations:
                        assert isinstance(citations, list)
                        for citation in citations:
                            assert "link" in citation
                            assert isinstance(citation["link"], str)
                    
                    if "final_report_without_citations" in data:
                        assert isinstance(data["final_report_without_citations"], str) or data["final_report_without_citations"] is None
                    
                    if messages:
                        assert isinstance(messages, list)
                    
                    if notes:
                        assert isinstance(notes, list)
                    
                    if "research_brief" in data:
                        assert isinstance(data["research_brief"], str) or data["research_brief"] is None
                
                elif event_type == "error":
                    error_event = event_data
                    print(f"  ❌ Error Event")
                    print(f"  Error Message: {data.get('error_message', 'Unknown error') or 'Unknown error'}")
                    print(f"  Started Time: {data.get('started_time', 'None') or 'None'}")
                    print(f"  Ended Time: {data.get('ended_time', 'None') or 'None'}")
                    print(f"  Duration: {data.get('duration', 0) or 0:.2f}s")
                    print(f"  Searches Occurred: {data.get('searches_occurred', 0) or 0}")
                    if data.get("configuration"):
                        print(f"  Configuration: {list(data['configuration'].keys())}")
                    
                    # Validate error event fields
                    assert "error_message" in data or data.get("error_message") is None
                    if data.get("error_message"):
                        assert isinstance(data["error_message"], str)
                
                elif event_type == "end":
                    print(f"  🏁 End Event")
                    print(f"  Started Time: {data.get('started_time', 'None') or 'None'}")
                    print(f"  Ended Time: {data.get('ended_time', 'None') or 'None'}")
                    print(f"  Duration: {data.get('duration', 0) or 0:.2f}s")
                    print(f"  Searches Occurred: {data.get('searches_occurred', 0) or 0}")
                    if data.get("configuration"):
                        print(f"  Configuration: {list(data['configuration'].keys())}")
                
                # Print all fields present in data (for debugging)
                print(f"\n  📋 All Fields Present:")
                present_fields = [k for k, v in data.items() if v is not None]
                print(f"     {', '.join(present_fields) if present_fields else 'None'}")
                
            except json.JSONDecodeError as e:
                print(f"  ⚠️  Failed to parse JSON: {e}")
                print(f"     Line: {line[:100]}")
                continue
    
    print(f"\n{'='*80}")
    print(f"📊 SUMMARY")
    print(f"{'='*80}")
    print(f"   Total events: {event_count}")
    print(f"   Progress events: {len(progress_events)}")
    print(f"   Complete event: {'✅' if complete_event else '❌'}")
    print(f"   Error event: {'❌' if error_event else '✅'}")
    
    if complete_event:
        data = complete_event["data"]
        print(f"\n   Final Report: {len(data.get('final_report', '') or '')} chars")
        print(f"   Citations: {len(data.get('citations', []) or [])}")
        print(f"   Visited Websites: {data.get('visited_websites', 0) or 0}")
        print(f"   Searches: {data.get('searches_occurred', 0) or 0}")
        print(f"   Duration: {data.get('duration', 0) or 0:.2f}s")
    
    # Assertions
    assert event_count > 0, "Should receive at least one event"
    assert len(progress_events) > 0, "Should receive at least one progress event"
    assert complete_event is not None or error_event is not None, "Should receive either complete or error event"
    
    if complete_event:
        data = complete_event["data"]
        assert data.get("final_report"), "Complete event should have final_report"
        assert data.get("started_time"), "Complete event should have started_time"
        assert data.get("ended_time"), "Complete event should have ended_time"
        assert data.get("duration") is not None, "Complete event should have duration"
    
    print("\n✅ Stream endpoint test passed!")


if __name__ == "__main__":
    print(f"Testing FastAPI stream endpoint at {API_BASE}")
    test_stream()
    print("\n✅ All stream tests passed!")

