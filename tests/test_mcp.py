import json
import os
import sys
from datetime import timedelta
from pathlib import Path

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def test_docker_mcp_host_is_allowed_but_untrusted_origins_are_rejected():
    from mcp.server.transport_security import TransportSecurityMiddleware
    from starlette.requests import HTTPConnection
    from qicetong.mcp_server import mcp

    middleware = TransportSecurityMiddleware(mcp.settings.transport_security)

    async def check(host, origin=None):
        headers = [(b"host", host.encode())]
        if origin:
            headers.append((b"origin", origin.encode()))
        return await middleware.validate_request(HTTPConnection({"type": "http", "headers": headers}))

    assert anyio.run(check, "host.docker.internal:8766") is None
    assert anyio.run(check, "127.0.0.1:8766") is None
    assert anyio.run(check, "untrusted.example:8766").status_code == 421
    assert anyio.run(check, "host.docker.internal:8766", "https://untrusted.example").status_code == 403


def test_real_mcp_initialize_discover_and_call(tmp_path):
    async def run():
        env = {**os.environ, "QCT_RUNTIME": str(tmp_path), "QCT_MCP_TRANSPORT": "stdio", "PYTHONUTF8": "1"}
        params = StdioServerParameters(command=sys.executable, args=["-m", "qicetong.mcp_server"], env=env, cwd=str(Path(__file__).resolve().parents[1]))
        async with stdio_client(params) as streams:
            async with ClientSession(*streams, read_timeout_seconds=timedelta(seconds=30)) as session:
                await session.initialize()
                names = {t.name for t in (await session.list_tools()).tools}
                assert {"review_enterprise", "get_system_evaluation", "preview_uploaded_policy_change"}.issubset(names) and len(names) == 9
                result = await session.call_tool("review_enterprise", {"company_id":"demo-01", "policy_id":"hnte-bj-2026", "as_of":"2026-09-22"})
                assert not result.isError
                report = result.structuredContent or json.loads(result.content[0].text)
                assert report["status"] == "pass" and report["is_demo"]
                graph = await session.call_tool("get_evidence_graph", {"report_id":report["id"]})
                assert not graph.isError
                export = await session.call_tool("export_review_report", {"report_id":report["id"]})
                assert not export.isError and "模拟" in export.content[0].text
                evaluation = await session.call_tool("get_system_evaluation", {})
                assert not evaluation.isError and "engine" in (evaluation.structuredContent or json.loads(evaluation.content[0].text))
    anyio.run(run)
