# src/graph.py

import re
import json
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from utube_to_infographics.llm import get_llm
from utube_to_infographics.mcp_client import call_mcp_tool


llm = get_llm()


# -----------------------
# Helper: Strip markdown fences from LLM output
# -----------------------

def clean_json(text: str) -> str:
    match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()


# -----------------------
# State Definition
# -----------------------

class GraphState(TypedDict):
    video_url: str
    transcript: Optional[str]
    structured_content: Optional[str]
    infographic_spec: Optional[str]
    output_path: Optional[str]


# -----------------------
# Node 1: Ingest + Structure
# -----------------------

async def ingest_node(state: GraphState):
    print("\n[1/3] Fetching transcript...")

    transcript = await call_mcp_tool(
        server_url="http://127.0.0.1:8000/sse",
        tool_name="get_transcript",
        payload={"url": state["video_url"]}
    )

    if transcript.get("status") == "error":
        raise Exception(f"Transcript error: {transcript.get('error')}")

    transcript_text = transcript.get("transcript", "")
    print(f"      Got {len(transcript_text)} chars of transcript")

    print("[2/3] Structuring content with LLM...")
    prompt = f"""
Convert this YouTube transcript into structured JSON for an infographic.
Return ONLY valid JSON — no explanation, no markdown fences.

The JSON must have this exact shape:
{{
  "title": "string",
  "sections": [
    {{
      "type": "bullets",
      "title": "Section Title",
      "content": ["point 1", "point 2"]
    }}
  ]
}}

Types allowed: "bullets", "steps", "numbers", "text"
Include 5-8 sections. Extract key numbers as a "numbers" section.

Transcript:
{transcript_text[:6000]}
"""

    response = await llm.ainvoke(prompt)

    return {
        "transcript": transcript_text,
        "structured_content": response.content
    }


# -----------------------
# Node 2: Layout Planner
# -----------------------

async def layout_node(state: GraphState):
    print("[3/3] Planning infographic layout...")

    prompt = f"""
Convert this structured content into an infographic spec JSON.
Return ONLY valid JSON — no explanation, no markdown fences.

The JSON must have this exact shape:
{{
  "title": "string",
  "canvas": {{"width": 900, "height": 1400}},
  "layout_type": "vertical",
  "color_palette": {{
    "background": "#1a1a2e",
    "primary": "#e94560",
    "secondary": "#0f3460",
    "text": "#ffffff",
    "accent": "#f5a623"
  }},
  "blocks": [
    {{
      "type": "bullets",
      "title": "Section Title",
      "content": ["item 1", "item 2"]
    }}
  ]
}}

Structured Content:
{state["structured_content"]}
"""

    response = await llm.ainvoke(prompt)

    return {
        "infographic_spec": response.content
    }


# -----------------------
# Node 3: Render
# -----------------------

async def render_node(state: GraphState):
    print("      Rendering infographic...")

    clean_spec = clean_json(state["infographic_spec"])

    result = await call_mcp_tool(
        server_url="http://127.0.0.1:8001/sse",
        tool_name="render_infographic",
        payload={"spec": clean_spec}
    )

    if result.get("status") == "error":
        raise Exception(f"Render error: {result.get('error')}")

    return {
        "output_path": result.get("file_path")
    }


# -----------------------
# Build Graph
# -----------------------

def build_graph():
    builder = StateGraph(GraphState)

    builder.add_node("ingest", ingest_node)
    builder.add_node("layout", layout_node)
    builder.add_node("render", render_node)

    builder.set_entry_point("ingest")

    builder.add_edge("ingest", "layout")
    builder.add_edge("layout", "render")
    builder.add_edge("render", END)

    return builder.compile()