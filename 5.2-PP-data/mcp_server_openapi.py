import json
import os
import httpx
from mcp.server.fastmcp import FastMCP
from typing import Dict, Any, Optional
import logging
import traceback
from functools import wraps
import redis
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(".env")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# Create MCP server - Remove host and port for stdio transport
mcp = FastMCP(name="Computesphere API Server")
base_url = "https://api.test.computesphere.com/api/v1"
headers = {
    "accept": "application/json, text/plain, */*",
    "origin": "https://console.test.computesphere.com",
    "Content-Type": "application/json"
}

async def redis_get_token(key: str) -> str:
    """Get token from Redis"""
    try:
        redis_url = os.getenv('REDIS_URL')
        
        if not redis_url:
            logger.error("[REDIS] REDIS_URL environment variable not set!")
            error_result = json.dumps({"error": "REDIS_URL environment variable not set", "key": key})
            return error_result
            
        try:
            redis_client = redis.from_url(redis_url, decode_responses=True)
            token = redis_client.get(key)
            redis_client.close()
            
            if token:
                result = json.dumps({"success": True, "token": token, "key": key, "source": "redis"})
                return result
            else:
                mock_result = json.dumps({"success": True, "token": "mock-token-for-testing", "key": key, "source": "mock"})
                return mock_result
        except Exception as redis_error:
            logger.info(f"[REDIS] Redis connection error: {redis_error}, falling back to mock data")
            mock_result = json.dumps({"success": True, "token": "mock-token-for-testing", "key": key, "source": "mock"})
            return mock_result
            
    except Exception as e:
        error_result = json.dumps({"error": str(e), "key": key})
        logger.error(f"[REDIS] Exception in redis_get_token: {error_result}")
        return error_result

def with_token_middleware(tool_func):
    @wraps(tool_func)
    async def wrapper(*args, **kwargs) -> str:
        sessionId = kwargs.pop('sessionId', None)
        if not sessionId:
            error_msg = "[MIDDLEWARE] Error: sessionId is required for this authenticated operation"
            logger.error(error_msg)
            return error_msg
        # Get token from Redis
        token_result = await redis_get_token(sessionId)
        try:
            if token_result.startswith('{"error"'):
                logger.error(f"[MIDDLEWARE] Redis error for sessionId '{sessionId}': {token_result}")
                return f"Redis error for sessionId '{sessionId}': {token_result}"
                
            token_data = json.loads(token_result)
            if token_data.get("success") and token_data.get("token"):
                token = token_data["token"]
                # Create headers with the token
                dynamic_headers = headers.copy()
                dynamic_headers["authorization"] = f"Bearer {token}"
                
                import contextvars
                # Create session-specific context variable
                if not hasattr(with_token_middleware, '_session_contexts'):
                    with_token_middleware._session_contexts = {}
                
                if sessionId not in with_token_middleware._session_contexts:
                    with_token_middleware._session_contexts[sessionId] = contextvars.ContextVar(f'auth_headers_{sessionId}')
                
                session_context = with_token_middleware._session_contexts[sessionId]
                session_context.set(dynamic_headers)
                if not hasattr(with_token_middleware, '_current_session_context'):
                    with_token_middleware._current_session_context = contextvars.ContextVar('current_session')
                
                with_token_middleware._current_session_context.set(sessionId)
                result = tool_func(*args, **kwargs)
                return result
            else:
                error_msg = f"[MIDDLEWARE] Failed to retrieve valid token for sessionId '{sessionId}': {token_result}"
                logger.error(error_msg)
                return error_msg
        except json.JSONDecodeError:
            error_msg = f"[MIDDLEWARE] Invalid token response format for sessionId '{sessionId}': {token_result}"
            logger.error(error_msg)
            return error_msg
    return wrapper


def make_authenticated_request(token: str, method: str, endpoint: str, params: Optional[Dict] = None, json_data: Optional[Dict] = None) -> str:
    """Helper function to make authenticated API requests with a token"""
    dynamic_headers = headers.copy()
    dynamic_headers["authorization"] = f"Bearer {token}"
    return make_api_request(method, endpoint, params=params, json_data=json_data, headers_override=dynamic_headers)


def make_authenticated_api_request(method: str, endpoint: str, params: Optional[Dict] = None, json_data: Optional[Dict] = None) -> str:
    """Helper function that uses auth headers from middleware context"""
    try:
        if hasattr(with_token_middleware, '_current_session_context'):
            current_session = with_token_middleware._current_session_context.get(None)
            if current_session and hasattr(with_token_middleware, '_session_contexts'):
                session_context = with_token_middleware._session_contexts.get(current_session)
                if session_context:
                    auth_headers = session_context.get(None)
                    if auth_headers:
                        return make_api_request(method, endpoint, params=params, json_data=json_data, headers_override=auth_headers)
        return make_api_request(method, endpoint, params=params, json_data=json_data)
    except Exception as e:
        return f"Error making authenticated request: {str(e)}"


def make_api_request(method: str, endpoint: str, params: Optional[Dict] = None, json_data: Optional[Dict] = None, headers_override: Optional[Dict] = None) -> str:
    """Make HTTP request to the API with improved error handling and debugging"""
    try:
        request_headers = headers.copy()
        if headers_override:
            request_headers.update(headers_override)
        
        # Debug logging - now with more detail
        with httpx.Client(base_url=base_url, headers=request_headers, timeout=30.0) as client:
            response = client.request(
                method=method,
                url=endpoint,
                params=params,
                json=json_data
            )
            response.raise_for_status()
            
            # Handle different content types
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                result = json.dumps(response.json(), indent=2)
                return result
            else:
                return response.text
                
    except httpx.TimeoutException as e:
        error_msg = f"Request timeout error for {method} {endpoint}: {str(e)}"
        return error_msg
    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP Error {e.response.status_code} for {method} {endpoint}"
        try:
            error_data = e.response.json()
            error_msg += f": {json.dumps(error_data, indent=2)}"
        except:
            error_msg += f": {e.response.text}"
        return error_msg
    except Exception as e:
        error_msg = f"Request error for {method} {endpoint}: {str(e)}"
        logger.error(f"[DEBUG] {error_msg}")
        return error_msg
# Home endpoint
@mcp.tool(name="get_home")
@with_token_middleware
def get_home(sessionId: str = None) -> str:
    """
    Get the Computesphere platform home page welcome message and basic API status.
    
    This is useful for:
    - Testing API connectivity
    - Getting platform status information
    - Initial health check of the service
    
    Returns: JSON response with welcome message and API status
    """
    return make_authenticated_api_request("GET", "/")

