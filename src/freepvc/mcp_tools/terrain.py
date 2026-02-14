"""MCP tools for terrain import and analysis.

Exposes terrain operations via Model Context Protocol.
"""

from mcp.types import TextContent, ImageContent
from mcp.server.fastmcp import Context
import numpy as np
import json

from freepvc.server import mcp
from freepvc.io.terrain_import import TerrainImporter, create_sample_terrain
from freepvc.engines.terrain_engine import TerrainEngine


@mcp.tool()
async def import_terrain(
    file_path: str,
    unit_scale: float = 1000.0,
    format: str = "auto",
    object_name: str = "Terrain",
    ctx: Context = None,
) -> list[TextContent | ImageContent]:
    """Import terrain data from file and create mesh in FreeCAD.

    Supports CSV point clouds, DEM ASCII grids, and XYZ text files.
    Creates a triangulated mesh and displays it in FreeCAD.

    Args:
        file_path: Path to terrain data file
        unit_scale: Multiplier to convert file units to mm (1000.0 for meters, 1.0 for mm)
        format: File format - "auto", "csv", "dem_ascii", or "xyz"
        object_name: Name for the terrain object in FreeCAD

    Returns:
        Summary of imported terrain with statistics
    """
    connection = ctx.request_context["connection"]

    try:
        # Import terrain data
        if format == "auto":
            terrain_data = TerrainImporter.import_auto(file_path, unit_scale=unit_scale)
        elif format == "csv":
            terrain_data = TerrainImporter.import_csv_points(file_path, unit_scale=unit_scale)
        elif format == "dem_ascii":
            terrain_data = TerrainImporter.import_dem_ascii(file_path, unit_scale=unit_scale)
        elif format == "xyz":
            terrain_data = TerrainImporter.import_xyz_text(file_path, unit_scale=unit_scale)
        else:
            return [TextContent(type="text", text=f"Error: Unknown format '{format}'")]

        # Generate mesh
        mesh = TerrainEngine.create_mesh_from_points(terrain_data)

        # Get statistics
        stats = terrain_data.get_statistics()

        # Create mesh in FreeCAD via RPC
        vertices_list = mesh.vertices.tolist()
        triangles_list = mesh.triangles.tolist()

        result = connection.create_terrain_mesh(vertices_list, triangles_list, object_name)

        # Format response
        response = f"""✓ Terrain imported successfully

**File:** {file_path}
**Source:** {terrain_data.source.value}
**Points:** {stats['num_points']:,}
**Mesh:** {mesh.num_vertices:,} vertices, {mesh.num_faces:,} faces

**Extent:**
- X: {stats['x_extent_m']:.1f} m
- Y: {stats['y_extent_m']:.1f} m
- Elevation range: {stats['elevation_range_m']:.1f} m

**Elevation:**
- Mean: {stats['mean_elevation_mm'] / 1000:.2f} m
- Std dev: {stats['std_elevation_mm'] / 1000:.2f} m

FreeCAD object: `{object_name}`
"""

        return [TextContent(type="text", text=response)]

    except Exception as e:
        return [TextContent(type="text", text=f"✗ Error importing terrain: {str(e)}")]


@mcp.tool()
async def analyze_terrain_slope(
    terrain_name: str = "Terrain",
    color_scheme: str = "slope",
    ctx: Context = None,
) -> list[TextContent | ImageContent]:
    """Analyze slope and aspect of terrain mesh and apply color heatmap.

    Calculates slope angle and aspect (compass direction) for each face
    of the terrain mesh, then applies color visualization.

    Args:
        terrain_name: Name of terrain object in FreeCAD
        color_scheme: Coloring scheme - "slope" (green to red) or "aspect" (compass colors)

    Returns:
        Slope analysis statistics and classification
    """
    connection = ctx.request_context["connection"]

    try:
        # Get terrain mesh from FreeCAD
        code = f"""
import FreeCAD
import numpy as np

doc = FreeCAD.ActiveDocument
terrain = doc.getObject("{terrain_name}")

if terrain is None:
    result = {{"error": "Terrain object not found"}}
else:
    # Extract mesh data
    mesh = terrain.Mesh
    vertices = []
    for v in mesh.Points:
        vertices.append([v.x, v.y, v.z])

    triangles = []
    for f in mesh.Facets:
        triangles.append([f.PointIndices[0], f.PointIndices[1], f.PointIndices[2]])

    result = {{
        "vertices": vertices,
        "triangles": triangles,
    }}
"""
        mesh_data = connection.execute_code(code)

        if "error" in mesh_data:
            return [TextContent(type="text", text=f"✗ {mesh_data['error']}")]

        # Reconstruct TerrainMesh
        from freepvc.models.terrain import TerrainMesh
        vertices = np.array(mesh_data["vertices"])
        triangles = np.array(mesh_data["triangles"])
        mesh = TerrainMesh(vertices=vertices, triangles=triangles)

        # Analyze slope
        slope_map = TerrainEngine.analyze_slope(mesh)
        stats = slope_map.get_statistics()

        # Generate colors
        colors = slope_map.compute_heatmap_colors(color_scheme)
        colors_list = colors.tolist()

        # Apply colors to FreeCAD mesh
        connection.set_face_colors(terrain_name, colors_list)

        # Format response
        response = f"""✓ Terrain slope analysis complete

**Slope Statistics:**
- Mean slope: {stats['mean_slope_deg']:.2f}°
- Max slope: {stats['max_slope_deg']:.2f}°
- Min slope: {stats['min_slope_deg']:.2f}°
- Std dev: {stats['std_slope_deg']:.2f}°

**Classification:**
- Flat (0-5°): {stats['num_flat']:,} faces
- Gentle (5-15°): {stats['num_gentle']:,} faces
- Moderate (15-25°): {stats['num_moderate']:,} faces
- Steep (25-35°): {stats['num_steep']:,} faces
- Very steep (>35°): {stats['num_very_steep']:,} faces

**Buildable area:** {stats['buildable_area_pct']:.1f}% (slope ≤ 20°)

Color scheme applied: {color_scheme}
"""

        return [TextContent(type="text", text=response)]

    except Exception as e:
        return [TextContent(type="text", text=f"✗ Error analyzing slope: {str(e)}")]


