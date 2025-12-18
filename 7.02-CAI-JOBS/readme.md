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

curl -X POST http://localhost:8000/api/sessions \
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
curl -X GET http://localhost:8000/api/sessions/8cf2a003-1f5d-4d80-a828-460bf6c7ca89/logs

# 5. Delete session and job (replace {session_id} with actual ID)
curl -X DELETE http://localhost:8000/api/sessions/{session_id}


POST /api/sessions - Create new session
GET /api/sessions - List all sessions
GET /api/sessions/{id} - Get specific session
GET /api/sessions/{id}/logs - Get session logs
DELETE /api/sessions/{id} - Delete session and job