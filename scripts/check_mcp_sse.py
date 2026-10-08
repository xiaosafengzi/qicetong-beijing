"""Verify the actual local SSE transport without modifying enterprise data."""
import json
from datetime import datetime, timezone
from pathlib import Path

import anyio
from mcp import ClientSession
from mcp.client.sse import sse_client


async def main():
    async with sse_client("http://127.0.0.1:8766/sse") as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            names = [tool.name for tool in (await session.list_tools()).tools]
            assert len(names) == 9 and {"get_system_evaluation", "preview_uploaded_policy_change"}.issubset(names)
            response = await session.call_tool("list_policy_catalog", {})
            assert not response.isError
            result = {"passed": True, "transport": "SSE", "url": "http://127.0.0.1:8766/sse", "tools": names,
                      "catalog_call_succeeded": True, "at": datetime.now(timezone.utc).isoformat(),
                      "scope": "MCP SDK client to local service; not a Nexent platform integration test"}
            output = Path(__file__).resolve().parents[1] / "artifacts" / "mcp-sse-results.json"
            output.parent.mkdir(exist_ok=True)
            output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    anyio.run(main)
