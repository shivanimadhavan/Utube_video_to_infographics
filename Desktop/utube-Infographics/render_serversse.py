# render_server.py
# Official MCP SDK server with SSE transport
# Run: python render_server.py

import json
import os
import re
import uuid
import uvicorn
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.requests import Request
from PIL import Image, ImageDraw, ImageFont



server = Server("render-server")
sse = SseServerTransport("/messages")

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def clean_json_string(text: str) -> str:
    match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()


def hex_to_rgb(hex_color: str):
    try:
        hex_color = hex_color.lstrip("#")
        if len(hex_color) == 3:
            hex_color = "".join(c * 2 for c in hex_color)
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    except Exception:
        return (255, 255, 255)


def get_fonts():
    sizes = {"title": 36, "heading": 24, "body": 18, "small": 14}
    fonts = {}
    candidates = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/calibri.ttf",
    ]
    for size_name, size in sizes.items():
        loaded = False
        for path in candidates:
            try:
                fonts[size_name] = ImageFont.truetype(path, size)
                loaded = True
                break
            except Exception:
                continue
        if not loaded:
            fonts[size_name] = ImageFont.load_default()
    return fonts


def wrap_text(text: str, max_chars: int) -> list:
    words = str(text).split()
    lines, current = [], ""
    for word in words:
        if len(current) + len(word) + 1 <= max_chars:
            current += (" " if current else "") + word
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def render_infographic(spec: dict) -> str:
    canvas = spec.get("canvas", {})
    width  = int(canvas.get("width", 900))
    height = int(canvas.get("height", 1400))

    palette    = spec.get("color_palette", {})
    bg_color   = palette.get("background", "#1a1a2e")
    primary    = palette.get("primary",    "#e94560")
    secondary  = palette.get("secondary",  "#0f3460")
    text_color = palette.get("text",       "#ffffff")
    accent     = palette.get("accent",     "#f5a623")

    img   = Image.new("RGB", (width, height), color=hex_to_rgb(bg_color))
    draw  = ImageDraw.Draw(img)
    fonts = get_fonts()
    padding   = 40
    max_chars = (width - padding * 2) // 10
    y = 0

    # Header
    draw.rectangle([0, 0, width, 90], fill=hex_to_rgb(secondary))
    title = spec.get("title", "Infographic")
    draw.text((padding, 25), title, font=fonts["title"], fill=hex_to_rgb(primary))
    y = 110

    blocks = spec.get("blocks", [])
    for block in blocks:
        if y > height - 120:
            break

        block_type  = block.get("type", "text")
        block_title = block.get("title", "")
        content     = block.get("content", [])
        if isinstance(content, str):
            content = [content]

        # Block title bar
        draw.rectangle([padding - 10, y - 4, width - padding + 10, y + 36],
                       fill=hex_to_rgb(secondary))
        draw.text((padding, y), str(block_title), font=fonts["heading"],
                  fill=hex_to_rgb(accent))
        y += 48

        if block_type in ("bullets", "list"):
            for item in content:
                if y > height - 60: break
                for line in wrap_text(f"  • {item}", max_chars):
                    draw.text((padding, y), line, font=fonts["body"],
                              fill=hex_to_rgb(text_color))
                    y += 26

        elif block_type == "steps":
            for i, item in enumerate(content):
                if y > height - 60: break
                for line in wrap_text(f"  {i+1}. {item}", max_chars):
                    draw.text((padding, y), line, font=fonts["body"],
                              fill=hex_to_rgb(text_color))
                    y += 26

        elif block_type in ("numbers", "stat"):
            x_pos = padding
            for item in content:
                draw.text((x_pos, y), str(item), font=fonts["heading"],
                          fill=hex_to_rgb(primary))
                x_pos += 220
                if x_pos > width - padding:
                    x_pos = padding
                    y += 44
            y += 44

        else:
            for item in content:
                for line in wrap_text(str(item), max_chars):
                    draw.text((padding, y), line, font=fonts["body"],
                              fill=hex_to_rgb(text_color))
                    y += 26

        draw.line([(padding, y + 6), (width - padding, y + 6)],
                  fill=hex_to_rgb(secondary), width=2)
        y += 22

    # Footer
    draw.rectangle([0, height - 44, width, height], fill=hex_to_rgb(secondary))
    draw.text((padding, height - 30), "Generated by utube-to-infographics",
              font=fonts["small"], fill=hex_to_rgb(text_color))

    filename = f"infographic_{uuid.uuid4().hex[:8]}.png"
    filepath = os.path.join(OUTPUT_DIR, filename)
    img.save(filepath)
    return filepath


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="render_infographic",
            description="Render an infographic PNG from a spec JSON string",
            inputSchema={
                "type": "object",
                "properties": {
                    "spec": {"type": "string", "description": "JSON string of infographic spec"}
                },
                "required": ["spec"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "render_infographic":
        spec_raw = arguments.get("spec", "{}")
        try:
            if isinstance(spec_raw, str):
                spec_raw = clean_json_string(spec_raw)
                spec = json.loads(spec_raw)
            else:
                spec = spec_raw
            file_path = render_infographic(spec)
            result = {"status": "success", "file_path": file_path}
        except Exception as e:
            result = {"status": "error", "error": str(e), "file_path": None}
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
    uvicorn.run(app, host="127.0.0.1", port=8001)
