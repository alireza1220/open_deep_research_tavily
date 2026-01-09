"""
title: Privacy Filter v5 (Image Analysis & Personalization)
author: Alireza Mounesisohi
version: 5.0.0
license: MIT
description: Injects user's name for personalization and uses a separate vision model to analyze images, adding the description to the context.
"""

import re
import subprocess
import sys
from typing import Any, Dict, List, Optional

import httpx
from fastapi.requests import Request
from open_webui.routers.memories import get_memories

# This new approach directly uses the OpenWebUI backend functions, which is more robust.
from open_webui.routers.users import Users
from pydantic import BaseModel, Field

# A unique prefix to identify our special memory record.
MEMORY_PREFIX = "PREFERRED_NAME::"


def install_requirements():
    """Installs required third-party libraries if they are not already installed."""
    try:
        __import__("httpx")
    except ImportError:
        print("httpx not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx"])


install_requirements()


class Filter:
    class Valves(BaseModel):
        # Personalization Valves
        enable_personalization: bool = Field(
            default=True,
            description="Enable personalized responses using the user's name.",
        )
        greet_only: bool = Field(
            default=True,
            description="If enabled, the AI will be instructed to only use the user's name in the initial greeting.",
        )
        model_name: str = Field(
            default="AskIB",
            description="The name of the AI assistant, to prevent confusion.",
        )

        # Image Analysis Valves
        enable_image_analysis: bool = Field(
            default=True,
            description="Enable pre-processing of images with a separate vision model.",
        )
        image_model_endpoint: str = Field(
            default="http://models.ai.nant.com/v1/chat/completions",
            description="The API endpoint for the external vision model.",
        )
        image_model_name: str = Field(
            default="Llama-4-Maverick",
            description="The name of the external vision model to use.",
        )
        image_model_api_key: str = Field(
            default="sk-_74oWR7B_Iw7MOYzpCuuGA",
            description="The API key for the external vision model.",
        )

    def __init__(self) -> None:
        self.valves = self.Valves()

        # TODO
        self.is_deepsearch_called = False

    async def inlet(
        self,
        body: Dict[str, Any],
        __request__: Request,
        __user__: Optional[Dict[str, Any]] = None,
        __event_emitter__: Optional[callable] = None,  # Added __event_emitter__ here
    ) -> Dict[str, Any]:
        messages = body.get("messages", [])

        # sample body
        # {'stream': True, 'model': 'Llama-4-Maverick', 'messages': [{'role': 'user', 'content': 'can you use the interactive tool and test tool to response'}], 'tool_ids': ['test_tool'], 'features': {'voice': False, 'image_generation': False, 'code_interpreter': False, 'web_search': False}, 'metadata': {'user_id': '8cd8f417-0b43-4934-8fee-9f83ec34840c', 'chat_id': '647f29c4-b21e-4884-b527-542c4cd4ca81', 'message_id': '378856b8-b728-4c77-842b-a5e1aa9e14b9', 'parent_message_id': '99d99b47-98de-430c-a17c-48e288b27679', 'session_id': 'GuQdBMcqexF2Su4UAAAT', 'filter_ids': [], 'tool_ids': ['test_tool'], 'tool_servers': [], 'files': None, 'features': {'voice': False, 'image_generation': False, 'code_interpreter': False, 'web_search': False}, 'variables': {'{{USER_NAME}}': 'admin', '{{USER_LOCATION}}': 'Unknown', '{{CURRENT_DATETIME}}': '2026-01-09 08:55:54', '{{CURRENT_DATE}}': '2026-01-09', '{{CURRENT_TIME}}': '08:55:54', '{{CURRENT_WEEKDAY}}': 'Friday', '{{CURRENT_TIMEZONE}}': 'America/Los_Angeles', '{{USER_LANGUAGE}}': 'en-US'}, 'model': {'id': 'Llama-4-Maverick', 'object': 'model', 'created': 1677610602, 'owned_by': 'openai', 'connection_type': 'external', 'name': 'Llama-4-Maverick', 'openai': {'id': 'Llama-4-Maverick', 'object': 'model', 'created': 1677610602, 'owned_by': 'openai', 'connection_type': 'external'}, 'urlIdx': 0, 'actions': [], 'filters': [], 'tags': []}, 'direct': False, 'params': {'stream_delta_chunk_size': None, 'reasoning_tags': None, 'function_calling': 'default'}}}

        # TODO: if body has the tool_id = deep_search or deepsearch or researcher let's say the set the is_deep_search_called to True

        # --- Image Analysis ---
        if self.valves.enable_image_analysis and self.valves.image_model_api_key:
            last_message = messages[-1] if messages else None

            if (
                last_message
                and last_message.get("role") == "user"
                and isinstance(last_message.get("content"), list)
            ):
                image_parts = []
                text_parts = []
                other_content = []

                for part in last_message["content"]:
                    if part.get("type") == "image_url":
                        image_url = part.get("image_url", {}).get("url", "")
                        if image_url.startswith("data:image"):
                            image_parts.append(
                                {"type": "image_url", "image_url": {"url": image_url}}
                            )
                    elif part.get("type") == "text":
                        # Collect non-empty text parts
                        text = part.get("text", "").strip()
                        if text:
                            text_parts.append(text)
                    else:
                        other_content.append(part)

                if image_parts:
                    # 1. Add default message if no text is present
                    if not text_parts:
                        print(
                            "IMAGE_FILTER: Image submitted without message. Adding default 'Analyze the image.'"
                        )
                        text_parts.append("Analyze the image.")

                    print(
                        f"IMAGE_FILTER: Found {len(image_parts)} image(s). Analyzing with {self.valves.image_model_name}."
                    )

                    # ** NEW: Emit 'Analyzing' status event **
                    if __event_emitter__:
                        await __event_emitter__(
                            {
                                "type": "status",
                                "data": {
                                    "description": "Image analyzing...",
                                    "done": False,
                                    "hidden": False,
                                },
                            }
                        )

                    analysis_results = []
                    try:
                        async with httpx.AsyncClient() as client:
                            payload = {
                                "model": self.valves.image_model_name,
                                "messages": [
                                    {
                                        "role": "user",
                                        "content": [
                                            {
                                                "type": "text",
                                                "text": "Describe this image in detail. Be objective and focus on facts.",
                                            },
                                            *image_parts,
                                        ],
                                    }
                                ],
                                "max_tokens": 500,
                            }
                            headers = {
                                "Authorization": f"Bearer {self.valves.image_model_api_key}",
                                "Content-Type": "application/json",
                            }

                            response = await client.post(
                                self.valves.image_model_endpoint,
                                json=payload,
                                headers=headers,
                                timeout=60.0,
                            )

                            if response.status_code == 200:
                                result_text = response.json()["choices"][0]["message"][
                                    "content"
                                ]
                                analysis_results.append(result_text)
                            else:
                                print(
                                    f"IMAGE_FILTER: Error from vision model API: {response.status_code} {response.text}"
                                )

                    except Exception as e:
                        print(f"IMAGE_FILTER: Exception during image analysis: {e}")

                    finally:
                        # ** NEW: Emit 'Completed' status event (in a finally block to ensure it runs) **
                        if __event_emitter__:
                            await __event_emitter__(
                                {
                                    "type": "status",
                                    "data": {
                                        "description": "Image analysis completed.",
                                        "done": True,
                                        "hidden": False,
                                    },
                                }
                            )

                    if analysis_results:
                        analysis_summary = "\n".join(analysis_results)
                        system_note = {
                            "role": "system",
                            "content": f"An image was provided and analyzed. Here is the description:\n---\n{analysis_summary}\n---",
                        }

                        # Insert the analysis right before the last user message
                        messages.insert(-1, system_note)

                        # Replace the user's last message content, removing the image
                        new_content = " ".join(text_parts).strip()

                        if other_content:
                            # Recreate the mixed content list
                            new_content_list = [
                                {"type": "text", "text": new_content},
                                *other_content,
                            ]
                            last_message["content"] = new_content_list
                        else:
                            last_message["content"] = new_content

        # --- Personalization Injection ---
        # ... (rest of the personalization code remains unchanged)
        prompt_marker_start = ""
        prompt_marker_end = ""

        for msg in messages:
            if msg.get("role") == "system":
                content = msg.get("content", "")
                if prompt_marker_start in content:
                    start_index = content.find(prompt_marker_start)
                    end_index = content.find(prompt_marker_end)
                    if end_index != -1:
                        msg["content"] = (
                            content[:start_index]
                            + content[end_index + len(prompt_marker_end) :]
                        ).strip()

        if self.valves.enable_personalization and __user__ and "id" in __user__:
            user_id = __user__["id"]
            name_to_use = ""

            user = Users.get_user_by_id(user_id)
            if user:
                try:
                    existing_memories = await get_memories(
                        user=user, request=__request__
                    )
                    for memory in existing_memories.get("memories", []):
                        if memory["content"].startswith(MEMORY_PREFIX):
                            name_to_use = memory["content"][
                                len(MEMORY_PREFIX) :
                            ].strip()
                except Exception as e:
                    print(f"FILTER: Error reading memories for user '{user_id}': {e}")

            if not name_to_use and "name" in __user__ and __user__["name"]:
                name_to_use = __user__["name"].split()[0]

            if name_to_use:
                if self.valves.greet_only:
                    prompt_text = f"You are an AI assistant. Your name is {self.valves.model_name}. The user's first name is {name_to_use}. Greet the user as {name_to_use} in your very first response only. Do not use the user's name in any subsequent messages and do not introduce yourself as {name_to_use}."
                else:
                    prompt_text = f"You are an AI assistant. Your name is {self.valves.model_name}. The user you are talking to has a preferred first name: {name_to_use}. Be friendly and address the user as {name_to_use} when it feels natural to do so. Do not introduce yourself as {name_to_use}."

                personalization_prompt = (
                    f"{prompt_marker_start}\n{prompt_text}\n{prompt_marker_end}"
                )

                system_message_found = False
                for msg in messages:
                    if msg.get("role") == "system":
                        msg["content"] = (
                            f"{personalization_prompt}\n\n{msg.get('content', '')}".strip()
                        )
                        system_message_found = True
                        break

                if not system_message_found:
                    messages.insert(
                        0, {"role": "system", "content": personalization_prompt}
                    )

        body["messages"] = messages
        return body

    ## TODO updating the async def stream to pause the streaming if there is deep search word in the tool, basically if the tool got the deep search call there should not be a post call to it.
    # async def stream(self, body)
    #     async def stream(
    #     self,
    #     event: dict
    # ) -> dict:
    # This is where you modify streamed chunks of model output.
    # print(f"stream event: {event}")
    # print(f"self event: {self}")
    # print()
    # if self.is_deepsearch_called True inlcude deepsearch or deep_search (lower case) just don't return anything return event()
    # return event choise to be empty like this or just empty
    # {
    #     "id": "chatcmpl-b43616451a5944a7b4380b4925a812c4",
    #     "created": 1767137139,
    #     "model": "Llama4-Scout",
    #     "object": "chat.completion.chunk",
    #     "choices": [{"index": 0, "delta": {"content": ""}}],
    # }
    # return

    async def outlet(
        self, body: Dict[str, Any], __user__: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        return body
