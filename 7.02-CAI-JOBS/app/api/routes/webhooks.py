"""Webhook routes."""
import logging
import os

from fastapi import APIRouter, HTTPException, Request

from ...services.session_store import sessions_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["webhooks"])


@router.post("/webhooks/{session_id}")
async def receive_webhook(session_id: str, request: Request):
    """Receive webhook notifications from completed jobs (accepts both JSON dict and raw JSON file). Also saves the payload to disk."""
    try:
        sid = session_id  # Save the session_id from the URL
        # Try to parse as JSON dict first
        try:
            payload = await request.json()
            # If it's a dict, process as before
            session_id = payload.get("session_id", sid)
            status = payload.get("status")
            log_path = payload.get("log_path")
            file_content = payload.get("file_content")
            pod_logs = payload.get("pod_logs")
            # Extract scan fields if present
            repository = payload.get("repository")
            scan_summary = payload.get("scan_summary")
            files = payload.get("files")
            security_analysis = payload.get("security_analysis")
            recommendations = payload.get("recommendations")
            # Save the payload to disk
            save_path = f"/tmp/webhook_payload_{session_id}.json"
            with open(save_path, "w") as f:
                import json as _json
                _json.dump(payload, f, indent=2)
        except Exception:
            # If not a dict, treat as raw JSON file (string)
            file_content = await request.body()
            file_content = file_content.decode("utf-8")
            status = None
            log_path = None
            pod_logs = None
            repository = None
            scan_summary = None
            files = None
            security_analysis = None
            recommendations = None
            # Save the raw file_content to disk
            save_path = f"/tmp/webhook_payload_{sid}.json"
            with open(save_path, "w") as f:
                f.write(file_content)
            # Optionally, try to extract session_id and scan fields if present in JSON
            import json
            try:
                parsed = json.loads(file_content)
                session_id = parsed.get("session_id", sid)
                repository = parsed.get("repository")
                scan_summary = parsed.get("scan_summary")
                files = parsed.get("files")
                security_analysis = parsed.get("security_analysis")
                recommendations = parsed.get("recommendations")
            except Exception:
                session_id = sid

        logger.info(f"Webhook received for session {session_id} with status {status}")
        logger.info(f"Log path: {log_path}")

        if file_content:
            logger.info(f"File content length: {len(file_content)} bytes")


        # Store the results in session store for later retrieval (always create or update entry)
        if session_id:
            if session_id not in sessions_store:
                sessions_store[session_id] = {}
            sessions_store[session_id]["result"] = {
                "log_path": log_path,
                "file_content": file_content,
                "pod_logs": pod_logs,
                "status": status,
                "repository": repository,
                "scan_summary": scan_summary,
                "files": files,
                "security_analysis": security_analysis,
                "recommendations": recommendations,
            }

        return {"status": "received", "session_id": session_id, "processed": True, "saved_to": save_path}
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/webhooks/result/{session_id}")
async def get_webhook_result(session_id: str):
    """Show parsed result from saved webhook data for a session, surfacing scan results if present. Loads from disk if not in memory."""
    from fastapi.responses import JSONResponse
    from ...services.session_store import sessions_store
    import json

    result = sessions_store.get(session_id, {}).get("result")
    # If not in memory, try to load from disk
    if not result:
        save_path = f"/tmp/webhook_payload_{session_id}.json"
        if os.path.exists(save_path):
            try:
                with open(save_path, "r") as f:
                    file_content = f.read()
                # Debug: print loaded file content
                print(f"[DEBUG] Loaded file content for session {session_id}: {file_content[:500]}")
                # Try to parse as JSON dict
                try:
                    parsed = json.loads(file_content)
                    print(f"[DEBUG] Parsed JSON for session {session_id}: {parsed}")
                    # If it's a dict, extract fields, including scan fields
                    if isinstance(parsed, dict):
                        result = {
                            "log_path": parsed.get("log_path"),
                            "file_content": file_content,
                            "pod_logs": parsed.get("pod_logs"),
                            "status": parsed.get("status"),
                            "repository": parsed.get("repository"),
                            "scan_summary": parsed.get("scan_summary"),
                            "files": parsed.get("files"),
                            "security_analysis": parsed.get("security_analysis"),
                            "recommendations": parsed.get("recommendations"),
                        }
                    else:
                        result = {"log_path": None, "file_content": file_content, "pod_logs": None, "status": None}
                except Exception as e:
                    print(f"[DEBUG] JSON parse error for session {session_id}: {e}")
                    result = {"log_path": None, "file_content": file_content, "pod_logs": None, "status": None}
            except Exception as e:
                print(f"[DEBUG] Error loading file for session {session_id}: {e}")
                return JSONResponse(status_code=404, content={"error": "No result found for this session."})
        else:
            print(f"[DEBUG] No file found for session {session_id}")
            return JSONResponse(status_code=404, content={"error": "No result found for this session."})

    # Try to parse file_content as JSON if present
    file_content = result.get("file_content")
    parsed_json = None
    scan_fields = {}
    if file_content:
        try:
            parsed_json = json.loads(file_content)
        except Exception:
            parsed_json = file_content  # Return raw if not valid JSON

    # Always surface scan fields at the root if present in parsed_json
    if isinstance(parsed_json, dict):
        for key in [
            "repository", "scan_summary", "files", "security_analysis", "recommendations"
        ]:
            if key in parsed_json:
                scan_fields[key] = parsed_json[key]

    return {
        "session_id": session_id,
        "status": result.get("status"),
        "log_path": result.get("log_path"),
        "pod_logs": result.get("pod_logs"),
        **scan_fields,
        "parsed_file_content": parsed_json,
    }
