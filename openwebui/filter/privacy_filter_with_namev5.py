"""
title: Deep Search Filter
author: Alireza Mounesisohi
version: 1.0.0
license: MIT
description: Filter that pauses model streaming when deep search tool is called, allowing the tool to handle its own streaming.
"""

from typing import Any, Dict, Optional

from fastapi.requests import Request
from pydantic import BaseModel


class Filter:
    class Valves(BaseModel):
        """No configuration needed for deep search filter."""
        pass

    def __init__(self) -> None:
        self.valves = self.Valves()
        self.is_deepsearch_called = False

    async def inlet(
        self,
        body: Dict[str, Any],
        __request__: Request,
        __user__: Optional[Dict[str, Any]] = None,
        __event_emitter__: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """
        Check if deep search tool is being called and set flag accordingly.
        """
        # Check if deep search tool is being called
        tool_ids = body.get("tool_ids", [])
        metadata_tool_ids = body.get("metadata", {}).get("tool_ids", [])
        all_tool_ids = list(set(tool_ids + metadata_tool_ids))
        
        # Reset deep search flag at the start of each request
        self.is_deepsearch_called = False
        
        # Check if any tool_id contains deep_search, deepsearch, or researcher (case-insensitive)
        for tool_id in all_tool_ids:
            tool_id_lower = str(tool_id).lower()
            if any(keyword in tool_id_lower for keyword in ["deep_search", "deepsearch", "researcher"]):
                self.is_deepsearch_called = True
                break

        return body

    async def stream(
        self,
        event: dict
    ) -> dict:
        """
        Modify streamed chunks of model output.
        If deep search tool is called, pause streaming by returning empty content.
        """
        # If deep search is called, return event with empty content to pause streaming
        # This allows the deep search tool to handle its own streaming
        if self.is_deepsearch_called:
            updated_event = event.copy()
            if "choices" in updated_event:
                for choice in updated_event.get("choices", []):
                    if "delta" in choice:
                        choice["delta"] = {"content": ""}
            else:
                updated_event["choices"] = [{"index": 0, "delta": {"content": ""}}]
            return updated_event
        
        # Otherwise, return the event as-is
        return event

    async def outlet(
        self, body: Dict[str, Any], __user__: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        return body
