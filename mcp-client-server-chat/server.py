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
from functools import wraps
import base64

load_dotenv()
mcp = FastMCP("AI Agent Tools Server", port=8000, debug=True)
redis_url = os.getenv('REDIS_URL', '')
redis_client = redis.from_url(redis_url, decode_responses=True)
http_client = httpx.AsyncClient()
BASE_API_URL = os.getenv('API_BASE_URL', "https://api.test.computesphere.com/api/v1")
BASE_URL = "https://api.test.computesphere.com"
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
        """Extract API path from RSS entry"""
        title = entry.get('title', '')
        description = entry.get('description', '')
        link = entry.get('link', '')
        import re
        title_pattern = r'(?:GET|POST|PUT|DELETE|PATCH)\s+(/[^\s]+)'
        title_match = re.search(title_pattern, title, re.IGNORECASE)
        if title_match:
            path = title_match.group(1)
            path = re.sub(r'\{[^}]+\}', '', path)
            path = path.rstrip('/').split('?')[0]
            if path and len(path) > 1:
                return path
        if link:
            url_pattern = r'https?://[^/]+(/api/v\d+/[^?\s]*)'
            url_match = re.search(url_pattern, link)
            if url_match:
                path = url_match.group(1)
                path = re.sub(r'\{[^}]+\}', '', path)
                path = path.rstrip('/').split('?')[0]
                if path and len(path) > 1:
                    return path
        text_to_search = f"{title} {description}".lower()
        fallback_mappings = {
            'projects': '/projects',
            'environments': '/environments', 
            'notifications': '/notifications',
            'services': '/services',
            'users': '/users',
            'user': '/users',
            'auth': '/auth',
            'login': '/auth',
            'profile': '/profile',
            'settings': '/settings'
        }
        
        for keyword, path in fallback_mappings.items():
            if keyword in text_to_search:
                if 'notification' in text_to_search and 'settings' in text_to_search:
                    return '/notifications/settings'
                elif 'users' in text_to_search and 'projects' in text_to_search:
                    return '/users/projects'
                return path
        
        return '/api/v1/default'

    def build_headers(
        token: str,
        content_type: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """Build standard headers for API requests"""
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:141.0) Gecko/20100101 Firefox/141.0",
            "Accept": "application/json, text/plain, */*",
            "x-user-token": token,
            "x-account-id": ACCOUNT_ID,
            "Origin": "https://console.test.computesphere.com",
            "Referer": "https://console.test.computesphere.com/",
        }
        if content_type:
            headers["Content-Type"] = content_type
        if extra_headers:
            headers.update(extra_headers)
        return headers

    def _extract_keywords_from_entry(self, entry) -> List[str]:
        """Extract keywords from RSS entry - customize this"""
        title = entry.get('title', '').lower()
        description = entry.get('description', '').lower()
        link = entry.get('link', '').lower()
        all_text = f"{title} {description} {link}"
        
        keywords = []
        api_keywords = [
            'get', 'post', 'put', 'delete', 'patch',
            'user', 'users', 'notification', 'notifications',
            'message', 'messages', 'auth', 'login', 'logout',
            'profile', 'settings', 'data', 'list', 'create',
            'update', 'remove', 'fetch', 'send', 'receive'
        ]
        
        for keyword in api_keywords:
            if keyword in all_text:
                keywords.append(keyword)
        
        words = all_text.split()
        common_words = {'the', 'and', 'for', 'are', 'with', 'this', 'that', 'from', 'they', 'have', 'will', 'been', 'said'}
        
        for word in words:
            clean_word = word.strip('.,!?()[]{}":;')
            if len(clean_word) > 3 and clean_word not in common_words and clean_word not in keywords:
                keywords.append(clean_word)
        
        return keywords[:10]

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
                    method = 'GET'
                path = self._extract_path_from_entry(entry)
                keywords = self._extract_keywords_from_entry(entry)
                
                print(f"  -> Method: {method}, Path: '{path}', Keywords: {keywords[:3]}")
                if not path:
                    path = '/api/v1/default'
                
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
session_manager = SessionManager()
# Authentication Middleware
async def auth_middleware(func, *args, **kwargs) -> str:
    """Middleware to check HTTP Basic Auth for all MCP tool calls"""
    try:
        auth_header = kwargs.get("Authorization") or kwargs.get("authorization")
        if not auth_header:
            return json.dumps(
                {
                    "error": "Authentication failed: Authorization header is missing",
                    "suggestion": "Please provide HTTP Basic Auth credentials."
                }
            )
        if not auth_header.startswith("Basic "):
            return json.dumps(
                {
                    "error": "Authentication failed: Authorization header must start with 'Basic '",
                    "suggestion": "Use HTTP Basic Auth with username and password."
                }
            )
        try:
            encoded_credentials = auth_header.split(" ", 1)[1]
            decoded_bytes = base64.b64decode(encoded_credentials)
            decoded_credentials = decoded_bytes.decode("utf-8")
            username, password = decoded_credentials.split(":", 1)
        except Exception:
            return json.dumps(
                {
                    "error": "Authentication failed: Invalid Basic Auth encoding",
                    "suggestion": "Ensure credentials are base64 encoded as 'username:password'."
                }
            )
        if username != "admin" or password != "admin":
            return json.dumps(
                {
                    "error": "Authentication failed: Invalid username or password",
                    "suggestion": "Use username 'admin' and password 'admin'."
                }
            )
        result = await func(*args, **kwargs)
        return result

    except Exception as e:
        return json.dumps(
            {
                "error": f"Authentication middleware error: {str(e)}",
                "suggestion": "Please check Basic Auth header format and credentials."
            }
        )

