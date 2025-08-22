import os
from fastmcp import FastMCP
from fastmcp.server.auth.providers.google import GoogleProvider

# The GoogleProvider handles Google's token format and validation
auth_provider = GoogleProvider(
    client_id=os.getenv("FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_ID") or "",  # Your Google OAuth Client ID
    client_secret=os.getenv("FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_SECRET") or "",  # Your Google OAuth Client Secret
    base_url="http://localhost:8000",                  # Must match your OAuth configuration
    required_scopes=["openid", "email", "profile"],    # Request user information
    redirect_path="/callback"                  # Default value, customize if needed
)

mcp = FastMCP(name="Google Secured App", auth=auth_provider)

# Add a protected tool to test authentication
@mcp.tool
async def get_user_info() -> dict:
    """Returns information about the authenticated Google user."""
    from fastmcp.server.dependencies import get_access_token
    
    token = get_access_token()
    # The GoogleProvider stores user data in token claims
    return {
        "google_id": token.claims.get("sub"),
        "email": token.claims.get("email"),
        "name": token.claims.get("name"),
        "picture": token.claims.get("picture"),
        "locale": token.claims.get("locale")
    }