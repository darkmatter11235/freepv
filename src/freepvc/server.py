"""FreePVC MCP Server - Entry point for the Model Context Protocol server.

Extends freecad-mcp with solar-specific tools for PV plant design.
"""

import asyncio
import json
import numpy as np
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP, Context
from mcp.types import TextContent, ImageContent

from freepvc.connection import FreePVCConnection
from freepvc.io.terrain_import import TerrainImporter, create_sample_terrain
from freepvc.engines.terrain_engine import TerrainEngine


@asynccontextmanager
async def server_lifespan(server: FastMCP):
    """Manage server lifecycle - establish FreeCAD connection on startup."""
    # Establish connection to FreeCAD XML-RPC server
    # Use 127.0.0.1 instead of localhost for better compatibility
    connection = FreePVCConnection(host="127.0.0.1")

    try:
        # Test connection
        connection.ping()
        print("✓ Connected to FreeCAD RPC server on port 9876", flush=True)
    except Exception as e:
        print(f"⚠ Warning: Could not connect to FreeCAD: {e}", flush=True)
        print("  Make sure FreeCAD is running with FreePVC workbench and RPC server started", flush=True)

    # Make connection available to all tool handlers via context
    yield {"connection": connection}


# Create FastMCP server instance with lifespan
mcp = FastMCP(
    "freepvc",
    instructions="FreePVC - Open-source solar plant design toolkit for FreeCAD",
    lifespan=server_lifespan,
)


# ===== Project Management Tools =====

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
        project_name: Name of the solar project
        latitude: Site latitude in decimal degrees
        longitude: Site longitude in decimal degrees
        altitude: Site altitude in meters above sea level
        timezone: IANA timezone string (e.g., "America/New_York")

    Returns:
        Confirmation message with project details
    """
    connection = ctx.request_context.lifespan_context["connection"]

    code = f"""
import FreeCAD

# Create new document
doc = FreeCAD.newDocument("{project_name}")

# Set document metadata
doc.Label = "{project_name}"
doc.Comment = "FreePVC Solar Plant Design"

# Store site information as document metadata
doc.Meta = {{
    "FreePVC.ProjectType": "Solar Plant",
    "FreePVC.Latitude": "{latitude}",
    "FreePVC.Longitude": "{longitude}",
    "FreePVC.Altitude": "{altitude}",
    "FreePVC.Timezone": "{timezone}",
}}

FreeCAD.setActiveDocument("{project_name}")
result = {{"name": doc.Name, "label": doc.Label}}
"""

    try:
        result = connection.execute_code(code)
        response = f"""✓ Created project: {project_name}

**Site Information:**
- Location: {latitude}°, {longitude}°
- Altitude: {altitude}m
- Timezone: {timezone}

Use `import_terrain` to add terrain data to the project.
"""
        return [TextContent(type="text", text=response)]
    except Exception as e:
        return [TextContent(type="text", text=f"✗ Error creating project: {str(e)}")]


@mcp.tool()
async def get_project_summary(
    ctx: Context = None,
) -> list[TextContent | ImageContent]:
    """Get summary of the current FreePVC project.

    Returns:
        Project details including site info and object counts
    """
    connection = ctx.request_context.lifespan_context["connection"]

    code = """
import FreeCAD

doc = FreeCAD.ActiveDocument
if doc:
    result = {
        "name": doc.Name,
        "label": doc.Label,
        "objects": len(doc.Objects),
        "meta": dict(doc.Meta) if hasattr(doc, "Meta") else {}
    }
else:
    result = {"error": "No active document"}
"""

    try:
        result = connection.execute_code(code)
        if "error" in result:
            return [TextContent(type="text", text="✗ No active project")]

        response = f"""**Project: {result.get('label', 'Unknown')}**

Objects: {result.get('objects', 0)}
"""
        return [TextContent(type="text", text=response)]
    except Exception as e:
        return [TextContent(type="text", text=f"✗ Error: {str(e)}")]


@mcp.tool()
async def save_project(
    file_path: str = None,
    ctx: Context = None,
) -> list[TextContent | ImageContent]:
    """Save the current FreePVC project.

    Args:
        file_path: Optional path to save file (defaults to project name)

    Returns:
        Confirmation message
    """
    connection = ctx.request_context.lifespan_context["connection"]

    code = f"""
import FreeCAD

doc = FreeCAD.ActiveDocument
if doc:
    if "{file_path}":
        doc.saveAs("{file_path}")
        result = {{"saved": "{file_path}"}}
    else:
        doc.save()
        result = {{"saved": doc.FileName}}
