"""
title: Deep Research (Browser Ui)
description: This tool performs deep research in realtime
author: algoz098
version: 0.0.1
license: MIT
"""

import asyncio
import json
import time
from typing import Any, Callable

import requests
from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        BASE_URL: str = Field(
            default="http://localhost:7788",
            description="Base URL for BrowserUI Web UI",
        )
        MODEL: str = Field(default="gpt-4o-mini", description="Model")
        MODEL_PROVIDER: str = Field(
            default="openai", description="Model provider (google, openai, ollama, etc)"
        )

    def __init__(self):
        self.valves = self.Valves()

    async def deep_research(
        self, query: str, __event_emitter__: Callable[[dict], Any] = None
    ) -> str:
        # emitter = EventEmitter(__event_emitter__)
        await __event_emitter__(
            {
                "type": "status",
                "data": {
                    "description": "Requesting BrowserUI to perform the action...",
                    "done": False,
                    "hidden": False,
                },
            }
        )

        request_data = {
            "data": [
                query,
                3,
                1,
                self.valves.MODEL_PROVIDER,
                self.valves.MODEL,
                32000,
                1,
                "",
                "",
                False,
                False,
                False,
            ]
        }

        try:
            start_url = f"{self.valves.BASE_URL}/gradio_api/call/run_deep_search"
            response = requests.post(start_url, json=request_data)
            response.raise_for_status()
            event_id = response.json().get("event_id")

            if not event_id:
                raise ValueError("Error to receive event_id!")

            stream_url = (
                f"{self.valves.BASE_URL}/gradio_api/queue/data?session_hash={event_id}"
            )

            final_result = ""
            download_link = ""

            with requests.get(stream_url, stream=True) as stream_response:
                for line in stream_response.iter_lines():
                    if line:
                        decoded_line = line.decode("utf-8").strip()
                        if decoded_line.startswith("data: "):
                            decoded_line = decoded_line[6:]

                        try:
                            msg = json.loads(decoded_line)

                        except json.JSONDecodeError:
                            print(
                                f"Erro ao decodificar JSON, dado recebido: {decoded_line}"
                            )

                            await __event_emitter__(
                                {
                                    "type": "status",  # We set the type here
                                    "data": {
                                        "description": f"JSON error: {decoded_line}",
                                        "done": True,
                                        "hidden": False,
                                    },
                                }
                            )
                            continue

                        try:
                            if msg.get("msg") == "estimation":
                                await __event_emitter__(
                                    {
                                        "type": "status",  # We set the type here
                                        "data": {
                                            "description": "BrowserUi is waiting for a browser....",
                                            "done": False,
                                            "hidden": False,
                                        },
                                        # Note done is False here indicating we are still emitting statuses
                                    }
                                )
                            elif msg.get("msg") == "process_starts":
                                await __event_emitter__(
                                    {
                                        "type": "status",  # We set the type here
                                        "data": {
                                            "description": "BrowserUi started to perform the actions....",
                                            "done": False,
                                            "hidden": False,
                                        },
                                        # Note done is False here indicating we are still emitting statuses
                                    }
                                )
                            elif msg.get("msg") == "heartbeat":
                                await __event_emitter__(
                                    {
                                        "type": "status",  # We set the type here
                                        "data": {
                                            "description": "BrowserUi is still running the actions...",
                                            "done": False,
                                            "hidden": False,
                                        },
                                        # Note done is False here indicating we are still emitting statuses
                                    }
                                )
                            elif msg.get("msg") == "process_generating":
                                await __event_emitter__(
                                    {
                                        "type": "status",  # We set the type here
                                        "data": {
                                            "description": "BrowserUi is finishing...",
                                            "done": False,
                                            "hidden": False,
                                        },
                                        # Note done is False here indicating we are still emitting statuses
                                    }
                                )
                            # Lidando com mensagens de progresso
                            elif msg.get("msg") == "status":
                                await __event_emitter__(
                                    {
                                        "type": "status",  # We set the type here
                                        "data": {
                                            "description": "Waiting BrowserUi to perform all the actions...",
                                            "done": False,
                                            "hidden": False,
                                        },
                                        # Note done is False here indicating we are still emitting statuses
                                    }
                                )

                            # Processamento Completo -> Pegamos o resultado final
                            elif msg.get("msg") == "process_completed":
                                output_data = msg.get("output", {}).get("data", [])

                                final_result = output_data[0]
                                status = output_data[1]
                                if status != None:
                                    download_link = output_data[1].get("url", "")
                                break  # Encontramos o resultado, pode sair do loop

                        except Exception as error:
                            print(">>>> ERROR")
                            print(">>>> ERROR")
                            print(f"Erro no loop: {error}")
                            await __event_emitter__(
                                {
                                    "type": "status",
                                    "data": {
                                        "description": f"Error: {str(error)}",  # Exibe a mensagem de erro corretamente
                                        "done": True,
                                        "hidden": False,
                                    },
                                }
                            )
                            break
            if not final_result:
                final_result = "Was not possible to perform the requested action."

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

            if download_link == "":
                await __event_emitter__(
                    {
                        "type": "message",  # We set the type here
                        "data": {
                            "content": f"## Browser UI's Web found an error: \n{final_result}\n---\n"
                        },
                        # Note that with message types we do NOT have to set a done condition
                    }
                )
                return f"Error occur: {final_result}"
            else:
                await __event_emitter__(
                    {
                        "type": "message",  # We set the type here
                        "data": {"content": f"{final_result}\n\n---\n"},
                        # Note that with message types we do NOT have to set a done condition
                    }
                )

                return f"Information from web in realtime: {final_result}"

        except requests.RequestException as e:
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
