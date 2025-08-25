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
redis_url = os.getenv('REDIS_URL', '')
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
    
    def _extract_path_from_entry(self, entry) -> str:
        """Extract API path from RSS entry - customize this"""
        title = entry.get('title', '')
        description = entry.get('description', '')
        link = entry.get('link', '')
        
        # Look for API paths in title, description, or link
        text_to_search = f"{title} {description} {link}".lower()
        
        # Common API path patterns
        import re
        
        # Look for explicit API paths
        api_patterns = [
            r'/api/v\d+/[a-zA-Z0-9/_-]+',  # /api/v1/users, /api/v2/notifications
            r'/v\d+/[a-zA-Z0-9/_-]+',      # /v1/users
            r'/[a-zA-Z]+(?:/[a-zA-Z0-9_-]+)*'  # /users, /notifications/list
        ]
        
        for pattern in api_patterns:
            matches = re.findall(pattern, text_to_search)
            if matches:
                # Return the first valid-looking path
                for match in matches:
                    if len(match) > 3:  # Ensure it's a meaningful path
                        return match
        
        # If no explicit path found, try to infer from keywords
        if 'user' in text_to_search:
            return '/users'
        elif 'notification' in text_to_search:
            return '/notifications'
        elif 'message' in text_to_search:
            return '/messages'
        elif 'auth' in text_to_search or 'login' in text_to_search:
            return '/auth'
        elif 'profile' in text_to_search:
            return '/profile'
        
        return ''

    def _extract_keywords_from_entry(self, entry) -> List[str]:
        """Extract keywords from RSS entry - customize this"""
        title = entry.get('title', '').lower()
        description = entry.get('description', '').lower()
        link = entry.get('link', '').lower()
        
        # Combine all text sources
        all_text = f"{title} {description} {link}"
        
        # Extract meaningful keywords
        keywords = []
        
        # Common API-related keywords
        api_keywords = [
            'get', 'post', 'put', 'delete', 'patch',
            'user', 'users', 'notification', 'notifications',
            'message', 'messages', 'auth', 'login', 'logout',
            'profile', 'settings', 'data', 'list', 'create',
            'update', 'remove', 'fetch', 'send', 'receive'
        ]
        
        # Add API keywords that are found
        for keyword in api_keywords:
            if keyword in all_text:
                keywords.append(keyword)
        
        # Extract other meaningful words (length > 3, not common words)
        words = all_text.split()
        common_words = {'the', 'and', 'for', 'are', 'with', 'this', 'that', 'from', 'they', 'have', 'will', 'been', 'said'}
        
        for word in words:
            clean_word = word.strip('.,!?()[]{}":;')
            if len(clean_word) > 3 and clean_word not in common_words and clean_word not in keywords:
                keywords.append(clean_word)
        
        return list(set(keywords))  # Remove duplicates

    async def load_rss_endpoints(self) -> List[APIEndpoint]:
        """Load API endpoints from RSS feed"""
        try:
            print(f"Loading RSS feed from: {RSS_FEED_URL}")
            response = await http_client.get(RSS_FEED_URL)
            response.raise_for_status()
            
            feed = feedparser.parse(response.text)
            endpoints = []
            
            print(f"Found {len(feed.entries)} RSS entries")
            
            for i, entry in enumerate(feed.entries):
                title = entry.get('title', '')
                description = entry.get('description', '')
                
                print(f"Entry {i+1}: Title='{title}', Description='{description[:100]}...'")
                
                # Determine HTTP method - be more flexible
                method = None
                text_to_check = f"{title} {description}".lower()
                
                if any(word in text_to_check for word in ['get', 'fetch', 'retrieve', 'list', 'show']):
                    method = 'GET'
                elif any(word in text_to_check for word in ['post', 'create', 'add', 'send']):
                    method = 'POST'
                elif any(word in text_to_check for word in ['put', 'update', 'modify', 'edit']):
                    method = 'PUT'
                elif any(word in text_to_check for word in ['delete', 'remove']):
                    method = 'DELETE'
                else:
                    # Default to GET if no method is clearly indicated
                    method = 'GET'
                
                # Extract path and keywords
                path = self._extract_path_from_entry(entry)
                keywords = self._extract_keywords_from_entry(entry)
                
                print(f"  -> Method: {method}, Path: '{path}', Keywords: {keywords[:3]}")
                
                # Always add the endpoint, even if path is empty (we'll use a default)
                if not path:
                    path = '/api/v1/default'  # Default path if none found
                
                endpoints.append(APIEndpoint(
                    method=method,
                    path=path,
                    keywords=keywords,
                    description=description or title
                ))
            
            self.rss_endpoints = endpoints
            print(f"Successfully loaded {len(endpoints)} API endpoints")
            return endpoints
            
        except Exception as e:
            print(f"Error loading RSS endpoints: {e}")
            return []
    
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