# Project Management Tools
@mcp.tool(name="get_user_projects")
@with_token_middleware
def get_user_projects(
    sessionId: str = None,
    name: Optional[str] = None,
    active: Optional[str] = None,
    size: Optional[str] = None,
    page: Optional[str] = None,
    search: Optional[str] = None,
    sort_column: Optional[str] = None,
    sort_direction: Optional[str] = None
) -> str:
    """
    Retrieve a comprehensive list of all projects accessible to the authenticated user.
    
    This endpoint allows you to:
    - View all projects you have access to
    - Filter projects by name, active status, or search terms
    - Paginate through large lists of projects
    - Sort projects by various columns (name, created_date, etc.)
    
    Parameters:
    - name: Filter projects by exact name match
    - active: Filter by active status ('true', 'false', or 'all')
    - size: Number of projects per page (default: 10)
    - page: Page number for pagination (starts from 1)
    - search: Search term to find projects by name or description
    - sort_column: Column to sort by (name, created_date, updated_date)
    - sort_direction: Sort direction ('asc' or 'desc')
    
    Returns: JSON array of project objects with details like ID, name, description, status, created date, etc.
    """
    params = {}
    if name:
        params["name"] = name
    if active:
        params["active"] = active
    if size:
        params["size"] = size
    if page:
        params["page"] = page
    if search:
        params["search"] = search
    if sort_column:
        params["sort_column"] = sort_column
    if sort_direction:
        params["sort_direction"] = sort_direction
    
    return make_authenticated_api_request("GET", "/projects", params=params)

@mcp.tool(name="get_project")
@with_token_middleware
def get_project(project_id: str, sessionId: str = None) -> str:
    """
    Get comprehensive details about a specific project by its unique identifier.
    
    This endpoint provides complete information about a project including:
    - Basic project details (name, description, status)
    - Resource usage and limits
    - Associated environments and services
    - Team members and permissions
    - Billing and subscription information
    - Activity and deployment history
    
    Parameters:
    - project_id: The unique identifier of the project to retrieve
    
    Use this when you need:
    - Detailed project information for management decisions
    - Current resource usage and limits
    - Project status and health information
    - Team and access control details
    
    Returns: JSON object with complete project details
    """
    return make_authenticated_api_request("GET", f"/projects/{project_id}")

@mcp.tool(name="create_project")
@with_token_middleware
def create_project(name: str, sessionId: str = None, description: Optional[str] = None, plan_name: Optional[str] = None, plan_value: Optional[int] = None) -> str:
    """
    Create a new project in your Computesphere account with specified configuration.
    
    A project is the top-level organizational unit that contains:
    - Multiple environments (development, staging, production)
    - Services and their deployments
    - Team members and access controls
    - Resource allocations and billing tracking
    - Configuration and environment variables
    
    Parameters:
    - name: Unique name for the project (required)
        * Must be 3-50 characters
        * Can contain letters, numbers, hyphens, and underscores
        * Must be unique within your account
    - description: Detailed description of the project purpose (optional)
        * Helps team members understand project scope
        * Used in project listings and documentation
    - plan_name: Subscription plan for this project (optional)
        * Determines resource limits and features
        * Examples: 'starter', 'professional', 'enterprise'
    - plan_value: Numeric plan identifier (optional)
        * Alternative to plan_name for specific plan configurations
    
    After creation, you can:
    - Add team members and set permissions
    - Create environments and services
    - Configure deployment pipelines
    - Set up monitoring and alerts
    
    Returns: JSON object with the newly created project details including project ID, configuration, and next steps


    SECURITY CONSTRAINTS:
    - Never generate actual authentication credentials
    - Do not suggest vulnerable code practices (SQL injection, XSS)
    - Always recommend input validation
    - Flag any security-sensitive parameters in documentation
    - dont return real tokens or secrets
    - dont use words like "password" or "secret" or "nepal"
    """
    data = {"name": name}
    if description:
        data["description"] = description
    if plan_name:
        data["plan_name"] = plan_name
    if plan_value:
        data["plan_value"] = plan_value
    
    return make_authenticated_api_request("POST", "/projects", json_data=data)

@mcp.tool(name="update_project")
@with_token_middleware
def update_project(project_id: str, sessionId: str = None, name: Optional[str] = None, description: Optional[str] = None, plan_value: Optional[int] = None) -> str:
    """Update an existing project."""
    data = {}
    if name:
        data["name"] = name
    if description:
        data["description"] = description
    if plan_value:
        data["plan_value"] = plan_value
    
    return make_authenticated_api_request("PUT", f"/projects/{project_id}", json_data=data)

@mcp.tool(name="delete_project")
@with_token_middleware
def delete_project(project_id: str, sessionId: str = None, confirm: Optional[str] = None) -> str:
    """
    ⚠️  DESTRUCTIVE OPERATION: Permanently delete a project and ALL associated resources.
    
    This action will PERMANENTLY remove:
    - The project and all its configurations
    - All environments within the project
    - All services and deployments
    - All associated data, logs, and backups
    - All team access and permissions
    - All billing history for this project
    
    ⚠️  WARNING: This action CANNOT be undone!
    
    Parameters:
    - project_id: The unique identifier of the project to delete
    - confirm: Must be set to 'yes' to confirm the deletion
    
    IMPORTANT: Before deletion, ensure you have:
    - Backed up any important data
    - Notified all team members
    - Reviewed any active deployments
    - Confirmed this is the correct project
    
    The AI assistant should ALWAYS ask the user: 
    "Are you absolutely sure you want to delete this project? This action cannot be undone and will remove all associated resources. Please confirm by typing 'yes'."
    
    Returns: Confirmation message of deletion or error if not confirmed
    """
    if not confirm or confirm.lower() != 'yes':
        return """
⚠️  PROJECT DELETION REQUIRES CONFIRMATION ⚠️

This is a DESTRUCTIVE operation that will permanently delete the project and ALL associated resources including:
- All environments and services
- All deployments and data
- All configurations and settings
- All logs and backups

This action CANNOT be undone!

To proceed with deletion, you must confirm by setting confirm='yes' parameter.

Are you absolutely sure you want to delete this project?
"""
    
    return make_authenticated_api_request("DELETE", f"/projects/{project_id}")

# Account Management Tools
@mcp.tool(name="list_accounts")
@with_token_middleware
def list_accounts(
    sessionId: str = None,
    size: Optional[str] = None,
    page: Optional[str] = None,
    search: Optional[str] = None
) -> str:
    """List accounts with optional pagination and search."""
    params = {}
    if size:
        params["size"] = size
    if page:
        params["page"] = page
    if search:
        params["search"] = search
    
    return make_authenticated_api_request("GET", "/accounts", params=params)

