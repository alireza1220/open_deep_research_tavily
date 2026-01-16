import asyncio
import logging
import os
import sys
from contextlib import redirect_stderr
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Annotated, Any, Dict, List, Literal, Optional

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import (
    BaseTool,
    InjectedToolArg,
    StructuredTool,
    ToolException,
    tool,
)
from perplexity import Perplexity

load_dotenv()

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    MessageLikeRepresentation,
    filter_messages,
)
from pydantic import BaseModel


class Summary(BaseModel):
    """Research summary with key findings."""

    summary: str
    key_excerpts: str


# Add project root to Python path for imports
# project_root = Path(__file__).parent.parent
# if str(project_root) not in sys.path:
#     sys.path.insert(0, str(project_root))

# from open_deep_research.state import ResearchComplete, Summary
# from configuration import Configuration, SearchAPI
from open_deep_research.configuration import Configuration, SearchAPI

# from prompts import summarize_webpage_prompt
from open_deep_research.prompts import summarize_webpage_prompt

# from prompts import summarize_webpage_prompt


# Add project root to Python path for imports
# project_root = Path(__file__).parent.parent
# if str(project_root) not in sys.path:
#     sys.path.insert(0, str(project_root))

# from configuration import Configuration, SearchAPI

# Load environment variables from .env
# Suppress parsing warnings for lines that aren't valid env vars (e.g., search results mixed in)
# env_path = project_root / ".env"
# with redirect_stderr(StringIO()):
#     load_dotenv(dotenv_path=env_path, verbose=False)


async def perplexity_search_async(
    queries: List[str],
    max_results: Annotated[int, InjectedToolArg] = 5,
    topic: Annotated[
        Literal["general", "news", "finance"], InjectedToolArg
    ] = "general",
    config: RunnableConfig = None,
) -> str:
    PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
    print(f" api key is fetched: {PERPLEXITY_API_KEY}")

    client = Perplexity(api_key=PERPLEXITY_API_KEY)

    # search = client.search.create(
    #     query=[
    #     "What is human evolution?",
    #     "who is the first human discovered"
    #     ]
    # )
    queries_with_topic = [f"{query} in {topic}" for query in queries]

    search = client.search.create(
        query=queries_with_topic,
        max_results=max_results,
    )

    # for result in search.results:
    #     print(f"{result.title}: {result.url}")

    summaries = [search.results[i].snippet for i in range(len(search.results))]

    configurable = Configuration.from_runnable_config(config)
    max_char_to_include = configurable.max_content_length

    model_provider = configurable.summarization_model.split(":")[0].upper()
    model_api_key = os.getenv(f"{model_provider}_API_KEY", "")
    model_base_url = os.getenv("MODEL_BASE_URL", "")
    summarization_model = (
        init_chat_model(
            model=configurable.summarization_model,
            max_tokens=configurable.summarization_model_max_tokens,
            api_key=model_api_key,
            base_url=model_base_url,
            tags=["langsmith:nostream"],
        )
        .with_structured_output(Summary)
        .with_retry(stop_after_attempt=configurable.max_structured_output_retries)
    )

    # Step 4: Create summarization tasks (skip empty content)
    async def noop():
        """No-op function for results without raw content."""
        return None

    # summarization_tasks = [
    #     noop()
    #     if not result.get("raw_content")
    #     else summarize_webpage(
    #         summarization_model, result["raw_content"][:max_char_to_include]
    #     )
    #     for result in unique_results.values()
    # ]

    summarization_tasks = [
        noop()
        if not summaries[i]
        else summarize_webpage(summarization_model, summaries[i][:max_char_to_include])
        for i in range(len(summaries))
    ]

    # Step 5: Execute all summarization tasks in parallel
    summaries = await asyncio.gather(*summarization_tasks)

    titles = [search.results[i].title for i in range(len(search.results))]
    urls = [search.results[i].url for i in range(len(search.results))]
    # summaries = [search.results[i].snippet for i in range(len(search.results))]

    # summaries_truncated = [summaries[i][:max_char_to_include] for i in range(len(summaries))]

    formatted_output = "Search results: \n\n"
    for i in range(len(titles)):
        formatted_output += f"\n\n--- SOURCE {i + 1}: {titles[i]} ---\n"
        formatted_output += f"URL: {urls[i]}\n\n"
        formatted_output += f"SUMMARY:\n{summaries[i]}\n\n"
        # formatted_output += f"SUMMARY:\n<summary>\n{summaries[i]}\n</summary>\n\n"
        formatted_output += "\n\n" + "-" * 80 + "\n"

    # print(formatted_output)
    return formatted_output


def get_today_str() -> str:
    """Get current date formatted for display in prompts and outputs.

    Returns:
        Human-readable date string in format like 'Mon Jan 15, 2024'
    """
    now = datetime.now()
    return f"{now:%a} {now:%b} {now.day}, {now:%Y}"


async def summarize_webpage(model: BaseChatModel, webpage_content: str) -> str:
    """Summarize webpage content using AI model with timeout protection.

    Args:
        model: The chat model configured for summarization
        webpage_content: Raw webpage content to be summarized

    Returns:
        Formatted summary with key excerpts, or original content if summarization fails
    """
    try:
        # Create prompt with current date context
        prompt_content = summarize_webpage_prompt.format(
            webpage_content=webpage_content, date=get_today_str()
        )

        # Execute summarization with timeout to prevent hanging
        summary = await asyncio.wait_for(
            model.ainvoke([HumanMessage(content=prompt_content)]),
            timeout=60.0,  # 60 second timeout for summarization
        )

        # Format the summary with structured sections
        formatted_summary = (
            f"<summary>\n{summary.summary}\n</summary>\n\n"
            f"<key_excerpts>\n{summary.key_excerpts}\n</key_excerpts>"
        )

        print(f"successfully processed the request: {formatted_summary}")

        return formatted_summary

    except asyncio.TimeoutError:
        # Timeout during summarization - return original content
        logging.warning(
            "Summarization timed out after 60 seconds, returning original content"
        )
        return webpage_content
    except Exception as e:
        # Other errors during summarization - log and return original content
        logging.warning(
            f"Summarization failed with error: {str(e)}, returning original content"
        )
        return webpage_content


if __name__ == "__main__":
    output = asyncio.run(
        perplexity_search_async(
            ["What is human evolution?", "who is the first human discovered"]
        )
    )
    print(output)
