"""Resolves the MCP_TOKEN env var to an org once, at process start.

stdio transport gives us one subprocess per configured MCP client entry,
started with env vars from claude_desktop_config.json — there's no
per-request Authorization header to read (that only exists over HTTP
transport). So auth happens once here, and every tool call in this
process is implicitly scoped to the resolved org.
"""

import os
import sys

_org_id = None


def resolve_org_or_exit():
    """Read MCP_TOKEN, resolve it, and store the org id for get_org_id().
    Exits the process with a clear stderr message on any failure."""
    global _org_id

    from apps.mcp_tokens.models import MCPToken

    plaintext = os.environ.get("MCP_TOKEN")
    if not plaintext:
        print("MCP_TOKEN env var is not set.", file=sys.stderr)
        sys.exit(1)

    token = MCPToken.resolve(plaintext)
    if token is None:
        print("MCP_TOKEN is invalid or has been revoked.", file=sys.stderr)
        sys.exit(1)

    _org_id = str(token.org_id)


def get_org_id():
    if _org_id is None:
        raise RuntimeError("resolve_org_or_exit() must run before get_org_id()")
    return _org_id
