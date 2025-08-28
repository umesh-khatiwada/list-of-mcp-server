import json
import httpx
from mcp.server.fastmcp import FastMCP
from typing import Dict, Any, Optional
import logging
import traceback

# Set up logging for debugging
# logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load OpenAPI spec
with open("openapi/openapi.json", "r") as f:
    openapi_spec = json.load(f)

# Create MCP server - Remove host and port for stdio transport
mcp = FastMCP(name="Computesphere API Server")
base_url = "https://api.test.computesphere.com/api/v1"
headers = {
    "accept": "application/json, text/plain, */*",
    "origin": "https://console.test.computesphere.com",
    "authorization": "Bearer eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJmdWp1NVVTWXU2eUlZcHhKRXhKOUh3a1diSGZON09fRFFRRWZTbUtNQmNrIn0.eyJleHAiOjE3NTYzODUzNTEsImlhdCI6MTc1NjM1NjU1MSwiYXV0aF90aW1lIjoxNzU2MzU2NTQ4LCJqdGkiOiJvbnJ0YWM6OWNmNzFjN2YtYTIwYi00Y2NkLWEzZmEtZTFlZTBjY2VmMzAwIiwiaXNzIjoiaHR0cHM6Ly9hY2NvdW50cy50ZXN0LmNvbXB1dGVzcGhlcmUuY29tL3JlYWxtcy9jb21wdXRlc3BoZXJlIiwiYXVkIjpbInJlYWxtLW1hbmFnZW1lbnQiLCJhY2NvdW50Il0sInN1YiI6IjM3NWFhNTNhLTBhNjQtNDk1YS1iNTRlLWQ1YTM5YmE4ZDhjYiIsInR5cCI6IkJlYXJlciIsImF6cCI6ImNvbXB1dGVzcGhlcmVfY2xpZW50Iiwic2lkIjoiNTM1MWFjN2YtNmMwYS00ZDQzLTg2NjMtMjUxYWNmYWYwMDY3IiwiYWNyIjoiMSIsImFsbG93ZWQtb3JpZ2lucyI6WyJodHRwczovL2NvbnNvbGUuYWRtaW4udGVzdC5jb21wdXRlc3BoZXJlLmNvbSIsImh0dHBzOi8vY29uc29sZS50ZXN0LmNvbXB1dGVzcGhlcmUuY29tIiwiaHR0cDovL2xvY2FsaG9zdDozMDAwIiwiaHR0cDovL2xvY2FsaG9zdDo2MDAwIl0sInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI6WyJkZWZhdWx0LXJvbGVzLWNvbXB1dGVzcGhlcmUiLCJvZmZsaW5lX2FjY2VzcyIsInVtYV9hdXRob3JpemF0aW9uIl19LCJyZXNvdXJjZV9hY2Nlc3MiOnsicmVhbG0tbWFuYWdlbWVudCI6eyJyb2xlcyI6WyJ2aWV3LXJlYWxtIiwidmlldy1pZGVudGl0eS1wcm92aWRlcnMiLCJtYW5hZ2UtaWRlbnRpdHktcHJvdmlkZXJzIiwiaW1wZXJzb25hdGlvbiIsInJlYWxtLWFkbWluIiwiY3JlYXRlLWNsaWVudCIsIm1hbmFnZS11c2VycyIsInF1ZXJ5LXJlYWxtcyIsInZpZXctYXV0aG9yaXphdGlvbiIsInF1ZXJ5LWNsaWVudHMiLCJxdWVyeS11c2VycyIsIm1hbmFnZS1ldmVudHMiLCJtYW5hZ2UtcmVhbG0iLCJ2aWV3LWV2ZW50cyIsInZpZXctdXNlcnMiLCJ2aWV3LWNsaWVudHMiLCJtYW5hZ2UtYXV0aG9yaXphdGlvbiIsIm1hbmFnZS1jbGllbnRzIiwicXVlcnktZ3JvdXBzIl19LCJhY2NvdW50Ijp7InJvbGVzIjpbIm1hbmFnZS1hY2NvdW50Iiwidmlldy1hcHBsaWNhdGlvbnMiLCJ2aWV3LWNvbnNlbnQiLCJ2aWV3LWdyb3VwcyIsIm1hbmFnZS1hY2NvdW50LWxpbmtzIiwibWFuYWdlLWNvbnNlbnQiLCJkZWxldGUtYWNjb3VudCIsInZpZXctcHJvZmlsZSJdfX0sInNjb3BlIjoib3BlbmlkIGVtYWlsIHByb2ZpbGUiLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwibmFtZSI6InVtZXNoLmtoYXRpd2FkYUBiZXJyeWJ5dGVzLmNvbSB1bWVzaC5raGF0aXdhZGFAYmVycnlieXRlcy5jb20iLCJwcmVmZXJyZWRfdXNlcm5hbWUiOiJ1bWVzaC5raGF0aXdhZGFAYmVycnlieXRlcy5jb20iLCJnaXZlbl9uYW1lIjoidW1lc2gua2hhdGl3YWRhQGJlcnJ5Ynl0ZXMuY29tIiwiZmFtaWx5X25hbWUiOiJ1bWVzaC5raGF0aXdhZGFAYmVycnlieXRlcy5jb20iLCJlbWFpbCI6InVtZXNoLmtoYXRpd2FkYUBiZXJyeWJ5dGVzLmNvbSJ9.Ir5PI_TbBmMOdI4NXM9encGiGeiiWFV-vwZDPjUDFBvHLEBpoT-25C3E_6z1uSA4wdJU7bhdECTh45-6H2AYYCcrNkj7_BbUv3at4T3g9tAvETgm706sS4LCJTl8uqXF2N1467ZWj7o2Dcub9qv6PbNP3MZWuURfZ0CODvpqkSTbnb-gcVEbLjJsSp_IzueeWOs0kKeTel_ko7VgByOdaTY8APkp9QQ4EL3GYnoofsG0bbyYkB6IGSC9AtNCJ8KWE7vgkPSrAY-HwQTbX7MeQsaA2-smLsRq0h5xVxpY9jiCvUXNQfMVMwZJ8mQPphUWwLhUiE4RL7eTomwdPWTiPw",
    "Content-Type": "application/json"
}

