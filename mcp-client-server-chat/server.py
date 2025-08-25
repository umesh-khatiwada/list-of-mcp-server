# mcp_server.py - The MCP Server (replaces your second n8n workflow)
import asyncio
import json
import redis.asyncio as redis
import httpx
import feedparser
from typing import Dict, Any, Optional, List
from fastmcp import FastMCP
from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("AI Agent Tools Server")

# Redis client
redis_url = os.getenv('REDIS_URL', 'redis://default:')
redis_client = redis.from_url(redis_url, decode_responses=True)

# HTTP client
http_client = httpx.AsyncClient()

# Base API URL
BASE_API_URL = os.getenv('API_BASE_URL', "https://api.test.computesphere.com/api/v1")
ACCOUNT_ID = os.getenv('ACCOUNT_ID', "ed95ae9d-05ca-4c41-b233-0891e53316d4")
RSS_FEED_URL = os.getenv('RSS_FEED_URL', "https://umeshkhatiwada.com.np/assets/file/cm.rss")

class APIEndpoint(BaseModel):
    method: str
    path: str
    keywords: List[str]
    description: str

class SessionManager:
    """Manages session tokens and RSS feed data"""
    
    def __init__(self):
        self.rss_endpoints = []
        self.rss_last_updated = None
    
    async def load_rss_endpoints(self) -> List[APIEndpoint]:
        """Load API endpoints from RSS feed"""
        try:
            response = await http_client.get(RSS_FEED_URL)
            response.raise_for_status()
            
            feed = feedparser.parse(response.text)
            endpoints = []
            
            for entry in feed.entries:
                # Parse RSS entry to extract API information
                # You'll need to customize this based on your RSS structure
                title = entry.get('title', '')
                description = entry.get('description', '')
                
                # Example parsing - customize based on your RSS format
                if 'GET' in title or 'get' in description.lower():
                    method = 'GET'
                elif 'POST' in title or 'post' in description.lower():
                    method = 'POST'
                elif 'PUT' in title or 'put' in description.lower():
                    method = 'PUT'
                else:
                    continue
                
                # Extract path and keywords - customize this logic
                path = self._extract_path_from_entry(entry)
                keywords = self._extract_keywords_from_entry(entry)
                
                if path:
                    endpoints.append(APIEndpoint(
                        method=method,
                        path=path,
                        keywords=keywords,
                        description=description
                    ))
            
            self.rss_endpoints = endpoints
            return endpoints
            
        except Exception as e:
            print(f"Error loading RSS endpoints: {e}")
            return []
    
    def _extract_path_from_entry(self, entry) -> str:
        """Extract API path from RSS entry - customize this"""
        # Example implementation - you'll need to adapt this
        description = entry.get('description', '')
        # Look for path patterns in the description
        if '/api/' in description:
            # Extract path using regex or string parsing
            return '/users'  # Placeholder
        return ''
    
    def _extract_keywords_from_entry(self, entry) -> List[str]:
        """Extract keywords from RSS entry - customize this"""
        title = entry.get('title', '').lower()
        description = entry.get('description', '').lower()
        
        # Extract keywords from title and description
        keywords = []
        words = (title + ' ' + description).split()
        keywords.extend([word.strip('.,!?') for word in words if len(word) > 3])
        
        return list(set(keywords))  # Remove duplicates
    
    def match_message_to_endpoint(self, message: str) -> Optional[APIEndpoint]:
        """Match user message to API endpoint"""
        message_lower = message.lower()
        best_match = None
        highest_score = 0
        
        for endpoint in self.rss_endpoints:
            score = 0
            for keyword in endpoint.keywords:
                if keyword in message_lower:
                    score += 1
            
            if score > highest_score:
                highest_score = score
                best_match = endpoint
        
        return best_match if highest_score > 0 else None

# Initialize session manager
session_manager = SessionManager()

@mcp.tool()
async def health_check() -> str:
    """Health check endpoint"""
    return json.dumps({"status": "healthy", "message": "Server is running"})

@mcp.tool()
async def redis_get_token(key: str) -> str:
    """Get authentication token from Redis"""
    try:
        token = await redis_client.get(key)
        if not token:
            return json.dumps({"error": "Token not found", "key": key})
        return json.dumps({"success": True, "token": token, "key": key})
    except Exception as e:
        return json.dumps({"error": str(e), "key": key})

@mcp.tool()
async def rss_feed_read() -> str:
    """Read RSS feed and load API endpoints"""
    try:
        endpoints = await session_manager.load_rss_endpoints()
        return json.dumps({
            "success": True, 
            "endpoints_count": len(endpoints),
            "endpoints": [{"method": ep.method, "path": ep.path, "keywords": ep.keywords[:5]} for ep in endpoints]
        })
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool()
async def perizer_data_curl_get(url: str, parameters2_Value: str) -> str:
    """Make HTTP GET request"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:141.0) Gecko/20100101 Firefox/141.0",
            "Accept": "application/json, text/plain, */*",
            "x-user-token": parameters2_Value,
            "x-account-id": ACCOUNT_ID,
            "Origin": "https://console.test.computesphere.com",
            "Referer": "https://console.test.computesphere.com/"
        }
        
        response = await http_client.get(url, headers=headers)
        response.raise_for_status()
        
        return json.dumps({
            "success": True,
            "status_code": response.status_code,
            "data": response.json()
        })
        
    except Exception as e:
        return json.dumps({"error": str(e), "url": url})

@mcp.tool()
async def perizer_data_curl_post(url: str, parameters4_Value: str, parameters0_Name: str = "", parameters0_Value: str = "", parameters1_Name: str = "", parameters1_Value: str = "") -> str:
    """Make HTTP POST request"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:141.0) Gecko/20100101 Firefox/141.0",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "x-user-token": parameters4_Value,
            "x-account-id": ACCOUNT_ID,
            "Origin": "https://console.test.computesphere.com",
            "Referer": "https://console.test.computesphere.com/"
        }
        
        # Build request body
        body = {}
        if parameters0_Name and parameters0_Value:
            body[parameters0_Name] = parameters0_Value
        if parameters1_Name and parameters1_Value:
            body[parameters1_Name] = parameters1_Value
        
        response = await http_client.post(url, headers=headers, json=body)
        response.raise_for_status()
        
        return json.dumps({
            "success": True,
            "status_code": response.status_code,
            "data": response.json()
        })
        
    except Exception as e:
        return json.dumps({"error": str(e), "url": url})

@mcp.tool()
async def perizer_data_curl_put(url: str, parameters4_Value: str, JSON: dict) -> str:
    """Make HTTP PUT request"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:141.0) Gecko/20100101 Firefox/141.0",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "x-user-token": parameters4_Value,
            "x-account-id": ACCOUNT_ID,
            "Origin": "https://console.test.computesphere.com",
            "Referer": "https://console.test.computesphere.com/"
        }
        
        response = await http_client.put(url, headers=headers, json=JSON)
        response.raise_for_status()
        
        return json.dumps({
            "success": True,
            "status_code": response.status_code,
            "data": response.json()
        })
        
    except Exception as e:
        return json.dumps({"error": str(e), "url": url})

if __name__ == "__main__":
    print("Starting MCP Server on http://localhost:8000")
    print("Make sure to start this server before running the client")
    try:
        mcp.run()
    except Exception as e:
        print(f"Server failed to start: {e}")
        print("Check if port 8000 is available")


