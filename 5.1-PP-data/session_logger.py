import json
import os
from datetime import datetime
from typing import Dict, List, Any

class SessionLogger:
    """Logs conversation sessions for analysis and debugging."""
    
    def __init__(self, log_dir: str = "session_logs"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
    
    def log_session_start(self, session_id: str, client_session_id: str):
        """Log the start of a new session."""
        log_entry = {
            "event": "session_start",
            "session_id": session_id,
            "client_session_id": client_session_id,
            "timestamp": datetime.now().isoformat(),
        }
        self._write_log(session_id, log_entry)
    
    def log_message(self, session_id: str, message_data: Dict):
        """Log a message in the session."""
        log_entry = {
            "event": "message",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "data": message_data
        }
        self._write_log(session_id, log_entry)
    
    def log_api_call(self, session_id: str, tool_name: str, parameters: Dict, response_preview: str):
        """Log an API call made during the session."""
        log_entry = {
            "event": "api_call",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "tool_name": tool_name,
            "parameters": parameters,
            "response_preview": response_preview[:200] + "..." if len(response_preview) > 200 else response_preview
        }
        self._write_log(session_id, log_entry)
    
    def log_session_end(self, session_id: str, session_stats: Dict):
        """Log the end of a session with statistics."""
        log_entry = {
            "event": "session_end",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "stats": session_stats
        }
        self._write_log(session_id, log_entry)
    
    def _write_log(self, session_id: str, log_entry: Dict):
        """Write log entry to session file."""
        log_file = os.path.join(self.log_dir, f"session_{session_id[:8]}.jsonl")
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def get_session_logs(self, session_id: str) -> List[Dict]:
        """Retrieve all logs for a specific session."""
        log_file = os.path.join(self.log_dir, f"session_{session_id[:8]}.jsonl")
        if not os.path.exists(log_file):
            return []
        
        logs = []
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    logs.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue
        return logs
    
    def list_sessions(self) -> List[str]:
        """List all available session IDs."""
        sessions = []
        for filename in os.listdir(self.log_dir):
            if filename.startswith("session_") and filename.endswith(".jsonl"):
                session_id = filename[8:-6]  # Remove "session_" prefix and ".jsonl" suffix
                sessions.append(session_id)
        return sorted(sessions, reverse=True)  # Most recent first
