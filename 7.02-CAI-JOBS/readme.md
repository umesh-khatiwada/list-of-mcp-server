Key Features:

Session Management

Create new chat sessions with prompts
Each session creates a dedicated Kubernetes Job
Track session status (Pending, Running, Completed, Failed)


Job Operations

Automatically creates K8s Jobs with the CAI Docker image
Passes session ID, prompt, and optional character ID/token as env vars
Auto-cleanup after 1 hour (configurable)


Real-time Monitoring

Fetch live pod logs for each session
Check job status updates
View last 100 log lines


API Endpoints

curl -X POST http://172.18.254.200:8000/api/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Test Session",
    "prompt": "ping google.com"
  }'


# 2. List all sessions
curl -X GET http://localhost:8000/api/sessions

# 3. Get specific session (replace {session_id} with actual ID)
curl -X GET http://localhost:8000/api/sessions/d463885-3a89-45f1-a4dd-eb9caa565b6d

# 4. Get session logs (replace {session_id} with actual ID)
curl -X GET http://172.18.254.200:8000/api/sessions/d5e76d1c-ec0d-42dd-9036-2c8cfcc22618/logs

# 5. Get complete job result with file content
curl -X GET http://localhost:8000/api/sessions/a94ff95b-dbf6-4c59-b532-91f94341ae59/result

# 6. Get output file content (JSON format - parsed JSONL)
curl -X GET http://localhost:8000/api/sessions/a94ff95b-dbf6-4c59-b532-91f94341ae59/file

# 7. Get output file content (raw format)
curl -X GET http://localhost:8000/api/sessions/a94ff95b-dbf6-4c59-b532-91f94341ae59/file?format=raw

# 8. Pretty print JSON output
curl -X GET http://localhost:8000/api/sessions/a94ff95b-dbf6-4c59-b532-91f94341ae59/file | jq .

# 9. Save output to file
curl -X GET http://localhost:8000/api/sessions/a94ff95b-dbf6-4c59-b532-91f94341ae59/file?format=raw -o output.jsonl

# 10. Delete session and job (replace {session_id} with actual ID)
curl -X DELETE http://localhost:8000/api/sessions/{session_id}


POST /api/sessions - Create new session
GET /api/sessions - List all sessions
GET /api/sessions/{id} - Get specific session
GET /api/sessions/{id}/logs - Get session logs
GET /api/sessions/{id}/result - Get complete job result with file content
GET /api/sessions/{id}/file - Get output file (JSON parsed)
GET /api/sessions/{id}/file?format=raw - Get output file (raw text)
DELETE /api/sessions/{id} - Delete session and job


Configuration for mcp


SSE (Server-Sent Events) - For web-based servers that push updates over HTTP connections:


CAI>/mcp load http://localhost:9876/sse burp
STDIO (Standard Input/Output) - For local inter-process communication:


CAI>/mcp load stdio myserver python mcp_server.py



uvicorn main:app --host 0.0.0.0 --port 8000 --log-level debug