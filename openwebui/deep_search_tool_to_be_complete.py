"""
title: Deep Research
description: This tool performs deep research in realtime with confgurable parameters
author: Alireza Mounesisohi
version: 0.0.1
"""

import asyncio
import json
import time
from typing import Any, Callable
import requests
from pydantic import BaseModel, Field

class Tools:
    class Valves(BaseModel)
        FASTAPI_BASE_URL=Field(
            default="https://defectless-overreadily-maye.ngrok-free.dev",
            description="Base URL for Deep Search FastAPI endpoint"
        )

        OPENAI_BASE_URL=Field(
             default="http://models.ai.nant.com/v1",
             description="Base URL for OPENAI"
        )

        OPENAI_API_KEY: Field(
            default="sk-",
            description="API key for API" 
        )


        SUMMARIZER_MODEL=Field(
            default="openai:Llama-4-Maverick",
            description="Model for summarizing research"
        )

        RESEARCH_MODEL=Field(
            default="openai:Llama-4-Maverick",
            description="Model for research"
        )

        COMPRESSION_MODEL=Field(
            default="openai:Llama-4-Maverick",
            description="Model for Compression"
        )

        FINAL_REPORT_MODEL=Field(
            default="openai:Llama-4-Maverick",
            description="Model model for final report"
        )

        ALLOW_CLARIFICATION = Field(
             default=False,
             description="Asking user for more clarification."
        )

        MAX_RESEARCHER_ITERATION=Field(
             default=6,
             description="Max research iteration."
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
                        "description": "Requesting Deep Search Tool to perform the action...",
                        "done": False,
                        "hidden": False,
                    },
                }
            )

            # request_data = {
            #     "data": [
            #         query,
            #         3,
            #         1,
            #         self.valves.MODEL_PROVIDER,
            #         self.valves.MODEL,
            #         32000,
            #         1,
            #         "",
            #         "",
            #         False,
            #         False,
            #         False,
            #     ]
            # }


            request_data = {
                "messages": [
                    {
                        "role": "user",
                        "content": query,
                    }
                ],
                "config": {
                    "allow_clarification": self.valves.ALLOW_CLARIFICATION,
                    "max_researcher_iterations": self.valves.MAX_RESEARCHER_ITERATION,
                    "apiKeys": {"OPENAI_API_KEY": self.valves.OPENAI_API_KEY},
                    "apiBaseUrl": {"OPENAI_API_BASE_URL": self.valves.OPENAI_BASE_URL},
                    "summarization_model": self.valves.SUMMARIZER_MODEL,
                    "research_model": self.valves.RESEARCH_MODEL,
                    "compression_model": self.valves.COMPRESSION_MODEL,
                    "final_report_model": self.valves.FINAL_REPORT_MODEL,
                },
            }





            try:
                start_url =  f"{self.valves.FASTAPI_BASE_URL}/v1/research/stream"
                
                with requests.post(start_url, json=request_data, stream=True, timeout=300, ) as response:
                    # Sample output:
                    # {
                    # "event": "progress",
                    # "data": {
                    #     "final_report": null,
                    #     "final_report_without_citations": null,
                    #     "citations": null,
                    #     "messages": null,
                    #     "notes": null,
                    #     "research_brief": "I am looking for the latest developments in .",
                    #     "nodes": [
                    #     "research_supervisor"
                    #     ],
                    #     "progress_message": "Conducting research",
                    #     "has_final_report": false,
                    #     "started_time": "2026-01-08T18:58:44.535495+00:00",
                    #     "ended_time": null,
                    #     "duration": null,
                    #     "visited_websites": null,
                    #     "searches_occurred": 0,
                    #     "configuration": {
                    #     "allow_clarification": false,
                    #     "max_researcher_iterations": 1,
                    #     "apiKeys": {
                    #         "OPENAI_API_KEY": ""
                    #     },
                    #     "apiBaseUrl": {
                    #         "OPENAI_API_BASE_URL": "http://models.ai.nant.com/v1"
                    #     },
                    #     "summarization_model": "openai:Llama-4-Maverick",
                    #     "research_model": "openai:Llama-4-Maverick",
                    #     "compression_model": "openai:Llama-4-Maverick",
                    #     "final_report_model": "openai:Llama-4-Maverick"
                    #     },
                    #     "error_message": null,
                    #     "stats": null
                    # }
                    # }
                    
                    if not response.ok:
                        print(f"Error: {response.status_code}")
                        print(response.text)
                    
                    else:
                        event_index = 0
                        for line in response.iter_lines(decode_unicode=True):
                        if not line:
                            continue
                        if line.startswith("data: "):
                            event_index += 1
                            try:
                                msg = json.loads(line[6:])  # strip "data: "
                            except json.JSONDecodeError as e:
                                print(f"**Failed to parse JSON for event {event_index}: {e}**\n\n")
                                await __event_emitter__(
                                    {
                                        "type": "status",  # We set the type here
                                        "data": {
                                            "description": f"JSON error: {line}",
                                            "done": True,
                                            "hidden": False,
                                        },
                                    }
                                )
                                continue

                            try:
                                if msg.get("event") == "progres":
                                    await __event_emitter__(
                                        {
                                            "type": "status", 
                                            "data": {
                                                "description": msg.get("data", {}).get("progress_message"),
                                                "done": False,
                                                "hidden": False,
                                            },
                                            # Note done is False here indicating we are still emitting statuses
                                        }
                                    )
                                
                                elif msg.get("event") == "complete":
                                    final_report = msg.get("data", {}).get("final_report")
                                    # exit the loop
                                    break

                                    

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
                
                if not final_report:
                    final_report = "Was not possible to perform the requested action."

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

                # stream the final report now 
                
                                

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
                







        