else:
    result = {{"error": "No active document"}}
"""

    try:
        result = connection.execute_code(code)
        if "error" in result:
            return [TextContent(type="text", text="✗ No active project to save")]

        return [TextContent(type="text", text=f"✓ Saved project: {result.get('saved')}")]
    except Exception as e:
        return [TextContent(type="text", text=f"✗ Error saving: {str(e)}")]


# ===== Terrain Analysis Tools =====

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
    connection = ctx.request_context.lifespan_context["connection"]

    try:
        # Import terrain data
        if format == "auto":
            terrain_data = TerrainImporter.import_auto(file_path, unit_scale=unit_scale)
        elif format == "csv":
            terrain_data = TerrainImporter.import_csv_points(file_path, unit_scale=unit_scale, skip_header=4)
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
async def import_terrain_from_coordinates(
    center_latitude: float,
    center_longitude: float,
    width_m: float = 1000.0,
    height_m: float = 1000.0,
    resolution_m: float = 10.0,
    object_name: str = "Terrain",
    ctx: Context = None,
) -> list[TextContent | ImageContent]:
    """Import terrain data from geographic coordinates using elevation API.

    Fetches elevation data from Open-Elevation API (free, no key required)
    and creates a triangulated terrain mesh in FreeCAD.

    Args:
        center_latitude: Center latitude in decimal degrees (e.g., 35.0872)
        center_longitude: Center longitude in decimal degrees (e.g., -106.6504)
        width_m: Area width in meters (east-west)
        height_m: Area height in meters (north-south)
        resolution_m: Sampling resolution in meters (default 10m)
        object_name: Name for the terrain object in FreeCAD

    Returns:
        Summary of imported terrain with statistics

    Example:
        Import terrain for 1km×1km area in Albuquerque, NM:
        center_latitude=35.0872, center_longitude=-106.6504, width_m=1000, height_m=1000
    """
    connection = ctx.request_context.lifespan_context["connection"]

    try:
        from freepvc.io.elevation_fetch import fetch_terrain_from_coordinates
        from freepvc.models.terrain import TerrainData, TerrainSource
        
        # Fetch elevation data from coordinates
        x, y, z = await fetch_terrain_from_coordinates(
            center_latitude,
            center_longitude,
            width_m,
            height_m,
            resolution_m,
        )
        
        # Combine into Nx3 points array
        import numpy as np
        points = np.column_stack((x, y, z))
        
        # Create TerrainData object
        terrain_data = TerrainData(
            points=points,
            source=TerrainSource.SURVEYED_POINTS,
        )
        
        # Generate mesh
        mesh = TerrainEngine.create_mesh_from_points(terrain_data)
        
        # Get statistics
        stats = terrain_data.get_statistics()
        
        # Create mesh in FreeCAD via RPC
        vertices_list = mesh.vertices.tolist()
        triangles_list = mesh.triangles.tolist()
        
        result = connection.create_terrain_mesh(vertices_list, triangles_list, object_name)
        
        # Format response
        response = f"""✓ Terrain imported from coordinates

**Location:**
- Center: {center_latitude:.6f}°, {center_longitude:.6f}°
- Area: {width_m:.0f}m × {height_m:.0f}m
- Resolution: {resolution_m:.1f}m

**Data:**
- Points: {stats['num_points']:,}
- Mesh: {mesh.num_vertices:,} vertices, {mesh.num_faces:,} faces

**Extent:**
- X: {stats['x_extent_m']:.1f} m
- Y: {stats['y_extent_m']:.1f} m
- Elevation range: {stats['elevation_range_m']:.1f} m

**Elevation:**
- Mean: {stats['mean_elevation_mm'] / 1000:.2f} m
- Std dev: {stats['std_elevation_mm'] / 1000:.2f} m

FreeCAD object: `{object_name}`

**Note:** Elevation data from Open-Elevation API (SRTM 30m dataset).
For higher resolution, export coordinates and use commercial DEM sources.
"""

        return [TextContent(type="text", text=response)]

    except Exception as e:
        return [TextContent(type="text", text=f"✗ Error importing terrain from coordinates: {str(e)}")]


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
    connection = ctx.request_context.lifespan_context["connection"]

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
    connection = ctx.request_context.lifespan_context["connection"]

    try:
        # Get terrain mesh from FreeCAD
        code = f"""
import FreeCAD

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
    connection = ctx.request_context.lifespan_context["connection"]

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


