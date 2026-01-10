############################
# Perplexity Search Tool Utils
############################

import asyncio
import os
from typing import Annotated, Any, List
from urllib.parse import urlparse

import aiohttp
import requests
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg, tool

from open_deep_research.utils import get_perplexity_api_key

PERPLEXITY_SEARCH_DESCRIPTION = (
    "Search the web using the Perplexity API and return an answer with citations. "
    "Useful for getting fast, cited web-backed responses."
)


@tool(description=PERPLEXITY_SEARCH_DESCRIPTION)
async def perplexity_search(
    queries: List[str],
    model: Annotated[str, InjectedToolArg] = "sonar-pro",
    max_tokens: Annotated[int, InjectedToolArg] = 1024,
    config: RunnableConfig = None,
) -> str:
    """Search the web using the Perplexity API and format results for the agent.

    Args:
        queries: List of search queries to execute
        model: Perplexity model name (e.g., sonar-pro)
        max_tokens: Max tokens to generate per query
        config: Runtime configuration for API key access

    Returns:
        Formatted string containing Perplexity answers and citations
    """
    api_key = get_perplexity_api_key(config)
    if not api_key:
        return (
            "Perplexity search is not configured. "
            "Set PERPLEXITY_API_KEY (or provide it via apiKeys when GET_API_KEYS_FROM_CONFIG=true)."
        )

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    async def _run_query(session: aiohttp.ClientSession, query: str) -> dict[str, Any]:
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [
                {
                    "role": "system",
                    "content": "Search the web and provide factual information with sources.",
                },
                {"role": "user", "content": query},
            ],
        }
        async with session.post(
            "https://api.perplexity.ai/chat/completions", headers=headers, json=payload
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
            content = data["choices"][0]["message"]["content"]
            citations = data.get("citations") or []
            return {"query": query, "content": content, "citations": citations}

    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*[_run_query(session, q) for q in queries])

    def _extract_title_from_url(url: str, query: str = "", is_primary: bool = True) -> str:
        """Extract a meaningful title from a URL or generate a descriptive one."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.replace("www.", "")
            
            # Extract meaningful parts from domain
            if domain:
                # Use domain name as base, capitalize appropriately
                domain_parts = domain.split(".")
                if len(domain_parts) >= 2:
                    site_name = domain_parts[-2].capitalize()
                else:
                    site_name = domain.capitalize()
                
                if is_primary and query:
                    return f"{site_name} - {query}"
                elif is_primary:
                    return f"{site_name} - Perplexity Search Result"
                else:
                    return f"{site_name} - Supporting Source"
            else:
                # Fallback if URL parsing fails
                if is_primary and query:
                    return f"Perplexity Search Result: {query}"
                elif is_primary:
                    return "Perplexity Search Result"
                else:
                    return "Perplexity Supporting Source"
        except Exception:
            # Fallback to generic title
            if is_primary and query:
                return f"Perplexity Search Result: {query}"
            elif is_primary:
                return "Perplexity Search Result"
            else:
                return "Perplexity Supporting Source"

    # Collect all sources from all queries
    all_sources = []
    source_counter = 1
    
    for result in results:
        citations = result.get("citations", [])
        content = result.get("content", "")
        query = result.get("query", "")
        
        if not citations:
            # If no citations, create a single source entry with the content
            title = _extract_title_from_url("https://www.perplexity.ai", query, is_primary=True)
            all_sources.append({
                "title": title,
                "url": "https://www.perplexity.ai",
                "content": content,
                "source_number": source_counter
            })
            source_counter += 1
        else:
            # Create a source entry for each citation
            for i, citation_url in enumerate(citations):
                is_primary = (i == 0)
                title = _extract_title_from_url(citation_url, query, is_primary=is_primary)
                
                if is_primary:
                    # First citation gets the full synthesized content
                    all_sources.append({
                        "title": title,
                        "url": citation_url,
                        "content": content,
                        "source_number": source_counter
                    })
                else:
                    # Additional citations are supporting sources
                    all_sources.append({
                        "title": title,
                        "url": citation_url,
                        "content": f"Supporting source referenced in the main answer for query: {query}",
                        "source_number": source_counter
                    })
                source_counter += 1

    # Format output to match Tavily format
    if not all_sources:
        return "No valid search results found. Please try different search queries or use a different search API."

    formatted_output = "Search results: \n\n"
    for source in all_sources:
        formatted_output += f"\n\n--- SOURCE {source['source_number']}: {source['title']} ---\n"
        formatted_output += f"URL: {source['url']}\n\n"
        formatted_output += f"SUMMARY:\n{source['content']}\n\n"
        formatted_output += "\n\n" + "-" * 80 + "\n"

    return formatted_output


def perplexity_search_legacy(search_queries):
    """Search the web using the Perplexity API.

    Args:
        search_queries (List[SearchQuery]): List of search queries to process

    Returns:
        List[dict]: List of search responses from Perplexity API, one per query. Each response has format:
            {
                'query': str,                    # The original search query
                'follow_up_questions': None,
                'answer': None,
                'images': list,
                'results': [                     # List of search results
                    {
                        'title': str,            # Title of the search result
                        'url': str,              # URL of the result
                        'content': str,          # Summary/snippet of content
                        'score': float,          # Relevance score
                        'raw_content': str|None  # Full content or None for secondary citations
                    },
                    ...
                ]
            }
    """
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Bearer {os.getenv('PERPLEXITY_API_KEY')}",
    }

    search_docs = []
    for query in search_queries:
        payload = {
            "model": "sonar-pro",
            "messages": [
                {
                    "role": "system",
                    "content": "Search the web and provide factual information with sources.",
                },
                {"role": "user", "content": query},
            ],
        }

        response = requests.post(
            "https://api.perplexity.ai/chat/completions", headers=headers, json=payload
        )
        response.raise_for_status()  # Raise exception for bad status codes

        # Parse the response
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        citations = data.get("citations", ["https://perplexity.ai"])

        # Create results list for this query
        results = []

        # First citation gets the full content
        results.append(
            {
                "title": f"Perplexity Search, Source 1",
                "url": citations[0],
                "content": content,
                "raw_content": content,
                "score": 1.0,  # Adding score to match Tavily format
            }
        )

        # Add additional citations without duplicating content
        for i, citation in enumerate(citations[1:], start=2):
            results.append(
                {
                    "title": f"Perplexity Search, Source {i}",
                    "url": citation,
                    "content": "See primary source for full content",
                    "raw_content": None,
                    "score": 0.5,  # Lower score for secondary sources
                }
            )

        # Format response to match Tavily structure
        search_docs.append(
            {
                "query": query,
                "follow_up_questions": None,
                "answer": None,
                "images": [],
                "results": results,
            }
        )

    return search_docs
