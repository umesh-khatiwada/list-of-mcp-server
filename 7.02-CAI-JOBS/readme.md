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

POST /api/sessions - Create new session
GET /api/sessions - List all sessions
GET /api/sessions/{id} - Get specific session
GET /api/sessions/{id}/logs - Get session logs
DELETE /api/sessions/{id} - Delete session and job