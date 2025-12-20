import asyncio
import os
from contextlib import AsyncExitStack
from typing import Any, List, Optional

import google.generativeai as genai
import nest_asyncio
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Apply nest_asyncio for Jupyter/IPython compatibility
nest_asyncio.apply()

# Load environment variables
load_dotenv(".env")


class MCPGeminiClient:
    """Client for interacting with Gemini models using MCP tools."""

    def __init__(self, model: str = "gemini-1.5-pro"):
        """Initialize the Gemini MCP client.
        Args:
            model: The Gemini model to use.
        """
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.model = model
        self.stdio: Optional[Any] = None
        self.write: Optional[Any] = None

        # Configure Gemini API (requires GOOGLE_API_KEY in .env)
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        self.gemini = genai.GenerativeModel(model)

    async def connect_to_server(self, server_script_path: str = "server.py"):
        """Connect to an MCP server."""
        server_params = StdioServerParameters(
            command="python",
            args=[server_script_path],
        )

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        await self.session.initialize()

        tools_result = await self.session.list_tools()
        print("\nConnected to server with tools:")
        for tool in tools_result.tools:
            print(f"  - {tool.name}: {tool.description}")

    async def get_mcp_tools(self) -> List[genai.protos.FunctionDeclaration]:
        """Get available tools from the MCP server in Gemini function format."""
        tools_result = await self.session.list_tools()

        gemini_tools = []
        for tool in tools_result.tools:
            # Create a simple schema that Gemini accepts
            # Use an empty schema for tools that don't need parameters
            schema = genai.protos.Schema(type=genai.protos.Type.OBJECT, properties={})

            function_decl = genai.protos.FunctionDeclaration(
                name=tool.name, description=tool.description, parameters=schema
            )

            gemini_tools.append(function_decl)

        return gemini_tools

    async def process_query(self, query: str) -> str:
        """Process a query using Gemini and available MCP tools."""
        try:
            tools = await self.get_mcp_tools()
            print(f"🔧 Available tools: {[tool.name for tool in tools]}")
            # Create tool configuration
            if tools:
                tool_config = genai.protos.Tool(function_declarations=tools)
                # Ask Gemini with tool awareness
                response = self.gemini.generate_content(
                    contents=query, tools=[tool_config]
                )
            else:
                response = self.gemini.generate_content(contents=query)
            if not response.candidates:
                return "No response from Gemini."
            candidate = response.candidates[0]
            # Check if there are function calls
            if hasattr(candidate, "content") and candidate.content.parts:
                for part in candidate.content.parts:
                    if hasattr(part, "function_call") and part.function_call:
                        fn_call = part.function_call
                        fn_name = fn_call.name
                        fn_args = dict(fn_call.args) if fn_call.args else {}

                        print(f"🚀 Calling tool: {fn_name} with args: {fn_args}")

                        # Call MCP tool
                        result = await self.session.call_tool(fn_name, fn_args)

                        # Extract result content
                        tool_result = ""
                        if hasattr(result, "content") and result.content:
                            if (
                                isinstance(result.content, list)
                                and len(result.content) > 0
                            ):
                                tool_result = result.content[0].text
                            else:
                                tool_result = str(result.content)
                        else:
                            tool_result = str(result)

                        print(f"📋 Tool result: {tool_result[:200]}...")
                        # Create a new prompt with the tool result
                        follow_up_prompt = f"""
                        User asked: {query}
                        I called the tool '{fn_name}' and got this result:
                        {tool_result}
                        Please provide a helpful response to the user's question based on this information.
                        """
                        # Get final response from Gemini
                        final_response = self.gemini.generate_content(follow_up_prompt)
                        return final_response.text
            # No function calls, return the direct response
            if hasattr(candidate, "content") and candidate.content.parts:
                return (
                    candidate.content.parts[0].text
                    if candidate.content.parts
                    else "No content returned."
                )

            return "No response generated."
        except Exception as e:
            import traceback

            print(f"Error details: {traceback.format_exc()}")
            return f"Error processing query: {str(e)}"

    async def cleanup(self):
        await self.exit_stack.aclose()


async def main():
    try:
        client = MCPGeminiClient()
        await client.connect_to_server("server.py")
        query = "What is our remote work policy"
        print(f"\nQuery: {query}")
        response = await client.process_query(query)
        print(f"\nResponse: {response}")
        await client.cleanup()
    except Exception as e:
        print(f"Main error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
