# src/mcp_client.py
# Connects to MCP servers over SSE using the official MCP SDK client

import json
from mcp import ClientSession
from mcp.client.sse import sse_client


async def call_mcp_tool(server_url: str, tool_name: str, payload: dict) -> dict:
    """
    Call a tool on an MCP SSE server.
    server_url: the /sse endpoint e.g. "http://127.0.0.1:8000/sse"
    """
    async with sse_client(url=server_url) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            result = await session.call_tool(tool_name, arguments=payload)

            for item in result.content:
                if hasattr(item, "text"):
                    try:
                        return json.loads(item.text)
                    except json.JSONDecodeError:
                        return {"raw": item.text}

    raise Exception(f"MCP tool '{tool_name}' returned no content from {server_url}")