def make_api_request(method: str, endpoint: str, params: Optional[Dict] = None, json_data: Optional[Dict] = None, headers_override: Optional[Dict] = None) -> str:
    """Make HTTP request to the API with improved error handling and debugging"""
    try:
        request_headers = headers.copy()
        if headers_override:
            request_headers.update(headers_override)
        
        # Debug logging
        logger.debug(f"Making {method} request to {base_url}{endpoint}")
        logger.debug(f"Headers: {dict(request_headers)}")
        logger.debug(f"Params: {params}")
        logger.debug(f"JSON Data: {json_data}")
            
        with httpx.Client(base_url=base_url, headers=request_headers, timeout=30.0) as client:
            response = client.request(
                method=method,
                url=endpoint,
                params=params,
                json=json_data
            )
            
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            
            response.raise_for_status()
            
            # Handle different content types
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                result = json.dumps(response.json(), indent=2)
                logger.debug(f"JSON Response: {result[:500]}...")  # Log first 500 chars
                return result
            else:
                logger.debug(f"Text Response: {response.text[:500]}...")
                return response.text
                
    except httpx.TimeoutException as e:
        error_msg = f"Request timeout error for {method} {endpoint}: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP Error {e.response.status_code} for {method} {endpoint}"
        logger.error(f"Status Code: {e.response.status_code}")
        logger.error(f"Response text: {e.response.text}")
        try:
            error_data = e.response.json()
            error_msg += f": {json.dumps(error_data, indent=2)}"
        except:
            error_msg += f": {e.response.text}"
        return error_msg
    except Exception as e:
        error_msg = f"Request error for {method} {endpoint}: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return error_msg

# Home endpoint
@mcp.tool(name="get_home")
def get_home() -> str:
    """Show Computesphere home page message."""
    return make_api_request("GET", "/")

# Project Management Tools
@mcp.tool(name="get_user_projects")
def get_user_projects(
    name: Optional[str] = None,
    active: Optional[str] = None,
    size: Optional[str] = None,
    page: Optional[str] = None,
    search: Optional[str] = None,
    sort_column: Optional[str] = None,
    sort_direction: Optional[str] = None
) -> str:
    """List all projects with optional filtering and pagination."""
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
    
    return make_api_request("GET", "/projects", params=params)

@mcp.tool(name="get_project")
def get_project(project_id: str) -> str:
    """Get detailed information about a specific project by ID."""
    return make_api_request("GET", f"/projects/{project_id}")

@mcp.tool(name="create_project")
def create_project(name: str, description: Optional[str] = None, plan_name: Optional[str] = None, plan_value: Optional[int] = None) -> str:
    """Create a new project."""
    data = {"name": name}
    if description:
        data["description"] = description
    if plan_name:
        data["plan_name"] = plan_name
    if plan_value:
        data["plan_value"] = plan_value
    
    return make_api_request("POST", "/projects", json_data=data)

