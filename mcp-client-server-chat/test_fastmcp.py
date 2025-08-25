import requests
import json
import re

session = requests.Session()
url = "http://localhost:8000/mcp"
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream"
}

def parse_sse_response(response_text):
    """Parse server-sent events response"""
    lines = response_text.strip().split('\n')
    data_line = None
    for line in lines:
        if line.startswith('data: '):
            data_line = line[6:]  # Remove 'data: ' prefix
            break
    
    if data_line:
        try:
            return json.loads(data_line)
        except json.JSONDecodeError:
            return {"error": "Failed to parse JSON", "raw": data_line}
    return {"error": "No data found", "raw": response_text}

# Initialize
init_data = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "python-client", "version": "1.0.0"}
    }
}

response = session.post(url, json=init_data, headers=headers)
print("Init response status:", response.status_code)
init_result = parse_sse_response(response.text)
print("Init result:", json.dumps(init_result, indent=2))

# Send initialized notification (this is a notification, not expecting response)
initialized_data = {
    "jsonrpc": "2.0",
    "method": "notifications/initialized"
}

response = session.post(url, json=initialized_data, headers=headers)
print("Initialized notification status:", response.status_code)

# Get tools - use session cookies for maintaining state
tools_data = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {}
}

response = session.post(url, json=tools_data, headers=headers)
print("Tools response status:", response.status_code)
if response.status_code == 200:
    tools_result = parse_sse_response(response.text)
    print("Tools:", json.dumps(tools_result, indent=2))
else:
    print("Tools error:", response.text)

# Test calling a tool - health check
tool_call_data = {
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
        "name": "health_check",
        "arguments": {}
    }
}

response = session.post(url, json=tool_call_data, headers=headers)
print("Health check status:", response.status_code)
if response.status_code == 200:
    health_result = parse_sse_response(response.text)
    print("Health check:", json.dumps(health_result, indent=2))
else:
    print("Health check error:", response.text)

# Test calling redis_get_token
redis_call_data = {
    "jsonrpc": "2.0",
    "id": 4,
    "method": "tools/call",
    "params": {
        "name": "redis_get_token",
        "arguments": {
            "key": "test_session_123"
        }
    }
}

response = session.post(url, json=redis_call_data, headers=headers)
print("Redis get token status:", response.status_code)
if response.status_code == 200:
    redis_result = parse_sse_response(response.text)
    print("Redis get token:", json.dumps(redis_result, indent=2))
else:
    print("Redis get token error:", response.text)