# src/mcp_client.py
# Launches MCP servers as subprocesses via STDIO - no SSE, no network issues

import json
import sys
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def _get_server_path(server_filename: str) -> str:
    """Find the server file relative to project root."""
    # Try project root (2 levels up from src/utube_to_infographics/)
    current = os.path.dirname(os.path.abspath(__file__))
    for _ in range(3):
        candidate = os.path.join(current, server_filename)
        if os.path.exists(candidate):
            return candidate
        current = os.path.dirname(current)
    raise FileNotFoundError(f"Could not find {server_filename}")


# Map server URLs to their script filenames
SERVER_MAP = {
    "http://127.0.0.1:8000/sse": "transcript_server.py",
    "http://127.0.0.1:8001/sse": "render_server.py",
}


async def call_mcp_tool(server_url: str, tool_name: str, payload: dict) -> dict:
    """
    Call an MCP tool by launching the server as a subprocess via STDIO.
    No SSE, no network — reliable on all platforms.
    """
    server_file = SERVER_MAP.get(server_url)
    if not server_file:
        raise ValueError(f"No server mapped for URL: {server_url}")

    server_path = _get_server_path(server_file)

    server_params = StdioServerParameters(
        command=sys.executable,  # uses the current venv's python
        args=[server_path],
        env=None
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments=payload)

            for item in result.content:
                if hasattr(item, "text"):
                    try:
                        return json.loads(item.text)
                    except json.JSONDecodeError:
                        return {"raw": item.text}

    raise Exception(f"MCP tool '{tool_name}' returned no content")