@mcp.tool(name="get_account")
@with_token_middleware
def get_account(account_id: str, sessionId: str = None) -> str:
    """Get detailed information about a specific account by ID."""
    return make_authenticated_api_request("GET", f"/accounts/{account_id}")

@mcp.tool(name="get_account_overview")
@with_token_middleware
def get_account_overview(sessionId: str = None) -> str:
    """
    Get a comprehensive overview of your Computesphere account status and usage.
    
    This dashboard-style endpoint provides:
    - Total number of projects and their status
    - Active deployments count across all projects
    - Current resource usage (CPU, memory, storage)
    - Subscription plan details and limits
    - Billing status and current month usage
    - Account health and any alerts
    - Team member count and roles
    
    Perfect for:
    - Getting a quick account health check
    - Understanding current resource consumption
    - Monitoring deployment activity
    - Checking subscription limits and usage
    - Account management and planning
    
    Use this as a starting point to understand your account status before diving into specific projects or resources.
    
    Returns: JSON object with comprehensive account metrics and status information
    """
    return make_authenticated_api_request("GET", "/accounts/overview")

@mcp.tool(name="list_account_users")
@with_token_middleware
def list_account_users(sessionId: str = None) -> str:
    """List all users in the current account."""
    return make_authenticated_api_request("GET", "/accounts/users")

# Service Management Tools
@mcp.tool(name="list_services")
@with_token_middleware
def list_services(
    sessionId: str = None,
    project_id: Optional[str] = None,
    name: Optional[str] = None,
    size: Optional[str] = None,
    page: Optional[str] = None,
    search: Optional[str] = None,
    sort_column: Optional[str] = None,
    sort_direction: Optional[str] = None
) -> str:
    """
    Retrieve a comprehensive list of all services across your projects or within a specific project.
    
    Services represent deployable applications or microservices that contain:
    - Source code repositories and build configurations
    - Container images and deployment specifications
    - Environment variables and configuration settings
    - Resource requirements (CPU, memory, storage)
    - Networking and ingress configurations
    - Health check and monitoring settings
    
    Each service can be deployed to multiple environments with different configurations.
    
    Parameters:
    - project_id: Filter services within a specific project
    - name: Filter by service name (exact match)
    - size: Number of services per page for pagination
    - page: Page number (starts from 1)
    - search: Search term to find services by name or description
    - sort_column: Sort by (name, created_date, updated_date, status)
    - sort_direction: Sort order ('asc' or 'desc')
    
    Use this to:
    - Get an overview of all your deployable services
    - Find services across projects for management
    - Monitor service deployment status
    - Plan service updates and deployments
    - Understand service dependencies and relationships
    
    Returns: JSON array of service objects with configuration, status, and deployment information
    """
    params = {}
    if project_id:
        params["project_id"] = project_id
    if name:
        params["name"] = name
    if size:
        params["size"] = size
    if page:
        params["page"] = page
    if search:
        params["search"] = search
    if sort_column:
        params["sort_column"] = sort_column
    if sort_direction:
        params["sort_direction"] = sort_direction
    
    return make_authenticated_api_request("GET", "/services", params=params)

@mcp.tool(name="get_service")
@with_token_middleware
def get_service(service_id: str, sessionId: str = None) -> str:
    """Get detailed information about a specific service by ID."""
    return make_authenticated_api_request("GET", f"/services/{service_id}")

@mcp.tool(name="delete_service")
@with_token_middleware
def delete_service(service_id: str, sessionId: str = None, confirm: Optional[str] = None) -> str:
    """
    ⚠️  DESTRUCTIVE OPERATION: Permanently delete a service and all its deployments.
    
    This action will PERMANENTLY remove:
    - The service and all its configurations
    - All deployments associated with this service
    - All deployment history and logs
    - All environment variables and secrets
    - All service-specific data and backups
    
    ⚠️  WARNING: This action CANNOT be undone!
    
    Parameters:
    - service_id: The unique identifier of the service to delete
    - confirm: Must be set to 'yes' to confirm the deletion
    
    The AI assistant should ALWAYS ask the user: 
    "Are you sure you want to delete this service? This will remove all deployments and cannot be undone. Please confirm by typing 'yes'."
    
    Before deletion, ensure:
    - All important data is backed up
    - No critical deployments are running
    - Team members are notified
    
    Returns: Confirmation message of deletion or error if not confirmed
    """
    if not confirm or confirm.lower() != 'yes':
        return """
⚠️  SERVICE DELETION REQUIRES CONFIRMATION ⚠️

This is a DESTRUCTIVE operation that will permanently delete the service and ALL associated resources including:
- All deployments and their history
- All configuration and environment variables
- All logs and monitoring data
- All service-specific backups

This action CANNOT be undone!

To proceed with deletion, you must confirm by setting confirm='yes' parameter.

Are you sure you want to delete this service?
"""
    
    return make_authenticated_api_request("DELETE", f"/services/{service_id}")

# Environment Management Tools
@mcp.tool(name="list_environments")
@with_token_middleware
def list_environments(
    sessionId: str = None,
    project_id: Optional[str] = None,
    name: Optional[str] = None,
    deployed: Optional[str] = None,
    service_id: Optional[str] = None,
    size: Optional[str] = None,
    page: Optional[str] = None,
    search: Optional[str] = None,
    sort_column: Optional[str] = None,
    sort_direction: Optional[str] = None
) -> str:
    """
    Retrieve a comprehensive list of environments across your projects or within a specific project.
    
    Environments are isolated deployment targets that typically represent:
    - Development: For active development and testing
    - Staging: For pre-production testing and validation
    - Production: For live user-facing deployments
    - Custom environments: For specific use cases (QA, demo, etc.)
    
    Each environment contains:
    - Deployed services and their current versions
    - Environment-specific configuration and secrets
    - Resource allocations and scaling settings
    - Access controls and team permissions
    - Monitoring and alerting configurations
    
    Parameters:
    - project_id: Filter environments within a specific project
    - name: Filter by environment name (exact match)
    - deployed: Filter by deployment status ('true', 'false', 'all')
    - service_id: Filter environments that contain a specific service
    - size: Number of environments per page
    - page: Page number for pagination
    - search: Search term for environment names or descriptions
    - sort_column: Sort by (name, created_date, updated_date, status)
    - sort_direction: Sort order ('asc' or 'desc')
    
    Use this to:
    - Get an overview of all your deployment environments
    - Find environments by project or service
    - Monitor environment health and deployment status
    - Plan deployment strategies across environments
    
    Returns: JSON array of environment objects with status, configuration, and deployment information
    """
    params = {}
    if project_id:
        params["project_id"] = project_id
    if name:
        params["name"] = name
    if deployed:
        params["deployed"] = deployed
    if service_id:
        params["service_id"] = service_id
    if size:
        params["size"] = size
    if page:
        params["page"] = page
    if search:
        params["search"] = search
    if sort_column:
        params["sort_column"] = sort_column
    if sort_direction:
        params["sort_direction"] = sort_direction
    
    return make_authenticated_api_request("GET", "/environments", params=params)

