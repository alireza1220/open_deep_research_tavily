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
        Reset deep search flag at the start of each request.
        Tool call detection happens in the stream method.
        """
        print("=" * 80, flush=True)
        print("🔍 FILTER INLET: Called", flush=True)
        print(f"🔍 FILTER INLET: Previous flag state: {self.is_deepsearch_called}", flush=True)
        
        # Reset deep search flag at the start of each request
        self.is_deepsearch_called = False
        print(f"🔍 FILTER INLET: Reset flag to: {self.is_deepsearch_called}", flush=True)
        
        # Log body structure for debugging
        print(f"🔍 FILTER INLET: Body keys: {list(body.keys()) if isinstance(body, dict) else 'NOT A DICT'}", flush=True)
        if isinstance(body, dict):
            tool_ids = body.get("tool_ids")
            print(f"🔍 FILTER INLET: tool_ids in body: {tool_ids}", flush=True)
            if "metadata" in body:
                metadata_tool_ids = body.get("metadata", {}).get("tool_ids")
                print(f"🔍 FILTER INLET: metadata.tool_ids: {metadata_tool_ids}", flush=True)
            
            # Check messages for tool calls from assistant
            messages = body.get("messages", [])
            print(f"🔍 FILTER INLET: Number of messages: {len(messages)}", flush=True)
            for msg_idx, msg in enumerate(messages):
                print(f"🔍 FILTER INLET: Message {msg_idx}: role={msg.get('role') if isinstance(msg, dict) else 'N/A'}", flush=True)
                if isinstance(msg, dict) and msg.get("role") == "assistant":
                    # Check for tool_calls in assistant message
                    tool_calls = msg.get("tool_calls")
                    print(f"🔍 FILTER INLET: Assistant message tool_calls: {tool_calls}", flush=True)
                    if tool_calls and isinstance(tool_calls, list):
                        print(f"🔍 FILTER INLET: Found {len(tool_calls)} tool calls in assistant message", flush=True)
                        for tc_idx, tc in enumerate(tool_calls):
                            if isinstance(tc, dict):
                                function_obj = tc.get("function", {})
                                tool_name = function_obj.get("name", "") if isinstance(function_obj, dict) else tc.get("name", "")
                                print(f"🔍 FILTER INLET: Tool call {tc_idx} name: '{tool_name}'", flush=True)
                                if tool_name:
                                    tool_name_lower = str(tool_name).lower()
                                    if any(keyword in tool_name_lower for keyword in ["deep_search", "deepsearch", "researcher"]):
                                        print(f"🔍 FILTER INLET: ✅ MATCH FOUND in messages! Setting flag to True", flush=True)
                                        self.is_deepsearch_called = True
                                        break
        
        print("=" * 80, flush=True)

        return body

    async def stream(
        self,
        event: dict
    ) -> dict:
        """
        Modify streamed chunks of model output.
        Detects actual tool calls in stream events and pauses streaming when deep search tool is called.
        """
        print("-" * 80, flush=True)
        print("🔍 FILTER STREAM: Called", flush=True)
        print(f"🔍 FILTER STREAM: Current flag state: {self.is_deepsearch_called}", flush=True)
        print(f"🔍 FILTER STREAM: Event type: {type(event)}", flush=True)
        print(f"🔍 FILTER STREAM: Event keys: {list(event.keys()) if isinstance(event, dict) else 'NOT A DICT'}", flush=True)
        
        # Log full event structure (truncated if too large)
        event_str = str(event)
        if len(event_str) > 500:
            print(f"🔍 FILTER STREAM: Event (truncated): {event_str[:500]}...", flush=True)
        else:
            print(f"🔍 FILTER STREAM: Event: {event_str}", flush=True)
        
        # Check for tool calls in stream events
        if not self.is_deepsearch_called and "choices" in event:
            print("🔍 FILTER STREAM: Checking choices for tool calls...", flush=True)
            choices = event.get("choices", [])
            print(f"🔍 FILTER STREAM: Number of choices: {len(choices)}", flush=True)
            
            for idx, choice in enumerate(choices):
                print(f"🔍 FILTER STREAM: Processing choice {idx}", flush=True)
                print(f"🔍 FILTER STREAM: Choice keys: {list(choice.keys()) if isinstance(choice, dict) else 'NOT A DICT'}", flush=True)
                print(f"🔍 FILTER STREAM: Full choice object: {choice}", flush=True)
                
                # Check finish_reason first - if it's "tool_calls", a tool was called
                finish_reason = choice.get("finish_reason")
                print(f"🔍 FILTER STREAM: finish_reason: {finish_reason}", flush=True)
                if finish_reason == "tool_calls":
                    print("🔍 FILTER STREAM: ⚠️ finish_reason is 'tool_calls' - tool was called!", flush=True)
                    # If finish_reason is tool_calls, check if we can identify which tool
                    # But even if we can't identify, we should pause if tool_ids contains deep_search
                    # This will be handled by checking tool_calls below
                
                # Check for tool_calls at choice level (not in delta)
                choice_tool_calls = choice.get("tool_calls")
                print(f"🔍 FILTER STREAM: tool_calls at choice level: {choice_tool_calls}", flush=True)
                if choice_tool_calls and isinstance(choice_tool_calls, list):
                    print(f"🔍 FILTER STREAM: Found tool_calls at choice level with {len(choice_tool_calls)} items", flush=True)
                    for tool_idx, tool_call in enumerate(choice_tool_calls):
                        print(f"🔍 FILTER STREAM: Checking choice-level tool_call {tool_idx}: {tool_call}", flush=True)
                        if isinstance(tool_call, dict):
                            function_obj = tool_call.get("function", {})
                            tool_name = function_obj.get("name", "") if isinstance(function_obj, dict) else tool_call.get("name", "")
                            print(f"🔍 FILTER STREAM: Choice-level tool_name: '{tool_name}'", flush=True)
                            if tool_name:
                                tool_name_lower = str(tool_name).lower()
                                if any(keyword in tool_name_lower for keyword in ["deep_search", "deepsearch", "researcher"]):
                                    print(f"🔍 FILTER STREAM: ✅ MATCH FOUND (choice-level)! Setting flag to True", flush=True)
                                    self.is_deepsearch_called = True
                                    break
                
                delta = choice.get("delta", {})
                print(f"🔍 FILTER STREAM: Delta keys: {list(delta.keys()) if isinstance(delta, dict) else 'NOT A DICT'}", flush=True)
                print(f"🔍 FILTER STREAM: Delta content: {delta}", flush=True)
                
                # Check for tool_calls array in delta (modern format)
                tool_calls = delta.get("tool_calls")
                print(f"🔍 FILTER STREAM: tool_calls in delta: {tool_calls}", flush=True)
                if tool_calls and isinstance(tool_calls, list):
                    print(f"🔍 FILTER STREAM: Found tool_calls array with {len(tool_calls)} items", flush=True)
                    for tool_idx, tool_call in enumerate(tool_calls):
                        print(f"🔍 FILTER STREAM: Checking tool_call {tool_idx}: {tool_call}", flush=True)
                        if isinstance(tool_call, dict):
                            # Check tool call name or function name
                            function_obj = tool_call.get("function", {})
                            print(f"🔍 FILTER STREAM: function object: {function_obj}", flush=True)
                            tool_name = function_obj.get("name", "") if isinstance(function_obj, dict) else tool_call.get("name", "")
                            print(f"🔍 FILTER STREAM: Extracted tool_name: '{tool_name}'", flush=True)
                            if tool_name:
                                tool_name_lower = str(tool_name).lower()
                                print(f"🔍 FILTER STREAM: Checking tool_name '{tool_name_lower}' against keywords", flush=True)
                                if any(keyword in tool_name_lower for keyword in ["deep_search", "deepsearch", "researcher"]):
                                    print(f"🔍 FILTER STREAM: ✅ MATCH FOUND! Setting flag to True", flush=True)
                                    self.is_deepsearch_called = True
                                    break
                
                # Check for function field (legacy format)
                function = delta.get("function")
                print(f"🔍 FILTER STREAM: function in delta: {function}", flush=True)
                if function and isinstance(function, dict):
                    function_name = function.get("name", "")
                    print(f"🔍 FILTER STREAM: Legacy function name: '{function_name}'", flush=True)
                    if function_name:
                        function_name_lower = str(function_name).lower()
                        print(f"🔍 FILTER STREAM: Checking function_name '{function_name_lower}' against keywords", flush=True)
                        if any(keyword in function_name_lower for keyword in ["deep_search", "deepsearch", "researcher"]):
                            print(f"🔍 FILTER STREAM: ✅ MATCH FOUND (legacy)! Setting flag to True", flush=True)
                            self.is_deepsearch_called = True
                            break
                
                # Check for tool_call field (alternative format)
                tool_call = delta.get("tool_call")
                print(f"🔍 FILTER STREAM: tool_call in delta: {tool_call}", flush=True)
                if tool_call and isinstance(tool_call, dict):
                    tool_name = tool_call.get("name", "") or (tool_call.get("function", {}).get("name", "") if isinstance(tool_call.get("function"), dict) else "")
                    print(f"🔍 FILTER STREAM: Alternative tool_call name: '{tool_name}'", flush=True)
                    if tool_name:
                        tool_name_lower = str(tool_name).lower()
                        print(f"🔍 FILTER STREAM: Checking alternative tool_name '{tool_name_lower}' against keywords", flush=True)
                        if any(keyword in tool_name_lower for keyword in ["deep_search", "deepsearch", "researcher"]):
                            print(f"🔍 FILTER STREAM: ✅ MATCH FOUND (alternative)! Setting flag to True", flush=True)
                            self.is_deepsearch_called = True
                            break
                
                if self.is_deepsearch_called:
                    print(f"🔍 FILTER STREAM: Breaking from choice loop, flag is now: {self.is_deepsearch_called}", flush=True)
                    break
        else:
            if self.is_deepsearch_called:
                print("🔍 FILTER STREAM: Flag already set, skipping tool call detection", flush=True)
            if "choices" not in event:
                print("🔍 FILTER STREAM: No 'choices' key in event", flush=True)
        
        print(f"🔍 FILTER STREAM: Final flag state: {self.is_deepsearch_called}", flush=True)
        
        # If deep search is called, return event with empty content to pause streaming
        # This allows the deep search tool to handle its own streaming
        if self.is_deepsearch_called:
            print("🔍 FILTER STREAM: ⏸️ PAUSING STREAM - returning empty content", flush=True)
            updated_event = event.copy()
            if "choices" in updated_event:
                for choice in updated_event.get("choices", []):
                    if "delta" in choice:
                        choice["delta"] = {"content": ""}
                        print("🔍 FILTER STREAM: Set delta content to empty string", flush=True)
            else:
                updated_event["choices"] = [{"index": 0, "delta": {"content": ""}}]
                print("🔍 FILTER STREAM: Created new choices with empty content", flush=True)
            print("-" * 80, flush=True)
            return updated_event
        
        # Otherwise, return the event as-is
        print("🔍 FILTER STREAM: ✅ ALLOWING STREAM - returning event as-is", flush=True)
        print("-" * 80, flush=True)
        return event

    async def outlet(
        self, body: Dict[str, Any], __user__: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Check outlet for tool execution results.
        This is called after the stream completes.
        """
        print("=" * 80, flush=True)
        print("🔍 FILTER OUTLET: Called", flush=True)
        print(f"🔍 FILTER OUTLET: Body keys: {list(body.keys()) if isinstance(body, dict) else 'NOT A DICT'}", flush=True)
        if isinstance(body, dict):
            # Check if there are tool call results in the response
            messages = body.get("messages", [])
            print(f"🔍 FILTER OUTLET: Number of messages: {len(messages)}", flush=True)
            for msg_idx, msg in enumerate(messages):
                if isinstance(msg, dict):
                    role = msg.get("role")
                    tool_calls = msg.get("tool_calls")
                    tool_call_id = msg.get("tool_call_id")
                    print(f"🔍 FILTER OUTLET: Message {msg_idx}: role={role}, tool_calls={tool_calls}, tool_call_id={tool_call_id}", flush=True)
                    if role == "assistant" and tool_calls:
                        print(f"🔍 FILTER OUTLET: Found tool_calls in assistant message!", flush=True)
                    if role == "tool" and tool_call_id:
                        print(f"🔍 FILTER OUTLET: Found tool response with tool_call_id={tool_call_id}", flush=True)
        print("=" * 80, flush=True)
        return body
