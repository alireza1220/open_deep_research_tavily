# ############################
# # Perplexity Search Tool Utils
# ############################

# import asyncio
# import json
# import os
# from typing import Annotated, Any, List
# from urllib.parse import urlparse

# import aiohttp
# import requests
# from langchain_core.runnables import RunnableConfig
# from langchain_core.tools import InjectedToolArg, ToolException, tool

# from open_deep_research.utils import get_perplexity_api_key

# PERPLEXITY_SEARCH_DESCRIPTION = (
#     "Search the web using the Perplexity API and return an answer with citations. "
#     "Useful for getting fast, cited web-backed responses."
# )


# @tool(description=PERPLEXITY_SEARCH_DESCRIPTION)
# async def perplexity_search(
#     queries: List[str],
#     model: Annotated[str, InjectedToolArg] = "sonar-pro",
#     max_tokens: Annotated[int, InjectedToolArg] = 1024,
#     config: RunnableConfig = None,
# ) -> str:
#     """Search the web using the Perplexity API and format results for the agent.

#     Args:
#         queries: List of search queries to execute
#         model: Perplexity model name (e.g., sonar-pro)
#         max_tokens: Max tokens to generate per query
#         config: Runtime configuration for API key access

#     Returns:
#         Formatted string containing Perplexity answers and citations
#     """
#     print(f"🔍 [perplexity_search] Called with queries: {queries}", flush=True)
#     api_key = get_perplexity_api_key(config)
#     print(f"🔍 [perplexity_search] API key retrieved: {'Yes' if api_key else 'No'}", flush=True)

#     if not api_key:
#         error_msg = (
#             "❌ Perplexity API key is missing. "
#             "Please set PERPLEXITY_API_KEY in your environment variables (.env file) "
#             "or provide it via config.apiKeys when GET_API_KEYS_FROM_CONFIG=true."
#         )
#         print(f"🚨 [perplexity_search] {error_msg}", flush=True)
#         raise ToolException(error_msg)

#     headers = {
#         "accept": "application/json",
#         "content-type": "application/json",
#         "Authorization": f"Bearer {api_key}",
#     }

#     async def _run_query(session: aiohttp.ClientSession, query: str) -> dict[str, Any]:
#         payload = {
#             "model": model,
#             "max_tokens": max_tokens,
#             "messages": [
#                 {
#                     "role": "system",
#                     "content": "Search the web and provide factual information with sources.",
#                 },
#                 {"role": "user", "content": query},
#             ],
#         }
#         try:
#             async with session.post(
#                 "https://api.perplexity.ai/chat/completions", headers=headers, json=payload
#             ) as resp:
#                 # Read response body first (before checking status) so we can print it on errors
#                 response_text = await resp.text()
                
#                 # Check for error status codes (4xx, 5xx)
#                 if resp.status >= 400:
#                     # Try to parse as JSON to get error details
#                     try:
#                         response_data = json.loads(response_text) if response_text else {}
#                     except json.JSONDecodeError:
#                         # If not JSON, use raw text (limit length for safety)
#                         response_data = {"raw_response": response_text[:1000]}
                    
#                     # Print full response for debugging
#                     print(f"🚨 [perplexity_search] Perplexity API error response (status {resp.status}):", flush=True)
#                     print(f"🚨 [perplexity_search] Response body: {json.dumps(response_data, indent=2)}", flush=True)
                    
#                     # Handle specific status codes with detailed messages
#                     if resp.status == 400:
#                         error_msg = (
#                             f"❌ Perplexity API bad request (400) for query '{query}'. "
#                             f"Response: {json.dumps(response_data)}"
#                         )
#                     elif resp.status == 401:
#                         error_msg = (
#                             f"❌ Perplexity API authentication failed (401 Unauthorized) for query '{query}'. "
#                             f"The API key may be invalid or expired. "
#                             f"Response: {json.dumps(response_data)}"
#                         )
#                     elif resp.status == 403:
#                         error_msg = (
#                             f"❌ Perplexity API access forbidden (403) for query '{query}'. "
#                             f"Your API key may not have permission to access this resource. "
#                             f"Response: {json.dumps(response_data)}"
#                         )
#                     elif resp.status == 429:
#                         error_msg = (
#                             f"❌ Perplexity API rate limit exceeded (429) for query '{query}'. "
#                             f"Please wait before making more requests. "
#                             f"Response: {json.dumps(response_data)}"
#                         )
#                     else:
#                         # Generic error for other 4xx/5xx status codes
#                         error_msg = (
#                             f"❌ Perplexity API error (status {resp.status}) for query '{query}'. "
#                             f"Response: {json.dumps(response_data)}"
#                         )
                    
#                     print(f"🚨 [perplexity_search] {error_msg}", flush=True)
#                     raise ToolException(error_msg)
                
#                 # Parse successful response
#                 try:
#                     data = json.loads(response_text) if response_text else {}
#                 except json.JSONDecodeError as e:
#                     error_msg = (
#                         f"❌ Perplexity API returned invalid JSON for query '{query}'. "
#                         f"Response text: {response_text[:500]}"
#                     )
#                     print(f"🚨 [perplexity_search] {error_msg}", flush=True)
#                     raise ToolException(error_msg) from e
                
