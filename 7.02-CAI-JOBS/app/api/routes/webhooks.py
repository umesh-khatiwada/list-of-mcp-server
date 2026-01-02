"""Webhook routes."""
import logging
import os

from fastapi import APIRouter, HTTPException, Request

from ...services.session_store import sessions_store, save_sessions

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# Ensure debug logs are output to console
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.propagate = True

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
            # Save the payload to disk, merging with existing data if present
            save_path = f"/tmp/webhook_payload_{session_id}.json"
            
            existing_data = {}
            if os.path.exists(save_path):
                try:
                    with open(save_path, "r") as f:
                        import json as _json
                        existing_data = _json.load(f)
                        if not isinstance(existing_data, dict):
                            existing_data = {}
                except Exception:
                    existing_data = {}
            
            # Merge new payload into existing data
            if isinstance(payload, dict):
                existing_data.update(payload)
                
            with open(save_path, "w") as f:
                import json as _json
                _json.dump(existing_data, f, indent=2)
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
            
            # Save the raw file_content to disk (merge if possible if it's JSON)
            save_path = f"/tmp/webhook_payload_{sid}.json"
            
            existing_data = {}
            if os.path.exists(save_path):
                try:
                    with open(save_path, "r") as f:
                        import json as _json
                        existing_data = _json.load(f)
                except Exception:
                    pass

            # Try to parse new content as JSON to merge
            import json
            try:
                parsed = json.loads(file_content)
                if isinstance(parsed, dict):
                    if isinstance(existing_data, dict):
                        existing_data.update(parsed)
                    else:
                        existing_data = parsed
                    
                    with open(save_path, "w") as f:
                        json.dump(existing_data, f, indent=2)
                else:
                    # Not a dict, just overwrite
                    with open(save_path, "w") as f:
                        f.write(file_content)
            except Exception:
                # Not JSON, overwrite
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
            save_sessions()

        return {"status": "received", "session_id": session_id, "processed": True, "saved_to": save_path}
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


from fastapi import Query

@router.get("/webhooks/result/{session_id}")
async def get_webhook_result(session_id: str, raw_file: bool = Query(False, description="If true, return raw file content instead of parsed result")):
    """Show parsed result from saved webhook data for a session, surfacing scan results if present. Loads from disk if not in memory."""
    from fastapi.responses import JSONResponse
    from ...services.session_store import sessions_store, save_sessions
    import json

    save_path = f"/tmp/webhook_payload_{session_id}.json"
    logger.debug(f"[DEBUG] Checking for file: {save_path}")
    if not os.path.exists(save_path):
        logger.debug(f"[DEBUG] No file found for session {session_id} at {save_path}")
        return JSONResponse(status_code=404, content={"error": "No result found for this session."})
    try:
        file_size = os.path.getsize(save_path)
        logger.debug(f"[DEBUG] File exists. Size: {file_size} bytes")
        with open(save_path, "r") as f:
            file_content = f.read()
        logger.debug(f"[DEBUG] Loaded file content for session {session_id} (first 500 chars): {file_content[:500]}")
        
        if raw_file:
            from fastapi.responses import PlainTextResponse
            return PlainTextResponse(file_content)

        # Attempt to parse as JSONL (multiple lines of JSON)
        merged_result = {
            "session_id": session_id,
            "flags_found": [],
            "vulnerabilities": [],
            "outputs": {}
        }
        
        lines = file_content.strip().split('\n')
        for line in lines:
            try:
                data = json.loads(line)
                if isinstance(data, dict):
                    # Merge top-level fields
                    if "repository" in data: merged_result["repository"] = data["repository"]
                    if "scan_summary" in data: merged_result["scan_summary"] = data["scan_summary"]
                    if "scan_report" in data: merged_result["scan_report"] = data["scan_report"]
                    if "security_analysis" in data: merged_result["security_analysis"] = data["security_analysis"]
                    if "recommendations" in data: merged_result["recommendations"] = data["recommendations"]
                    if "status" in data: merged_result["status"] = data["status"]
                    
                    # Accumulate lists
                    if "flags_found" in data and isinstance(data["flags_found"], list):
                        merged_result["flags_found"].extend(data["flags_found"])
                    if "vulnerabilities" in data and isinstance(data["vulnerabilities"], list):
                        merged_result["vulnerabilities"].extend(data["vulnerabilities"])
                        
                    # Merge outputs via agent type if available
                    if "agent_type" in data and "output" in data:
                        merged_result["outputs"][data["agent_type"]] = data["output"]
                        
            except Exception:
                pass
                
        # If we found nothing structured, try parsing the whole file as a single JSON
        if not merged_result.get("repository") and not merged_result["flags_found"]:
             try:
                parsed_json = json.loads(file_content)
                logger.debug(f"[DEBUG] Parsed single JSON for session {session_id}")
                return parsed_json
             except Exception:
                 pass

        return merged_result
    except Exception as e:
        logger.debug(f"[DEBUG] Error loading or parsing file for session {session_id}: {e}")
        return JSONResponse(status_code=404, content={"error": f"No result found for this session. Error: {e}"})
