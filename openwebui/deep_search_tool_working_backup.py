"""
title: Deep Research this is working but the key for perplexity should be set behind the scene.
description: This tool performs deep research in realtime with confgurable parameters
author: Alireza Mounesisohi
version: 0.0.1
"""

import json
from typing import Any, Callable, Literal

import httpx
from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        FASTAPI_BASE_URL: str = Field(
            default="http://host.docker.internal:8000",
            description="Base URL for Deep Search FastAPI endpoint. "
            "For Docker: use 'host.docker.internal:8000' (Mac/Windows) or host IP (Linux). "
            "For same Docker network: use service name like 'fastapi:8000'. "
            "For public access: use ngrok/cloudflared URL.",
        )

        OPENAI_BASE_URL: str = Field(
            default="http://models.ai.nant.com/v1", description="Base URL for OPENAI"
        )

        OPENAI_API_KEY: str = Field(default="sk-", description="API key for API")

        SUMMARIZER_MODEL: str = Field(
            default="openai:Llama-4-Maverick",
            description="Model for summarizing research",
        )

        RESEARCH_MODEL: str = Field(
            default="openai:Llama-4-Maverick", description="Model for research"
        )

        COMPRESSION_MODEL: str = Field(
            default="openai:Llama-4-Maverick", description="Model for Compression"
        )

        FINAL_REPORT_MODEL: str = Field(
            default="openai:Llama-4-Maverick",
            description="Model model for final report",
        )

        ALLOW_CLARIFICATION: bool = Field(
            default=False, description="Asking user for more clarification if required."
        )

        MAX_RESEARCHER_ITERATION: int = Field(
            default=6, description="Max research iteration."
        )

        # SEARCH_API: Literal["tavily", "perplexity"] = Field(
        #     default="tavily",
        #     description="Search engine to use for web research. Tavily provides comprehensive search results with AI-generated summaries. Perplexity provides fast, cited web-backed responses.",
        # )
        SEARCH_API: Literal["perplexity"] = Field(
            default="perplexity",
            description="Search engine to use for web research. Perplexity provides fast, cited web-backed responses.",
        )

    def __init__(self):
        self.valves = self.Valves()
        # Store conversation history for clarification loop
        self.conversation_history = []

    async def deep_research(
        self, query: str, __event_emitter__: Callable[[dict], Any] = None, **kwargs
    ) -> str:
        await __event_emitter__(
            {
                "type": "status",
                "data": {
                    "description": "Requesting Deep Search Tool to perform the action...",
                    "done": False,
                    "hidden": False,
                },
            }
        )

        # Build messages array with conversation history
        messages = []

        # Add previous conversation history if available
        if self.conversation_history:
            messages.extend(self.conversation_history)
            print(
                f"🔍 Using {len(self.conversation_history)} messages from conversation history",
                flush=True,
            )

        # Add current user query
        messages.append(
            {
                "role": "user",
                "content": query,
            }
        )

        request_data = {
            "messages": messages,
            "config": {
                "allow_clarification": self.valves.ALLOW_CLARIFICATION,
                "max_researcher_iterations": self.valves.MAX_RESEARCHER_ITERATION,
                "search_api": self.valves.SEARCH_API,
                "apiKeys": {"OPENAI_API_KEY": self.valves.OPENAI_API_KEY},
                "apiBaseUrl": {"OPENAI_API_BASE_URL": self.valves.OPENAI_BASE_URL},
                "summarization_model": self.valves.SUMMARIZER_MODEL,
                "research_model": self.valves.RESEARCH_MODEL,
                "compression_model": self.valves.COMPRESSION_MODEL,
                "final_report_model": self.valves.FINAL_REPORT_MODEL,
            },
        }

        print(f"🔍 Using search API: {self.valves.SEARCH_API}")

        try:
            start_url = f"{self.valves.FASTAPI_BASE_URL}/v1/research/stream"

            final_report = None
            citations = []

            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream(
                    "POST", start_url, json=request_data
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        error_message = (
                            f"Error: {response.status_code} - {error_text.decode()}"
                        )
                        print(error_message)
                        await __event_emitter__(
                            {
                                "type": "status",
                                "data": {
                                    "description": error_message,
                                    "done": True,
                                    "hidden": False,
                                },
                            }
                        )
                        return error_message

                    event_index = 0
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        if line.startswith("data: "):
                            event_index += 1
                            try:
                                msg = json.loads(line[6:])  # strip "data: "
                            except json.JSONDecodeError as e:
                                print(
                                    f"**Failed to parse JSON for event {event_index}: {e}**\n\n"
                                )
                                await __event_emitter__(
                                    {
                                        "type": "status",
                                        "data": {
                                            "description": f"JSON error: {line}",
                                            "done": True,
                                            "hidden": False,
                                        },
                                    }
                                )
                                continue

                            try:
                                if msg.get("event") == "progress":
                                    progress_msg = msg.get("data", {}).get(
                                        "progress_message"
                                    )
                                    if progress_msg:
                                        await __event_emitter__(
                                            {
                                                "type": "status",
                                                "data": {
                                                    "description": progress_msg,
                                                    "done": False,
                                                    "hidden": False,
                                                },
                                            }
                                        )

                                elif msg.get("event") == "complete":
                                    event_data = msg.get("data", {})
                                    final_report = event_data.get("final_report")
                                    citations = event_data.get("citations", [])
                                    # Clear conversation history on successful completion
                                    self.conversation_history = []
                                    # exit the loop
                                    break

                                elif msg.get("event") == "end":
                                    # Handle end event (e.g., clarification needed)
                                    event_data = msg.get("data", {})
                                    messages_from_response = event_data.get(
                                        "messages", []
                                    )

                                    # Extract clarification message if present
                                    if messages_from_response:
                                        # Find the last assistant message (clarification question)
                                        for message in reversed(messages_from_response):
                                            if message.get("role") == "assistant":
                                                clarification_msg = message.get(
                                                    "content", ""
                                                )
                                                if clarification_msg:
                                                    # Store conversation history for next call
                                                    self.conversation_history = (
                                                        messages_from_response.copy()
                                                    )
                                                    print(
                                                        f"🔍 Stored {len(self.conversation_history)} messages in conversation history",
                                                        flush=True,
                                                    )

                                                    # Emit clarification message to user
                                                    await __event_emitter__(
                                                        {
                                                            "type": "message",
                                                            "data": {
                                                                "content": clarification_msg,
                                                            },
                                                        }
                                                    )
                                                    # Mark status as done
                                                    await __event_emitter__(
                                                        {
                                                            "type": "status",
                                                            "data": {
                                                                "description": "Clarification needed",
                                                                "done": True,
                                                                "hidden": False,
                                                            },
                                                        }
                                                    )
                                                    return f"Clarification needed: {clarification_msg}"
                                    # If no messages, break normally
                                    break

                            except Exception as error:
                                print(">>>> ERROR")
                                print(">>>> ERROR")
                                print(f"Error in loop: {error}")
                                await __event_emitter__(
                                    {
                                        "type": "status",
                                        "data": {
                                            "description": f"Error: {str(error)}",
                                            "done": True,
                                            "hidden": False,
                                        },
                                    }
                                )
                                break

            if not final_report:
                final_report = "Was not possible to perform the requested action."

            # Single final status event to mark all previous statuses as done
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": "Completed the task",
                        "done": True,
                        "hidden": False,
                    },
                }
            )

            # Emit individual citation events for each citation
            if citations:
                for citation in citations:
                    article = {
                        "link": citation.get("link", ""),
                        "title": citation.get("title", ""),
                        "content": citation.get(
                            "title", ""
                        ),  # Use title as content since citations don't have content field
                    }

                    # Emit citation event in exact OpenWebUI format
                    await __event_emitter__(
                        {
                            "type": "citation",
                            "data": {
                                "document": [article["content"]],
                                "metadata": [{"source": article["link"]}],
                                "source": {"name": article["title"]},
                            },
                        }
                    )
                else:
                    print("No citations found")

            # Emit the final report as a message
            await __event_emitter__(
                {
                    "type": "message",
                    "data": {
                        "content": f"{final_report}\n\n---\n",
                    },
                }
            )

            return f"Deep research completed: {final_report}"

        except httpx.RequestError as e:
            error_message = (
                f"BrowserUI found this error performing the action: {str(e)}"
            )
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": error_message,
                        "done": True,
                        "hidden": False,
                    },
                }
            )
            return error_message
