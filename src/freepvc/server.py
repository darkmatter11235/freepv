"""FreePVC MCP Server - Entry point for the Model Context Protocol server.

Extends freecad-mcp with solar-specific tools for PV plant design.
"""

import asyncio
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP

from freepvc.connection import FreePVCConnection


# Create FastMCP server instance
mcp = FastMCP("freepvc")


@asynccontextmanager
async def server_lifespan(server: FastMCP):
    """Manage server lifecycle - establish FreeCAD connection on startup."""
    # Establish connection to FreeCAD XML-RPC server
    connection = FreePVCConnection()

    try:
        # Test connection
        connection.ping()
        print("✓ Connected to FreeCAD RPC server on port 9876", flush=True)
    except Exception as e:
        print(f"⚠ Warning: Could not connect to FreeCAD: {e}", flush=True)
        print("  Make sure FreeCAD is running with FreePVC workbench and RPC server started", flush=True)

    # Make connection available to all tool handlers via context
    yield {"connection": connection}


# Register the lifespan handler
mcp.lifespan = server_lifespan


# Import MCP tools to register them with the server
# These imports will register @mcp.tool decorated functions
from freepvc.mcp_tools import project  # noqa: E402, F401


def main():
    """Entry point for the freepvc command."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
