"""
Real Estate Market Analyzer — Agent Core

Key pattern: when the model requests multiple tool calls in a single turn,
AgentSession dispatches all of them concurrently via asyncio.gather().
Total wait time equals the slowest tool, not the sum.

  Sequential estimate: 1.2 + 0.8 + 1.5 + 0.9 + 0.5 = 4.9 seconds
  Concurrent:          max(1.2, 0.8, 1.5, 0.9, 0.5) = 1.5 seconds

Uses the azure-ai-projects async client (azure.ai.projects.aio) throughout.
"""

import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from azure.identity.aio import DefaultAzureCredential
from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import FunctionTool, ToolSet
from dotenv import load_dotenv

from tools import FUNCTION_MAP

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv(Path(__file__).parent / ".env")

PROJECT_ENDPOINT = os.environ["PROJECT_ENDPOINT"]
MODEL_DEPLOYMENT_NAME = os.environ["MODEL_DEPLOYMENT_NAME"]
SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "system_prompt.txt").read_text()

# Known simulated latencies — used to show the concurrency benefit at runtime.
LATENCY_MAP = {
    "get_property_listings": 1.2,
    "get_neighborhood_stats": 0.8,
    "get_school_ratings": 1.5,
    "get_crime_index": 0.9,
    "get_mortgage_rates": 0.5,
}


@dataclass
class ToolBatch:
    """One round of concurrent tool calls (a single asyncio.gather invocation)."""
    calls: list[dict]        # [{"name": str, "args": dict}, ...]
    elapsed: float           # actual wall-clock seconds
    sequential_estimate: float  # sum of individual latencies if run sequentially


@dataclass
class QueryResult:
    """Structured result returned by AgentSession.send_message()."""
    response: str
    tool_batches: list[ToolBatch] = field(default_factory=list)


class AgentSession:
    """
    Manages an Azure AI Foundry agent lifecycle and handles concurrent tool dispatch.

    Use as an async context manager:

        async with AgentSession() as session:
            result = await session.send_message("Analyse Austin for a family buyer")
            print(result.response)

    A single thread is maintained for the lifetime of the session so the model
    has conversational context across multiple send_message() calls.
    """

    async def __aenter__(self) -> "AgentSession":
        self._credential = DefaultAzureCredential()
        self._client = AIProjectClient(
            endpoint=PROJECT_ENDPOINT,
            credential=self._credential,
        )
        await self._client.__aenter__()

        toolset = ToolSet()
        toolset.add(FunctionTool(set(FUNCTION_MAP.values())))

        agent = await self._client.agents.create_agent(
            model=MODEL_DEPLOYMENT_NAME,
            name="real-estate-analyzer",
            instructions=SYSTEM_PROMPT,
            tools=toolset.definitions,
        )
        self._agent_id = agent.id

        thread = await self._client.agents.threads.create()
        self._thread_id = thread.id
        return self

    async def __aexit__(self, *args) -> None:
        if hasattr(self, "_agent_id"):
            try:
                await self._client.agents.delete_agent(self._agent_id)
            except Exception:
                pass
        await self._client.__aexit__(*args)
        await self._credential.close()

    async def send_message(self, query: str) -> QueryResult:
        """Send a user message and return the assistant response with tool timing metadata."""
        await self._client.agents.messages.create(
            thread_id=self._thread_id,
            role="user",
            content=query,
        )

        run = await self._client.agents.runs.create(
            thread_id=self._thread_id,
            agent_id=self._agent_id,
        )

        tool_batches: list[ToolBatch] = []

        while run.status in ("queued", "in_progress", "requires_action"):
            if self._has_tool_calls(run):
                tool_outputs, batch = await self._dispatch_tool_batch(run)
                tool_batches.append(batch)
                run = await self._client.agents.runs.submit_tool_outputs(
                    thread_id=self._thread_id,
                    run_id=run.id,
                    tool_outputs=tool_outputs,
                )
            else:
                await asyncio.sleep(0.5)
                run = await self._client.agents.runs.get(
                    thread_id=self._thread_id,
                    run_id=run.id,
                )

        if run.status == "failed":
            raise RuntimeError(f"Run failed: {run.last_error}")

        response = await self._extract_latest_response()
        return QueryResult(response=response, tool_batches=tool_batches)

    async def _dispatch_tool_batch(self, run) -> tuple[list[dict], ToolBatch]:
        """Execute all tool calls in one run step concurrently via asyncio.gather()."""
        tool_calls = run.required_action.submit_tool_outputs.tool_calls
        calls_info = [
            {"name": tc.function.name, "args": json.loads(tc.function.arguments)}
            for tc in tool_calls
        ]
        sequential_est = sum(
            LATENCY_MAP.get(tc.function.name, 1.0) for tc in tool_calls
        )

        t0 = time.perf_counter()
        outputs = await asyncio.gather(*[self._call_tool(tc) for tc in tool_calls])
        elapsed = time.perf_counter() - t0

        batch = ToolBatch(
            calls=calls_info,
            elapsed=elapsed,
            sequential_estimate=sequential_est,
        )
        return list(outputs), batch

    async def _call_tool(self, tool_call) -> dict:
        fn_name = tool_call.function.name
        fn_args = json.loads(tool_call.function.arguments)
        result = await FUNCTION_MAP[fn_name](**fn_args)
        return {"tool_call_id": tool_call.id, "output": result}

    async def _extract_latest_response(self) -> str:
        messages = await self._client.agents.messages.list(thread_id=self._thread_id)
        for msg in messages:
            if msg.role == "assistant":
                return "\n".join(
                    c.text.value for c in msg.content if hasattr(c, "text")
                )
        return ""

    @staticmethod
    def _has_tool_calls(run) -> bool:
        return (
            run.status == "requires_action"
            and run.required_action is not None
            and run.required_action.submit_tool_outputs is not None
        )


# ── CLI entry point ───────────────────────────────────────────────────────────

async def main():
    print("Real Estate Market Analyzer")
    print("Supported cities: Austin, Phoenix, Denver, Miami")
    print("Type 'exit' to quit.\n")

    async with AgentSession() as session:
        while True:
            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if user_input.lower() in {"exit", "quit"}:
                break
            if not user_input:
                continue

            try:
                result = await session.send_message(user_input)
            except RuntimeError as exc:
                print(f"Error: {exc}\n")
                continue

            for i, batch in enumerate(result.tool_batches, 1):
                print(f"\n  [tools] batch {i}: {len(batch.calls)} call(s) concurrently:")
                for call in batch.calls:
                    print(f"    \u2192 {call['name']}({call['args']})")
                print(
                    f"  [tools] completed in {batch.elapsed:.2f}s "
                    f"(sequential would be ~{batch.sequential_estimate:.1f}s)"
                )

            print(f"\nAssistant: {result.response}\n")


if __name__ == "__main__":
    asyncio.run(main())