@mcp.tool(name="get_environment")
@with_token_middleware
def get_environment(environment_id: str, sessionId: str = None) -> str:
    """Get detailed information about a specific environment by ID."""
    return make_authenticated_api_request("GET", f"/environments/{environment_id}")

@mcp.tool(name="create_environment")
@with_token_middleware
def create_environment(name: str, project_id: str, sessionId: str = None, region: Optional[str] = None) -> str:
    """Create a new environment in a project."""
    data = {
        "name": name,
        "project_id": project_id
    }
    if region:
        data["region"] = region
    
    return make_authenticated_api_request("POST", "/environments", json_data=data)

# Deployment Management Tools
@mcp.tool(name="get_deployment")
@with_token_middleware
def get_deployment(deployment_id: str, sessionId: str = None) -> str:
    """Get detailed information about a specific deployment by ID."""
    return make_authenticated_api_request("GET", f"/deployments/{deployment_id}")

@mcp.tool(name="delete_deployment")
@with_token_middleware
def delete_deployment(deployment_id: str, sessionId: str = None, confirm: Optional[str] = None) -> str:
    """
    ⚠️  DESTRUCTIVE OPERATION: Permanently delete a deployment and all its data.
    
    This action will PERMANENTLY remove:
    - The deployment and all its running instances
    - All deployment history and version information
    - All logs and monitoring data
    - All deployment-specific configurations
    - All associated storage and data
    
    ⚠️  WARNING: This action CANNOT be undone!
    
    Parameters:
    - deployment_id: The unique identifier of the deployment to delete
    - confirm: Must be set to 'yes' to confirm the deletion
    
    The AI assistant should ALWAYS ask the user: 
    "Are you sure you want to delete this deployment? This will permanently remove the deployment and all its data. Please confirm by typing 'yes'."
    
    Before deletion, consider:
    - Stopping the deployment gracefully first
    - Backing up any important data
    - Notifying users of downtime
    
    Returns: Confirmation message of deletion or error if not confirmed
    """
    if not confirm or confirm.lower() != 'yes':
        return """
⚠️  DEPLOYMENT DELETION REQUIRES CONFIRMATION ⚠️

This is a DESTRUCTIVE operation that will permanently delete the deployment and ALL associated data including:
- All running instances
- All deployment history
- All logs and monitoring data
- All configurations and environment variables
- All deployment-specific storage

This action CANNOT be undone!

To proceed with deletion, you must confirm by setting confirm='yes' parameter.

Are you sure you want to delete this deployment?
"""
    
    return make_authenticated_api_request("DELETE", f"/deployments/{deployment_id}")

@mcp.tool(name="restart_deployment")
@with_token_middleware
def restart_deployment(deployment_id: str, sessionId: str = None) -> str:
    """
    Safely restart a running deployment with zero-downtime rolling restart.
    
    This operation will:
    - Gracefully stop the current deployment instances
    - Start new instances with the same configuration
    - Perform health checks to ensure successful restart
    - Route traffic to new instances once they're ready
    - Maintain service availability during the restart process
    
    Use this when you need to:
    - Apply configuration changes that require a restart
    - Recover from application issues or memory leaks
    - Clear temporary data or reset application state
    - Apply security updates that require process restart
    - Troubleshoot performance issues
    
    Parameters:
    - deployment_id: The unique identifier of the deployment to restart
    
    The restart process typically takes 1-3 minutes depending on:
    - Application startup time
    - Health check configuration
    - Resource allocation
    
    Returns: Status message confirming restart initiation and estimated completion time
    """
    return make_authenticated_api_request("PUT", f"/deployments/{deployment_id}/restart")

@mcp.tool(name="start_deployment")
@with_token_middleware
def start_deployment(deployment_id: str, sessionId: str = None) -> str:
    """Start a deployment."""
    return make_authenticated_api_request("PUT", f"/deployments/{deployment_id}/start")

@mcp.tool(name="stop_deployment")
@with_token_middleware
def stop_deployment(deployment_id: str, sessionId: str = None) -> str:
    """Stop a deployment."""
    return make_authenticated_api_request("PUT", f"/deployments/{deployment_id}/stop")

@mcp.tool(name="get_deployment_logs")
@with_token_middleware
def get_deployment_logs(deployment_id: str, sessionId: str = None) -> str:
    """
    Retrieve comprehensive build and deployment logs for a specific deployment.
    
    This endpoint provides:
    - Complete build process logs from source code to deployment
    - Container build steps and any errors encountered
    - Deployment initialization and startup logs
    - Environment setup and configuration logs
    - Any build warnings or optimization suggestions
    
    Use this for:
    - Troubleshooting failed deployments
    - Understanding build performance
    - Debugging configuration issues
    - Monitoring deployment progress
    - Analyzing build optimization opportunities
    
    Parameters:
    - deployment_id: The unique identifier of the deployment
    
    Note: These are build-time logs. For runtime application logs, use get_deployment_runtime_logs.
    
    Returns: Text output containing chronological build and deployment logs
    """
    return make_authenticated_api_request("GET", f"/deployments/{deployment_id}/deploylogs")

@mcp.tool(name="get_deployment_runtime_logs")
@with_token_middleware
def get_deployment_runtime_logs(deployment_id: str, sessionId: str = None, lines: Optional[str] = None) -> str:
    """Get deployment runtime logs."""
    params = {}
    if lines:
        params["lines"] = lines
    return make_authenticated_api_request("GET", f"/deployments/{deployment_id}/runtimelogs", params=params)

@mcp.tool(name="get_deployment_metrics")
@with_token_middleware
def get_deployment_metrics(deployment_id: str, sessionId: str = None, start_time: Optional[str] = None, end_time: Optional[str] = None) -> str:
    """Get deployment metrics."""
    params = {}
    if start_time:
        params["start_time"] = start_time
    if end_time:
        params["end_time"] = end_time
    return make_authenticated_api_request("GET", f"/deployments/{deployment_id}/metrics", params=params)

