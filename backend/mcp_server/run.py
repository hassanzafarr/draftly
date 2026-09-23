"""Entrypoint for the standalone Draftly MCP server (stdio transport).

Run with: MCP_TOKEN=<secret> python mcp_server/run.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from mcp_server.auth import resolve_org_or_exit  # noqa: E402
from mcp_server.server import mcp  # noqa: E402

if __name__ == "__main__":
    resolve_org_or_exit()
    mcp.run(transport="stdio")
