"""
Real Estate Market Analyzer — Agent Core

Key pattern: when the model requests multiple tool calls in a single turn,
AgentSession dispatches all of them concurrently via asyncio.gather().
Total wait time equals the slowest tool, not the sum.

  Sequential estimate: 1.2 + 0.8 + 1.5 + 0.9 + 0.5 = 4.9 seconds
  Concurrent:          max(1.2, 0.8, 1.5, 0.9, 0.5) = 1.5 seconds

Uses azure-ai-projects 2.x + openai SDK Responses API:
  - AIProjectClient.get_openai_client() → AsyncOpenAI pointed at Foundry
  - client.responses.create() with previous_response_id maintains conversation
  - No persistent thread or assistant objects needed
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
from dotenv import load_dotenv

from tools import FUNCTION_MAP, TOOL_DEFINITIONS

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
    calls: list[dict]               # [{"name": str, "args": dict}, ...]
    elapsed: float                  # actual wall-clock seconds
    sequential_estimate: float      # sum of individual latencies if run sequentially


@dataclass
class QueryResult:
    """Structured result returned by AgentSession.send_message()."""
    response: str
    tool_batches: list[ToolBatch] = field(default_factory=list)


class AgentSession:
    """
    Manages conversation state with an Azure AI Foundry model via the Responses API.

    Use as an async context manager:

        async with AgentSession() as session:
            result = await session.send_message("Analyse Austin for a family buyer")
            print(result.response)

    Conversation continuity is maintained via previous_response_id — each call
    to send_message() chains to the previous response so the model retains context.
    """

    async def __aenter__(self) -> "AgentSession":
        self._credential = DefaultAzureCredential()
        project_client = AIProjectClient(
            endpoint=PROJECT_ENDPOINT,
            credential=self._credential,
        )
        # get_openai_client() returns an AsyncOpenAI pointed at the Foundry endpoint
        self._client = await project_client.get_openai_client()
        self._previous_response_id: str | None = None
        return self

    async def __aexit__(self, *_) -> None:
        if hasattr(self, "_client"):
            await self._client.close()
        await self._credential.close()

    async def send_message(self, query: str) -> QueryResult:
        """Send a user message and return the assistant response with tool timing metadata."""
        create_kwargs: dict = {
            "model": MODEL_DEPLOYMENT_NAME,
            "input": query,
            "instructions": SYSTEM_PROMPT,
            "tools": TOOL_DEFINITIONS,
            "store": True,
        }
        if self._previous_response_id:
            create_kwargs["previous_response_id"] = self._previous_response_id

        response = await self._client.responses.create(**create_kwargs)

        tool_batches: list[ToolBatch] = []

        # Tool-call loop: the model may request multiple rounds of tool calls
        while True:
            tool_calls = [item for item in response.output if item.type == "function_call"]
            if not tool_calls:
                break

            tool_outputs, batch = await self._dispatch_tool_batch(tool_calls)
            tool_batches.append(batch)

            response = await self._client.responses.create(
                model=MODEL_DEPLOYMENT_NAME,
                previous_response_id=response.id,
                input=tool_outputs,
                tools=TOOL_DEFINITIONS,
                store=True,
            )

        self._previous_response_id = response.id
        return QueryResult(
            response=self._extract_text(response),
            tool_batches=tool_batches,
        )

    async def _dispatch_tool_batch(self, tool_calls) -> tuple[list[dict], ToolBatch]:
        """Execute all tool calls concurrently via asyncio.gather()."""
        calls_info = [
            {"name": tc.name, "args": json.loads(tc.arguments)}
            for tc in tool_calls
        ]
        sequential_est = sum(LATENCY_MAP.get(tc.name, 1.0) for tc in tool_calls)

        t0 = time.perf_counter()
        results = await asyncio.gather(*[
            FUNCTION_MAP[tc.name](**json.loads(tc.arguments)) for tc in tool_calls
        ])
        elapsed = time.perf_counter() - t0

        tool_outputs = [
            {"type": "function_call_output", "call_id": tc.call_id, "output": result}
            for tc, result in zip(tool_calls, results)
        ]
        return tool_outputs, ToolBatch(
            calls=calls_info,
            elapsed=elapsed,
            sequential_estimate=sequential_est,
        )

    @staticmethod
    def _extract_text(response) -> str:
        parts = []
        for item in response.output:
            if item.type == "message":
                for content in item.content:
                    if hasattr(content, "text"):
                        parts.append(content.text)
        return "\n".join(parts)


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
            except Exception as exc:
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