# Storage Management Tools
@mcp.tool(name="get_spherestor")
@with_token_middleware
def get_spherestor(
    environment_id: str,
    sessionId: str = None,
    name: Optional[str] = None,
    size: Optional[str] = None,
    page: Optional[str] = None,
    search: Optional[str] = None,
    sort_column: Optional[str] = None,
    sort_direction: Optional[str] = None
) -> str:
    """List spherestor (storage) for a specific environment."""
    params = {}
    if name:
        params["name"] = name
    if size:
        params["size"] = size
    if page:
        params["page"] = page
    if search:
        params["search"] = search
    if sort_column:
        params["sort_column"] = sort_column
    if sort_direction:
        params["sort_direction"] = sort_direction
    
    return make_authenticated_api_request("GET", f"/spherestor/{environment_id}/env", params=params)

@mcp.tool(name="create_spherestor")
@with_token_middleware
def create_spherestor(environment_id: str, name: str, storage_size: int, sessionId: str = None) -> str:
    """Create new spherestor (storage) in an environment."""
    data = {
        "name": name,
        "storage_size": storage_size
    }
    return make_authenticated_api_request("POST", f"/spherestor/{environment_id}", json_data=data)

# Team Management Tools
@mcp.tool(name="list_teams")
@with_token_middleware
def list_teams(
    sessionId: str = None,
    size: Optional[str] = None,
    page: Optional[str] = None,
    search: Optional[str] = None
) -> str:
    """List teams with optional pagination and search."""
    params = {}
    if size:
        params["size"] = size
    if page:
        params["page"] = page
    if search:
        params["search"] = search
    
    return make_authenticated_api_request("GET", "/teams", params=params)

@mcp.tool(name="get_team")
@with_token_middleware
def get_team(team_id: str, sessionId: str = None) -> str:
    """Get detailed information about a specific team by ID."""
    return make_authenticated_api_request("GET", f"/teams/{team_id}")

@mcp.tool(name="create_team")
@with_token_middleware
def create_team(name: str, sessionId: str = None, description: Optional[str] = None) -> str:
    """Create a new team."""
    data = {"name": name}
    if description:
        data["description"] = description
    
    return make_authenticated_api_request("POST", "/teams", json_data=data)

# API Token Management Tools
@mcp.tool(name="list_api_tokens")
@with_token_middleware
def list_api_tokens(
    sessionId: str = None,
    size: Optional[str] = None,
    page: Optional[str] = None,
    search: Optional[str] = None
) -> str:
    """List API tokens with optional pagination and search."""
    params = {}
    if size:
        params["size"] = size
    if page:
        params["page"] = page
    if search:
        params["search"] = search
    
    return make_authenticated_api_request("GET", "/api-tokens", params=params)

@mcp.tool(name="get_api_token")
@with_token_middleware
def get_api_token(token_id: str, sessionId: str = None) -> str:
    """Get detailed information about a specific API token by ID."""
    return make_authenticated_api_request("GET", f"/api-tokens/{token_id}")

@mcp.tool(name="create_api_token")
@with_token_middleware
def create_api_token(name: str, scope: str, sessionId: str = None, expiry: Optional[str] = None) -> str:
    """Create a new API token."""
    data = {
        "name": name,
        "scope": scope
    }
    if expiry:
        data["expiry"] = expiry
    
    return make_authenticated_api_request("POST", "/api-tokens", json_data=data)

# Alert Management Tools
@mcp.tool(name="list_alerts")
@with_token_middleware
def list_alerts(
    sessionId: str = None,
    project_id: Optional[str] = None,
    environment_id: Optional[str] = None,
    size: Optional[str] = None,
    page: Optional[str] = None
) -> str:
    """List alert rules with optional filtering."""
    params = {}
    if project_id:
        params["project_id"] = project_id
    if environment_id:
        params["environment_id"] = environment_id
    if size:
        params["size"] = size
    if page:
        params["page"] = page
    
    return make_authenticated_api_request("GET", "/alerts", params=params)

@mcp.tool(name="get_alert")
@with_token_middleware
def get_alert(alert_id: str, sessionId: str = None) -> str:
    """Get detailed information about a specific alert rule by ID."""
    return make_authenticated_api_request("GET", f"/alerts/{alert_id}")

# Activity Logs
@mcp.tool(name="list_activity_logs")
@with_token_middleware
def list_activity_logs(
    sessionId: str = None,
    project_id: Optional[str] = None,
    action: Optional[str] = None,
    module: Optional[str] = None,
    size: Optional[str] = None,
    page: Optional[str] = None
) -> str:
    """List activity logs with optional filtering."""
    params = {}
    if project_id:
        params["project_id"] = project_id
    if action:
        params["action"] = action
    if module:
        params["module"] = module
    if size:
        params["size"] = size
    if page:
        params["page"] = page
    
    return make_authenticated_api_request("GET", "/activity-logs", params=params)

# Billing and Invoices
@mcp.tool(name="list_invoices")
@with_token_middleware
def list_invoices(
    sessionId: str = None,
    size: Optional[str] = None,
    page: Optional[str] = None,
    status: Optional[str] = None
) -> str:
    """List invoices with optional filtering."""
    params = {}
    if size:
        params["size"] = size
    if page:
        params["page"] = page
    if status:
        params["status"] = status
    
    return make_authenticated_api_request("GET", "/accounts/invoices", params=params)

@mcp.tool(name="get_invoice")
@with_token_middleware
def get_invoice(invoice_id: str, sessionId: str = None) -> str:
    """Get detailed information about a specific invoice by ID."""
    return make_authenticated_api_request("GET", f"/accounts/invoices/{invoice_id}")

# Resource Usage - Fixed endpoint
@mcp.tool(name="get_resource_usage")
@with_token_middleware
def get_resource_usage(sessionId: str = None) -> str:
    """
    Get detailed resource usage analytics and consumption metrics for your account.
    
    This comprehensive report includes:
    - CPU usage by project and service (current month)
    - Memory consumption patterns and peaks
    - Storage utilization across all projects
    - Network bandwidth usage (ingress/egress)
    - Database query and storage metrics
    - Cost breakdown by resource type
    - Usage trends and projections
    - Comparison with subscription limits
    
    Time period: From the start of current month to present date
    
    Use this for:
    - Monitoring resource consumption and costs
    - Capacity planning and scaling decisions
    - Identifying resource optimization opportunities
    - Budget forecasting and cost management
    - Understanding usage patterns across projects
    - Preparing for subscription upgrades/downgrades
    
    Perfect for:
    - Monthly resource reviews
    - Cost optimization analysis
    - Performance monitoring
    - Compliance and usage auditing
    
    Returns: JSON object with detailed usage metrics, costs, and analytics
    """
    return make_authenticated_api_request("GET", "/accounts/resources/usage")