def with_auth_middleware(tool_func):
    @wraps(tool_func)
    async def wrapper(*args, **kwargs):
        return await auth_middleware(tool_func, *args, **kwargs)
    return wrapper

@mcp.tool(name="health_check", description="Check server health status")
async def health_check() -> str:
    """Health check endpoint"""
    return json.dumps({"status": "healthy", "message": "Server is running"})

@mcp.tool(name="redis_set_token", description="Set authentication token in Redis")
@with_auth_middleware
async def redis_get_token(key: str, Authorization: str) -> str:
    """Get authentication token from Redis"""
    try:
        token = await redis_client.get(key)
        if not token:
            return json.dumps({"error": "Token not found", "key": key})
        return json.dumps({"success": True, "token": token, "key": key})
    except Exception as e:
        return json.dumps({"error": str(e), "key": key})

@mcp.tool(name="rss_feed_read", description="Read RSS feed and load API endpoints")
@with_auth_middleware
async def rss_feed_read(Authorization: str) -> str:
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

@mcp.tool(name="perizer_data_curl_get", description="Make HTTP GET request")
@with_auth_middleware
async def perizer_data_curl_get(url: str, parameters2_Value: str, Authorization: str) -> str:
    """Make HTTP GET request"""
    try:
        headers = session_manager.build_headers(parameters2_Value)
        
        response = await http_client.get(url, headers=headers)
        response.raise_for_status()
        
        return json.dumps({
            "success": True,
            "status_code": response.status_code,
            "data": response.json()
        })
        
    except Exception as e:
        return json.dumps({"error": str(e), "url": url})

@mcp.tool(name="perizer_data_curl_post", description="Make HTTP POST request")
@with_auth_middleware
async def perizer_data_curl_post(
    url: str,
    parameters4_Value: str,
    Authorization: str,
    parameters0_Name: str = "",
    parameters0_Value: str = "",
    parameters1_Name: str = "",
    parameters1_Value: str = ""
) -> str:
    """Make HTTP POST request"""
    try:
        headers = session_manager.build_headers(parameters4_Value, content_type="application/json")
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

@mcp.tool(name="perizer_data_curl_put", description="Make HTTP PUT request")
@with_auth_middleware
async def perizer_data_curl_put(url: str, parameters4_Value: str, JSON: dict, Authorization: str) -> str:
    """Make HTTP PUT request"""
    try:
        headers = session_manager.build_headers(parameters4_Value, content_type="application/json")
        response = await http_client.put(url, headers=headers, json=JSON)
        print("response",response)
        response.raise_for_status()
        
        return json.dumps({
            "success": True,
            "status_code": response.status_code,
            "data": response.json()
        })
        
    except Exception as e:
        return json.dumps({"error": str(e), "url": url})