#                 # Check for API errors in response body
#                 if "error" in data:
#                     error_info = data["error"]
#                     error_msg = (
#                         f"❌ Perplexity API error for query '{query}': "
#                         f"{error_info.get('message', 'Unknown error')} "
#                         f"(Type: {error_info.get('type', 'unknown')})"
#                     )
#                     print(f"🚨 [perplexity_search] {error_msg}", flush=True)
#                     raise ToolException(error_msg)
                
#                 # Validate response structure
#                 if "choices" not in data or not data["choices"]:
#                     error_msg = (
#                         f"❌ Perplexity API returned invalid response for query '{query}': "
#                         f"No choices in response. Response: {str(data)[:200]}"
#                     )
#                     print(f"🚨 [perplexity_search] {error_msg}", flush=True)
#                     raise ToolException(error_msg)
                
#                 if "message" not in data["choices"][0] or "content" not in data["choices"][0]["message"]:
#                     error_msg = (
#                         f"❌ Perplexity API returned invalid response for query '{query}': "
#                         f"Missing content in response. Response: {str(data)[:200]}"
#                     )
#                     print(f"🚨 [perplexity_search] {error_msg}", flush=True)
#                     raise ToolException(error_msg)
                
#                 content = data["choices"][0]["message"]["content"]
#                 citations = data.get("citations") or []
#                 print(f"✅ [perplexity_search] Successfully got response for query '{query}' - Content length: {len(content)}, Citations: {len(citations)}", flush=True)
                
#                 # Print all citation URLs from Perplexity
#                 if citations:
#                     print(f"🔗 [perplexity_search] Perplexity returned {len(citations)} citation URLs for query '{query}':", flush=True)
#                     for i, citation_url in enumerate(citations, 1):
#                         print(f"🔗 [perplexity_search]   [{i}] {citation_url}", flush=True)
#                 else:
#                     print(f"⚠️  [perplexity_search] No citations returned by Perplexity for query '{query}'", flush=True)
                
#                 return {"query": query, "content": content, "citations": citations}
#         except ToolException:
#             # Re-raise ToolException to fail the research
#             raise
#         except aiohttp.ClientError as e:
#             error_msg = f"❌ Network error connecting to Perplexity API for query '{query}': {str(e)}"
#             print(f"🚨 [perplexity_search] {error_msg}", flush=True)
#             raise ToolException(error_msg) from e
#         except Exception as e:
#             error_msg = f"❌ Unexpected error calling Perplexity API for query '{query}': {str(e)}"
#             print(f"🚨 [perplexity_search] {error_msg}", flush=True)
#             raise ToolException(error_msg) from e

#     # Execute queries - ToolException will propagate and fail the research
#     # Use return_exceptions=False so ToolException propagates immediately
#     print(f"🔍 [perplexity_search] Starting to execute {len(queries)} search queries", flush=True)
#     async with aiohttp.ClientSession() as session:
#         try:
#             results = await asyncio.gather(*[_run_query(session, q) for q in queries], return_exceptions=False)
#             print(f"✅ [perplexity_search] Successfully completed {len(results)} search queries", flush=True)
#             for i, result in enumerate(results, 1):
#                 query = result.get("query", "unknown")
#                 citations_count = len(result.get("citations", []))
#                 print(f"✅ [perplexity_search] Query {i}: '{query}' - Found {citations_count} citations", flush=True)
#         except ToolException:
#             # Re-raise ToolException to fail the research
#             raise
#         except Exception as e:
#             # Check if it's an ExceptionGroup containing ToolException
#             if hasattr(e, "exceptions"):
#                 for sub_exc in e.exceptions:
#                     if isinstance(sub_exc, ToolException):
#                         raise sub_exc
#             # If it's a different error, wrap it as ToolException
#             error_msg = f"❌ Failed to execute Perplexity search queries: {str(e)}"
#             print(f"🚨 [perplexity_search] {error_msg}", flush=True)
#             raise ToolException(error_msg) from e

#     def _extract_title_from_url(
#         url: str, query: str = "", is_primary: bool = True
#     ) -> str:
#         """Extract a meaningful title from a URL or generate a descriptive one."""
#         try:
#             parsed = urlparse(url)
#             domain = parsed.netloc.replace("www.", "")

#             # Extract meaningful parts from domain
#             if domain:
#                 # Use domain name as base, capitalize appropriately
#                 domain_parts = domain.split(".")
#                 if len(domain_parts) >= 2:
#                     site_name = domain_parts[-2].capitalize()
#                 else:
#                     site_name = domain.capitalize()

#                 if is_primary and query:
#                     return f"{site_name} - {query}"
#                 elif is_primary:
#                     return f"{site_name} - Perplexity Search Result"
#                 else:
#                     return f"{site_name} - Supporting Source"
#             else:
#                 # Fallback if URL parsing fails
#                 if is_primary and query:
#                     return f"Perplexity Search Result: {query}"
#                 elif is_primary:
#                     return "Perplexity Search Result"
#                 else:
#                     return "Perplexity Supporting Source"
#         except Exception:
#             # Fallback to generic title
#             if is_primary and query:
#                 return f"Perplexity Search Result: {query}"
#             elif is_primary:
#                 return "Perplexity Search Result"
#             else:
#                 return "Perplexity Supporting Source"

