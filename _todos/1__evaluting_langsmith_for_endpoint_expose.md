<!-- 1__evaluting_langsmith_for_endpoint_expose.md -->

1. Search web and find out if the langsmith can be used for exposing endpoint
2. Determine if the web search is propriotory or not.
3. Is it recommended to use the langsmith or not for the production environment.


For context I see the following that make the call.

https://api.smith.langchain.com/runs/019b8f0d-1d28-7930-948b-0957cb05c186?exclude_s3_stored_attributes=true&exclude_serialized=false

payload:
exclude_s3_stored_attributes
- true
exclude_serialized
- false


Response:
{
    "name": "Deep Researcher",
    "inputs": {
        "messages": [
            {
                "content": "Can you do a deep search about human evolution?",
                "type": "human"
            }
        ]
    },
    "inputs_preview": null,
    "run_type": "chain",
    "start_time": "2026-01-05T16:46:01.068924",
    "end_time": "2026-01-05T16:46:04.510089",
    "extra": {
        "metadata": {
            "LANGGRAPH_API_URL": "http://127.0.0.1:2024",
            "LANGSMITH_LANGGRAPH_API_VARIANT": "local_dev",
            "LANGSMITH_PROJECT": "ib_deep_research",
            "LANGSMITH_TRACING": "true",
            "allow_clarification": true,
            "assistant_id": "e9a5370f-7a53-55a8-ada8-6ab9ef15bb5b",
            "compression_model": "openai:gpt-4.1",
            "created_by": "system",
            "final_report_model": "openai:gpt-4.1",
            "from_studio": true,
            "graph_id": "Deep Researcher",
            "langgraph_api_url": "http://127.0.0.1:2024",
            "langgraph_api_version": "0.6.17",
            "langgraph_host": "self-hosted",
            "langgraph_plan": "developer",
            "langgraph_request_id": "16ae9316-80ae-4f72-89c7-2dcd0903e6a2",
            "langgraph_version": "1.0.5",
            "ls_run_depth": 0,
            "max_concurrent_research_units": 5,
            "max_content_length": 50000,
            "max_react_tool_calls": 10,
            "max_researcher_iterations": 6,
            "max_structured_output_retries": 3,
            "research_model": "openai:gpt-4.1",
            "revision_id": "b419df8",
            "run_attempt": 1,
            "run_id": "019b8f0d-1d28-7930-948b-0957cb05c186",
            "search_api": "tavily",
            "summarization_model": "openai:gpt-4.1-mini",
            "thread_id": "eca339f1-81f7-401f-a1bd-99e725f94c10",
            "user_id": "langgraph-studio-user"
        },
        "runtime": {
            "langchain_core_version": "1.2.6",
            "langchain_version": "1.2.0",
            "library": "langchain-core",
            "library_version": "1.2.6",
            "platform": "macOS-26.1-arm64-arm-64bit",
            "py_implementation": "CPython",
            "runtime": "python",
            "runtime_version": "3.11.12",
            "sdk": "langsmith-py",
            "sdk_version": "0.6.0"
        }
    },
    "error": null,
    "execution_order": 1,
    "serialized": null,
    "outputs": {
        "messages": [
            {
                "additional_kwargs": {},
                "content": "Can you do a deep search about human evolution?",
                "id": "9c9a5624-6601-4cf4-a127-8df609ba3f8e",
                "response_metadata": {},
                "type": "human"
            },
            {
                "additional_kwargs": {},
                "content": "Can you specify which aspects of human evolution you are most interested in? For example, are you looking for details on fossil discoveries, genetic evidence, evolutionary milestones, or the cultural evolution of humans?",
                "id": "f80de6a1-b3d0-4566-b9fa-f7657199f81e",
                "invalid_tool_calls": [],
                "response_metadata": {},
                "tool_calls": [],
                "type": "ai"
            }
        ],
        "notes": [],
        "raw_notes": [],
        "supervisor_messages": []
    },
    "outputs_preview": null,
    "parent_run_id": null,
    "manifest_id": null,
    "manifest_s3_id": null,
    "events": [
        {
            "name": "start",
            "time": "2026-01-05T16:46:01.068924+00:00"
        },
        {
            "name": "end",
            "time": "2026-01-05T16:46:04.510089+00:00"
        }
    ],
    "tags": [],
    "inputs_s3_urls": null,
    "outputs_s3_urls": null,
    "s3_urls": null,
    "trace_id": "019b8f0d-1d28-7930-948b-0957cb05c186",
    "dotted_order": "20260105T164601068924Z019b8f0d-1d28-7930-948b-0957cb05c186",
    "trace_min_start_time": null,
    "trace_max_start_time": null,
    "id": "019b8f0d-1d28-7930-948b-0957cb05c186",
    "status": "success",
    "child_run_ids": null,
    "direct_child_run_ids": null,
    "parent_run_ids": [],
    "feedback_stats": null,
    "reference_example_id": null,
    "total_tokens": 624,
    "prompt_tokens": 570,
    "completion_tokens": 54,
    "prompt_token_details": {
        "audio": 0,
        "cache_read": 0
    },
    "completion_token_details": {
        "audio": 0,
        "reasoning": 0
    },
    "total_cost": 0.001572,
    "prompt_cost": 0.00114,
    "completion_cost": 0.000432,
    "prompt_cost_details": {
        "audio": 0.0,
        "cache_read": 0.0
    },
    "completion_cost_details": {
        "audio": 0.0,
        "reasoning": 0.0
    },
    "price_model_id": null,
    "first_token_time": "2026-01-05T16:46:03.605517",
    "messages": null,
    "session_id": "39037901-6b38-4915-b7dc-318b42ec8a71",
    "app_path": "/o/9601a462-4aae-4b1d-bdee-4d10181393ab/projects/p/39037901-6b38-4915-b7dc-318b42ec8a71/r/019b8f0d-1d28-7930-948b-0957cb05c186?trace_id=019b8f0d-1d28-7930-948b-0957cb05c186&start_time=2026-01-05T16:46:01.068924",
    "last_queued_at": null,
    "in_dataset": false,
    "share_token": null,
    "trace_tier": "shortlived",
    "trace_first_received_at": "2026-01-05T16:46:02.420680",
    "ttl_seconds": 1209600,
    "trace_upgrade": false,
    "reference_dataset_id": null,
    "thread_id": "eca339f1-81f7-401f-a1bd-99e725f94c10"
}