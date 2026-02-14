#!/usr/bin/env python3
"""
Quick test to verify MCP server lists terrain tools correctly.
This doesn't require FreeCAD connection.
"""

import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_list_tools():
    """List all available MCP tools."""
    server_params = StdioServerParameters(
        command="/home/dark/freepvc/.venv/bin/python",
        args=["/home/dark/freepvc/src/freepvc/server.py"],
        env={"PYTHONPATH": "/home/dark/freepvc/src"}
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List tools
            tools_result = await session.list_tools()

            print("=" * 60)
            print("FreePVC MCP Tools")
            print("=" * 60)

            for tool in tools_result.tools:
                print(f"\n{tool.name}")
                print(f"  {tool.description}")

            print("\n" + "=" * 60)
            print(f"Total tools: {len(tools_result.tools)}")
            print("=" * 60)

            # Check for terrain tools
            tool_names = [t.name for t in tools_result.tools]
            terrain_tools = [
                "import_terrain",
                "analyze_terrain_slope",
                "query_terrain_elevation",
                "create_sample_terrain_demo"
            ]

            print("\nTerrain tools found:")
            for tool in terrain_tools:
                status = "✓" if tool in tool_names else "✗"
                print(f"  {status} {tool}")

if __name__ == "__main__":
    try:
        asyncio.run(test_list_tools())
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
