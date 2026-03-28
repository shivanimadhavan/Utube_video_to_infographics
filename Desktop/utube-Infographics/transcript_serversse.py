# transcript_server.py
# Official MCP SDK server with SSE transport
# Run: python transcript_server.py

import re
import json
import uvicorn
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.requests import Request
from youtube_transcript_api import YouTubeTranscriptApi
import os
from pathlib import Path
CERT_PATH = Path(__file__).parent.parent / "iav-certs.pem"  
os.environ["REQUESTS_CA_BUNDLE"] = str(CERT_PATH)
os.environ["SSL_CERT_FILE"] = str(CERT_PATH)
server = Server("transcript-server")
sse = SseServerTransport("/messages")


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
            transcript_list = fetched
            full_text = " ".join([snippet.text if hasattr(snippet, "text") else snippet["text"] for snippet in transcript_list])
            result = {"video_id": video_id, "transcript": full_text, "status": "success"}
        except Exception as e:
            result = {"status": "error", "error": str(e)}
        return [TextContent(type="text", text=json.dumps(result))]
    raise ValueError(f"Unknown tool: {name}")


async def handle_sse(request: Request):
    async with sse.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await server.run(
            streams[0], streams[1],
            server.create_initialization_options()
        )


async def handle_messages(request: Request):
    await sse.handle_post_message(
        request.scope, request.receive, request._send
    )


app = Starlette(routes=[
    Route("/sse", endpoint=handle_sse),
    Route("/messages", endpoint=handle_messages, methods=["POST"]),
])


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
