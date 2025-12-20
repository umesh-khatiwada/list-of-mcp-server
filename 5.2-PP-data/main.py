import logging
from typing import Optional

from client import ComputesphereAgent
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# --- Strands Observability Metrics Exporters ---


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Computesphere Agent API", version="1.0.0")

# Global agent instance
agent_instance = None


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


@app.on_event("startup")
async def startup_event():
    """Initialize the agent on startup"""
    global agent_instance
    agent_instance = ComputesphereAgent()
    await agent_instance.initialize_agent()
    print(" Agent initialized and ready!")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global agent_instance
    if agent_instance:
        await agent_instance.close()


@app.get("/api")
async def root():
    return {"message": "Computesphere Agent API", "status": "running"}


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "agent_ready": agent_instance is not None,
        "agent_type": str(type(agent_instance)) if agent_instance else None,
    }


@app.get("/api/debug")
async def debug_info():
    """Debug endpoint to check agent status"""
    if not agent_instance:
        return {"error": "Agent not initialized"}

    try:
        return {
            "agent_initialized": True,
            "session_id": agent_instance.session_id,
            "memory_enabled": agent_instance.enable_memory,
            "conversation_count": len(agent_instance.get_conversation_history()),
            "agent_type": str(type(agent_instance.agent))
            if agent_instance.agent
            else None,
        }
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Chat with the agent"""
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        if request.session_id:
            agent_instance.session_id = request.session_id

        logger.info(f"Processing chat request: {request.message}")
        logger.info(f"Session ID: {agent_instance.session_id}")

        response = await agent_instance.chat(request.message, stream=request.stream)

        logger.info(f"Agent response type: {type(response)}")
        logger.info(f"Agent response length: {len(str(response)) if response else 0}")
        logger.info(f"Agent response preview: {str(response)[:200]}...")

        # Ensure response is properly formatted
        if response is None:
            response = "No response received from agent"
        elif not isinstance(response, str):
            response = str(response)

        return {
            "response": response,
            "session_id": agent_instance.session_id,
            "success": True,
        }
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/memory/store")
async def store_memory(request: MemoryRequest):
    """Store information in memory"""
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        if request.session_id:
            agent_instance.session_id = request.session_id

        logger.info(f"Storing memory: {request.content}")
        result = await agent_instance.store_memory(request.content)
        logger.info(f"Memory store result: {result}")

        return {"message": result, "success": True}
    except Exception as e:
        logger.error(f"Error storing memory: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/memory/retrieve")
async def retrieve_memories(request: MemoryQueryRequest):
    """Retrieve memories"""
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        if request.session_id:
            agent_instance.session_id = request.session_id

        logger.info(f"Retrieving memories with query: {request.query}")
        memories = await agent_instance.retrieve_memories(request.query)
        logger.info(f"Retrieved memories: {memories}")

        return {"memories": memories, "success": True}
    except Exception as e:
        logger.error(f"Error retrieving memories: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tools")
async def get_tools():
    """Get available tools"""
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        logger.info("Getting available tools")
        tools = await agent_instance.get_available_tools()
        logger.info(f"Found {len(tools) if tools else 0} tools")
        return {"tools": tools}
    except Exception as e:
        logger.error(f"Error getting tools: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/history/{session_id}")
async def get_history(session_id: str):
    """Get conversation history for a session"""
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        logger.info(f"Getting history for session: {session_id}")
        # Temporarily set session to get history
        original_session = agent_instance.session_id
        agent_instance.session_id = session_id
        history = agent_instance.get_conversation_history()
        agent_instance.session_id = original_session

        logger.info(f"Found {len(history) if history else 0} messages in history")
        return {"history": history, "session_id": session_id}
    except Exception as e:
        logger.error(f"Error getting history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