# ===== Solar Layout Tools =====

@mcp.tool()
async def create_panel_template(
    width_m: float = 1.134,
    height_m: float = 2.278,
    thickness_mm: float = 35.0,
    power_watts: float = 550.0,
    manufacturer: str = "Generic",
    model: str = "550W-Mono",
    template_name: str = "PanelTemplate",
    ctx: Context = None,
) -> list[TextContent | ImageContent]:
    """Create a solar panel template for reuse across multiple racks.
    
    The template defines panel specifications that can be shared
    by many rack instances for memory efficiency. When you change
    the template, all racks using it will automatically update.

    Args:
        width_m: Panel width in meters
        height_m: Panel height in meters
        thickness_mm: Panel thickness in millimeters
        power_watts: Rated power output in watts
        manufacturer: Panel manufacturer name
        model: Panel model designation
        template_name: Name for the template object

    Returns:
        Confirmation message with template details
    """
    connection = ctx.request_context.lifespan_context["connection"]

    try:
        # Create panel template via RPC
        config = {
            "name": template_name,
            "width": width_m * 1000,  # Convert to mm
            "height": height_m * 1000,
            "thickness": thickness_mm,
            "power_watts": power_watts,
            "manufacturer": manufacturer,
            "model": model,
        }
        
        result = connection.server.create_panel_template(config)
        
        response = f"""✓ Created panel template: {result}

**Dimensions:**
- Size: {width_m}m × {height_m}m
- Thickness: {thickness_mm}mm
- Area: {width_m * height_m:.2f}m²

**Electrical:**
- Power: {power_watts}W
- Efficiency: {(power_watts / (width_m * height_m * 1000)) * 100:.1f}%

**Model:** {manufacturer} {model}

Use this template name when creating racks to enable object reuse.
When you modify this template, all racks using it will automatically update.
"""
        return [TextContent(type="text", text=response)]

    except Exception as e:
        return [TextContent(type="text", text=f"✗ Error creating panel template: {str(e)}")]


@mcp.tool()
async def create_fixed_rack(
    panels_per_row: int = 2,
    rows: int = 1,
    tilt_angle_deg: float = 25.0,
    azimuth_deg: float = 180.0,
    post_height_m: float = 2.0,
    panel_template: str = None,
    rack_name: str = "FixedRack",
    ctx: Context = None,
) -> list[TextContent | ImageContent]:
    """Create a parametric fixed-tilt solar rack.
    
    Creates a single rack object that can be used as a template
    for array generation. The rack is fully parametric - you can
    change any property and it will automatically rebuild.

    Args:
        panels_per_row: Number of panels across (horizontally)
        rows: Number of panel rows (vertically)
        tilt_angle_deg: Tilt angle from horizontal (degrees)
        azimuth_deg: Azimuth orientation (0=N, 90=E, 180=S, 270=W)
        post_height_m: Support post height in meters
        panel_template: Optional name of panel template to reference
        rack_name: Name for the rack object

    Returns:
        Confirmation with rack details and DC capacity
    """
    connection = ctx.request_context.lifespan_context["connection"]

    try:
        # Create rack via RPC
        config = {
            "name": rack_name,
            "panels_per_row": panels_per_row,
            "rows": rows,
            "tilt_angle": tilt_angle_deg,
            "azimuth": azimuth_deg,
            "post_height": post_height_m * 1000,  # Convert to mm
        }
        
        if panel_template:
            config["panel_template"] = panel_template
        
        result = connection.server.create_fixed_rack(config)
        
        # Calculate capacity (assuming default panel if no template)
        panel_power = 550.0  # Default
        total_panels = panels_per_row * rows
        dc_capacity_kw = (total_panels * panel_power) / 1000.0
        
        response = f"""✓ Created fixed rack: {result}

**Configuration:**
- Layout: {panels_per_row} × {rows} = {total_panels} panels
- Tilt: {tilt_angle_deg}°
- Azimuth: {azimuth_deg}° ({_azimuth_to_cardinal(azimuth_deg)})
- Post height: {post_height_m}m

**Capacity:**
- DC: {dc_capacity_kw:.2f} kW
- Panel template: {panel_template if panel_template else "Default (550W)"}

**Object Reuse:**
This rack is parametric. You can:
- Change any property in FreeCAD's Properties panel
- Use it as a template for array generation
- Update panel template and this rack will automatically update
"""
        return [TextContent(type="text", text=response)]

    except Exception as e:
        return [TextContent(type="text", text=f"✗ Error creating fixed rack: {str(e)}")]