@mcp.tool()
async def query_terrain_elevation(
    x: float,
    y: float,
    terrain_name: str = "Terrain",
    ctx: Context = None,
) -> list[TextContent | ImageContent]:
    """Query elevation at a specific (x, y) coordinate.

    Interpolates elevation from terrain mesh at the query point.

    Args:
        x: X coordinate in mm
        y: Y coordinate in mm
        terrain_name: Name of terrain object in FreeCAD

    Returns:
        Interpolated elevation value
    """
    connection = ctx.request_context["connection"]

    try:
        # Get terrain mesh from FreeCAD (same as analyze_terrain_slope)
        code = f"""
import FreeCAD
import numpy as np

doc = FreeCAD.ActiveDocument
terrain = doc.getObject("{terrain_name}")

if terrain is None:
    result = {{"error": "Terrain object not found"}}
else:
    mesh = terrain.Mesh
    vertices = [[v.x, v.y, v.z] for v in mesh.Points]
    triangles = [[f.PointIndices[0], f.PointIndices[1], f.PointIndices[2]] for f in mesh.Facets]

    result = {{
        "vertices": vertices,
        "triangles": triangles,
    }}
"""
        mesh_data = connection.execute_code(code)

        if "error" in mesh_data:
            return [TextContent(type="text", text=f"✗ {mesh_data['error']}")]

        # Reconstruct mesh
        from freepvc.models.terrain import TerrainMesh
        vertices = np.array(mesh_data["vertices"])
        triangles = np.array(mesh_data["triangles"])
        mesh = TerrainMesh(vertices=vertices, triangles=triangles)

        # Interpolate elevation
        query_point = np.array([x, y])
        elevation = TerrainEngine.interpolate_elevation(mesh, query_point)

        # Also compute slope at this point
        slopes = TerrainEngine.compute_slopes_at_points(mesh, query_point.reshape(1, -1))
        slope = slopes[0]

        response = f"""✓ Terrain elevation query

**Location:** ({x/1000:.2f}m, {y/1000:.2f}m)
**Elevation:** {elevation/1000:.2f} m ({elevation:.1f} mm)
**Slope:** {slope:.2f}°
"""

        return [TextContent(type="text", text=response)]

    except Exception as e:
        return [TextContent(type="text", text=f"✗ Error querying elevation: {str(e)}")]


@mcp.tool()
async def create_sample_terrain_demo(
    size_m: float = 50.0,
    spacing_m: float = 2.0,
    slope_deg: float = 5.0,
    roughness_m: float = 0.5,
    apply_slope_colors: bool = True,
    object_name: str = "SampleTerrain",
    ctx: Context = None,
) -> list[TextContent | ImageContent]:
    """Create a sample terrain for testing and demonstration.

    Generates a synthetic terrain with specified characteristics.

    Args:
        size_m: Terrain extent in meters (default 50m square)
        spacing_m: Point spacing in meters (default 2m)
        slope_deg: Base slope in degrees (default 5°)
        roughness_m: Random elevation variation in meters (default 0.5m)
        apply_slope_colors: Apply slope-based color heatmap
        object_name: Name for terrain object

    Returns:
        Statistics of created terrain
    """
    connection = ctx.request_context["connection"]

    try:
        # Create sample terrain data
        terrain_data = create_sample_terrain(
            size=size_m * 1000,  # Convert to mm
            spacing=spacing_m * 1000,
            slope=slope_deg,
            roughness=roughness_m * 1000,
        )

        # Generate mesh
        mesh = TerrainEngine.create_mesh_from_points(terrain_data)

        # Create in FreeCAD
        vertices_list = mesh.vertices.tolist()
        triangles_list = mesh.triangles.tolist()
        connection.create_terrain_mesh(vertices_list, triangles_list, object_name)

        # Apply slope colors if requested
        if apply_slope_colors:
            slope_map = TerrainEngine.analyze_slope(mesh)
            colors = slope_map.compute_heatmap_colors("slope")
            connection.set_face_colors(object_name, colors.tolist())

        # Get statistics
        stats = terrain_data.get_statistics()

        response = f"""✓ Sample terrain created

**Configuration:**
- Size: {size_m}m × {size_m}m
- Point spacing: {spacing_m}m
- Base slope: {slope_deg}°
- Roughness: ±{roughness_m}m

**Generated:**
- Points: {stats['num_points']:,}
- Mesh: {mesh.num_vertices:,} vertices, {mesh.num_faces:,} faces
- Elevation range: {stats['elevation_range_m']:.1f}m

Object: `{object_name}`
Color heatmap: {'Applied' if apply_slope_colors else 'Not applied'}
"""

        return [TextContent(type="text", text=response)]

    except Exception as e:
        return [TextContent(type="text", text=f"✗ Error creating sample terrain: {str(e)}")]