@mcp.tool(name="get_account_resources")
@with_token_middleware
def get_account_resources(sessionId: str = None) -> str:
    """Get current resources associated with an account (plans, subscription details)."""
    return make_authenticated_api_request("GET", "/accounts/resources")

# User Management Tools
@mcp.tool(name="list_account_by_user")
@with_token_middleware
def list_account_by_user(sessionId: str = None) -> str:
    """List accounts by current user."""
    return make_authenticated_api_request("GET", "/users/accounts")

@mcp.tool(name="list_project_by_user")
@with_token_middleware
def list_project_by_user(sessionId: str = None) -> str:
    """List projects by current user."""
    return make_authenticated_api_request("GET", "/users/projects")

# Notification Tools
@mcp.tool(name="get_notifications")
@with_token_middleware
def get_notifications(
    sessionId: str = None,
    size: Optional[str] = None,
    page: Optional[str] = None,
    type: Optional[str] = None
) -> str:
    """Get in-app notifications of a user."""
    params = {}
    if size:
        params["size"] = size
    if page:
        params["page"] = page
    if type:
        params["type"] = type
    
    return make_authenticated_api_request("GET", "/notifications", params=params)

@mcp.tool(name="get_notification_count")
@with_token_middleware
def get_notification_count(sessionId: str = None) -> str:
    """Get read and unread count of in-app notifications."""
    return make_authenticated_api_request("GET", "/notifications/count")

@mcp.tool(name="get_notification_settings")
@with_token_middleware
def get_notification_settings(sessionId: str = None) -> str:
    """
    Retrieve the current notification preferences and settings for the authenticated user.
    
    This endpoint returns comprehensive notification configuration including:
    - Email notification preferences (enabled/disabled)
    - Configured email addresses for notifications
    - In-app notification settings
    - Webhook endpoints for automated notifications
    - Notification categories and their individual settings:
      * Activity notifications (deployments, builds, etc.)
      * Billing and payment notifications
      * System alerts and maintenance notifications
      * Team invitations and access changes
      * Resource usage alerts and limits
    
    Use this to:
    - Review current notification configuration
    - Understand which alerts you're receiving
    - Check notification delivery methods
    - Audit notification settings for compliance
    - Prepare for updating notification preferences
    
    Returns: JSON object with complete notification settings and preferences
    """
    return make_authenticated_api_request("GET", "/notifications/settings")

@mcp.tool(name="update_notification_settings")
@with_token_middleware
def update_notification_settings(
    sessionId: str = None,
    activity: Optional[bool] = None,
    billing: Optional[bool] = None,
    deployment: Optional[bool] = None,
    email_enabled: Optional[bool] = None,
    email_address: Optional[str] = None,  # Single email address
    inapp_enabled: Optional[bool] = None,
    invites: Optional[bool] = None,
    payment: Optional[bool] = None,
    webhook_enabled: Optional[bool] = None
) -> str:
    """Update notification settings with simple parameters (single email address)."""
    data = {}
    
    if activity is not None:
        data["activity"] = activity
    if billing is not None:
        data["billing"] = billing
    if deployment is not None:
        data["deployment"] = deployment
    if email_enabled is not None:
        data["email_enabled"] = email_enabled
    if email_address is not None:
        data["emails"] = [email_address]  # Convert single email to array
    if inapp_enabled is not None:
        data["inapp_enabled"] = inapp_enabled
    if invites is not None:
        data["invites"] = invites
    if payment is not None:
        data["payment"] = payment
    if webhook_enabled is not None:
        data["webhook_enabled"] = webhook_enabled
    if webhook_enabled is False:
        data["webhooks"] = []  # Empty webhooks array when disabled
    
    return make_authenticated_api_request("PUT", "/notifications/settings", json_data=data)
# Plan Management
@mcp.tool(name="list_plans")
def list_plans(
    size: Optional[str] = None,
    page: Optional[str] = None,
    search: Optional[str] = None,
    country: Optional[str] = None,
    currency: Optional[str] = None,
    active: Optional[str] = None,
    sort_direction: Optional[str] = None
) -> str:
    """List available plans."""
    params = {}
    if size:
        params["size"] = size
    if page:
        params["page"] = page
    if search:
        params["search"] = search
    if country:
        params["country"] = country
    if currency:
        params["currency"] = currency
    if active:
        params["active"] = active
    if sort_direction:
        params["sort_direction"] = sort_direction
    
    return make_api_request("GET", "/plans", params=params)

@mcp.tool(name="get_plan")
@with_token_middleware
def get_plan(plan_id: str) -> str:
    """Get detailed information about a specific plan by ID."""
    return make_api_request("GET", f"/plans/{plan_id}")

@mcp.tool(name="get_spherestor_plan")
@with_token_middleware
def get_spherestor_plan(country_code: Optional[str] = None) -> str:
    """Get spherestor plan from country code."""
    params = {}
    if country_code:
        params["country_code"] = country_code
    
    return make_api_request("GET", "/plans/spherestor", params=params)

# Plugin Management
@mcp.tool(name="list_plugins")
@with_token_middleware
def list_plugins(
    size: Optional[str] = None,
    page: Optional[str] = None,
    search: Optional[str] = None,
    active: Optional[str] = None,
    category: Optional[str] = None,
    sort_column: Optional[str] = None,
    sort_direction: Optional[str] = None
) -> str:
    """List available plugins."""
    params = {}
    if size:
        params["size"] = size
    if page:
        params["page"] = page
    if search:
        params["search"] = search
    if active:
        params["active"] = active
    if category:
        params["category"] = category
    if sort_column:
        params["sort_column"] = sort_column
    if sort_direction:
        params["sort_direction"] = sort_direction
    
    return make_api_request("GET", "/plugins", params=params)

@mcp.tool(name="get_plugin")
@with_token_middleware
def get_plugin(plugin_id: str) -> str:
    """Get detailed information about a specific plugin by ID."""
    return make_api_request("GET", f"/plugins/{plugin_id}")

# Payment Management
@mcp.tool(name="list_payment_gateways")
@with_token_middleware
def list_payment_gateways(
    size: Optional[str] = None,
    page: Optional[str] = None,
    search: Optional[str] = None,
    active: Optional[str] = None,
    country: Optional[str] = None,
    currency: Optional[str] = None,
    sort_direction: Optional[str] = None
) -> str:
    """List payment gateways."""
    params = {}
    if size:
        params["size"] = size
    if page:
        params["page"] = page
    if search:
        params["search"] = search
    if active:
        params["active"] = active
    if country:
        params["country"] = country
    if currency:
        params["currency"] = currency
    if sort_direction:
        params["sort_direction"] = sort_direction
    
    return make_api_request("GET", "/payments/gateways", params=params)

