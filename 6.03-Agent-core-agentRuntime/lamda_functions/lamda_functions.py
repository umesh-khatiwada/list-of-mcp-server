import json
import logging
import os

import urllib3

# Setup logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Create HTTP client
http = urllib3.PoolManager()

# MCP server endpoint (must include path like: https://<host>/mcp/execute)
MCP_SERVER_ENDPOINT = os.environ.get("MCP_SERVER_ENDPOINT")


def lambda_handler(event, context):
    logger.info("Received event: %s", json.dumps(event))

    try:
        # Extract command from Bedrock agent payload
        request_body = event.get("requestBody", {})
        command_json_string = (
            request_body.get("content", {})
            .get("application/json", {})
            .get("properties", [])[0]
            .get("value")
        )

        if not command_json_string:
            return format_response_for_agent(
                "Missing 'command_json_string' in the request", success=False
            )

        logger.info("Forwarding command to MCP: %s", command_json_string)

        # Send POST request to MCP server
        mcp_response = http.request(
            method="POST",
            url=MCP_SERVER_ENDPOINT,
            headers={"Content-Type": "application/json"},
            body=command_json_string.encode("utf-8"),
        )

        # Check for non-200 status codes from MCP server
        if mcp_response.status != 200:
            error_detail = mcp_response.data.decode("utf-8")
            logger.error(
                f"MCP server returned non-200 status: {mcp_response.status}, Detail: {error_detail}"
            )
            return format_response_for_agent(
                f"Failed to get valid response from MCP server (Status: {mcp_response.status}). Detail: {error_detail}",
                success=False,
                http_status_code=mcp_response.status,
            )

        # Parse MCP server response (it's a JSON string)
        mcp_result_json_str = mcp_response.data.decode("utf-8")
        logger.info("MCP Response (raw string): %s", mcp_result_json_str)

        try:
            mcp_result = json.loads(mcp_result_json_str)
            logger.info("MCP Response (parsed JSON): %s", mcp_result)

            # --- Format the parsed MCP result into a string for Bedrock Agent ---
            # The Bedrock Agent's OpenAPI schema expects a simple 'message' string.
            # We need to summarize the structured K8s response into a human-readable string.
            formatted_message = "Kubernetes command executed successfully."
            if mcp_result.get("status") == "success":
                result_data = mcp_result.get("result", {})
                if "pods" in result_data:
                    pod_names = [
                        p.get("name") for p in result_data["pods"] if p.get("name")
                    ]
                    if pod_names:
                        formatted_message = f"Found pods: {', '.join(pod_names)}."
                    else:
                        formatted_message = "No pods found."
                elif "services" in result_data:
                    service_names = [
                        s.get("name") for s in result_data["services"] if s.get("name")
                    ]
                    if service_names:
                        formatted_message = (
                            f"Found services: {', '.join(service_names)}."
                        )
                    else:
                        formatted_message = "No services found."
                elif "pod" in result_data:
                    pod_info = result_data["pod"]
                    formatted_message = f"Pod '{pod_info.get('name')}' status: {pod_info.get('status')}."
                elif "logs" in result_data:
                    logs_content = result_data["logs"]
                    # Truncate logs if very long for summary, provide full in body if needed
                    formatted_message = (
                        f"Logs retrieved: {logs_content[:200]}..."
                        if len(logs_content) > 200
                        else f"Logs retrieved: {logs_content}"
                    )
                else:
                    formatted_message = "Kubernetes command executed successfully with unknown result format."
            else:
                formatted_message = f"Kubernetes command failed: {mcp_result.get('error', 'Unknown error')}"
            # --- End Formatting ---

            return format_response_for_agent(formatted_message, success=True)

        except json.JSONDecodeError as e:
            logger.error(
                f"Failed to parse MCP response as JSON: {e}, Raw response: {mcp_result_json_str}"
            )
            return format_response_for_agent(
                f"Failed to parse MCP server response: {str(e)}", success=False
            )

    except Exception as e:
        logger.exception("Unexpected error occurred in Lambda handler")
        return format_response_for_agent(
            f"An unexpected error occurred: {str(e)}", success=False
        )


def format_response_for_agent(message: str, success: bool, http_status_code: int = 200):
    """Format response for Bedrock Agent based on its OpenAPI schema."""
    # The schema expects a 'message' property directly in the content.
    # We are simplifying the MCP server's structured output into this single string.
    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": "KubernetesCommands",
            "apiPath": "/process_k8s_command",
            "httpMethod": "POST",
            "httpStatusCode": http_status_code,
            "responseBody": {  # Changed from 'content' to 'responseBody' for direct JSON
                "application/json": {
                    "body": {  # The schema expects a JSON object here
                        "message": message  # This is the 'message' property the schema expects
                    }
                }
            },
        },
    }
