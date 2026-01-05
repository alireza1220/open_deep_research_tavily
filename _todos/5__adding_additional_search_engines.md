<!-- 5__adding_additional_search_engines.md -->

adding additional search engines such as perplexity if tavily not available

1. Upldaing the requirement and adding perplexity as the back up engine using uv add perplexityai
2. Updating related prompt engineering to ensure it is working properly.
3. Upadting the codebase and ensuring the call to the perplexity endpoints preferebly using perplexity sdk not the http call
4. adding the .env file to set the default engine if nothing provided tavily should be used for the default engine
5. 