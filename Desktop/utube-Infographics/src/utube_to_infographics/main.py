# src/main.py

import asyncio
from utube_to_infographics.graph import build_graph

async def run():

    url = input("Enter YouTube URL: ")

    graph = build_graph()

    result = await graph.ainvoke({
        "video_url": url,
        "transcript": None,
        "structured_content": None,
        "infographic_spec": None,
        "output_path": None
    })

    print("\nInfographic created at:")
    print(result["output_path"])


if __name__ == "__main__":
    asyncio.run(run())
