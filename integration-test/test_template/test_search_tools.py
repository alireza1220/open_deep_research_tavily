#!/usr/bin/env python3
"""Quick test script to verify Tavily and Perplexity search tools work correctly."""

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

from open_deep_research.perplexity_utils import perplexity_search
from open_deep_research.utils import tavily_search


async def test_tavily():
    """Test Tavily search tool."""
    print("=" * 80)
    print("Testing Tavily Search Tool")
    print("=" * 80)
    
    # Set environment variable for API key
    tavily_key = os.getenv("TAVILY_API_KEY")
    if not tavily_key:
        print("\n❌ Tavily test FAILED: TAVILY_API_KEY not set")
        return False
    
    # Set GET_API_KEYS_FROM_CONFIG to use config-based keys
    os.environ["GET_API_KEYS_FROM_CONFIG"] = "true"
    
    # Tavily also needs OpenAI key for summarization
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
            {"queries": ["Python programming"], "max_results": 2},
            config=config
        )
        print("\n✅ Tavily test PASSED")
        print(f"Result length: {len(result)} characters")
        print(f"First 200 chars: {result[:200]}...")
        print("\n" + "-" * 80)
        return True
    except Exception as e:
        print(f"\n❌ Tavily test FAILED: {e}")
        import traceback
        traceback.print_exc()
        print("\n" + "-" * 80)
        return False


async def test_perplexity():
    """Test Perplexity search tool."""
    print("=" * 80)
    print("Testing Perplexity Search Tool")
    print("=" * 80)
    
    # Set environment variable for API key
    perplexity_key = os.getenv("PERPLEXITY_API_KEY")
    if not perplexity_key:
        print("\n❌ Perplexity test FAILED: PERPLEXITY_API_KEY not set")
        return False
    
    # Set GET_API_KEYS_FROM_CONFIG to use config-based keys
    os.environ["GET_API_KEYS_FROM_CONFIG"] = "true"
    
    config = RunnableConfig(
        configurable={
            "apiKeys": {"PERPLEXITY_API_KEY": perplexity_key}
        }
    )
    
    try:
        # perplexity_search is a tool, use ainvoke
        result = await perplexity_search.ainvoke(
            {"queries": ["Python programming"]},
            config=config
        )
        print("\n✅ Perplexity test PASSED")
        print(f"Result length: {len(result)} characters")
        print(f"First 200 chars: {result[:200]}...")
        print("\n" + "-" * 80)
        return True
    except Exception as e:
        print(f"\n❌ Perplexity test FAILED: {e}")
        import traceback
        traceback.print_exc()
        print("\n" + "-" * 80)
        return False


async def main():
    """Run both tests."""
    print("\n🔍 Testing Search Tools\n")
    
    tavily_ok = await test_tavily()
    perplexity_ok = await test_perplexity()
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Tavily: {'✅ PASSED' if tavily_ok else '❌ FAILED'}")
    print(f"Perplexity: {'✅ PASSED' if perplexity_ok else '❌ FAILED'}")
    
    if tavily_ok and perplexity_ok:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

