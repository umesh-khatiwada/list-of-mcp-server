"""Session management store."""
from typing import Any, Dict

# In-memory session store (use Redis/Database in production)
sessions_store: Dict[str, Any] = {}
