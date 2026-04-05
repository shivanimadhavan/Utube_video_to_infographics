## Project Overview

This project converts a YouTube video into an infographic using a structured **LLM + LangGraph + MCP** pipeline.  
The system accepts a YouTube URL, extracts the transcript, transforms the transcript into structured content, generates an infographic specification in JSON, and renders the final infographic as a PNG image.

### Workflow

```mermaid
flowchart TD
    A[User enters YouTube URL] --> B[Main Application]
    B --> C[LangGraph Pipeline]

    C --> D[Ingest Node]
    D --> E[Transcript MCP Server]
    E --> F[YouTube Transcript Extraction]

    D --> G[LLM Content Structuring]
    G --> H[Structured JSON Content]

    H --> I[Layout Node]
    I --> J[LLM Infographic Planning]
    J --> K[Infographic Spec JSON]

    K --> L[Render Node]
    L --> M[Render MCP Server]
    M --> N[PIL Image Rendering]
    N --> O[Final Infographic PNG in outputs/]
