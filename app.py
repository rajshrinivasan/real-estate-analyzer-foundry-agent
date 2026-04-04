"""
Real Estate Market Analyzer — Web UI

FastAPI application that exposes the agent as a chat interface.
A single AgentSession (one Azure agent + thread) is created at startup
and reused across requests. A lock ensures requests are serialised so
that Azure run state is not corrupted by concurrent callers.

Start the server:
    uvicorn app:app --reload
Then open http://localhost:8000
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from agent import AgentSession


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AgentSession() as session:
        app.state.session = session
        app.state.lock = asyncio.Lock()
        yield


app = FastAPI(title="Real Estate Market Analyzer", lifespan=lifespan)
templates = Jinja2Templates(directory="templates")


class ChatRequest(BaseModel):
    message: str


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/chat")
async def chat(body: ChatRequest, request: Request):
    async with request.app.state.lock:
        try:
            result = await request.app.state.session.send_message(body.message)
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    return {
        "response": result.response,
        "tool_batches": [
            {
                "calls": batch.calls,
                "elapsed": round(batch.elapsed, 2),
                "sequential_estimate": round(batch.sequential_estimate, 1),
            }
            for batch in result.tool_batches
        ],
    }