#     # Collect all sources from all queries
#     all_sources = []
#     source_counter = 1

#     print(f"🔗 [perplexity_search] Processing sources from {len(results)} search results", flush=True)
    
#     for result in results:
#         citations = result.get("citations", [])
#         content = result.get("content", "")
#         query = result.get("query", "")

#         print(f"🔗 [perplexity_search] Processing query '{query}' - Found {len(citations)} citations", flush=True)
#         if citations:
#             for i, citation_url in enumerate(citations, 1):
#                 print(f"🔗 [perplexity_search]   Citation {i}: {citation_url}", flush=True)

#         if not citations:
#             # If no citations, create a single source entry with the content
#             title = _extract_title_from_url(
#                 "https://www.perplexity.ai", query, is_primary=True
#             )
#             all_sources.append(
#                 {
#                     "title": title,
#                     "url": "https://www.perplexity.ai",
#                     "content": content,
#                     "source_number": source_counter,
#                 }
#             )
#             source_counter += 1
#         else:
#             # Create a source entry for each citation
#             for i, citation_url in enumerate(citations):
#                 is_primary = i == 0
#                 title = _extract_title_from_url(
#                     citation_url, query, is_primary=is_primary
#                 )

#                 if is_primary:
#                     # First citation gets the full synthesized content
#                     all_sources.append(
#                         {
#                             "title": title,
#                             "url": citation_url,
#                             "content": content,
#                             "source_number": source_counter,
#                         }
#                     )
#                 else:
#                     # Additional citations are supporting sources
#                     all_sources.append(
#                         {
#                             "title": title,
#                             "url": citation_url,
#                             "content": f"Supporting source referenced in the main answer for query: {query}",
#                             "source_number": source_counter,
#                         }
#                     )
#                 source_counter += 1

#     # Format output to match Tavily format
#     if not all_sources:
#         return "No valid search results found. Please try different search queries or use a different search API."

#     formatted_output = "Search results: \n\n"
#     for source in all_sources:
#         formatted_output += (
#             f"\n\n--- SOURCE {source['source_number']}: {source['title']} ---\n"
#         )
#         formatted_output += f"URL: {source['url']}\n\n"
#         formatted_output += f"SUMMARY:\n{source['content']}\n\n"
#         formatted_output += "\n\n" + "-" * 80 + "\n"

#     return formatted_output


# def perplexity_search_legacy(search_queries):
#     """Search the web using the Perplexity API.

#     Args:
#         search_queries (List[SearchQuery]): List of search queries to process

#     Returns:
#         List[dict]: List of search responses from Perplexity API, one per query. Each response has format:
#             {
#                 'query': str,                    # The original search query
#                 'follow_up_questions': None,
#                 'answer': None,
#                 'images': list,
#                 'results': [                     # List of search results
#                     {
#                         'title': str,            # Title of the search result
#                         'url': str,              # URL of the result
#                         'content': str,          # Summary/snippet of content
#                         'score': float,          # Relevance score
#                         'raw_content': str|None  # Full content or None for secondary citations
#                     },
#                     ...
#                 ]
#             }
#     """
#     headers = {
#         "accept": "application/json",
#         "content-type": "application/json",
#         "Authorization": f"Bearer {os.getenv('PERPLEXITY_API_KEY')}",
#     }

#     search_docs = []
#     for query in search_queries:
#         payload = {
#             "model": "sonar-pro",
#             "messages": [
#                 {
#                     "role": "system",
#                     "content": "Search the web and provide factual information with sources.",
#                 },
#                 {"role": "user", "content": query},
#             ],
#         }

#         response = requests.post(
#             "https://api.perplexity.ai/chat/completions", headers=headers, json=payload
#         )
#         response.raise_for_status()  # Raise exception for bad status codes

#         # Parse the response
#         data = response.json()
#         content = data["choices"][0]["message"]["content"]
#         citations = data.get("citations", ["https://perplexity.ai"])

#         # Create results list for this query
#         results = []

#         # First citation gets the full content
#         results.append(
#             {
#                 "title": f"Perplexity Search, Source 1",
#                 "url": citations[0],
#                 "content": content,
#                 "raw_content": content,
#                 "score": 1.0,  # Adding score to match Tavily format
#             }
#         )

#         # Add additional citations without duplicating content
#         for i, citation in enumerate(citations[1:], start=2):
#             results.append(
#                 {
#                     "title": f"Perplexity Search, Source {i}",
#                     "url": citation,
#                     "content": "See primary source for full content",
#                     "raw_content": None,
#                     "score": 0.5,  # Lower score for secondary sources
#                 }
#             )

#         # Format response to match Tavily structure
#         search_docs.append(
#             {
#                 "query": query,
#                 "follow_up_questions": None,
#                 "answer": None,
#                 "images": [],
#                 "results": results,
#             }
#         )

#     return search_docs