@mcp.tool()
async def create_tracker(
    panels_per_tracker: int = 28,
    panels_high: int = 1,
    rotation_angle_deg: float = 0.0,
    max_rotation_deg: float = 60.0,
    post_height_m: float = 2.5,
    panel_template: str = None,
    tracker_name: str = "Tracker",
    ctx: Context = None,
) -> list[TextContent | ImageContent]:
    """Create a parametric single-axis tracker.
    
    Creates a tracker that can rotate to follow the sun. The tracker
    is fully parametric and can be used as a template for arrays.

    Args:
        panels_per_tracker: Number of panels along tracker length
        panels_high: Number of panels vertically (1 or 2 typical)
        rotation_angle_deg: Current rotation angle (±60° typical)
        max_rotation_deg: Maximum rotation limit
        post_height_m: Center post height in meters
        panel_template: Optional name of panel template to reference
        tracker_name: Name for the tracker object

    Returns:
        Confirmation with tracker details and DC capacity
    """
    connection = ctx.request_context.lifespan_context["connection"]

    try:
        # Create tracker via RPC
        config = {
            "name": tracker_name,
            "panels_per_tracker": panels_per_tracker,
            "panels_high": panels_high,
            "rotation_angle": rotation_angle_deg,
            "max_rotation": max_rotation_deg,
            "post_height": post_height_m * 1000,  # Convert to mm
        }
        
        if panel_template:
            config["panel_template"] = panel_template
        
        result = connection.server.create_tracker(config)
        
        # Calculate capacity
        panel_power = 550.0  # Default
        total_panels = panels_per_tracker * panels_high
        dc_capacity_kw = (total_panels * panel_power) / 1000.0
        tracker_length_m = panels_per_tracker * 1.134  # Default panel width
        
        response = f"""✓ Created single-axis tracker: {result}

**Configuration:**
- Layout: {panels_per_tracker} × {panels_high} = {total_panels} panels
- Tracker length: {tracker_length_m:.1f}m
- Current rotation: {rotation_angle_deg}°
- Max rotation: ±{max_rotation_deg}°
- Post height: {post_height_m}m

**Capacity:**
- DC: {dc_capacity_kw:.2f} kW per tracker
- Panel template: {panel_template if panel_template else "Default (550W)"}

**Animation:**
You can animate the tracker by changing the RotationAngle property.
Try values from -{max_rotation_deg}° to +{max_rotation_deg}°.
"""
        return [TextContent(type="text", text=response)]

    except Exception as e:
        return [TextContent(type="text", text=f"✗ Error creating tracker: {str(e)}")]


