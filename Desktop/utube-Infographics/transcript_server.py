# transcript_server.py
# MCP server using STDIO transport (most reliable, no network issues)
# This is called as a subprocess by the client - do NOT run manually

import re
import json
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from youtube_transcript_api import YouTubeTranscriptApi
import os
from pathlib import Path
CERT_PATH = Path(__file__).parent.parent / "iav-certs.pem"  
os.environ["REQUESTS_CA_BUNDLE"] = str(CERT_PATH)
os.environ["SSL_CERT_FILE"] = str(CERT_PATH)

server = Server("transcript-server")


def extract_video_id(url: str) -> str:
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
        r"(?:embed\/)([0-9A-Za-z_-]{11})",
        r"(?:youtu\.be\/)([0-9A-Za-z_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Could not extract video ID from: {url}")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_transcript",
            description="Fetch the transcript of a YouTube video by URL",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "YouTube video URL"}
                },
                "required": ["url"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "get_transcript":
        url = arguments.get("url", "")
        try:
            video_id = extract_video_id(url)
            ytt = YouTubeTranscriptApi()
            fetched = ytt.fetch(video_id)
            full_text = " ".join([
                snippet.text if hasattr(snippet, "text") else snippet["text"]
                for snippet in fetched
            ])
            result = {"video_id": video_id, "transcript": full_text, "status": "success"}
        except Exception as e:
            result = {"status": "error", "error": str(e)}
        return [TextContent(type="text", text=json.dumps(result))]
    raise ValueError(f"Unknown tool: {name}")


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
