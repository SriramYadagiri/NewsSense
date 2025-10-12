import os
import requests
import json
from typing import Optional, List
from agno.tools import Toolkit
from dotenv import load_dotenv

load_dotenv(override=True)
class GoogleSearchToolkit(Toolkit):
    """
    Google Search Tool using Custom Search JSON API.
    """

    def __init__(self, api_key: Optional[str] = None, cse_id: Optional[str] = None):
        self.api_key = api_key or os.getenv("GOOGLE_SEARCH_API_KEY")
        self.cse_id = cse_id or os.getenv("GOOGLE_CSE_ID")
        if not self.api_key or not self.cse_id:
            raise ValueError("GOOGLE_SEARCH_API_KEY and GOOGLE_CSE_ID must be set.")

        tools = [self.google_search]
        super().__init__(name="google_search_tool", tools=tools)

    def google_search(self, query: str) -> str:
        """
        Searches Google Custom Search API for relevant articles.
        Args:
            query (str): Search query.
        Returns:
            str: Formatted string of top search results.
        """
        print(f"[GoogleSearchTool] Searching for: {query}")

        response = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params={
                "key": self.api_key,
                "cx": self.cse_id,
                "q": query,
                "num": 5 # Limit to top 5 results
            }
        )

        if response.status_code != 200:
            return json.dumps({
                "error": f"Search failed: {response.status_code}",
                "details": response.text
            })

        results = response.json().get("items", [])
        formatted = []
        for item in results:
            formatted.append({
                "title": item.get("title"),
                "link": item.get("link"),
                "snippet": item.get("snippet")
            })

        return json.dumps(formatted, indent=2)
