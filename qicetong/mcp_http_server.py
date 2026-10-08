"""Run the Qicetong MCP server using Nexent's streamable HTTP transport."""
from __future__ import annotations

import os

os.environ.setdefault("QCT_MCP_PORT", "8767")

from . import mcp_server  # noqa: E402


if __name__ == "__main__":
    mcp_server.store.initialize()
    mcp_server.mcp.run(transport="streamable-http")