@mcp.tool(name="ai_agent_process", description="Process user messages and execute API calls")
@with_auth_middleware
async def ai_agent_process(user_message: str, session_id: str, Authorization: str) -> str:
    """AI Agent tool that processes user messages and executes appropriate API calls"""
    try:
        token = await redis_client.get(session_id)
        if not token:
            return json.dumps({"error": "Token not found", "session_id": session_id})
        endpoints = await session_manager.load_rss_endpoints()
        if not endpoints:
            return json.dumps({"error": "No RSS endpoints available"})
        best_match = session_manager.match_message_to_endpoint(user_message)

        if not best_match:
            return json.dumps({
                "error": "No matching endpoint found",
                "message": "I cannot find the answer in the available resources.",
                "suggestion": "Try asking about users, notifications, messages, or other available API endpoints."
            })
        # Check if path already includes /api/v1, if so don't add it again
        if best_match.path.startswith('/api/v1'):
            full_url = BASE_URL + best_match.path
        else:
            full_url = f"{BASE_URL}/api/v1{best_match.path}"

        try:
            if best_match.method == 'GET':
                api_response_str = await perizer_data_curl_get(full_url, token)
                api_response = json.loads(api_response_str)
                
            elif best_match.method == 'POST':
                api_response_str = await perizer_data_curl_post(full_url, token)
                api_response = json.loads(api_response_str)
                
            elif best_match.method == 'PUT':
                api_response_str = await perizer_data_curl_put(full_url, token, {})
                api_response = json.loads(api_response_str)
            else:
                return json.dumps({"error": f"Unsupported HTTP method: {best_match.method}"})
            if api_response.get("success"):
                formatted_response = _format_api_response_for_human(api_response.get("data", {}))
                
                return json.dumps({
                    "success": True,
                    "method": best_match.method,
                    "url": full_url,
                    "status_code": api_response.get("status_code"),
                    "matched_endpoint": {
                        "path": best_match.path,
                        "keywords": best_match.keywords[:5],
                        "description": best_match.description
                    },
                    "raw_response": api_response.get("data", {}),
                    "formatted_response": formatted_response,
                    "suggestion": "You can ask about other endpoints or request specific actions like creating, updating, or deleting items."
                })
            else:
                return json.dumps({
                    "error": f"API request failed: {api_response.get('error', 'Unknown error')}",
                    "url": full_url,
                    "method": best_match.method,
                    "suggestion": "Please check your session token or try a different request."
                })
                
        except Exception as e:
            return json.dumps({
                "error": f"API call execution failed: {str(e)}",
                "url": full_url,
                "method": best_match.method
            })
            
    except Exception as e:
        return json.dumps({"error": f"Agent processing failed: {str(e)}"})

def _format_api_response_for_human(data: Any) -> str:
    """Convert API response data to human-readable format"""
    if isinstance(data, dict):
        if not data:
            return "No data found."
        
        formatted = "Here's the information I found:\n"
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                formatted += f"• {k}: {json.dumps(v, indent=2)}\n"
            else:
                formatted += f"• {k}: {v}\n"
        return formatted
        
    elif isinstance(data, list):
        if not data:
            return "No items found."
        
        formatted = f"Found {len(data)} items:\n"
        for i, item in enumerate(data[:5], 1):
            if isinstance(item, dict):
                formatted += f"{i}. {json.dumps(item, indent=2)}\n"
            else:
                formatted += f"{i}. {item}\n"
        
        if len(data) > 5:
            formatted += f"... and {len(data) - 5} more items."
        return formatted
        
    return str(data)

if __name__ == "__main__":
    print("Starting MCP Server on http://localhost:8000")
    try:
        mcp.run()
    except Exception as e:
        print(f"Server failed to start: {e}")