@mcp.tool(name="update_project")
def update_project(project_id: str, name: Optional[str] = None, description: Optional[str] = None, plan_value: Optional[int] = None) -> str:
    """Update an existing project."""
    data = {}
    if name:
        data["name"] = name
    if description:
        data["description"] = description
    if plan_value:
        data["plan_value"] = plan_value
    
    return make_api_request("PUT", f"/projects/{project_id}", json_data=data)

@mcp.tool(name="delete_project")
def delete_project(project_id: str) -> str:
    """Delete a project by ID."""
    return make_api_request("DELETE", f"/projects/{project_id}")

# Account Management Tools
@mcp.tool(name="list_accounts")
def list_accounts(
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
    
    return make_api_request("GET", "/accounts", params=params)

@mcp.tool(name="get_account")
def get_account(account_id: str) -> str:
    """Get detailed information about a specific account by ID."""
    return make_api_request("GET", f"/accounts/{account_id}")

@mcp.tool(name="get_account_overview")
def get_account_overview() -> str:
    """Get account overview with deployment count, project count, and resource usage."""
    return make_api_request("GET", "/accounts/overview")

@mcp.tool(name="list_account_users")
def list_account_users() -> str:
    """List all users in the current account."""
    return make_api_request("GET", "/accounts/users")

# Service Management Tools
@mcp.tool(name="list_services")
def list_services(
    project_id: Optional[str] = None,
    name: Optional[str] = None,
    size: Optional[str] = None,
    page: Optional[str] = None,
    search: Optional[str] = None,
    sort_column: Optional[str] = None,
    sort_direction: Optional[str] = None
) -> str:
    """List services with optional filtering."""
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
    
    return make_api_request("GET", "/services", params=params)

@mcp.tool(name="get_service")
def get_service(service_id: str) -> str:
    """Get detailed information about a specific service by ID."""
    return make_api_request("GET", f"/services/{service_id}")

@mcp.tool(name="delete_service")
def delete_service(service_id: str) -> str:
    """Delete a service by ID."""
    return make_api_request("DELETE", f"/services/{service_id}")

# Environment Management Tools
@mcp.tool(name="list_environments")
def list_environments(
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
    """List environments with optional filtering."""
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
    
    return make_api_request("GET", "/environments", params=params)

@mcp.tool(name="get_environment")
def get_environment(environment_id: str) -> str:
    """Get detailed information about a specific environment by ID."""
    return make_api_request("GET", f"/environments/{environment_id}")

@mcp.tool(name="create_environment")
def create_environment(name: str, project_id: str, region: Optional[str] = None) -> str:
    """Create a new environment in a project."""
    data = {
        "name": name,
        "project_id": project_id
    }
    if region:
        data["region"] = region
    
    return make_api_request("POST", "/environments", json_data=data)

# Deployment Management Tools
@mcp.tool(name="get_deployment")
def get_deployment(deployment_id: str) -> str:
    """Get detailed information about a specific deployment by ID."""
    return make_api_request("GET", f"/deployments/{deployment_id}")

@mcp.tool(name="delete_deployment")
def delete_deployment(deployment_id: str) -> str:
    """Delete a deployment by ID."""
    return make_api_request("DELETE", f"/deployments/{deployment_id}")

@mcp.tool(name="restart_deployment")
def restart_deployment(deployment_id: str) -> str:
    """Restart a deployment."""
    return make_api_request("PUT", f"/deployments/{deployment_id}/restart")

@mcp.tool(name="start_deployment")
def start_deployment(deployment_id: str) -> str:
    """Start a deployment."""
    return make_api_request("PUT", f"/deployments/{deployment_id}/start")

@mcp.tool(name="stop_deployment")
def stop_deployment(deployment_id: str) -> str:
    """Stop a deployment."""
    return make_api_request("PUT", f"/deployments/{deployment_id}/stop")

@mcp.tool(name="get_deployment_logs")
def get_deployment_logs(deployment_id: str) -> str:
    """Get deployment build logs."""
    return make_api_request("GET", f"/deployments/{deployment_id}/deploylogs")

@mcp.tool(name="get_deployment_runtime_logs")
def get_deployment_runtime_logs(deployment_id: str, lines: Optional[str] = None) -> str:
    """Get deployment runtime logs."""
    params = {}
    if lines:
        params["lines"] = lines
    return make_api_request("GET", f"/deployments/{deployment_id}/runtimelogs", params=params)

@mcp.tool(name="get_deployment_metrics")
def get_deployment_metrics(deployment_id: str, start_time: Optional[str] = None, end_time: Optional[str] = None) -> str:
    """Get deployment metrics."""
    params = {}
    if start_time:
        params["start_time"] = start_time
    if end_time:
        params["end_time"] = end_time
    return make_api_request("GET", f"/deployments/{deployment_id}/metrics", params=params)

# Storage Management Tools
@mcp.tool(name="get_spherestor")
def get_spherestor(
    environment_id: str,
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
    
    return make_api_request("GET", f"/spherestor/{environment_id}/env", params=params)

@mcp.tool(name="create_spherestor")
def create_spherestor(environment_id: str, name: str, storage_size: int) -> str:
    """Create new spherestor (storage) in an environment."""
    data = {
        "name": name,
        "storage_size": storage_size
    }
    return make_api_request("POST", f"/spherestor/{environment_id}", json_data=data)

# Team Management Tools
@mcp.tool(name="list_teams")
def list_teams(
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
    
    return make_api_request("GET", "/teams", params=params)

@mcp.tool(name="get_team")
def get_team(team_id: str) -> str:
    """Get detailed information about a specific team by ID."""
    return make_api_request("GET", f"/teams/{team_id}")

@mcp.tool(name="create_team")
def create_team(name: str, description: Optional[str] = None) -> str:
    """Create a new team."""
    data = {"name": name}
    if description:
        data["description"] = description
    
    return make_api_request("POST", "/teams", json_data=data)

# API Token Management Tools
@mcp.tool(name="list_api_tokens")
def list_api_tokens(
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
    
    return make_api_request("GET", "/api-tokens", params=params)

@mcp.tool(name="get_api_token")
def get_api_token(token_id: str) -> str:
    """Get detailed information about a specific API token by ID."""
    return make_api_request("GET", f"/api-tokens/{token_id}")

@mcp.tool(name="create_api_token")
def create_api_token(name: str, scope: str, expiry: Optional[str] = None) -> str:
    """Create a new API token."""
    data = {
        "name": name,
        "scope": scope
    }
    if expiry:
        data["expiry"] = expiry
    
    return make_api_request("POST", "/api-tokens", json_data=data)

# Alert Management Tools
@mcp.tool(name="list_alerts")
def list_alerts(
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
    
    return make_api_request("GET", "/alerts", params=params)

@mcp.tool(name="get_alert")
def get_alert(alert_id: str) -> str:
    """Get detailed information about a specific alert rule by ID."""
    return make_api_request("GET", f"/alerts/{alert_id}")

# Activity Logs
@mcp.tool(name="list_activity_logs")
def list_activity_logs(
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
    
    return make_api_request("GET", "/activity-logs", params=params)

# Billing and Invoices
@mcp.tool(name="list_invoices")
def list_invoices(
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
    
    return make_api_request("GET", "/accounts/invoices", params=params)

@mcp.tool(name="get_invoice")
def get_invoice(invoice_id: str) -> str:
    """Get detailed information about a specific invoice by ID."""
    return make_api_request("GET", f"/accounts/invoices/{invoice_id}")

# Resource Usage - Fixed endpoint
@mcp.tool(name="get_resource_usage")
def get_resource_usage() -> str:
    """Get resource usage history from the start of month till date."""
    return make_api_request("GET", "/accounts/resources/usage")

@mcp.tool(name="get_account_resources")
def get_account_resources() -> str:
    """Get current resources associated with an account (plans, subscription details)."""
    return make_api_request("GET", "/accounts/resources")

# User Management Tools
@mcp.tool(name="list_account_by_user")
def list_account_by_user() -> str:
    """List accounts by current user."""
    return make_api_request("GET", "/users/accounts")

@mcp.tool(name="list_project_by_user")
def list_project_by_user() -> str:
    """List projects by current user."""
    return make_api_request("GET", "/users/projects")

# Notification Tools
@mcp.tool(name="get_notifications")
def get_notifications(
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
    
    return make_api_request("GET", "/notifications", params=params)

@mcp.tool(name="get_notification_count")
def get_notification_count() -> str:
    """Get read and unread count of in-app notifications."""
    return make_api_request("GET", "/notifications/count")

@mcp.tool(name="get_notification_settings")
def get_notification_settings() -> str:
    """Get notification settings of a user."""
    return make_api_request("GET", "/notifications/settings")

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
def get_plan(plan_id: str) -> str:
    """Get detailed information about a specific plan by ID."""
    return make_api_request("GET", f"/plans/{plan_id}")

@mcp.tool(name="get_spherestor_plan")
def get_spherestor_plan(country_code: Optional[str] = None) -> str:
    """Get spherestor plan from country code."""
    params = {}
    if country_code:
        params["country_code"] = country_code
    
    return make_api_request("GET", "/plans/spherestor", params=params)

# Plugin Management
@mcp.tool(name="list_plugins")
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
def get_plugin(plugin_id: str) -> str:
    """Get detailed information about a specific plugin by ID."""
    return make_api_request("GET", f"/plugins/{plugin_id}")

# Payment Management
@mcp.tool(name="list_payment_gateways")
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
def get_payment_gateway(gateway_id: str) -> str:
    """Get payment gateway by ID."""
    return make_api_request("GET", f"/payments/gateways/{gateway_id}")

@mcp.tool(name="list_payment_history")
def list_payment_history(
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
    
    return make_api_request("GET", "/accounts/payments/history", params=params)

@mcp.tool(name="get_payment_history")
def get_payment_history(payment_id: str) -> str:
    """Get specific payment history by ID."""
    return make_api_request("GET", f"/accounts/payments/history/{payment_id}")

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
def get_sphere_count(
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
    
    return make_api_request("GET", "/spheres/count", params=params)

# SphereOps Tools
@mcp.tool(name="get_sphereops_config")
def get_sphereops_config() -> str:
    """Get SphereOps configuration."""
    return make_api_request("GET", "/sphereops/config")

@mcp.tool(name="get_sphereops_cpu")
def get_sphereops_cpu(
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
    
    return make_api_request("GET", "/sphereops/cpu", params=params)

@mcp.tool(name="get_sphereops_memory")
def get_sphereops_memory(
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
    
    return make_api_request("GET", "/sphereops/memory", params=params)

@mcp.tool(name="get_sphereops_spherelets_usage")
def get_sphereops_spherelets_usage(
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
    
    return make_api_request("GET", "/sphereops/spherelets-usage", params=params)

@mcp.tool(name="get_sphereops_storage_usage")
def get_sphereops_storage_usage(
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
    
    return make_api_request("GET", "/sphereops/storage-usage", params=params)

# Status endpoint
@mcp.tool(name="get_deployment_status")
def get_deployment_status(
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
    
    return make_api_request("GET", "/status", params=params)

# Additional Deployment Tools
@mcp.tool(name="get_deployment_pod_count")
def get_deployment_pod_count(
    deployment_id: str,
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
    
    return make_api_request("GET", f"/deployments/{deployment_id}/podCount", params=params)

@mcp.tool(name="redeploy_deployment")
def redeploy_deployment(deployment_id: str) -> str:
    """Redeploy a deployment."""
    return make_api_request("PUT", f"/deployments/{deployment_id}/redeploy")

@mcp.tool(name="get_deployment_current_version")
def get_deployment_current_version(deployment_id: str) -> str:
    """Get current version of deployment history."""
    return make_api_request("GET", f"/deployments/{deployment_id}/currentVersion")

@mcp.tool(name="list_deployment_histories")
def list_deployment_histories(
    deployment_id: str,
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
    
    return make_api_request("GET", f"/deployments/{deployment_id}/histories", params=params)

@mcp.tool(name="get_deployment_history")
def get_deployment_history(deployment_id: str, history_id: str) -> str:
    """Get specific deployment history."""
    return make_api_request("GET", f"/deployments/{deployment_id}/histories/{history_id}")

@mcp.tool(name="get_deployment_ci_build_logs")
def get_deployment_ci_build_logs(deployment_id: str) -> str:
    """Get deployment CI build logs."""
    return make_api_request("GET", f"/deployments/{deployment_id}/ciBuildlogs")

@mcp.tool(name="stop_deployment_ci")
def stop_deployment_ci(deployment_id: str) -> str:
    """Stop deployment CI process."""
    return make_api_request("PUT", f"/deployments/{deployment_id}/stopCI")

@mcp.tool(name="test_connection")
def test_connection() -> str:
    """Test the API connection and authentication."""
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

if __name__ == "__main__":
    print("🚀 Starting Computesphere API MCP server...")
    # Use stdio transport for MCP client compatibility
    try:
        mcp.run(transport="stdio")
    except RuntimeError as e:
        if "asyncio is already running" in str(e):
            # If asyncio is already running, use nest_asyncio
            import nest_asyncio
            nest_asyncio.apply()
            mcp.run(transport="stdio")
        else:
            raise
