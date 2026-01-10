#!/usr/bin/env python3
"""Test script to verify Tavily and Perplexity output formats match exactly."""

import asyncio
import os
from pathlib import Path
from langchain_core.runnables import RunnableConfig

# Load .env file if it exists
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip().strip('"').strip("'")

os.environ["GET_API_KEYS_FROM_CONFIG"] = "true"

from open_deep_research.perplexity_utils import perplexity_search
from open_deep_research.utils import tavily_search


async def test_tavily_format():
    """Test Tavily output format."""
    print("=" * 80)
    print("TAVILY OUTPUT FORMAT TEST")
    print("=" * 80)
    
    tavily_key = os.getenv("TAVILY_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY", "")
    
    config = RunnableConfig(
        configurable={
            "apiKeys": {
                "TAVILY_API_KEY": tavily_key,
                "OPENAI_API_KEY": openai_key
            }
        }
    )
    
    try:
        result = await tavily_search.ainvoke(
            {"queries": ["artificial intelligence"], "max_results": 2},
            config=config
        )
        print("\n✅ Tavily output received")
        print(f"Total length: {len(result)} characters\n")
        print("=" * 80)
        print("FULL OUTPUT:")
        print("=" * 80)
        print(result)
        print("=" * 80)
        return result
    except Exception as e:
        print(f"\n❌ Tavily test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_perplexity_format():
    """Test Perplexity output format."""
    print("\n" + "=" * 80)
    print("PERPLEXITY OUTPUT FORMAT TEST")
    print("=" * 80)
    
    perplexity_key = os.getenv("PERPLEXITY_API_KEY")
    
    config = RunnableConfig(
        configurable={
            "apiKeys": {"PERPLEXITY_API_KEY": perplexity_key}
        }
    )
    
    try:
        result = await perplexity_search.ainvoke(
            {"queries": ["artificial intelligence"]},
            config=config
        )
        print("\n✅ Perplexity output received")
        print(f"Total length: {len(result)} characters\n")
        print("=" * 80)
        print("FULL OUTPUT:")
        print("=" * 80)
        print(result)
        print("=" * 80)
        return result
    except Exception as e:
        print(f"\n❌ Perplexity test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None


def analyze_format(output: str, tool_name: str):
    """Analyze the output format structure."""
    print(f"\n{'=' * 80}")
    print(f"{tool_name} FORMAT ANALYSIS")
    print("=" * 80)
    
    lines = output.split("\n")
    
    # Check for key format elements
    checks = {
        "Starts with 'Search results:'": output.startswith("Search results:"),
        "Contains 'SOURCE' entries": "SOURCE" in output,
        "Contains 'URL:' lines": "URL:" in output,
        "Contains 'SUMMARY:' lines": "SUMMARY:" in output,
        "Has separator lines (80 dashes)": "-" * 80 in output,
    }
    
    # Count SOURCE entries
    source_count = output.count("--- SOURCE")
    checks[f"Number of SOURCE entries: {source_count}"] = source_count > 0
    
    # Check structure pattern
    import re
    source_pattern = r"--- SOURCE \d+: (.+?) ---"
    url_pattern = r"URL: (.+)"
    summary_pattern = r"SUMMARY:\n(.+?)(?=\n\n---|$)"
    
    sources = re.findall(source_pattern, output)
    urls = re.findall(url_pattern, output)
    summaries = re.findall(summary_pattern, output, re.DOTALL)
    
    print("\nFormat Structure:")
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {check}")
    
    print(f"\nFound {len(sources)} sources:")
    for i, (source, url, summary) in enumerate(zip(sources[:3], urls[:3], summaries[:3]), 1):
        print(f"\n  Source {i}:")
        print(f"    Title: {source[:60]}...")
        print(f"    URL: {url[:60]}...")
        print(f"    Summary length: {len(summary)} chars")
    
    return checks, len(sources), len(urls), len(summaries)


async def compare_formats():
    """Compare Tavily and Perplexity output formats."""
    print("\n" + "=" * 80)
    print("COMPARING OUTPUT FORMATS")
    print("=" * 80)
    
    tavily_output = await test_tavily_format()
    perplexity_output = await test_perplexity_format()
    
    if not tavily_output or not perplexity_output:
        print("\n❌ Cannot compare - one or both outputs failed")
        return
    
    tavily_checks, tavily_sources, tavily_urls, tavily_summaries = analyze_format(
        tavily_output, "TAVILY"
    )
    perplexity_checks, perplexity_sources, perplexity_urls, perplexity_summaries = analyze_format(
        perplexity_output, "PERPLEXITY"
    )
    
    print("\n" + "=" * 80)
    print("FORMAT COMPARISON")
    print("=" * 80)
    
    # Compare key elements
    comparison = {
        "Starts with 'Search results:'": (
            tavily_checks["Starts with 'Search results:'"],
            perplexity_checks["Starts with 'Search results:'"]
        ),
        "Uses 'SOURCE X:' format": (
            tavily_checks["Contains 'SOURCE' entries"],
            perplexity_checks["Contains 'SOURCE' entries"]
        ),
        "Has 'URL:' lines": (
            tavily_checks["Contains 'URL:' lines"],
            perplexity_checks["Contains 'URL:' lines"]
        ),
        "Has 'SUMMARY:' lines": (
            tavily_checks["Contains 'SUMMARY:' lines"],
            perplexity_checks["Contains 'SUMMARY:' lines"]
        ),
        "Uses separator lines": (
            tavily_checks["Has separator lines (80 dashes)"],
            perplexity_checks["Has separator lines (80 dashes)"]
        ),
    }
    
    all_match = True
    for element, (tavily_ok, perplexity_ok) in comparison.items():
        match = tavily_ok == perplexity_ok and tavily_ok
        status = "✅ MATCH" if match else "❌ MISMATCH"
        print(f"{status}: {element}")
        print(f"         Tavily: {tavily_ok}, Perplexity: {perplexity_ok}")
        if not match:
            all_match = False
    
    print(f"\nStructure counts:")
    print(f"  Sources - Tavily: {tavily_sources}, Perplexity: {perplexity_sources}")
    print(f"  URLs - Tavily: {tavily_urls}, Perplexity: {perplexity_urls}")
    print(f"  Summaries - Tavily: {tavily_summaries}, Perplexity: {perplexity_summaries}")
    
    if all_match:
        print("\n🎉 Formats are standardized and match!")
    else:
        print("\n⚠️  Formats differ - standardization needed")
    
    return all_match


if __name__ == "__main__":
    result = asyncio.run(compare_formats())
    exit(0 if result else 1)

