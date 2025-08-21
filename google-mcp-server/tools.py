"""
Tools for FastMCP Google OAuth Server
"""

from fastmcp import current_auth

# Get current auth provider
auth = current_auth()

@mcp.tool
def get_user_info() -> dict:
    """Return the authenticated user's Google profile info."""
    user = auth.get_current_user()
    if user:
        return {"email": user.email, "name": user.name, "id": user.id}
    return {"error": "User not logged in"}

@mcp.tool
def is_logged_in() -> bool:
    """Check if the user is currently logged in."""
    user = auth.get_current_user()
    return bool(user)

@mcp.tool
def get_login_url() -> str:
    """Return the Google OAuth login URL."""
    return auth.get_login_url()

@mcp.tool
def logout() -> str:
    """Logout the current user."""
    auth.logout_current_user()
    return "Successfully logged out"

@mcp.tool
def get_user_email() -> str:
    """Return the authenticated user's email."""
    user = auth.get_current_user()
    if user:
        return user.email
    return "Not logged in"