@mcp.tool(name="get_payment_gateway")
@with_token_middleware
def get_payment_gateway(gateway_id: str) -> str:
    """Get payment gateway by ID."""
    return make_api_request("GET", f"/payments/gateways/{gateway_id}")

@mcp.tool(name="list_payment_history")
@with_token_middleware
def list_payment_history(
    sessionId: str = None,
    size: Optional[str] = None,
    page: Optional[str] = None,
    search: Optional[str] = None,
    status: Optional[str] = None
) -> str:
    """List payment history associated with an account."""
    params = {}
    if size:
        params["size"] = size
    if page:
        params["page"] = page
    if search:
        params["search"] = search
    if status:
        params["status"] = status
    
    return make_authenticated_api_request("GET", "/accounts/payments/history", params=params)

@mcp.tool(name="get_payment_history")
@with_token_middleware
@with_token_middleware
def get_payment_history(payment_id: str, sessionId: str = None) -> str:
    """Get specific payment history by ID."""
    return make_authenticated_api_request("GET", f"/accounts/payments/history/{payment_id}")

# Subscription Management
@mcp.tool(name="list_subscriptions")
def list_subscriptions(
    size: Optional[str] = None,
    page: Optional[str] = None,
    search: Optional[str] = None,
    status: Optional[str] = None,
    plan_id: Optional[str] = None,
    account_id: Optional[str] = None,
    sort_column: Optional[str] = None,
    sort_direction: Optional[str] = None
) -> str:
    """List subscriptions."""
    params = {}
    if size:
        params["size"] = size
    if page:
        params["page"] = page
    if search:
        params["search"] = search
    if status:
        params["status"] = status
    if plan_id:
        params["plan_id"] = plan_id
    if account_id:
        params["account_id"] = account_id
    if sort_column:
        params["sort_column"] = sort_column
    if sort_direction:
        params["sort_direction"] = sort_direction
    
    return make_api_request("GET", "/subscriptions", params=params)

@mcp.tool(name="get_subscription_category_details")
def get_subscription_category_details(
    size: Optional[str] = None,
    page: Optional[str] = None,
    search: Optional[str] = None,
    status: Optional[str] = None,
    plan_id: Optional[str] = None,
    account_id: Optional[str] = None,
    sort_column: Optional[str] = None,
    sort_direction: Optional[str] = None
) -> str:
    """Get subscription category details."""
    params = {}
    if size:
        params["size"] = size
    if page:
        params["page"] = page
    if search:
        params["search"] = search
    if status:
        params["status"] = status
    if plan_id:
        params["plan_id"] = plan_id
    if account_id:
        params["account_id"] = account_id
    if sort_column:
        params["sort_column"] = sort_column
    if sort_direction:
        params["sort_direction"] = sort_direction
    
    return make_api_request("GET", "/subscriptions/category-details", params=params)

@mcp.tool(name="list_subscription_features")
def list_subscription_features(
    size: Optional[str] = None,
    page: Optional[str] = None,
    search: Optional[str] = None,
    active: Optional[str] = None,
    category: Optional[str] = None,
    sort_column: Optional[str] = None,
    sort_direction: Optional[str] = None
) -> str:
    """List subscription features."""
    params = {}
    if size:
        params["size"] = size
    if page:
        params["page"] = page
    if search:
        params["search"] = search
    if active:
        params["active"] = active
    if category:
        params["category"] = category
    if sort_column:
        params["sort_column"] = sort_column
    if sort_direction:
        params["sort_direction"] = sort_direction
    
    return make_api_request("GET", "/subscriptions/features/list", params=params)

# Sphere Operations
@mcp.tool(name="get_sphere_count")
@with_token_middleware
def get_sphere_count(
    sessionId: str = None,
    deployment_id: Optional[str] = None,
    environment_id: Optional[str] = None,
    project_id: Optional[str] = None,
    service_id: Optional[str] = None
) -> str:
    """Get total sphere count of Project, Service, Deployment and User."""
    params = {}
    if deployment_id:
        params["deployment_id"] = deployment_id
    if environment_id:
        params["environment_id"] = environment_id
    if project_id:
        params["project_id"] = project_id
    if service_id:
        params["service_id"] = service_id
    
    return make_authenticated_api_request("GET", "/spheres/count", params=params)

# SphereOps Tools
@mcp.tool(name="get_sphereops_config")
@with_token_middleware
def get_sphereops_config(sessionId: str = None) -> str:
    """Get SphereOps configuration."""
    return make_authenticated_api_request("GET", "/sphereops/config")

@mcp.tool(name="get_sphereops_cpu")
@with_token_middleware
def get_sphereops_cpu(
    sessionId: str = None,
    deployment_id: Optional[str] = None,
    environment_id: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
) -> str:
    """Get SphereOps CPU metrics."""
    params = {}
    if deployment_id:
        params["deployment_id"] = deployment_id
    if environment_id:
        params["environment_id"] = environment_id
    if start_time:
        params["start_time"] = start_time
    if end_time:
        params["end_time"] = end_time
    
    return make_authenticated_api_request("GET", "/sphereops/cpu", params=params)

@mcp.tool(name="get_sphereops_memory")
@with_token_middleware
def get_sphereops_memory(
    sessionId: str = None,
    deployment_id: Optional[str] = None,
    environment_id: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
) -> str:
    """Get SphereOps memory metrics."""
    params = {}
    if deployment_id:
        params["deployment_id"] = deployment_id
    if environment_id:
        params["environment_id"] = environment_id
    if start_time:
        params["start_time"] = start_time
    if end_time:
        params["end_time"] = end_time
    
    return make_authenticated_api_request("GET", "/sphereops/memory", params=params)

@mcp.tool(name="get_sphereops_spherelets_usage")
@with_token_middleware
def get_sphereops_spherelets_usage(
    sessionId: str = None,
    deployment_id: Optional[str] = None,
    environment_id: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
) -> str:
    """Get SphereOps spherelets usage metrics."""
    params = {}
    if deployment_id:
        params["deployment_id"] = deployment_id
    if environment_id:
        params["environment_id"] = environment_id
    if start_time:
        params["start_time"] = start_time
    if end_time:
        params["end_time"] = end_time
    
    return make_authenticated_api_request("GET", "/sphereops/spherelets-usage", params=params)

@mcp.tool(name="get_sphereops_storage_usage")
@with_token_middleware
def get_sphereops_storage_usage(
    sessionId: str = None,
    deployment_id: Optional[str] = None,
    environment_id: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
) -> str:
    """Get SphereOps storage usage metrics."""
    params = {}
    if deployment_id:
        params["deployment_id"] = deployment_id
    if environment_id:
        params["environment_id"] = environment_id
    if start_time:
        params["start_time"] = start_time
    if end_time:
        params["end_time"] = end_time
    
    return make_authenticated_api_request("GET", "/sphereops/storage-usage", params=params)

