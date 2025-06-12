import os
from tavily import TavilyClient
from typing import Dict, List, Optional

class WebSearchTool:
    """Tool for performing web searches using Tavily API"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize search tool with API key.

        Args:
            api_key (str, optional): Tavily API key. Defaults to env var TAVILY_API_KEY.
        """
        self.api_key = "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"
        if not self.api_key:
            raise ValueError("Tavily API key not found. Set TAVILY_API_KEY env var.")
        self.client = TavilyClient(api_key=self.api_key)

    def search(self, query: list, num_results: int = 10) -> List[Dict]:
        """
        Perform search via Tavily API.

        Args:
            query (str): Search query.
            num_results (int, optional): Number of results to return. Defaults to 5.

        Returns:
            List[Dict]: Search results with title, snippet, and link.
        """
        try:
            # Perform the search
            response = self.client.search(query=query, max_results=num_results, search_depth="advanced")
            results = response.get("results", [])

            # Process and return the results
            return [
                {
                    "title": result.get("title", ""),
                    "snippet": result.get("content", ""),
                    "link": result.get("url", "")
                }
                for result in results
            ]

        except Exception as e:
            print(f"Search error: {str(e)}")
            return []
