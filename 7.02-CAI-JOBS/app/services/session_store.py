"""Session management store."""
import json
import logging
import os
import atexit
from typing import Any, Dict

# File for persistence
SESSIONS_FILE = os.environ.get("SESSIONS_FILE", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "sessions.json"))
if os.environ.get("OUTPUT_DIR"):
    SESSIONS_FILE = os.path.join(os.environ.get("OUTPUT_DIR"), "sessions.json")
logger = logging.getLogger(__name__)

# In-memory session store
sessions_store: Dict[str, Any] = {}

def load_sessions():
    """Load sessions from file."""
    logger.info(f"Loading sessions from {SESSIONS_FILE}")
    global sessions_store
    if os.path.exists(SESSIONS_FILE):
        try:
            with open(SESSIONS_FILE, 'r', encoding='utf-8') as f:
                sessions_store = json.load(f)
                logger.info(f"Successfully loaded {len(sessions_store)} sessions from {SESSIONS_FILE}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse sessions file {SESSIONS_FILE}: {e}")
            # Backup corrupted file
            backup_file = f"{SESSIONS_FILE}.backup"
            try:
                os.rename(SESSIONS_FILE, backup_file)
                logger.info(f"Backed up corrupted sessions file to {backup_file}")
            except Exception:
                pass
            sessions_store = {}
        except Exception as e:
            logger.error(f"Failed to load sessions from {SESSIONS_FILE}: {e}")
            sessions_store = {}
    else:
        logger.info(f"Sessions file {SESSIONS_FILE} does not exist, starting with empty store")
        sessions_store = {}

def save_sessions():
    """Save sessions to file with proper error handling."""
    global sessions_store
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(SESSIONS_FILE), exist_ok=True)
        
        # Write to temporary file first, then rename (atomic write)
        temp_file = f"{SESSIONS_FILE}.tmp"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(sessions_store, f, indent=2, ensure_ascii=False)
        
        # Atomic rename
        os.replace(temp_file, SESSIONS_FILE)
        logger.debug(f"Saved {len(sessions_store)} sessions to {SESSIONS_FILE}")
    except PermissionError as e:
        logger.error(f"Permission denied writing to {SESSIONS_FILE}: {e}")
    except OSError as e:
        logger.error(f"Failed to save sessions to {SESSIONS_FILE}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error saving sessions: {e}")

# Register save on exit
atexit.register(save_sessions)
