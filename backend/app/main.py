from __future__ import annotations

import json
from collections.abc import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agents.orchestrator import process_query

load_dotenv()

app = FastAPI(title="The Lighthouse API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    query: str


async def _sse_stream(query: str) -> AsyncGenerator[str, None]:
    async for event in process_query(query):
        yield f"data: {json.dumps(event)}\n\n"
    yield "data: [DONE]\n\n"


@app.post("/api/search")
async def search(request: SearchRequest) -> StreamingResponse:
    """Stream SSE events: N article events then one bias_report event."""
    return StreamingResponse(
        _sse_stream(request.query),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/sources")
async def get_sources() -> list[dict]:
    """Return all tracked news sources with their metadata."""
    from app.agents.source_registry import load_registry  # noqa: PLC0415
    return load_registry()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