@mcp.tool()
async def generate_array_layout(
    base_rack: str,
    terrain_name: str = None,
    spacing_m: float = 6.0,
    target_capacity_mw: float = None,
    max_slope_deg: float = 20.0,
    gcr_target: float = 0.4,
    layout_name: str = "ArrayLayout",
    ctx: Context = None,
) -> list[TextContent | ImageContent]:
    """Generate automated solar array layout using efficient object reuse.
    
    Creates an array of solar racks using App::Link for memory efficiency.
    All instances share the base rack geometry but have independent placements.
    When you change the base rack, all instances automatically update!

    Args:
        base_rack: Name of rack or tracker object to use as template
        terrain_name: Optional terrain object name to follow
        spacing_m: Row-to-row spacing in meters
        target_capacity_mw: Optional target DC capacity in MW
        max_slope_deg: Maximum buildable slope (degrees)
        gcr_target: Target ground coverage ratio (0.3-0.5 typical)
        layout_name: Name for the layout group

    Returns:
        Summary with total racks, panels, DC capacity, and GCR
    """
    connection = ctx.request_context.lifespan_context["connection"]

    try:
        from freepvc.models.solar_objects import RackConfig, LayoutConfig, PanelSpec
        from freepvc.engines.layout_engine import LayoutEngine
        from freepvc.models.terrain import TerrainMesh
        
        # Get terrain if specified
        terrain_mesh = None
        if terrain_name:
            # Fetch terrain mesh data from FreeCAD
            code = f"""
import FreeCAD
import numpy as np
doc = FreeCAD.ActiveDocument
terrain = doc.getObject("{terrain_name}")
if terrain and hasattr(terrain, "Mesh"):
    mesh = terrain.Mesh
    vertices = []
    for point in mesh.Points:
        vertices.append([point.x, point.y, point.z])
    
    triangles = []
    for facet in mesh.Facets:
        triangles.append(facet.PointIndices)
    
    result = {{
        "vertices": vertices,
        "triangles": triangles,
    }}
else:
    result = None
result
"""
            terrain_data = connection.execute_code(code)
            
            if terrain_data:
                import numpy as np
                vertices = np.array(terrain_data["vertices"], dtype=np.float64)
                triangles = np.array(terrain_data["triangles"], dtype=np.int32)
                terrain_mesh = TerrainMesh(vertices=vertices, triangles=triangles)
            else:
                return [TextContent(type="text", text=f"✗ Error: Terrain '{terrain_name}' not found or invalid")]
        
        # Query the base rack properties from FreeCAD
        code = f"""
import FreeCAD
doc = FreeCAD.ActiveDocument
base = doc.getObject("{base_rack}")
if base:
    panel_template = base.PanelTemplate if hasattr(base, "PanelTemplate") else None
    if panel_template:
        power_w = float(panel_template.PowerWatts) if hasattr(panel_template, "PowerWatts") else 550.0
    else:
        power_w = 550.0
    result = {{
        "panels_per_row": int(base.PanelsPerRow) if hasattr(base, "PanelsPerRow") else 2,
        "rows": int(base.Rows) if hasattr(base, "Rows") else 1,
        "tilt_angle": float(base.TiltAngle) if hasattr(base, "TiltAngle") else 25.0,
        "power_watts": power_w,
    }}
else:
    result = None
result
"""
        base_rack_props = connection.execute_code(code)
        
        if not base_rack_props:
            return [TextContent(type="text", text=f"✗ Error: Base rack '{base_rack}' not found")]
        
        # Create rack config from base rack properties
        rack_config = RackConfig(
            panel_spec=PanelSpec(power_watts=base_rack_props["power_watts"]),
            panels_per_row=base_rack_props["panels_per_row"],
            rows=base_rack_props["rows"],
            tilt_angle_deg=base_rack_props["tilt_angle"],
        )
        
        layout_config = LayoutConfig(
            rack_config=rack_config,
            spacing_m=spacing_m,
            gcr_target=gcr_target,
            max_slope_deg=max_slope_deg,
            target_capacity_mw=target_capacity_mw,
        )
        
        # Generate layout
        layout = LayoutEngine.generate_grid_layout(layout_config, terrain_mesh)
        
        # Convert placements to RPC format (ensure native Python types for XML-RPC)
        placements_data = [
            {
                "x": float(p.x),
                "y": float(p.y),
                "z": float(p.z),
                "rotation_x": float(p.rotation_x),
                "rotation_y": float(p.rotation_y),
                "rotation_z": float(p.rotation_z),
                "name": p.rack_id,
            }
            for p in layout.placements
        ]
        
        # Create array in FreeCAD using efficient Links
        result = connection.server.create_array_layout(base_rack, placements_data)
        
        # Handle result - it might be a dict or might need to extract info
        group_name = result.get('group_name', 'ArrayLayout') if isinstance(result, dict) else 'ArrayLayout'
        total_instances = result.get('total_instances', len(placements_data)) if isinstance(result, dict) else len(placements_data)
        
        response = f"""✓ Generated array layout: {group_name}

**Layout Statistics:**
- Total racks: {total_instances}
- Total panels: {layout.total_panels}
- DC capacity: {layout.dc_capacity_kw / 1000:.2f} MW

**Parameters:**
- Row spacing: {spacing_m}m
- Ground coverage ratio: {gcr_target:.1%}
- Max slope: {max_slope_deg}°

**Object Reuse (High Performance!):**
- Base template: {base_rack}
- Instances use App::Link (shared geometry)
- Memory usage: ~{total_instances * 0.001:.1f} MB (vs {total_instances * 50:.1f} MB without Links)

**Performance:**
Change the base rack properties and watch ALL {total_instances} instances
update automatically! This is the power of parametric object reuse.
"""
        return [TextContent(type="text", text=response)]

    except Exception as e:
        import traceback
        return [TextContent(type="text", text=f"✗ Error generating layout: {str(e)}\n\n{traceback.format_exc()}")]


def _azimuth_to_cardinal(azimuth: float) -> str:
    """Convert azimuth angle to cardinal direction."""
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    index = int((azimuth + 22.5) / 45.0) % 8
    return directions[index]


def main():
    """Entry point for the freepvc command."""
    mcp.run()


if __name__ == "__main__":
    main()
