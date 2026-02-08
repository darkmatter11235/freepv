"""Project management MCP tools for FreePVC."""

from typing import Any, Dict
from mcp.types import TextContent, ImageContent
from mcp.server.fastmcp import Context

# Import the mcp server instance from server.py
from freepvc.server import mcp


@mcp.tool()
async def create_project(
    project_name: str,
    latitude: float,
    longitude: float,
    altitude: float = 0.0,
    timezone: str = "UTC",
    ctx: Context = None,
) -> list[TextContent | ImageContent]:
    """Create a new FreePVC solar project with site information.

    Args:
        project_name: Name of the project
        latitude: Site latitude in decimal degrees
        longitude: Site longitude in decimal degrees
        altitude: Site altitude in meters (default: 0)
        timezone: Site timezone (default: UTC)
        ctx: MCP context

    Returns:
        List containing project creation status and details
    """
    connection = ctx.request_context["connection"]

    try:
        # Create a new FreeCAD document
        code = f"""
import FreeCAD
import FreeCADGui

# Create new document
doc = FreeCAD.newDocument("{project_name}")
FreeCAD.setActiveDocument("{project_name}")

# Add project metadata as document properties
doc.addProperty("App::PropertyString", "ProjectName", "FreePVC", "Project name")
doc.ProjectName = "{project_name}"

doc.addProperty("App::PropertyFloat", "Latitude", "FreePVC", "Site latitude (deg)")
doc.Latitude = {latitude}

doc.addProperty("App::PropertyFloat", "Longitude", "FreePVC", "Site longitude (deg)")
doc.Longitude = {longitude}

doc.addProperty("App::PropertyFloat", "Altitude", "FreePVC", "Site altitude (m)")
doc.Altitude = {altitude}

doc.addProperty("App::PropertyString", "Timezone", "FreePVC", "Site timezone")
doc.Timezone = "{timezone}"

# Create main groups for organization
layout_group = doc.addObject("App::DocumentObjectGroup", "Layout")
terrain_group = doc.addObject("App::DocumentObjectGroup", "Terrain")
electrical_group = doc.addObject("App::DocumentObjectGroup", "Electrical")
civil_group = doc.addObject("App::DocumentObjectGroup", "Civil")

doc.recompute()

"Project created successfully"
"""
        result = connection.execute_code(code)

        return [
            TextContent(
                type="text",
                text=f"""✓ FreePVC Project Created

Project: {project_name}
Location: {latitude}°N, {longitude}°E
Altitude: {altitude} m
Timezone: {timezone}

Document groups created:
- Layout (solar arrays)
- Terrain (site terrain)
- Electrical (cables, inverters)
- Civil (grading, infrastructure)

Ready to import terrain data and create layouts.
""",
            )
        ]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=f"✗ Error creating project: {str(e)}\n\nMake sure FreeCAD is running with the FreePVC RPC server started.",
            )
        ]


@mcp.tool()
async def get_project_summary(
    ctx: Context = None,
) -> list[TextContent]:
    """Get an overview of the current project state.

    Returns:
        Summary of current FreeCAD document with project details
    """
    connection = ctx.request_context["connection"]

    try:
        code = """
import FreeCAD

doc = FreeCAD.ActiveDocument
if doc is None:
    "No active project"
else:
    info = {
        "name": doc.Name,
        "objects": len(doc.Objects),
        "project_name": getattr(doc, "ProjectName", "Unknown"),
        "latitude": getattr(doc, "Latitude", None),
        "longitude": getattr(doc, "Longitude", None),
        "altitude": getattr(doc, "Altitude", None),
        "timezone": getattr(doc, "Timezone", "Unknown"),
    }

    # Count objects by type
    groups = {}
    for grp in ["Layout", "Terrain", "Electrical", "Civil"]:
        try:
            g = doc.getObject(grp)
            groups[grp] = len(g.Group) if g else 0
        except:
            groups[grp] = 0

    info["groups"] = groups
    info
"""
        result = connection.execute_code(code)

        if isinstance(result, str) and result == "No active project":
            return [TextContent(type="text", text="No active FreePVC project. Use create_project first.")]

        # Format the summary
        summary = f"""📊 FreePVC Project Summary

Document: {result.get('name', 'Unknown')}
Project: {result.get('project_name', 'Unknown')}
Location: {result.get('latitude', 'N/A')}°N, {result.get('longitude', 'N/A')}°E
Altitude: {result.get('altitude', 'N/A')} m
Timezone: {result.get('timezone', 'Unknown')}

Total Objects: {result.get('objects', 0)}

Object Groups:
"""
        groups = result.get("groups", {})
        for group_name, count in groups.items():
            summary += f"  {group_name}: {count} objects\n"

        return [TextContent(type="text", text=summary)]

    except Exception as e:
        return [TextContent(type="text", text=f"✗ Error getting project summary: {str(e)}")]


@mcp.tool()
async def save_project(
    file_path: str = "",
    ctx: Context = None,
) -> list[TextContent]:
    """Save the current FreeCAD document.

    Args:
        file_path: Path to save the .FCStd file (optional, uses current path if already saved)

    Returns:
        Save status
    """
    connection = ctx.request_context["connection"]

    try:
        if file_path:
            code = f"""
import FreeCAD
doc = FreeCAD.ActiveDocument
if doc:
    doc.saveAs("{file_path}")
    "Saved to {file_path}"
else:
    "No active document"
"""
        else:
            code = """
import FreeCAD
doc = FreeCAD.ActiveDocument
if doc:
    if doc.FileName:
        doc.save()
        f"Saved to {doc.FileName}"
    else:
        "Document has not been saved yet. Provide a file path."
else:
    "No active document"
"""
        result = connection.execute_code(code)

        return [TextContent(type="text", text=f"✓ {result}")]

    except Exception as e:
        return [TextContent(type="text", text=f"✗ Error saving project: {str(e)}")]
