from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os
from dotenv import load_dotenv
import asyncio
import uvicorn
import datetime
import json
from contextlib import asynccontextmanager
import httpx
import aiohttp

# Import your ComputesphereAgent (assuming it's in client.py)
# from client import ComputesphereAgent


# Load environment variables from .env
load_dotenv()

# Global agent instance
agent_instance = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown"""
    # Startup
    global agent_instance
    # Replace MockComputesphereAgent with ComputesphereAgent when available
    agent_instance = MockComputesphereAgent()
    await agent_instance.initialize_agent()
    print("✅ Agent initialized and ready!")
    
    yield
    
    # Shutdown
    if agent_instance:
        await agent_instance.close()
        print("🔄 Agent shutdown complete!")

app = FastAPI(
    title="Computesphere Agent API with UI", 
    version="1.0.0",
    lifespan=lifespan
)

# Set up templates
templates = Jinja2Templates(directory="templates")

class MockComputesphereAgent:
    def __init__(self):
        self.session_id = os.getenv("SESSION_ID", "5c669c6f-911a-41ac-a5bd-e11c848f2215")
        self.conversations = {}
        self.memories = {}
        self.server_client = ServerClient()
        
    async def initialize_agent(self):
        print("Mock agent initialized")
        # Try to connect to port 8000 server
        try:
            await self.server_client.make_request("/")
            print("✅ Connected to server on port 8001")
        except:
            print("⚠️  Server on port 8001 not accessible")
        
    async def close(self):
        print("Mock agent closed")
        
    async def chat(self, message: str, stream: bool = False):
        # Forward the message to the port 8000 server
        try:
            result = await self.server_client.make_request(
                "/api/chat", 
                method="POST", 
                data={"message": message, "session_id": self.session_id}
            )
            print(f"Server response: {result}")
            if result.get("success") and result.get("data"):
                return result["data"].get("response", "No response from server")
            else:
                return "Server responded but no valid data received"
        except Exception as e:
            print(f"Error communicating with port 8000 server: {e}")
            return f"Cannot connect to server on port 8000: {str(e)}"
        
    async def store_memory(self, content: str):
        if self.session_id not in self.memories:
            self.memories[self.session_id] = []
        self.memories[self.session_id].append({
            "content": content,
            "timestamp": datetime.datetime.now().isoformat()
        })
        return f"Memory stored successfully: {content[:50]}..."
        
    async def retrieve_memories(self, query: Optional[str] = None):
        session_memories = self.memories.get(self.session_id, [])
        if query:
            # Simple filtering by query
            return [m for m in session_memories if query.lower() in m["content"].lower()]
        return session_memories
        
    async def get_available_tools(self):
        return [
            {"name": "web_search", "description": "Search the web for information"},
            {"name": "calculator", "description": "Perform mathematical calculations"},
            {"name": "file_manager", "description": "Manage files and directories"},
            {"name": "memory_store", "description": "Store and retrieve information"}
        ]
        
    def get_conversation_history(self):
        return self.conversations.get(self.session_id, [])

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    stream: bool = False

class MemoryRequest(BaseModel):
    content: str
    session_id: Optional[str] = None

class MemoryQueryRequest(BaseModel):
    query: Optional[str] = None
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    success: bool
    timestamp: str

class ProxyRequest(BaseModel):
    endpoint: str
    method: str = "GET"
    data: Optional[Dict[Any, Any]] = None
    headers: Optional[Dict[str, str]] = None

# HTTP Client for port 8000 server
class ServerClient:
    def __init__(self, base_url: str = None):
        # Get base_url from environment variable SERVER_BASE_URL, fallback to default
        self.base_url = base_url or os.getenv("SERVER_BASE_URL", "http://localhost:8000")
        
    async def make_request(self, endpoint: str, method: str = "GET", data: Optional[Dict] = None, headers: Optional[Dict] = None):
        """Make HTTP request to the server on port 8000"""
        url = f"{self.base_url}{endpoint}"
        
        # Set timeout to 3 minutes (180 seconds)
        timeout = httpx.Timeout(180.0)
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                if method.upper() == "GET":
                    response = await client.get(url, headers=headers)
                elif method.upper() == "POST":
                    response = await client.post(url, json=data, headers=headers)
                elif method.upper() == "PUT":
                    response = await client.put(url, json=data, headers=headers)
                elif method.upper() == "DELETE":
                    response = await client.delete(url, headers=headers)
                else:
                    raise HTTPException(status_code=400, detail=f"Unsupported method: {method}")
                
                print(f"Port 8000 response: {response.status_code}")
                return {
                    "status_code": response.status_code,
                    "data": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                    "headers": dict(response.headers),
                    "success": response.status_code < 400
                }
            except httpx.ConnectError:
                raise HTTPException(status_code=503, detail="Cannot connect to server on port 8000")
            except httpx.TimeoutException:
                raise HTTPException(status_code=408, detail="Request to port 8000 server timed out after 3 minutes")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")

# Initialize server client
server_client = ServerClient()
# REST API Endpoints
@app.get("/api")
async def root():
    return {"message": "Computesphere Agent API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "agent_ready": agent_instance is not None}

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Chat with the agent"""
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    try:
        print(f"📨 Received chat request: {request.message}")
        print(f"📋 Session ID: {request.session_id}")
        
        if request.session_id:
            agent_instance.session_id = request.session_id
        
        response = await agent_instance.chat(request.message, stream=request.stream)
        print(f"🤖 Agent response: {response}")
        
        # Store conversation
        if agent_instance.session_id not in agent_instance.conversations:
            agent_instance.conversations[agent_instance.session_id] = []
        
        agent_instance.conversations[agent_instance.session_id].append({
            "user_message": request.message,
            "agent_response": response,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
        result = {
            "response": response,
            "session_id": agent_instance.session_id,
            "success": True,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        print(f"📤 API returning: {result}")
        return result
        
    except Exception as e:
        print(f"❌ Chat API error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/memory/store")
async def store_memory(request: MemoryRequest):
    """Store information in memory"""
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        if request.session_id:
            agent_instance.session_id = request.session_id
            
        result = await agent_instance.store_memory(request.content)
        return {
            "message": result,
            "success": True,
            "timestamp": datetime.datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/memory/retrieve")
async def retrieve_memories(request: MemoryQueryRequest):
    """Retrieve memories"""
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        if request.session_id:
            agent_instance.session_id = request.session_id
            
        memories = await agent_instance.retrieve_memories(request.query)
        return {
            "memories": memories,
            "success": True,
            "timestamp": datetime.datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tools")
async def get_tools():
    """Get available tools"""
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        tools = await agent_instance.get_available_tools()
        return {"tools": tools}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history/{session_id}")
async def get_history(session_id: str):
    """Get conversation history for a session"""
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        # Temporarily set session to get history
        original_session = agent_instance.session_id
        agent_instance.session_id = session_id
        history = agent_instance.get_conversation_history()
        agent_instance.session_id = original_session
        
        return {"history": history, "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions")
async def get_sessions():
    """Get all available sessions"""
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        sessions = list(agent_instance.conversations.keys())
        return {"sessions": sessions if sessions else ["default"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Proxy endpoints for port 8000 server
@app.post("/api/proxy")
async def proxy_request(request: ProxyRequest):
    """Proxy requests to the server on port 8000"""
    try:
        result = await server_client.make_request(
            endpoint=request.endpoint,
            method=request.method,
            data=request.data,
            headers=request.headers
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/server-status")
async def check_server_status():
    """Check if the server on port 8000 is accessible"""
    try:
        result = await server_client.make_request("/")
        return {
            "server_accessible": True,
            "status_code": result["status_code"],
            "message": "Server on port 8000 is accessible"
        }
    except HTTPException as e:
        return {
            "server_accessible": False,
            "error": e.detail,
            "message": "Server on port 8000 is not accessible"
        }

@app.get("/api/server/{path:path}")
async def proxy_get(path: str):
    """Proxy GET requests to the server on port 8000"""
    try:
        result = await server_client.make_request(f"/{path}")
        return result
    except HTTPException:
        raise

@app.post("/api/server/{path:path}")
async def proxy_post(path: str, data: Dict[Any, Any]):
    """Proxy POST requests to the server on port 8000"""
    try:
        result = await server_client.make_request(f"/{path}", method="POST", data=data)
        return result
    except HTTPException:
        raise

# UI Routes
@app.get("/chat", response_class=HTMLResponse)
async def chat_ui(request: Request):
    """Chat UI page"""
    return templates.TemplateResponse("chat.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_ui(request: Request):
    """Dashboard UI page"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/ui", response_class=HTMLResponse)
async def main_ui(request: Request):
    """Main UI page with all features"""
    return templates.TemplateResponse("main.html", {"request": request})

@app.get("/server", response_class=HTMLResponse)
async def server_comm_ui(request: Request):
    """Server communication UI page"""
    return templates.TemplateResponse("server_comm.html", {"request": request})

if __name__ == "__main__":
    uvicorn.run("computesphere_api:app", host="0.0.0.0", port=8001, reload=True)
