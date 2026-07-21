import os
import requests
from typing import Type, Any
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

class HermesSearchInput(BaseModel):
    query: str = Field(description="Search query to execute.")
    max_results: int = Field(default=5, description="Maximum number of results to return.")

class HermesSearchTool(BaseTool):
    name: str = "hermes_search_tool"
    description: str = "A search engine optimized for comprehensive, accurate, and trusted results using local Hermes Stack."
    args_schema: Type[BaseModel] = HermesSearchInput

    # Pydantic v2 requires this if we define fields not in BaseModel, but it's simpler to use PrivateAttr or just not define it
    # We will fetch URL inside the function to keep it simple

    def _run(self, query: str, max_results: int = 5, **kwargs: Any) -> Any:
        """Use the tool."""
        # Gunakan SearXNG lokal Hermes Stack atau endpoint v1/tools
        # Default nembak ke SearXNG lokal (biasanya searxng container di port tertentu, misal 8080)
        # Jika Rois menggunakan endpoint wrapper, sesuaikan HERMES_SEARCH_URL di .env
        search_url = os.environ.get("HERMES_SEARCH_URL", "http://searxng:8080/search")
        
        try:
            params = {
                "q": query,
                "format": "json",
                "engines": "google,bing,duckduckgo",
                "language": "en"
            }
            
            # Kita coba pakai format request searxng standard
            response = requests.get(search_url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            results = data.get("results", [])
            
            # Format output mirip dengan Tavily agar LLM tidak bingung
            formatted_results = []
            for item in results[:max_results]:
                formatted_results.append({
                    "url": item.get("url", ""),
                    "content": item.get("content", item.get("snippet", "")),
                    "title": item.get("title", "")
                })
                
            if not formatted_results:
                return "No relevant search results found."
                
            return formatted_results
            
        except Exception as e:
            # Fallback format jika request gagal
            return f"Error executing Hermes Stack search: {str(e)}"