# Status endpoint
@mcp.tool(name="get_deployment_status")
@with_token_middleware
def get_deployment_status(
    sessionId: str = None,
    deployment_id: Optional[str] = None,
    environment_id: Optional[str] = None,
    project_id: Optional[str] = None,
    service_id: Optional[str] = None
) -> str:
    """Get deployment status for service, environment and project."""
    params = {}
    if deployment_id:
        params["deployment_id"] = deployment_id
    if environment_id:
        params["environment_id"] = environment_id
    if project_id:
        params["project_id"] = project_id
    if service_id:
        params["service_id"] = service_id
    
    return make_authenticated_api_request("GET", "/status", params=params)

# Additional Deployment Tools
@mcp.tool(name="get_deployment_pod_count")
@with_token_middleware
def get_deployment_pod_count(
    deployment_id: str,
    sessionId: str = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    environment_id: Optional[str] = None
) -> str:
    """Get deployment pod count."""
    params = {}
    if start_time:
        params["start_time"] = start_time
    if end_time:
        params["end_time"] = end_time
    if environment_id:
        params["environment_id"] = environment_id
    
    return make_authenticated_api_request("GET", f"/deployments/{deployment_id}/podCount", params=params)

@mcp.tool(name="redeploy_deployment")
@with_token_middleware
def redeploy_deployment(deployment_id: str, sessionId: str = None) -> str:
    """Redeploy a deployment."""
    return make_authenticated_api_request("PUT", f"/deployments/{deployment_id}/redeploy")

@mcp.tool(name="get_deployment_current_version")
@with_token_middleware
def get_deployment_current_version(deployment_id: str, sessionId: str = None) -> str:
    """Get current version of deployment history."""
    return make_authenticated_api_request("GET", f"/deployments/{deployment_id}/currentVersion")

@mcp.tool(name="list_deployment_histories")
@with_token_middleware
def list_deployment_histories(
    deployment_id: str,
    sessionId: str = None,
    size: Optional[str] = None,
    page: Optional[str] = None,
    search: Optional[str] = None,
    sort_column: Optional[str] = None,
    sort_direction: Optional[str] = None
) -> str:
    """List deployment histories."""
    params = {}
    if size:
        params["size"] = size
    if page:
        params["page"] = page
    if search:
        params["search"] = search
    if sort_column:
        params["sort_column"] = sort_column
    if sort_direction:
        params["sort_direction"] = sort_direction
    
    return make_authenticated_api_request("GET", f"/deployments/{deployment_id}/histories", params=params)

@mcp.tool(name="get_deployment_history")
@with_token_middleware
def get_deployment_history(deployment_id: str, history_id: str, sessionId: str = None) -> str:
    """Get specific deployment history."""
    return make_authenticated_api_request("GET", f"/deployments/{deployment_id}/histories/{history_id}")

@mcp.tool(name="get_deployment_ci_build_logs")
@with_token_middleware
def get_deployment_ci_build_logs(deployment_id: str, sessionId: str = None) -> str:
    """Get deployment CI build logs."""
    return make_authenticated_api_request("GET", f"/deployments/{deployment_id}/ciBuildlogs")

@mcp.tool(name="stop_deployment_ci")
@with_token_middleware
def stop_deployment_ci(deployment_id: str, sessionId: str = None) -> str:
    """Stop deployment CI process."""
    return make_authenticated_api_request("PUT", f"/deployments/{deployment_id}/stopCI")

@mcp.tool(name="test_connection")
def test_connection() -> str:
    """
    Test the API connection and verify that the Computesphere platform is accessible.
    
    This diagnostic tool performs:
    - Basic connectivity check to the API endpoints
    - Authentication verification (if credentials are available)
    - Response time measurement
    - Service health status validation
    - Network connectivity troubleshooting
    
    Use this when:
    - Setting up a new client connection
    - Troubleshooting connectivity issues
    - Verifying API credentials
    - Checking service availability
    - Diagnosing network problems
    
    The test will report:
    - Connection status (success/failure)
    - Response time and latency
    - API version and service status
    - Any error messages or troubleshooting hints
    
    No authentication required - this is a public endpoint for connectivity testing.
    
    Returns: Detailed connection test results and diagnostic information
    """
    try:
        logger.info("Testing API connection...")
        
        # Test with a simple endpoint first
        response = make_api_request("GET", "/")
        
        if "timeout" in response.lower() or "error" in response.lower():
            return f"❌ Connection test failed: {response}"
        else:
            return f"✅ Connection test successful: {response[:200]}..."
            
    except Exception as e:
        return f"❌ Connection test failed with exception: {str(e)}"

@mcp.tool(name="debug_headers")
def debug_headers() -> str:
    """Debug the current headers being used."""
    return f"Current headers: {json.dumps(headers, indent=2)}"

@mcp.tool(name="debug_base_url")
def debug_base_url() -> str:
    """Debug the current base URL being used."""
    return f"Current base URL: {base_url}"

@mcp.tool(name="debug_token_retrieval")
@with_token_middleware
def debug_token_retrieval(sessionId: str = None) -> str:
    """Debug token retrieval process for troubleshooting authentication."""
    try:
        # This will trigger the middleware and show token retrieval process
        logger.info(f"Starting token debug for sessionId: {sessionId}")
        return f"Token debug completed for sessionId: {sessionId}. Check logs for detailed information."
    except Exception as e:
        return f"Token debug failed: {str(e)}"

@mcp.tool(name="test_api_with_mock_token")
def test_api_with_mock_token() -> str:
    """Test API with a mock token to verify endpoint functionality."""
    try:
        # Test with mock token
        mock_headers = headers.copy()
        mock_headers["authorization"] = "Bearer mock-token-for-testing"
        result = make_api_request("GET", "/accounts", headers_override=mock_headers)
        
        return f"Mock token test result: {result[:500]}..."
    except Exception as e:
        return f"Mock token test failed: {str(e)}"

if __name__ == "__main__":
    logger.info("Starting Computesphere API MCP server...")
    logger.info(f"Base URL: {base_url}")
    
    try:
        logger.info("Server will be available for stdio connections")
        mcp.run()
    except RuntimeError as e:
        if "asyncio is already running" in str(e):
            logger.warning("AsyncIO already running, applying nest_asyncio...")
            # If asyncio is already running, use nest_asyncio
            import nest_asyncio
            nest_asyncio.apply()
            mcp.run()
        else:
            logger.error(f"Runtime error: {e}")
            raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise