from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    from .api.routes.sessions import router as sessions_router
except ImportError:
    # Handle missing router gracefully
    sessions_router = None

app = FastAPI()

# Add CORS middleware to allow requests from the UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust to specific origins in production for security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the sessions router if available
if sessions_router:
    app.include_router(sessions_router)

@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "ok"}
